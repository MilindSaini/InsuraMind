package com.insuramind.document.dto;

import java.util.List;

public record InternalIngestRequest(
        String documentType,
        String status,
        String message,
        List<InternalChunkRequest> chunks,
        List<InternalEntityRequest> entities
) {}
