package com.insuramind.client;

import java.util.UUID;

public record ProcessDocumentRequest(
        UUID documentId,
        UUID userId,
        String objectKey,
        String fileName,
        String fileType
) {}
