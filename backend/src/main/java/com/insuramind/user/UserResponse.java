package com.insuramind.user;

import com.insuramind.security.SecurityUser;

import java.util.UUID;

public record UserResponse(
        UUID id,
        String username,
        String email,
        String fullName
) {
    public static UserResponse from(SecurityUser user) {
        return new UserResponse(user.getId(), user.getUsername(), user.getEmail(), user.getFullName());
    }
}
