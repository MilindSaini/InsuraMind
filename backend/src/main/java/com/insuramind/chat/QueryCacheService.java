package com.insuramind.chat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.insuramind.client.AiQueryResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.HexFormat;
import java.util.Optional;
import java.util.UUID;

@Service
public class QueryCacheService {
    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;
    private final Duration ttl;

    public QueryCacheService(
            StringRedisTemplate redis,
            ObjectMapper objectMapper,
            @Value("${app.cache.query-response-ttl-hours}") long ttlHours
    ) {
        this.redis = redis;
        this.objectMapper = objectMapper;
        this.ttl = Duration.ofHours(ttlHours);
    }

    public Optional<AiQueryResponse> get(UUID userId, UUID documentId, String question) {
        try {
            String raw = redis.opsForValue().get(key(userId, documentId, question));
            if (raw == null || raw.isBlank()) {
                return Optional.empty();
            }
            return Optional.of(objectMapper.readValue(raw, AiQueryResponse.class));
        } catch (Exception ignored) {
            return Optional.empty();
        }
    }

    public void put(UUID userId, UUID documentId, String question, AiQueryResponse response) {
        try {
            String raw = objectMapper.writeValueAsString(response);
            redis.opsForValue().set(key(userId, documentId, question), raw, ttl);
        } catch (Exception ignored) {
            // Cache must never block the core answer flow.
        }
    }

    private String key(UUID userId, UUID documentId, String question) {
        String normalized = question.trim().toLowerCase().replaceAll("\\s+", " ");
        return "insuramind:query:v1:%s:%s:%s".formatted(userId, documentId, sha256(normalized));
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            return Integer.toHexString(value.hashCode());
        }
    }
}
