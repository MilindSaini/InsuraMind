package com.insuramind.chat.dto;

import java.util.List;
import java.util.UUID;

public record ChatResponse(
        UUID sessionId,
        String answer,
        double confidence,
        String intent,
        boolean verified,
        List<CitationDto> citations,
        List<String> riskAlerts
) {}
