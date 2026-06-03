package com.insuramind.document;

import com.insuramind.document.dto.DocumentResponse;
import com.insuramind.document.dto.InsightResponse;
import com.insuramind.document.dto.SignedUrlResponse;
import com.insuramind.security.SecurityUser;
import org.springframework.http.MediaType;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/documents")
public class DocumentController {
    private final DocumentService documentService;

    public DocumentController(DocumentService documentService) {
        this.documentService = documentService;
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

    @GetMapping("/{id}/file-url")
    public SignedUrlResponse fileUrl(@AuthenticationPrincipal SecurityUser principal, @PathVariable UUID id) {
        return documentService.signedUrl(principal, id);
    }

    @GetMapping("/{id}/insights")
    public InsightResponse insights(@AuthenticationPrincipal SecurityUser principal, @PathVariable UUID id) {
        return documentService.insights(principal, id);
    }
}
