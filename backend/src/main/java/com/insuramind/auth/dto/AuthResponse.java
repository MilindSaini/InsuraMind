package com.insuramind.auth.dto;

import java.util.UUID;

public record AuthResponse(
        String accessToken,
        String refreshToken,
        UUID userId,
        String username,
        String email,
        String fullName,
        String role
) {}
