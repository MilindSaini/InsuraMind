package com.insuramind.document;

import com.insuramind.common.ApiException;
import com.insuramind.document.dto.ChunkResponse;
import com.insuramind.document.dto.InternalIngestRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/internal/documents")
public class InternalDocumentController {
    private final DocumentService documentService;
    private final DocumentChunkRepository chunks;
    private final String internalToken;

    public InternalDocumentController(DocumentService documentService, DocumentChunkRepository chunks, @Value("${app.internal-token}") String internalToken) {
        this.documentService = documentService;
        this.chunks = chunks;
        this.internalToken = internalToken;
    }

    @PostMapping("/{id}/ingest")
    public Map<String, String> ingest(
            @RequestHeader(name = "X-Internal-Token", required = false) String token,
            @PathVariable UUID id,
            @RequestBody InternalIngestRequest request
    ) {
        verify(token);
        documentService.ingest(id, request);
        return Map.of("status", "ok");
    }

    @PostMapping("/{id}/failed")
    public Map<String, String> failed(
            @RequestHeader(name = "X-Internal-Token", required = false) String token,
            @PathVariable UUID id,
            @RequestBody(required = false) Map<String, String> request
    ) {
        verify(token);
        documentService.markFailed(id, request == null ? "Processing failed" : request.getOrDefault("message", "Processing failed"));
        return Map.of("status", "ok");
    }

    @GetMapping("/{id}/chunks")
    public List<ChunkResponse> chunks(
            @RequestHeader(name = "X-Internal-Token", required = false) String token,
            @PathVariable UUID id
    ) {
        verify(token);
        return chunks.findByDocumentIdOrderByChunkIndex(id).stream().map(ChunkResponse::from).toList();
    }

    private void verify(String token) {
        if (token == null || !token.equals(internalToken)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Invalid internal token");
        }
    }
}
