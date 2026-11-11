package com.star.agent.infra.crypto;

import com.star.agent.infra.config.AppConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * 字段级加密：敏感字段（猎聘 Token、微信 botToken、会话恢复上下文）落库前加密，读出来再解密。
 *
 * <p>算法：AES-256-GCM（认证加密）。GCM 自带完整性校验，密文被篡改会在解密时直接抛异常，
 * 而不是解出一段垃圾明文继续往下跑。
 *
 * <p>密文格式：{@code enc:v1:<base64url(iv || ciphertext || tag)>}
 * <ul>
 *   <li>12 字节 IV，每条密文随机生成（同明文两次加密结果不同，避免可比对）</li>
 *   <li>128 位认证标签</li>
 *   <li>前缀带版本号：将来换算法/换密钥可以按前缀分流，老数据继续能读</li>
 * </ul>
 *
 * <p>为什么带 AAD：把"字段身份"绑进密文。这样 user_config 的密文不能被拷到 wechat_session
 * 去冒充，也不能拿 A 字段的密文解出 B 字段的内容——防止跨字段搬运攻击。
 *
 * <p>向后兼容：库里已存在的历史明文（没有前缀）读的时候原样返回，写入时一律加密。
 * 存量数据靠 {@link CryptoMigrationRunner} 刷一遍，不阻塞上线。
 */
@Component
public class FieldCipher {

    private static final Logger logger = LoggerFactory.getLogger(FieldCipher.class);

    /** 密文前缀，同时充当版本号 */
    public static final String PREFIX = "enc:v1:";

    /** AAD：字段身份，防止跨字段/跨表搬运密文 */
    public static final String AAD_USER_LIEPIN_TOKEN = "user_config.liepin_token";
    public static final String AAD_WECHAT_BOT_TOKEN = "wechat_session.bot_token";
    public static final String AAD_WECHAT_RESUME_JSON = "wechat_session.resume_json";

    private static final String TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int IV_LENGTH = 12;
    private static final int TAG_BITS = 128;
    private static final String KEY_SALT = "linkagent.field.v1|";

    private static final SecureRandom RANDOM = new SecureRandom();
    private static final Base64.Encoder ENCODER = Base64.getUrlEncoder().withoutPadding();
    private static final Base64.Decoder DECODER = Base64.getUrlDecoder();

    private final SecretKeySpec key;

    /** Spring 用：从配置解析密钥 */
    @Autowired
    public FieldCipher(AppConfig appConfig) {
        this(resolveKeyMaterial(appConfig));
    }

    /** 测试/脚本用：直接给一段口令（内部仍走 SHA-256 派生，保证 32 字节） */
    public FieldCipher(String rawKeyMaterial) {
        this.key = new SecretKeySpec(sha256(KEY_SALT + rawKeyMaterial), "AES");
    }

    /**
     * 密钥来源优先级：FIELD_ENCRYPTION_KEY > JWT_SECRET > 进程内临时随机。
     * 临时随机只用于没配密钥的本地/CI 环境，必须吵醒人——重启后历史密文就解不开了。
     */
    private static String resolveKeyMaterial(AppConfig config) {
        String dedicated = config.fieldEncryptionKey();
        if (dedicated != null && !dedicated.isBlank()) {
            logger.info("字段加密已启用：密钥来源 FIELD_ENCRYPTION_KEY（指纹 {}）", fingerprint(dedicated));
            return dedicated;
        }
        String jwtSecret = config.jwtSecret();
        if (jwtSecret != null && !jwtSecret.isBlank()) {
            logger.warn("未配置 FIELD_ENCRYPTION_KEY，回退用 JWT_SECRET 派生字段密钥（指纹 {}）。"
                    + "注意：更换 JWT_SECRET 会导致已加密的历史数据无法解密，生产建议单独配置 FIELD_ENCRYPTION_KEY。",
                    fingerprint(jwtSecret));
            return jwtSecret;
        }
        String ephemeral = Base64.getEncoder().encodeToString(randomBytes(32));
        logger.warn("未配置 FIELD_ENCRYPTION_KEY / JWT_SECRET，使用进程内临时密钥（指纹 {}）。"
                + "仅适用于测试环境，重启后历史密文将无法解密。", fingerprint(ephemeral));
        return ephemeral;
    }

    /** 是否已是本组件产出的密文 */
    public boolean isEncrypted(String value) {
        return value != null && value.startsWith(PREFIX);
    }

    /**
     * 加密。null 原样返回；已加密的值幂等返回（避免重复加密）。
     *
     * @param aad 字段身份，用本类的 AAD_* 常量
     */
    public String encrypt(String plain, String aad) {
        if (plain == null) {
            return null;
        }
        if (isEncrypted(plain)) {
            return plain;
        }
        try {
            byte[] iv = randomBytes(IV_LENGTH);
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
            cipher.updateAAD(aad.getBytes(StandardCharsets.UTF_8));

            byte[] encrypted = cipher.doFinal(plain.getBytes(StandardCharsets.UTF_8));
            byte[] payload = new byte[iv.length + encrypted.length];
            System.arraycopy(iv, 0, payload, 0, iv.length);
            System.arraycopy(encrypted, 0, payload, iv.length, encrypted.length);
            return PREFIX + ENCODER.encodeToString(payload);
        } catch (GeneralSecurityException e) {
            // 加密失败属于环境/密钥问题，必须让调用方知道，绝不静默降级成明文入库
            throw new IllegalStateException("字段加密失败", e);
        }
    }

    /**
     * 解密。null 或历史明文原样返回（双读兼容）；密文损坏/密钥不匹配直接抛异常（失败关闭）。
     *
     * @param aad 必须与加密时一致，否则认证失败
     */
    public String decrypt(String stored, String aad) {
        if (stored == null || !isEncrypted(stored)) {
            return stored;
        }
        try {
            byte[] payload = DECODER.decode(stored.substring(PREFIX.length()));
            if (payload.length <= IV_LENGTH) {
                throw new IllegalStateException("密文长度非法");
            }
            byte[] iv = new byte[IV_LENGTH];
            System.arraycopy(payload, 0, iv, 0, IV_LENGTH);

            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
            cipher.updateAAD(aad.getBytes(StandardCharsets.UTF_8));

            byte[] plain = cipher.doFinal(payload, IV_LENGTH, payload.length - IV_LENGTH);
            return new String(plain, StandardCharsets.UTF_8);
        } catch (GeneralSecurityException | IllegalArgumentException e) {
            throw new IllegalStateException("字段解密失败（密钥不匹配或密文被篡改）", e);
        }
    }

    private static byte[] sha256(String text) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8));
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("SHA-256 不可用", e);
        }
    }

    private static byte[] randomBytes(int len) {
        byte[] bytes = new byte[len];
        RANDOM.nextBytes(bytes);
        return bytes;
    }

    /** 只打印后 4 位，用于确认"用的是哪把钥匙"，不泄露密钥本身 */
    private static String fingerprint(String key) {
        return (key == null || key.length() < 4) ? "无" : key.substring(key.length() - 4);
    }
}
