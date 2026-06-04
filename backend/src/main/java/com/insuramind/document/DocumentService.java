package com.insuramind.document;

import com.insuramind.common.ApiException;
import com.insuramind.document.dto.ChunkResponse;
import com.insuramind.document.dto.DocumentResponse;
import com.insuramind.document.dto.EntityResponse;
import com.insuramind.document.dto.InsightResponse;
import com.insuramind.document.dto.InternalIngestRequest;
import com.insuramind.document.dto.SignedUrlResponse;
import com.insuramind.security.SecurityUser;
import com.insuramind.user.User;
import com.insuramind.user.UserRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.core.io.InputStreamResource;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.multipart.MultipartFile;

import java.security.MessageDigest;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

@Service
public class DocumentService {
    private static final Set<String> ALLOWED_EXTENSIONS = Set.of("pdf", "png", "jpg", "jpeg", "docx", "zip");
    private static final DateTimeFormatter KEY_DATE = DateTimeFormatter.ofPattern("yyyy/MM/dd").withZone(ZoneOffset.UTC);

    private final InsuranceDocumentRepository documents;
    private final DocumentChunkRepository chunks;
    private final ExtractedEntityRepository entities;
    private final UserRepository users;
    private final MinioStorageService storage;
    private final DocumentProcessingService processingService;
    private final long maxBytes;

    public DocumentService(
            InsuranceDocumentRepository documents,
            DocumentChunkRepository chunks,
            ExtractedEntityRepository entities,
            UserRepository users,
            MinioStorageService storage,
            DocumentProcessingService processingService,
            @Value("${app.upload.max-bytes}") long maxBytes
    ) {
        this.documents = documents;
        this.chunks = chunks;
        this.entities = entities;
        this.users = users;
        this.storage = storage;
        this.processingService = processingService;
        this.maxBytes = maxBytes;
    }

    @Transactional
    public DocumentResponse upload(SecurityUser principal, MultipartFile file) {
        validate(file);
        User user = users.findById(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "User not found"));

        UUID id = UUID.randomUUID();
        String cleanName = sanitizeName(file.getOriginalFilename());
        String objectKey = principal.getId() + "/" + KEY_DATE.format(Instant.now()) + "/" + id + "-" + cleanName;

        InsuranceDocument document = new InsuranceDocument();
        document.setId(id);
        document.setUser(user);
        document.setFileName(cleanName);
        document.setFileType(file.getContentType() == null ? "application/octet-stream" : file.getContentType());
        document.setObjectKey(objectKey);
        document.setSha256(hash(file));
        document.setSizeBytes(file.getSize());
        document.setStatus(DocumentStatus.UPLOADED);

        storage.upload(objectKey, file);
        InsuranceDocument saved = documents.save(document);
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                processingService.process(saved.getId(), principal.getId(), saved.getObjectKey(), saved.getFileName(), saved.getFileType());
            }
        });
        return DocumentResponse.from(saved);
    }

    public List<DocumentResponse> list(SecurityUser principal) {
        return documents.findByUserIdOrderByCreatedAtDesc(principal.getId()).stream()
                .map(DocumentResponse::from)
                .toList();
    }

    public DocumentResponse get(SecurityUser principal, UUID documentId) {
        return DocumentResponse.from(getOwnedDocument(principal, documentId));
    }

    public SignedUrlResponse signedUrl(SecurityUser principal, UUID documentId) {
        InsuranceDocument document = getOwnedDocument(principal, documentId);
        return new SignedUrlResponse(storage.signedUrl(document.getObjectKey(), 900), 900);
    }

    public DocumentPreview preview(SecurityUser principal, UUID documentId) {
        InsuranceDocument document = getOwnedDocument(principal, documentId);
        return new DocumentPreview(
                new InputStreamResource(storage.download(document.getObjectKey())),
                document.getFileName(),
                document.getFileType(),
                document.getSizeBytes()
        );
    }

    public InsightResponse insights(SecurityUser principal, UUID documentId) {
        InsuranceDocument document = getOwnedDocument(principal, documentId);
        List<ChunkResponse> all = chunks.findByDocumentIdOrderByChunkIndex(documentId).stream()
                .map(ChunkResponse::from)
                .toList();
        List<EntityResponse> extracted = entities.findByDocumentIdOrderByEntityTypeAsc(documentId).stream()
                .map(EntityResponse::from)
                .toList();
        return new InsightResponse(
                DocumentResponse.from(document),
                extracted,
                filter(all, "coverage"),
                filter(all, "exclusion"),
                filter(all, "waiting_period"),
                all.stream().filter(c -> "high".equalsIgnoreCase(c.riskLevel())).toList(),
                all
        );
    }

    @Transactional
    public void ingest(UUID documentId, InternalIngestRequest request) {
        InsuranceDocument document = documents.findById(documentId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Document not found"));
        chunks.deleteByDocumentId(documentId);
        entities.deleteByDocumentId(documentId);

        if (request.chunks() != null) {
            request.chunks().forEach(in -> {
                DocumentChunk chunk = new DocumentChunk();
                chunk.setDocument(document);
                chunk.setChunkIndex(in.chunkIndex());
                chunk.setSectionType(defaultValue(in.sectionType(), "general"));
                chunk.setHeading(in.heading());
                chunk.setText(defaultValue(in.text(), ""));
                chunk.setPageNumber(in.pageNumber());
                chunk.setRiskLevel(defaultValue(in.riskLevel(), "low"));
                chunk.setImportance(defaultValue(in.importance(), "normal"));
                chunk.setCitationLabel(in.citationLabel());
                chunks.save(chunk);
            });
        }

        if (request.entities() != null) {
            request.entities().forEach(in -> {
                ExtractedEntity entity = new ExtractedEntity();
                entity.setDocument(document);
                entity.setEntityType(defaultValue(in.entityType(), "unknown"));
                entity.setEntityValue(defaultValue(in.entityValue(), ""));
                entity.setConfidence(in.confidence());
                entity.setPageNumber(in.pageNumber());
                entity.setSourceChunkIndex(in.sourceChunkIndex());
                entities.save(entity);
            });
        }

        document.setDocumentType(defaultValue(request.documentType(), "policy"));
        document.setProcessingMessage(defaultValue(request.message(), "Document processed"));
        document.setStatus("FAILED".equalsIgnoreCase(request.status()) ? DocumentStatus.FAILED : DocumentStatus.READY);
        documents.save(document);
    }

    @Transactional
    public void markProcessing(UUID documentId, String message) {
        documents.findById(documentId).ifPresent(document -> {
            document.setStatus(DocumentStatus.PROCESSING);
            document.setProcessingMessage(message);
            documents.save(document);
        });
    }

    @Transactional
    public void markFailed(UUID documentId, String message) {
        documents.findById(documentId).ifPresent(document -> {
            document.setStatus(DocumentStatus.FAILED);
            document.setProcessingMessage(message);
            documents.save(document);
        });
    }

    public InsuranceDocument getOwnedDocument(SecurityUser principal, UUID documentId) {
        return documents.findByIdAndUserId(documentId, principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Document not found"));
    }

    private List<ChunkResponse> filter(List<ChunkResponse> all, String section) {
        return all.stream().filter(c -> section.equalsIgnoreCase(c.sectionType())).toList();
    }

    private String defaultValue(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private void validate(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "File is required");
        }
        if (file.getSize() > maxBytes) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "File is too large");
        }
        String name = sanitizeName(file.getOriginalFilename());
        String extension = extension(name);
        if (!ALLOWED_EXTENSIONS.contains(extension)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Unsupported file type");
        }
    }

    private String sanitizeName(String name) {
        String fallback = "document.pdf";
        if (name == null || name.isBlank()) return fallback;
        return name.replaceAll("[^A-Za-z0-9._ -]", "_").trim();
    }

    private String extension(String name) {
        int dot = name.lastIndexOf('.');
        if (dot < 0) return "";
        return name.substring(dot + 1).toLowerCase(Locale.ROOT);
    }

    private String hash(MultipartFile file) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(file.getBytes()));
        } catch (Exception ex) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Could not read file");
        }
    }

    public record DocumentPreview(
            InputStreamResource resource,
            String fileName,
            String contentType,
            long sizeBytes
    ) {}
}
