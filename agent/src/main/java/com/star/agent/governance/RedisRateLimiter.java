package com.star.agent.governance;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicLong;

// 限次：Redis 版实现（正式版），key 走 RedisKeys 规范
// 跨天清零靠 TTL：第一次计数时把 key 的过期时间设到"明天零点"，到点 Redis 自动删，天然重计
// 降级：Redis 不可用（未启动/网络断）时自动退回内存计数，限流只是辅助能力，不能因此把对话打挂
@Component
@ConditionalOnProperty(name = "linkagent.redis-enabled", havingValue = "true")
public class RedisRateLimiter implements RateLimiter {

    private static final Logger logger = LoggerFactory.getLogger(RedisRateLimiter.class);
    private static final long WARN_INTERVAL_MS = 60_000L;   // 同类告警最多每分钟打一条，避免刷屏

    private final StringRedisTemplate redis;
    private final InMemoryRateLimiter fallback = new InMemoryRateLimiter();   // Redis 挂了的兜底账本
    private final AtomicLong lastWarnAt = new AtomicLong(0);

    public RedisRateLimiter(StringRedisTemplate redis) {
        this.redis = redis;
    }

    @Override
    public int increment(String key) {
        try {
            // INCR 原子自增：并发下也不会加错（比内存版 Map 更可靠）
            Long count = redis.opsForValue().increment(RedisKeys.rate(key));
            if (count != null && count == 1) {
                // 首次计数：设 TTL 到今天结束（明天 00:00:00），跨天自动清零
                LocalDateTime midnight = LocalDate.now().plusDays(1).atStartOfDay();
                long ttlSeconds = Duration.between(LocalDateTime.now(), midnight).getSeconds();
                try {
                    redis.expire(RedisKeys.rate(key), Duration.ofSeconds(ttlSeconds));
                } catch (RuntimeException e) {
                    // 计数已成功，TTL 失败只影响跨天清零，不重复计数
                    warnDegrade("Redis 限次 TTL 设置失败", e);
                }
            }
            return count == null ? 0 : count.intValue();
        } catch (RuntimeException e) {
            warnDegrade("Redis 限次不可用，降级为内存计数", e);
            return fallback.increment(key);
        }
    }

    @Override
    public int count(String key) {
        try {
            // 只查不增：过期 key 已消失，返回 0
            String v = redis.opsForValue().get(RedisKeys.rate(key));
            return v == null ? 0 : Integer.parseInt(v);
        } catch (RuntimeException e) {
            warnDegrade("Redis 限次查询不可用，降级为内存计数", e);
            return fallback.count(key);
        }
    }

    private void warnDegrade(String action, RuntimeException e) {
        long now = System.currentTimeMillis();
        long last = lastWarnAt.get();
        if (now - last >= WARN_INTERVAL_MS && lastWarnAt.compareAndSet(last, now)) {
            logger.warn("{}: {}", action, e.getMessage());
        }
    }
}