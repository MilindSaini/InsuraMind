package com.insuramind.document;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "extracted_entities")
public class ExtractedEntity {
    @Id
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "document_id", nullable = false)
    private InsuranceDocument document;

    @Column(name = "entity_type", nullable = false, length = 120)
    private String entityType;

    @Column(name = "entity_value", nullable = false, columnDefinition = "TEXT")
    private String entityValue;

    @Column(nullable = false)
    private double confidence;

    @Column(name = "page_number")
    private Integer pageNumber;

    @Column(name = "source_chunk_index")
    private Integer sourceChunkIndex;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @PrePersist
    void prePersist() {
        if (id == null) id = UUID.randomUUID();
        if (createdAt == null) createdAt = Instant.now();
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public InsuranceDocument getDocument() { return document; }
    public void setDocument(InsuranceDocument document) { this.document = document; }
    public String getEntityType() { return entityType; }
    public void setEntityType(String entityType) { this.entityType = entityType; }
    public String getEntityValue() { return entityValue; }
    public void setEntityValue(String entityValue) { this.entityValue = entityValue; }
    public double getConfidence() { return confidence; }
    public void setConfidence(double confidence) { this.confidence = confidence; }
    public Integer getPageNumber() { return pageNumber; }
    public void setPageNumber(Integer pageNumber) { this.pageNumber = pageNumber; }
    public Integer getSourceChunkIndex() { return sourceChunkIndex; }
    public void setSourceChunkIndex(Integer sourceChunkIndex) { this.sourceChunkIndex = sourceChunkIndex; }
    public Instant getCreatedAt() { return createdAt; }
}
