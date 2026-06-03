package com.insuramind.client;

import java.util.List;

public record AiQueryResponse(
        String answer,
        double confidence,
        List<AiCitationResponse> citations,
        List<String> riskAlerts,
        String intent,
        boolean verified
) {}
