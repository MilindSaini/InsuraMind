package com.insuramind.document;

import com.insuramind.document.dto.DocumentResponse;
import com.insuramind.document.dto.InsightResponse;
import com.insuramind.document.dto.SignedUrlResponse;
import com.insuramind.security.SecurityUser;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/documents")
public class DocumentController {
    private final DocumentService documentService;
    private final DocumentStatusBroadcaster broadcaster;

    public DocumentController(DocumentService documentService, DocumentStatusBroadcaster broadcaster) {
        this.documentService = documentService;
        this.broadcaster = broadcaster;
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public DocumentResponse upload(@AuthenticationPrincipal SecurityUser principal, @RequestPart("file") MultipartFile file) {
        return documentService.upload(principal, file);
    }

    @GetMapping
    public List<DocumentResponse> list(@AuthenticationPrincipal SecurityUser principal) {
        return documentService.list(principal);
    }

    @GetMapping("/{id}")
    public DocumentResponse get(@AuthenticationPrincipal SecurityUser principal, @PathVariable UUID id) {
        return documentService.get(principal, id);
    }

    @DeleteMapping("/{id}")
    public java.util.Map<String, String> delete(@AuthenticationPrincipal SecurityUser principal, @PathVariable UUID id) {
        documentService.delete(principal, id);
        return java.util.Map.of("status", "deleted");
    }

    @GetMapping("/{id}/file-url")
    public SignedUrlResponse fileUrl(@AuthenticationPrincipal SecurityUser principal, @PathVariable UUID id) {
        return documentService.signedUrl(principal, id);
    }

    @GetMapping("/{id}/preview")
    public ResponseEntity<InputStreamResource> preview(@AuthenticationPrincipal SecurityUser principal, @PathVariable UUID id) {
        DocumentService.DocumentPreview preview = documentService.preview(principal, id);
        MediaType mediaType = MediaType.APPLICATION_PDF;
        try {
            mediaType = MediaType.parseMediaType(preview.contentType());
        } catch (Exception ignored) {
            // Default to PDF for browser preview.
        }
        return ResponseEntity.ok()
                .contentType(mediaType)
                .contentLength(preview.sizeBytes())
                .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.inline()
                        .filename(preview.fileName())
                        .build()
                        .toString())
                .body(preview.resource());
    }

    @GetMapping("/{id}/insights")
    public InsightResponse insights(@AuthenticationPrincipal SecurityUser principal, @PathVariable UUID id) {
        return documentService.insights(principal, id);
    }

    /**
     * Server-Sent Events stream for live document processing status.
     * The client connects once; the server pushes "status" events until
     * the document reaches READY or FAILED, then closes the stream.
     *
     * Usage (browser):
     *   const es = new EventSource(`/api/documents/${id}/status-stream`, { withCredentials: true });
     *   es.addEventListener('status', e => console.log(JSON.parse(e.data)));
     */
    @GetMapping(value = "/{id}/status-stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter statusStream(
            @AuthenticationPrincipal SecurityUser principal,
            @PathVariable UUID id
    ) {
        // Ownership check — throws 404 if not owned
        documentService.get(principal, id);
        return broadcaster.subscribe(id);
    }
}
