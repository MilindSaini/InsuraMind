package com.insuramind.chat;

import com.insuramind.common.ApiException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.UUID;

@Service
public class RateLimitService {
    private final StringRedisTemplate redis;
    private final int maxQueriesPerMinute;

    public RateLimitService(
            StringRedisTemplate redis,
            @Value("${app.rate-limit.query-per-minute}") int maxQueriesPerMinute
    ) {
        this.redis = redis;
        this.maxQueriesPerMinute = maxQueriesPerMinute;
    }

    public void checkQueryLimit(UUID userId) {
        try {
            String key = "insuramind:rate:query:%s:%d".formatted(userId, System.currentTimeMillis() / 60_000);
            Long count = redis.opsForValue().increment(key);
            if (count != null && count == 1L) {
                redis.expire(key, Duration.ofSeconds(90));
            }
            if (count != null && count > maxQueriesPerMinute) {
                throw new ApiException(HttpStatus.TOO_MANY_REQUESTS, "Too many questions. Please wait a minute and try again.");
            }
        } catch (ApiException ex) {
            throw ex;
        } catch (Exception ignored) {
            // Redis outages should not break the MVP query flow.
        }
    }
}
