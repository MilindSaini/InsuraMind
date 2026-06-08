package com.insuramind.document.dto;

import java.util.List;
import java.util.Map;

/**
 * DTR-aware insight response.
 *
 * <p>Backward-compatible: still includes the insurance-specific named fields
 * (coverage, exclusions, waitingPeriods) but also provides a generic
 * {@code sections} map for DTR-driven doc types where section keys are dynamic.</p>
 */
public record InsightResponse(
        DocumentResponse document,
        List<EntityResponse> entities,
        // ── Legacy named sections (kept for frontend backward compat) ────────
        List<ChunkResponse> coverage,
        List<ChunkResponse> exclusions,
        List<ChunkResponse> waitingPeriods,
        List<ChunkResponse> riskAlerts,
        List<ChunkResponse> allChunks,
        // ── DTR dynamic sections ─────────────────────────────────────────────
        String docType,
        String docTypeDisplayName,
        Map<String, List<ChunkResponse>> sections
) {}
