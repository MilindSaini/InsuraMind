package com.insuramind.document;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface DocumentTypeConfigRepository extends JpaRepository<DocumentTypeConfig, String> {

    List<DocumentTypeConfig> findByEnabledTrue();

    Optional<DocumentTypeConfig> findByDocType(String docType);
}
