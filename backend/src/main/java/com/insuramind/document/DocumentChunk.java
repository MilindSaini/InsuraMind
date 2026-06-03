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
@Table(name = "document_chunks")
public class DocumentChunk {
    @Id
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "document_id", nullable = false)
    private InsuranceDocument document;

    @Column(name = "chunk_index", nullable = false)
    private int chunkIndex;

    @Column(name = "section_type", nullable = false, length = 80)
    private String sectionType;

    @Column(length = 512)
    private String heading;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String text;

    @Column(name = "page_number")
    private Integer pageNumber;

    @Column(name = "risk_level", nullable = false, length = 32)
    private String riskLevel;

    @Column(nullable = false, length = 32)
    private String importance;

    @Column(name = "citation_label", length = 80)
    private String citationLabel;

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
    public int getChunkIndex() { return chunkIndex; }
    public void setChunkIndex(int chunkIndex) { this.chunkIndex = chunkIndex; }
    public String getSectionType() { return sectionType; }
    public void setSectionType(String sectionType) { this.sectionType = sectionType; }
    public String getHeading() { return heading; }
    public void setHeading(String heading) { this.heading = heading; }
    public String getText() { return text; }
    public void setText(String text) { this.text = text; }
    public Integer getPageNumber() { return pageNumber; }
    public void setPageNumber(Integer pageNumber) { this.pageNumber = pageNumber; }
    public String getRiskLevel() { return riskLevel; }
    public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }
    public String getImportance() { return importance; }
    public void setImportance(String importance) { this.importance = importance; }
    public String getCitationLabel() { return citationLabel; }
    public void setCitationLabel(String citationLabel) { this.citationLabel = citationLabel; }
    public Instant getCreatedAt() { return createdAt; }
}
