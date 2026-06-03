package com.insuramind.document;

import com.insuramind.client.AiServiceClient;
import com.insuramind.client.ProcessDocumentRequest;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
public class DocumentProcessingService {
    private final InsuranceDocumentRepository documents;
    private final AiServiceClient aiServiceClient;

    public DocumentProcessingService(InsuranceDocumentRepository documents, AiServiceClient aiServiceClient) {
        this.documents = documents;
        this.aiServiceClient = aiServiceClient;
    }

    @Async("documentTaskExecutor")
    public void process(UUID documentId, UUID userId, String objectKey, String fileName, String fileType) {
        markProcessing(documentId, "AI pipeline started");
        try {
            aiServiceClient.process(new ProcessDocumentRequest(documentId, userId, objectKey, fileName, fileType));
        } catch (Exception ex) {
            markFailed(documentId, "AI processing failed: " + ex.getMessage());
        }
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
}
