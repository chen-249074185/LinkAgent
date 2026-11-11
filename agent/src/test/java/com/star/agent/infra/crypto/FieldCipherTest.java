package com.star.agent.infra.crypto;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

// 字段加密单测：加解密往返、随机 IV、AAD 绑定、篡改检测、历史明文兼容
class FieldCipherTest {

    private final FieldCipher cipher = new FieldCipher("unit-test-key-please-change");
    private static final String AAD = FieldCipher.AAD_USER_LIEPIN_TOKEN;

    @Test
    void roundTrip_returnsOriginal() {
        String plain = "jwt-token-abcdef-123456";

        String stored = cipher.encrypt(plain, AAD);

        assertNotEquals(plain, stored, "密文不能等于明文");
        assertTrue(stored.startsWith(FieldCipher.PREFIX), "密文必须带版本前缀");
        assertEquals(plain, cipher.decrypt(stored, AAD));
    }

    @Test
    void chineseAndLongText_roundTrip() {
        String plain = "中文 Token 也要能加密：" + "内容".repeat(500);

        String stored = cipher.encrypt(plain, FieldCipher.AAD_WECHAT_RESUME_JSON);

        assertEquals(plain, cipher.decrypt(stored, FieldCipher.AAD_WECHAT_RESUME_JSON));
    }

    @Test
    void nullAndEmpty_areSafe() {
        assertNull(cipher.encrypt(null, AAD));
        assertNull(cipher.decrypt(null, AAD));
        assertEquals("", cipher.decrypt(cipher.encrypt("", AAD), AAD));
    }

    @Test
    void encrypt_isIdempotent() {
        String once = cipher.encrypt("token-A", AAD);

        assertEquals(once, cipher.encrypt(once, AAD), "已加密的值不能被二次加密");
    }

    @Test
    void legacyPlaintext_passesThrough() {
        // 库里历史数据没有前缀，必须原样返回，否则老用户升级后配置全丢
        assertEquals("old-plain-token", cipher.decrypt("old-plain-token", AAD));
        assertFalse(cipher.isEncrypted("old-plain-token"));
    }

    @Test
    void samePlaintext_producesDifferentCiphertext() {
        String a = cipher.encrypt("same", AAD);
        String b = cipher.encrypt("same", AAD);

        assertNotEquals(a, b, "随机 IV：同明文两次加密结果必须不同");
        assertEquals("same", cipher.decrypt(a, AAD));
        assertEquals("same", cipher.decrypt(b, AAD));
    }

    @Test
    void wrongAad_cannotDecrypt() {
        String stored = cipher.encrypt("token-A", FieldCipher.AAD_USER_LIEPIN_TOKEN);

        // 跨字段搬运密文必须失败：把 user_config 的密文塞进 wechat_session 解不出来
        assertThrows(IllegalStateException.class,
                () -> cipher.decrypt(stored, FieldCipher.AAD_WECHAT_BOT_TOKEN));
    }

    @Test
    void tamperedCiphertext_failsClosed() {
        String stored = cipher.encrypt("token-A", AAD);

        // 精确篡改密文最后一个字节（落在 GCM tag 里），保证认证一定失败；
        // 不能靠翻转 base64 末位字符——末位的低位可能是填充位，翻了等于没翻（会假通过）
        byte[] payload = java.util.Base64.getUrlDecoder()
                .decode(stored.substring(FieldCipher.PREFIX.length()));
        payload[payload.length - 1] ^= 0x01;
        String tampered = FieldCipher.PREFIX
                + java.util.Base64.getUrlEncoder().withoutPadding().encodeToString(payload);

        assertThrows(IllegalStateException.class, () -> cipher.decrypt(tampered, AAD));
    }

    @Test
    void differentKeys_cannotDecryptEachOther() {
        FieldCipher other = new FieldCipher("another-key");
        String stored = other.encrypt("token-A", AAD);

        assertThrows(IllegalStateException.class, () -> cipher.decrypt(stored, AAD));
    }
}
