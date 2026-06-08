package com.insuramind.document;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;

/**
 * JPA entity for the document_type_registry table.
 *
 * Each row defines a complete configuration for one document type:
 * entity schemas, section taxonomies, query intents, risk patterns,
 * answer templates, and regulatory context.
 */
@Entity
@Table(name = "document_type_registry")
public class DocumentTypeConfig {

    @Id
    @Column(name = "doc_type", length = 64)
    private String docType;

    @Column(name = "display_name", nullable = false, length = 128)
    private String displayName;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "entity_schema", columnDefinition = "jsonb")
    private String entitySchema;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "section_taxonomy", columnDefinition = "jsonb")
    private String sectionTaxonomy;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "query_intents", columnDefinition = "jsonb")
    private String queryIntents;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "risk_patterns", columnDefinition = "jsonb")
    private String riskPatterns;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "answer_templates", columnDefinition = "jsonb")
    private String answerTemplates;

    @Column(name = "regulatory_context", columnDefinition = "TEXT")
    private String regulatoryContext;

    @Column(name = "classifier_exemplar", columnDefinition = "TEXT")
    private String classifierExemplar;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "classifier_terms", columnDefinition = "jsonb")
    private String classifierTerms;

    @Column(nullable = false)
    private boolean enabled = true;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @PrePersist
    void prePersist() {
        Instant now = Instant.now();
        createdAt = now;
        updatedAt = now;
    }

    @PreUpdate
    void preUpdate() {
        updatedAt = Instant.now();
    }

    // ── Getters / Setters ────────────────────────────────────────────────────

    public String getDocType() { return docType; }
    public void setDocType(String docType) { this.docType = docType; }

    public String getDisplayName() { return displayName; }
    public void setDisplayName(String displayName) { this.displayName = displayName; }

    public String getEntitySchema() { return entitySchema; }
    public void setEntitySchema(String entitySchema) { this.entitySchema = entitySchema; }

    public String getSectionTaxonomy() { return sectionTaxonomy; }
    public void setSectionTaxonomy(String sectionTaxonomy) { this.sectionTaxonomy = sectionTaxonomy; }

    public String getQueryIntents() { return queryIntents; }
    public void setQueryIntents(String queryIntents) { this.queryIntents = queryIntents; }

    public String getRiskPatterns() { return riskPatterns; }
    public void setRiskPatterns(String riskPatterns) { this.riskPatterns = riskPatterns; }

    public String getAnswerTemplates() { return answerTemplates; }
    public void setAnswerTemplates(String answerTemplates) { this.answerTemplates = answerTemplates; }

    public String getRegulatoryContext() { return regulatoryContext; }
    public void setRegulatoryContext(String regulatoryContext) { this.regulatoryContext = regulatoryContext; }

    public String getClassifierExemplar() { return classifierExemplar; }
    public void setClassifierExemplar(String classifierExemplar) { this.classifierExemplar = classifierExemplar; }

    public String getClassifierTerms() { return classifierTerms; }
    public void setClassifierTerms(String classifierTerms) { this.classifierTerms = classifierTerms; }

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }

    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
