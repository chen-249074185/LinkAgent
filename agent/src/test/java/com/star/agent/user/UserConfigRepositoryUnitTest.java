package com.star.agent.user;

import com.star.agent.infra.crypto.FieldCipher;
import com.star.agent.user.dao.UserConfigDao;
import com.star.agent.user.domain.UserConfigDo;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

// 仓库层加解密单测（不连数据库）：验证写进 DAO 的到底是什么、读出来能不能还原
class UserConfigRepositoryUnitTest {

    private final UserConfigDao dao = mock(UserConfigDao.class);
    private final FieldCipher cipher = new FieldCipher("unit-test-key");
    private final UserConfigRepository repository = new UserConfigRepository(dao, cipher);

    @Test
    void save_writesCiphertextToDao() {
        repository.saveLiepinToken("u1", "plain-token");

        ArgumentCaptor<UserConfigDo> captor = ArgumentCaptor.forClass(UserConfigDo.class);
        verify(dao).upsert(captor.capture());

        String stored = captor.getValue().getLiepinToken();
        assertNotEquals("plain-token", stored, "写进 DAO 的不能是明文");
        assertTrue(stored.startsWith(FieldCipher.PREFIX), "写进 DAO 的应是密文");
        assertEquals("u1", captor.getValue().getUserId());
    }

    @Test
    void find_decryptsCiphertext() {
        UserConfigDo row = new UserConfigDo();
        row.setUserId("u1");
        row.setLiepinToken(cipher.encrypt("plain-token", FieldCipher.AAD_USER_LIEPIN_TOKEN));
        when(dao.findByUserId("u1")).thenReturn(row);

        assertEquals("plain-token", repository.findLiepinToken("u1"));
        verify(dao, never()).upsert(any());   // 已是密文，不应触发迁移写回
    }

    @Test
    void find_legacyPlaintext_returnsAndMigrates() {
        UserConfigDo row = new UserConfigDo();
        row.setUserId("u1");
        row.setLiepinToken("legacy-plain");   // 加密上线前的历史数据
        when(dao.findByUserId("u1")).thenReturn(row);

        assertEquals("legacy-plain", repository.findLiepinToken("u1"), "历史明文必须还能读");

        ArgumentCaptor<UserConfigDo> captor = ArgumentCaptor.forClass(UserConfigDo.class);
        verify(dao).upsert(captor.capture());  // 顺手迁移
        assertTrue(captor.getValue().getLiepinToken().startsWith(FieldCipher.PREFIX));
    }

    @Test
    void find_missing_returnsNull() {
        when(dao.findByUserId("nobody")).thenReturn(null);

        assertNull(repository.findLiepinToken("nobody"));
    }
}
