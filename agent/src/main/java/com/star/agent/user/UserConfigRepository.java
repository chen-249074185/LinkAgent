package com.star.agent.user;

import com.star.agent.infra.crypto.FieldCipher;
import com.star.agent.user.dao.UserConfigDao;
import com.star.agent.user.domain.UserConfigDo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

// 用户配置仓库：user_config 表读写（当前存猎聘 Token，按 userId 隔离——每用户自己的猎聘账号）
// 落库前用 FieldCipher 做 AES-256-GCM 加密，库里只有密文；读取时解密，历史明文双读并顺手迁移
@Component
public class UserConfigRepository {

    private static final Logger logger = LoggerFactory.getLogger(UserConfigRepository.class);

    private final UserConfigDao dao;
    private final FieldCipher cipher;

    public UserConfigRepository(UserConfigDao dao, FieldCipher cipher) {
        this.dao = dao;
        this.cipher = cipher;
    }

    // 保存某用户的猎聘 Token（只写该用户自己的行，别人覆盖不了）；强制加密后入库
    public void saveLiepinToken(String userId, String token) {
        UserConfigDo c = new UserConfigDo();
        c.setUserId(userId);
        c.setLiepinToken(cipher.encrypt(token, FieldCipher.AAD_USER_LIEPIN_TOKEN));
        dao.upsert(c);
    }

    // 取某用户的猎聘 Token；未配置 → null（调用方引导配置，绝不回退用别人的）
    // 历史明文（没有 enc:v1: 前缀）原样返回，并顺手刷成密文——读路径自愈，不需要停机迁移
    public String findLiepinToken(String userId) {
        UserConfigDo c = dao.findByUserId(userId);
        if (c == null || c.getLiepinToken() == null) {
            return null;
        }
        String stored = c.getLiepinToken();
        if (!cipher.isEncrypted(stored)) {
            try {
                saveLiepinToken(userId, stored);
                logger.info("历史明文猎聘 Token 已迁移为密文: userId={}", userId);
            } catch (RuntimeException e) {
                // 迁移失败不能影响本次读取，否则用户会莫名其妙"配置丢失"
                logger.warn("历史明文猎聘 Token 迁移失败，本次按明文返回: userId={}", userId, e);
            }
            return stored;
        }
        return cipher.decrypt(stored, FieldCipher.AAD_USER_LIEPIN_TOKEN);
    }

    // 删除某用户的猎聘 Token（用户注销/不再使用猎聘时，Web/小程序"删除配置"按钮）
    public void deleteLiepinToken(String userId) {
        dao.deleteByUserId(userId);
    }

    // 查配置状态（Web/小程序"我的配置"页展示用：是否已配置 + 更新时间，不暴露 Token 明文）
    // 注意：这里返回的 liepinToken 是密文，调用方只应判空，不要当明文使用
    public UserConfigDo findByUserId(String userId) {
        return dao.findByUserId(userId);
    }

    // 账号合并：猎聘 Token 改归另一用户（调用方先判目标有无，有则删源，无则迁）
    // 直接搬密文即可，AAD 只绑字段不绑用户，换 user_id 不影响解密
    public void transferLiepinToken(String fromUserId, String toUserId) {
        dao.transferUserId(fromUserId, toUserId);
    }
}
