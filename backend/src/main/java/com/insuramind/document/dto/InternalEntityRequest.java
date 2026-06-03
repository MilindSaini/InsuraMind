package com.insuramind.document.dto;

public record InternalEntityRequest(
        String entityType,
        String entityValue,
        double confidence,
        Integer pageNumber,
        Integer sourceChunkIndex
) {}
