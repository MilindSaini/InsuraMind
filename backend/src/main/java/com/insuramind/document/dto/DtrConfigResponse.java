package com.insuramind.document.dto;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insuramind.document.DocumentTypeConfig;

/**
 * DTO for exposing DTR configs to the AI service via the internal API.
 * Parses JSONB strings back to raw JSON nodes for clean serialization.
 */
public record DtrConfigResponse(
        String docType,
        String displayName,
        Object entitySchema,
        Object sectionTaxonomy,
        Object queryIntents,
        Object riskPatterns,
        Object answerTemplates,
        String regulatoryContext,
        String classifierExemplar,
        Object classifierTerms
) {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public static DtrConfigResponse from(DocumentTypeConfig config) {
        return new DtrConfigResponse(
                config.getDocType(),
                config.getDisplayName(),
                parseJson(config.getEntitySchema(), "{}"),
                parseJson(config.getSectionTaxonomy(), "{}"),
                parseJson(config.getQueryIntents(), "[]"),
                parseJson(config.getRiskPatterns(), "[]"),
                parseJson(config.getAnswerTemplates(), "{}"),
                config.getRegulatoryContext(),
                config.getClassifierExemplar(),
                parseJson(config.getClassifierTerms(), "[]")
        );
    }

    private static Object parseJson(String raw, String fallback) {
        if (raw == null || raw.isBlank()) raw = fallback;
        try {
            return MAPPER.readTree(raw);
        } catch (JsonProcessingException e) {
            try {
                return MAPPER.readTree(fallback);
            } catch (JsonProcessingException ex) {
                return fallback;
            }
        }
    }
}
