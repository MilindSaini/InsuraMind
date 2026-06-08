package com.insuramind.document.dto;

import com.insuramind.document.DocumentChunk;

import java.util.UUID;

public record ChunkResponse(
        UUID id,
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
) {
    public static ChunkResponse from(DocumentChunk chunk) {
        return new ChunkResponse(
                chunk.getId(),
                chunk.getChunkIndex(),
                chunk.getSectionType(),
                chunk.getHeading(),
                chunk.getParentHeading(),
                chunk.getText(),
                chunk.getPageNumber(),
                chunk.getRiskLevel(),
                chunk.getRiskScore(),
                chunk.getRiskReason(),
                chunk.getImportance(),
                chunk.getCitationLabel()
        );
    }
}
