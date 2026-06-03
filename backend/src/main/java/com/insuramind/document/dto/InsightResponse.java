package com.insuramind.document.dto;

import java.util.List;

public record InsightResponse(
        DocumentResponse document,
        List<EntityResponse> entities,
        List<ChunkResponse> coverage,
        List<ChunkResponse> exclusions,
        List<ChunkResponse> waitingPeriods,
        List<ChunkResponse> riskAlerts,
        List<ChunkResponse> allChunks
) {}
