package com.insuramind.document;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Maintains a registry of SSE emitters per document ID.
 * Listens for {@link DocumentStatusChangedEvent} and pushes status updates
 * to every connected client watching that document.
 *
 * Thread-safe: uses ConcurrentHashMap + CopyOnWriteArrayList so concurrent
 * subscribe/unsubscribe never races with event dispatch.
 */
@Component
public class DocumentStatusBroadcaster {

    private static final Logger log = LoggerFactory.getLogger(DocumentStatusBroadcaster.class);
    private static final long SSE_TIMEOUT_MS = 5 * 60 * 1_000L; // 5 minutes

    /** documentId → list of active SSE connections */
    private final Map<UUID, List<SseEmitter>> registry = new ConcurrentHashMap<>();

    // ── Public API ──────────────────────────────────────────────────────────────

    /**
     * Create and register a new SSE emitter for {@code documentId}.
     * The emitter auto-cleans up on completion, timeout, or error.
     */
    public SseEmitter subscribe(UUID documentId) {
        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT_MS);
        List<SseEmitter> emitters = registry.computeIfAbsent(documentId, k -> new CopyOnWriteArrayList<>());
        emitters.add(emitter);
        log.debug("sse.subscribed documentId={} total={}", documentId, emitters.size());

        Runnable cleanup = () -> remove(documentId, emitter);
        emitter.onCompletion(cleanup);
        emitter.onTimeout(cleanup);
        emitter.onError(ex -> remove(documentId, emitter));
        return emitter;
    }

    // ── Internal event listener ──────────────────────────────────────────────────

    @EventListener
    public void onStatusChanged(DocumentStatusChangedEvent event) {
        List<SseEmitter> emitters = registry.get(event.documentId());
        if (emitters == null || emitters.isEmpty()) return;

        String json = String.format(
                "{\"documentId\":\"%s\",\"status\":\"%s\",\"message\":\"%s\"}",
                event.documentId(),
                event.status(),
                escape(event.message())
        );

        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name("status")
                        .data(json));

                // Automatically close the emitter once READY or FAILED
                if ("READY".equals(event.status()) || "FAILED".equals(event.status())) {
                    emitter.complete();
                }
            } catch (IOException ex) {
                log.debug("sse.send_failed documentId={} — removing stale emitter", event.documentId());
                remove(event.documentId(), emitter);
            }
        }
    }

    // ── Helpers ─────────────────────────────────────────────────────────────────

    private void remove(UUID documentId, SseEmitter emitter) {
        List<SseEmitter> emitters = registry.get(documentId);
        if (emitters != null) {
            emitters.remove(emitter);
            if (emitters.isEmpty()) {
                registry.remove(documentId);
            }
        }
    }

    private static String escape(String value) {
        if (value == null) return "";
        return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n");
    }
}
