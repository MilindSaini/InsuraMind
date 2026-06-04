package com.insuramind.auth;

import com.insuramind.auth.dto.AuthResponse;
import com.insuramind.auth.dto.LoginRequest;
import com.insuramind.auth.dto.RefreshTokenRequest;
import com.insuramind.auth.dto.SignupRequest;
import com.insuramind.common.ApiException;
import com.insuramind.security.JwtService;
import com.insuramind.security.SecurityUser;
import com.insuramind.user.Role;
import com.insuramind.user.User;
import com.insuramind.user.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.Locale;
import java.util.UUID;

@Service
public class AuthService {
    private final UserRepository users;
    private final PasswordEncoder encoder;
    private final AuthenticationManager authenticationManager;
    private final JwtService jwtService;
    private final RefreshTokenRepository refreshTokens;
    private final SecureRandom secureRandom = new SecureRandom();

    public AuthService(
            UserRepository users,
            PasswordEncoder encoder,
            AuthenticationManager authenticationManager,
            JwtService jwtService,
            RefreshTokenRepository refreshTokens
    ) {
        this.users = users;
        this.encoder = encoder;
        this.authenticationManager = authenticationManager;
        this.jwtService = jwtService;
        this.refreshTokens = refreshTokens;
    }

    @Transactional
    public AuthResponse signup(SignupRequest request) {
        String fullName = request.fullName().trim();
        String email = request.email().trim().toLowerCase();
        String username = usernameFor(fullName, email);
        if (users.existsByUsernameIgnoreCase(username)) {
            throw new ApiException(HttpStatus.CONFLICT, "Username already exists");
        }
        if (users.existsByEmailIgnoreCase(email)) {
            throw new ApiException(HttpStatus.CONFLICT, "Email already exists");
        }

        User user = new User();
        user.setUsername(username);
        user.setEmail(email);
        user.setFullName(fullName);
        user.setPasswordHash(encoder.encode(request.password()));
        user.setRole(Role.USER);
        User saved = users.save(user);

        SecurityUser principal = new SecurityUser(saved);
        return response(principal, saved.getRole().name());
    }

    @Transactional
    public AuthResponse login(LoginRequest request) {
        String identifier = request.email().trim();
        authenticationManager.authenticate(
            new UsernamePasswordAuthenticationToken(identifier, request.password())
        );
        User user = users.findByUsernameIgnoreCase(identifier)
            .or(() -> users.findByEmailIgnoreCase(identifier))
            .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "Invalid email, username, or password"));
        return response(new SecurityUser(user), user.getRole().name());
    }

    @Transactional
    public AuthResponse refresh(RefreshTokenRequest request) {
        RefreshToken token = refreshTokens.findByTokenHash(sha256(request.refreshToken().trim()))
                .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "Invalid refresh token"));
        if (token.getRevokedAt() != null || token.getExpiresAt().isBefore(Instant.now())) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Refresh token expired");
        }
        token.setRevokedAt(Instant.now());
        refreshTokens.save(token);
        User user = token.getUser();
        return response(new SecurityUser(user), user.getRole().name());
    }

    private AuthResponse response(SecurityUser user, String role) {
        String refreshToken = createRefreshToken(user.getId());
        return new AuthResponse(
                jwtService.generate(user),
                refreshToken,
                user.getId(),
                user.getUsername(),
                user.getEmail(),
                user.getFullName(),
                role
        );
    }

    private String createRefreshToken(UUID userId) {
        User user = users.findById(userId)
                .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "User not found"));
        byte[] bytes = new byte[48];
        secureRandom.nextBytes(bytes);
        String rawToken = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);

        RefreshToken token = new RefreshToken();
        token.setUser(user);
        token.setTokenHash(sha256(rawToken));
        token.setExpiresAt(Instant.now().plusSeconds(60L * 60 * 24 * 30));
        refreshTokens.save(token);
        return rawToken;
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "Could not process token");
        }
    }

    private String usernameFor(String fullName, String email) {
        String base = fullName.toLowerCase(Locale.ROOT)
                .replaceAll("[^a-z0-9]+", ".")
                .replaceAll("\\.+", ".")
                .replaceAll("^\\.|\\.$", "");
        if (base.isBlank()) {
            base = email.substring(0, email.indexOf('@')).toLowerCase(Locale.ROOT);
        }
        String candidate = base.length() > 48 ? base.substring(0, 48) : base;
        candidate = candidate.replaceAll("^\\.+|\\.+$", "");
        if (candidate.isBlank()) {
            candidate = "user";
        }
        return candidate + "-" + UUID.randomUUID().toString().substring(0, 8);
    }
}
