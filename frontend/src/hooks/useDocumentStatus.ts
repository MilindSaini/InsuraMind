/**
 * useDocumentStatus — real-time document status via Server-Sent Events.
 *
 * Connects to GET /api/documents/{id}/status-stream and listens for
 * "status" events pushed by the Spring Boot backend whenever the document
 * processing pipeline moves through stages.
 *
 * Behaviour:
 * - Automatically connects when the document is not yet READY.
 * - Automatically disconnects when READY or FAILED is received.
 * - Falls back gracefully (no crash) if SSE is unsupported or the server
 *   is unreachable — the caller should continue polling in that case.
 * - Invalidates React Query cache for ["document", id] so the rest of the
 *   UI re-fetches the latest metadata automatically.
 */

"use client";

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { API_URL } from "@/services/api";

export type DocumentStatusPayload = {
  documentId: string;
  status: string;
  message: string;
};

type Options = {
  /** Called on every status push from the server */
  onStatusChange?: (payload: DocumentStatusPayload) => void;
  /** Whether to connect at all (e.g. skip when already READY) */
  enabled?: boolean;
};

export function useDocumentStatus(documentId: string, options: Options = {}) {
  const { onStatusChange, enabled = true } = options;
  const queryClient = useQueryClient();
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled || !documentId || typeof EventSource === "undefined") return;

    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("insuramind_token")
        : null;

    // Build the SSE URL — token is passed as a query param because EventSource
    // does not support custom request headers.
    const url = `${API_URL}/documents/${documentId}/status-stream${
      token ? `?token=${encodeURIComponent(token)}` : ""
    }`;

    const es = new EventSource(url, { withCredentials: true });
    esRef.current = es;

    es.addEventListener("status", (event: MessageEvent) => {
      try {
        const payload: DocumentStatusPayload = JSON.parse(event.data);

        // Invalidate the query cache so DocumentPage re-fetches metadata
        queryClient.invalidateQueries({ queryKey: ["document", documentId] });

        onStatusChange?.(payload);

        // Close the stream once we hit a terminal state
        if (payload.status === "READY" || payload.status === "FAILED") {
          es.close();
          esRef.current = null;
        }
      } catch {
        // Malformed JSON — ignore
      }
    });

    es.onerror = () => {
      // Connection dropped — close and let React Query polling take over
      es.close();
      esRef.current = null;
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [documentId, enabled, onStatusChange, queryClient]);
}
