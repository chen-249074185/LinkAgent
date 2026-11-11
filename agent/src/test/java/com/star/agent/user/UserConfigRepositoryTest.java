package com.star.agent.user;

import com.star.agent.infra.crypto.FieldCipher;
import com.star.agent.user.dao.UserConfigDao;
import com.star.agent.user.domain.UserConfigDo;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

// 用户配置仓库集成测试（真实 MySQL user_config 表）：
// 每用户 Token 隔离（u1 存的不影响 u2）、覆盖更新、未配置 null
@SpringBootTest(properties = "linkagent.wechat.bot-enabled=false")
class UserConfigRepositoryTest {

    @Autowired
    UserConfigRepository repository;

    @Autowired
    UserConfigDao dao;

    @AfterEach
    void tearDown() {
        dao.deleteByUserId("itest:cfg1");
        dao.deleteByUserId("itest:cfg2");
    }

    @Test
    void saveAndFind_roundTrip() {
        repository.saveLiepinToken("itest:cfg1", "token-A");

        assertEquals("token-A", repository.findLiepinToken("itest:cfg1"));
    }

    // 每用户隔离：u1 配了自己的，u2 查不到（绝不串号）
    @Test
    void userIsolation_otherUserCannotRead() {
        repository.saveLiepinToken("itest:cfg1", "token-A");

        assertNull(repository.findLiepinToken("itest:cfg2"), "未配置的用户查不到别人 Token");
    }

    @Test
    void saveAgain_overwrites() {
        repository.saveLiepinToken("itest:cfg1", "old");
        repository.saveLiepinToken("itest:cfg1", "new");

        assertEquals("new", repository.findLiepinToken("itest:cfg1"));
    }

    @Test
    void noConfig_returnsNull() {
        assertNull(repository.findLiepinToken("no-such-user"));
    }

    // 删除配置：删后查不到（Web/小程序"删除配置"按钮的仓库支撑）
    @Test
    void deleteLiepinToken_removesConfig() {
        repository.saveLiepinToken("itest:cfg1", "token-A");

        repository.deleteLiepinToken("itest:cfg1");

        assertNull(repository.findLiepinToken("itest:cfg1"), "删除后应查不到");
    }

    // 落库加密：库里不能出现明文，且必须是带版本前缀的密文
    @Test
    void savedValue_isEncryptedAtRest() {
        repository.saveLiepinToken("itest:cfg1", "token-plain");

        String stored = dao.findByUserId("itest:cfg1").getLiepinToken();

        assertNotEquals("token-plain", stored, "库里不允许出现明文 Token");
        assertTrue(stored.startsWith(FieldCipher.PREFIX), "库里应是 enc:v1: 前缀的密文");
        assertEquals("token-plain", repository.findLiepinToken("itest:cfg1"), "读出来必须能还原");
    }

    // 历史明文兼容：升级前写进去的明文，读的时候原样返回，并顺手刷成密文（读路径自愈）
    @Test
    void legacyPlaintext_isMigratedOnRead() {
        UserConfigDo row = new UserConfigDo();
        row.setUserId("itest:cfg1");
        row.setLiepinToken("legacy-plain");   // 模拟加密上线前的历史数据
        dao.upsert(row);

        assertEquals("legacy-plain", repository.findLiepinToken("itest:cfg1"), "历史明文仍要能读");

        String after = dao.findByUserId("itest:cfg1").getLiepinToken();
        assertTrue(after.startsWith(FieldCipher.PREFIX), "读过一次后应自动迁移成密文");
        assertEquals("legacy-plain", repository.findLiepinToken("itest:cfg1"));
    }
}