package com.insuramind.client;

import java.util.UUID;

public record AiQueryRequest(
        UUID documentId,
        UUID userId,
        String question
) {}
