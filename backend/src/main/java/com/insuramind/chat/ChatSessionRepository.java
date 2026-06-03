package com.insuramind.chat;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface ChatSessionRepository extends JpaRepository<ChatSession, UUID> {
    Optional<ChatSession> findFirstByUserIdAndDocumentIdOrderByCreatedAtAsc(UUID userId, UUID documentId);
}
