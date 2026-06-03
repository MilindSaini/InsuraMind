package com.insuramind.audit;

import com.insuramind.user.UserRepository;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class AuditService {
    private final AuditLogRepository logs;
    private final UserRepository users;

    public AuditService(AuditLogRepository logs, UserRepository users) {
        this.logs = logs;
        this.users = users;
    }

    public void log(UUID userId, String action, String resourceId, String metadata) {
        AuditLog log = new AuditLog();
        users.findById(userId).ifPresent(log::setUser);
        log.setAction(action);
        log.setResourceId(resourceId);
        log.setMetadata(metadata);
        logs.save(log);
    }
}
