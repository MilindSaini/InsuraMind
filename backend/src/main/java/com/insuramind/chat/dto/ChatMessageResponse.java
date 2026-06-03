package com.insuramind.chat.dto;

import com.insuramind.chat.ChatMessage;

import java.time.Instant;
import java.util.UUID;

public record ChatMessageResponse(
        UUID id,
        String role,
        String content,
        Double confidence,
        String citationsJson,
        String riskAlertsJson,
        Instant createdAt
) {
    public static ChatMessageResponse from(ChatMessage message) {
        return new ChatMessageResponse(
                message.getId(),
                message.getRole().name(),
                message.getContent(),
                message.getConfidence(),
                message.getCitationsJson(),
                message.getRiskAlertsJson(),
                message.getCreatedAt()
        );
    }
}
