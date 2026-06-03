package com.insuramind.document.dto;

public record InternalChunkRequest(
        int chunkIndex,
        String sectionType,
        String heading,
        String text,
        Integer pageNumber,
        String riskLevel,
        String importance,
        String citationLabel
) {}
