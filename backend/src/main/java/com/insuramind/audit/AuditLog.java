package com.insuramind.audit;

import com.insuramind.user.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "audit_logs")
public class AuditLog {
    @Id
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;

    @Column(nullable = false, length = 120)
    private String action;

    @Column(name = "resource_id", length = 160)
    private String resourceId;

    @Column(name = "ip_address", length = 80)
    private String ipAddress;

    @Column(columnDefinition = "TEXT")
    private String metadata;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @PrePersist
    void prePersist() {
        if (id == null) id = UUID.randomUUID();
        if (createdAt == null) createdAt = Instant.now();
    }

    public void setUser(User user) { this.user = user; }
    public void setAction(String action) { this.action = action; }
    public void setResourceId(String resourceId) { this.resourceId = resourceId; }
    public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }
    public void setMetadata(String metadata) { this.metadata = metadata; }
}
