package com.star.agent.governance;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicLong;

// 确认态存储：Redis 版实现（正式版），key 走 RedisKeys 规范
// 条件装配：linkagent.redis-enabled=true 时注册，取代内存版
// 降级：Redis 不可用时退回内存确认态，高危操作确认流程不能因缓存故障中断
@Component
@ConditionalOnProperty(name = "linkagent.redis-enabled", havingValue = "true")
public class RedisConfirmationStore implements ConfirmationStore {

    private static final Logger logger = LoggerFactory.getLogger(RedisConfirmationStore.class);
    private static final long WARN_INTERVAL_MS = 60_000L;

    private final StringRedisTemplate redis;
    private final InMemoryConfirmationStore fallback = new InMemoryConfirmationStore();
    private final AtomicLong lastWarnAt = new AtomicLong(0);

    // StringRedisTemplate 是 Spring Boot 自动配好的 bean，存字符串正好够用
    public RedisConfirmationStore(StringRedisTemplate redis) {
        this.redis = redis;
    }

    @Override
    public void save(String key, String value, long ttlSeconds) {
        try {
            // TTL 交给 Redis 原生过期（不用像内存版那样自己算过期时间戳）
            redis.opsForValue().set(RedisKeys.confirmation(key), value, Duration.ofSeconds(ttlSeconds));
        } catch (RuntimeException e) {
            warnDegrade(e);
            fallback.save(key, value, ttlSeconds);
        }
    }

    @Override
    public String get(String key) {
        try {
            // Redis 过期后自动消失，get 自然返回 null，无需懒过期逻辑
            return redis.opsForValue().get(RedisKeys.confirmation(key));
        } catch (RuntimeException e) {
            warnDegrade(e);
            return fallback.get(key);
        }
    }

    @Override
    public void delete(String key) {
        try {
            redis.delete(RedisKeys.confirmation(key));
        } catch (RuntimeException e) {
            warnDegrade(e);
        }
        fallback.delete(key);   // 两侧都删，避免降级期间残留旧确认态
    }

    private void warnDegrade(RuntimeException e) {
        long now = System.currentTimeMillis();
        long last = lastWarnAt.get();
        if (now - last >= WARN_INTERVAL_MS && lastWarnAt.compareAndSet(last, now)) {
            logger.warn("Redis 确认态不可用，降级为内存存储: {}", e.getMessage());
        }
    }
}