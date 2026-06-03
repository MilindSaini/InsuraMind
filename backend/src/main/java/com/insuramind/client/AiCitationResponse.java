package com.insuramind.client;

public record AiCitationResponse(
        String citationLabel,
        Integer pageNumber,
        String sectionType,
        String text,
        double score
) {}
