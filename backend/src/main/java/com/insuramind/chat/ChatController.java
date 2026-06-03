package com.insuramind.chat;

import com.insuramind.chat.dto.ChatMessageResponse;
import com.insuramind.chat.dto.ChatRequest;
import com.insuramind.chat.dto.ChatResponse;
import com.insuramind.security.SecurityUser;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/chat")
public class ChatController {
    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping("/documents/{documentId}/query")
    public ChatResponse ask(
            @AuthenticationPrincipal SecurityUser principal,
            @PathVariable UUID documentId,
            @Valid @RequestBody ChatRequest request
    ) {
        return chatService.ask(principal, documentId, request);
    }

    @GetMapping("/documents/{documentId}/messages")
    public List<ChatMessageResponse> history(@AuthenticationPrincipal SecurityUser principal, @PathVariable UUID documentId) {
        return chatService.history(principal, documentId);
    }
}
