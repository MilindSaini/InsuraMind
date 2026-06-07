package com.insuramind.document;

/**
 * Internal domain event fired when a document's status changes.
 * Consumed by DocumentStatusBroadcaster to push SSE updates to connected clients.
 */
public record DocumentStatusChangedEvent(
        java.util.UUID documentId,
        String status,
        String message
) {}
