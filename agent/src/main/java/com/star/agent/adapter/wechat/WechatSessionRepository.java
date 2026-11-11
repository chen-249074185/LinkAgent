package com.star.agent.adapter.wechat;
import com.star.agent.adapter.wechat.dao.WechatSessionDao;
import com.star.agent.adapter.wechat.domain.WechatSessionDo;
import com.star.agent.infra.crypto.FieldCipher;

import com.github.wechat.ilink.sdk.core.context.ResumeContext;
import com.github.wechat.ilink.sdk.core.login.LoginContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.List;

// 微信会话仓库（数据库版）：wechat_session 表读写 ResumeContext
// 语义与文件版 SessionStore 一致（save/load），Spring 链路用数据库版，手动 main 链路用文件版
// ResumeContext 的 JSON 编解码复用 SessionStore.toJson/fromJson（单一来源防逻辑漂移）
// bot_token 和 resume_json（内含 botToken）都是凭据，落库前用 FieldCipher 加密
@Component
public class WechatSessionRepository {

    private static final Logger logger = LoggerFactory.getLogger(WechatSessionRepository.class);

    private final WechatSessionDao mapper;
    private final FieldCipher cipher;

    public WechatSessionRepository(WechatSessionDao mapper, FieldCipher cipher) {
        this.mapper = mapper;
        this.cipher = cipher;
    }

    // 保存会话（登录后调用）：bot_id 唯一键，同 bot 重复登录=顶号覆盖
    public void save(ResumeContext ctx) {
        LoginContext lc = ctx.getLoginContext();
        WechatSessionDo s = new WechatSessionDo();
        s.setBotId(lc.getBotId());
        s.setUserId(lc.getUserId());
        s.setBotToken(cipher.encrypt(lc.getBotToken(), FieldCipher.AAD_WECHAT_BOT_TOKEN));
        try {
            s.setResumeJson(cipher.encrypt(SessionStore.toJson(ctx), FieldCipher.AAD_WECHAT_RESUME_JSON));
        } catch (IOException e) {
            throw new IllegalStateException("会话序列化失败", e);
        }
        mapper.upsert(s);
    }

    // 恢复会话（免扫码用）；无记录或 JSON 损坏 → null（调用方转扫码）
    // 历史明文 resume_json（没有 enc:v1: 前缀）照样能读，并顺手刷成密文
    public ResumeContext load(String botId) {
        WechatSessionDo s = mapper.findByBotId(botId);
        if (s == null || s.getResumeJson() == null) {
            return null;
        }
        String stored = s.getResumeJson();
        if (!cipher.isEncrypted(stored)) {
            try {
                mapper.upsert(reencrypt(s));
                logger.info("历史明文微信会话已迁移为密文: botId={}", botId);
            } catch (RuntimeException e) {
                logger.warn("历史明文微信会话迁移失败，本次按明文读取: botId={}", botId, e);
            }
            return SessionStore.fromJson(stored);
        }
        return SessionStore.fromJson(cipher.decrypt(stored, FieldCipher.AAD_WECHAT_RESUME_JSON));
    }

    // 把一行历史明文刷成密文（不改 botId/userId/saved_at 语义）
    private WechatSessionDo reencrypt(WechatSessionDo old) {
        WechatSessionDo fresh = new WechatSessionDo();
        fresh.setBotId(old.getBotId());
        fresh.setUserId(old.getUserId());
        fresh.setBotToken(cipher.encrypt(old.getBotToken(), FieldCipher.AAD_WECHAT_BOT_TOKEN));
        fresh.setResumeJson(cipher.encrypt(old.getResumeJson(), FieldCipher.AAD_WECHAT_RESUME_JSON));
        return fresh;
    }

    // 全部 botId（启动扫表多 Bot 恢复用）
    public List<String> findAllBotIds() {
        return mapper.findAll().stream().map(WechatSessionDo::getBotId).toList();
    }

    // 同微信只保留最新会话的 botId（启动恢复用，防同微信多 botId 顶号）：
    // 微信扫码换 bot 会生成新 botId，若旧 botId 会话没删干净，重启会同时恢复两个 Bot 连同一微信
    // → 一个微信一个 Bot 原则：按 user_id 分组，只留 saved_at 最新的那个
    public List<String> findLatestBotIds() {
        return mapper.findAll().stream()
                .collect(java.util.stream.Collectors.groupingBy(
                        WechatSessionDo::getUserId,   // 按微信身份分组
                        java.util.stream.Collectors.maxBy(
                                java.util.Comparator.comparing(s -> s.getSavedAt() == null
                                        ? java.time.LocalDateTime.MIN : s.getSavedAt()))))
                .values().stream()
                .filter(java.util.Optional::isPresent)
                .map(java.util.Optional::get)
                .map(WechatSessionDo::getBotId)
                .toList();
    }

    // 删除某 bot 的会话（登出命令/测试清理用）
    public void delete(String botId) {
        mapper.deleteByBotId(botId);
    }

    // 删除某微信身份的全部旧会话（扫码确认换 Bot 时清被顶掉的旧 bot，避免重启恢复一堆失效会话）
    public void deleteByUserId(String userId) {
        mapper.deleteByUserId(userId);
    }

    // 删除 saved_at 早于 days 天前的会话（过期清理）；返回删除条数
    public int deleteOlderThan(int days) {
        return mapper.deleteOlderThan(LocalDateTime.now().minusDays(days));
    }

    // 改某条会话的保存时间（测试造"旧数据"用）
    public void updateSavedAt(String botId, LocalDateTime savedAt) {
        mapper.updateSavedAt(botId, savedAt);
    }

    // 会话总数（统计/调试）
    public long count() {
        return mapper.count();
    }
}