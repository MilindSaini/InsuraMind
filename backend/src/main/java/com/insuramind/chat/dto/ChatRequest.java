package com.insuramind.chat.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ChatRequest(
        @NotBlank(message = "Question is required")
        @Size(max = 1200, message = "Question is too long")
        String question
) {}
