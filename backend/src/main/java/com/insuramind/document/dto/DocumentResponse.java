package com.insuramind.document.dto;

import com.insuramind.document.InsuranceDocument;

import java.time.Instant;
import java.util.UUID;

public record DocumentResponse(
        UUID id,
        String fileName,
        String fileType,
        long sizeBytes,
        String status,
        String documentType,
        String documentTypeDisplayName,
        String processingMessage,
        Instant createdAt,
        Instant updatedAt
) {
    public static DocumentResponse from(InsuranceDocument document) {
        return from(document, null);
    }

    public static DocumentResponse from(InsuranceDocument document, String displayName) {
        return new DocumentResponse(
                document.getId(),
                document.getFileName(),
                document.getFileType(),
                document.getSizeBytes(),
                document.getStatus().name(),
                document.getDocumentType(),
                displayName,
                document.getProcessingMessage(),
                document.getCreatedAt(),
                document.getUpdatedAt()
        );
    }
}
