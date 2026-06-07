package com.insuramind.chat;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insuramind.audit.AuditService;
import com.insuramind.chat.dto.ChatMessageResponse;
import com.insuramind.chat.dto.ChatRequest;
import com.insuramind.chat.dto.ChatResponse;
import com.insuramind.chat.dto.CitationDto;
import com.insuramind.client.AiQueryRequest;
import com.insuramind.client.AiQueryResponse;
import com.insuramind.client.AiServiceClient;
import com.insuramind.common.ApiException;
import com.insuramind.document.DocumentService;
import com.insuramind.document.DocumentStatus;
import com.insuramind.document.InsuranceDocument;
import com.insuramind.security.SecurityUser;
import com.insuramind.user.User;
import com.insuramind.user.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
public class ChatService {
    private final ChatSessionRepository sessions;
    private final ChatMessageRepository messages;
    private final UserRepository users;
    private final DocumentService documents;
    private final AiServiceClient aiServiceClient;
    private final QueryCacheService queryCacheService;
    private final RateLimitService rateLimitService;
    private final AuditService auditService;
    private final ObjectMapper objectMapper;

    public ChatService(
            ChatSessionRepository sessions,
            ChatMessageRepository messages,
            UserRepository users,
            DocumentService documents,
            AiServiceClient aiServiceClient,
            QueryCacheService queryCacheService,
            RateLimitService rateLimitService,
            AuditService auditService,
            ObjectMapper objectMapper
    ) {
        this.sessions = sessions;
        this.messages = messages;
        this.users = users;
        this.documents = documents;
        this.aiServiceClient = aiServiceClient;
        this.queryCacheService = queryCacheService;
        this.rateLimitService = rateLimitService;
        this.auditService = auditService;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public ChatResponse ask(SecurityUser principal, UUID documentId, ChatRequest request) {
        InsuranceDocument document = documents.getOwnedDocument(principal, documentId);
        if (document.getStatus() != DocumentStatus.READY) {
            throw new ApiException(HttpStatus.CONFLICT, "Document is not ready for chat yet");
        }

        rateLimitService.checkQueryLimit(principal.getId());
        ChatSession session = getOrCreateSession(principal, document);
        saveMessage(session, ChatRole.USER, request.question(), null, null, null);

        AiQueryResponse ai = queryCacheService
                .get(principal.getId(), documentId, request.question())
                .orElseGet(() -> fetchAndCache(principal, documentId, request.question()));
        if (ai == null) {
            throw new ApiException(HttpStatus.BAD_GATEWAY, "AI service returned no response");
        }

        String citationsJson = toJson(ai.citations());
        String riskJson = toJson(ai.riskAlerts());
        saveMessage(session, ChatRole.ASSISTANT, ai.answer(), ai.confidence(), citationsJson, riskJson);
        auditService.log(principal.getId(), "DOCUMENT_QUERY", documentId.toString(), request.question());

        List<CitationDto> citations = ai.citations() == null ? List.of() : ai.citations().stream()
            .map(c -> new CitationDto(c.citationLabel(), c.pageNumber(), c.sectionType(), c.heading(), c.text(), c.score()))
                .toList();
        return new ChatResponse(
                session.getId(),
                ai.answer(),
                ai.confidence(),
                ai.intent(),
                ai.verified(),
                citations,
                ai.riskAlerts() == null ? List.of() : ai.riskAlerts()
        );
    }

    private AiQueryResponse fetchAndCache(SecurityUser principal, UUID documentId, String question) {
        AiQueryResponse response = aiServiceClient.query(new AiQueryRequest(documentId, principal.getId(), question));
        if (response != null) {
            queryCacheService.put(principal.getId(), documentId, question, response);
        }
        return response;
    }

    public List<ChatMessageResponse> history(SecurityUser principal, UUID documentId) {
        documents.getOwnedDocument(principal, documentId);
        return sessions.findFirstByUserIdAndDocumentIdOrderByCreatedAtAsc(principal.getId(), documentId)
                .map(session -> messages.findBySessionIdOrderByCreatedAtAsc(session.getId()).stream()
                        .map(ChatMessageResponse::from)
                        .toList())
                .orElse(List.of());
    }

    private ChatSession getOrCreateSession(SecurityUser principal, InsuranceDocument document) {
        return sessions.findFirstByUserIdAndDocumentIdOrderByCreatedAtAsc(principal.getId(), document.getId())
                .orElseGet(() -> {
                    User user = users.findById(principal.getId())
                            .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "User not found"));
                    ChatSession session = new ChatSession();
                    session.setUser(user);
                    session.setDocument(document);
                    session.setTitle(document.getFileName());
                    return sessions.save(session);
                });
    }

    private void saveMessage(ChatSession session, ChatRole role, String content, Double confidence, String citations, String risks) {
        ChatMessage message = new ChatMessage();
        message.setSession(session);
        message.setRole(role);
        message.setContent(content);
        message.setConfidence(confidence);
        message.setCitationsJson(citations);
        message.setRiskAlertsJson(risks);
        messages.save(message);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? List.of() : value);
        } catch (JsonProcessingException ex) {
            return "[]";
        }
    }
}
