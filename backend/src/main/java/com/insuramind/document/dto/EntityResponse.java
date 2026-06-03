package com.insuramind.document.dto;

import com.insuramind.document.ExtractedEntity;

import java.util.UUID;

public record EntityResponse(
        UUID id,
        String entityType,
        String entityValue,
        double confidence,
        Integer pageNumber,
        Integer sourceChunkIndex
) {
    public static EntityResponse from(ExtractedEntity entity) {
        return new EntityResponse(
                entity.getId(),
                entity.getEntityType(),
                entity.getEntityValue(),
                entity.getConfidence(),
                entity.getPageNumber(),
                entity.getSourceChunkIndex()
        );
    }
}
