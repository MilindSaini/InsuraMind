package com.insuramind.document.dto;

public record InternalChunkRequest(
        int chunkIndex,
        String sectionType,
        String heading,
        String parentHeading,
        String text,
        Integer pageNumber,
        String riskLevel,
        Float riskScore,
        String riskReason,
        String importance,
        String citationLabel
) {}
