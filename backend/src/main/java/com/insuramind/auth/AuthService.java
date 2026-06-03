package com.insuramind.auth;

import com.insuramind.auth.dto.AuthResponse;
import com.insuramind.auth.dto.LoginRequest;
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

import java.util.Locale;
import java.util.UUID;

@Service
public class AuthService {
    private final UserRepository users;
    private final PasswordEncoder encoder;
    private final AuthenticationManager authenticationManager;
    private final JwtService jwtService;

    public AuthService(UserRepository users, PasswordEncoder encoder, AuthenticationManager authenticationManager, JwtService jwtService) {
        this.users = users;
        this.encoder = encoder;
        this.authenticationManager = authenticationManager;
        this.jwtService = jwtService;
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

    private AuthResponse response(SecurityUser user, String role) {
        return new AuthResponse(
                jwtService.generate(user),
                user.getId(),
                user.getUsername(),
                user.getEmail(),
                user.getFullName(),
                role
        );
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
