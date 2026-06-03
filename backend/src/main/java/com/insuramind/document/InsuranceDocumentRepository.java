package com.insuramind.document;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface InsuranceDocumentRepository extends JpaRepository<InsuranceDocument, UUID> {
    List<InsuranceDocument> findByUserIdOrderByCreatedAtDesc(UUID userId);
    Optional<InsuranceDocument> findByIdAndUserId(UUID id, UUID userId);
}
