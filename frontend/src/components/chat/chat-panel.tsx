"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, CircleAlert, Send, Shield, MoreVertical } from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Badge } from "@/components/ui/badge";
import { askDocument, getMessages } from "@/services/api";
import type { ChatResponse, Entity } from "@/types";

const fallbackSuggestions = [
  "What are exclusions?",
  "Is diabetes covered?",
  "Summarize Section 4",
];

export function ChatPanel({
  documentId,
  disabled,
  onAnswer,
  entities = [],
}: {
  documentId: string;
  disabled?: boolean;
  onAnswer?: (answer: ChatResponse) => void;
  entities?: Entity[];
}) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [lastAnswer, setLastAnswer] = useState<ChatResponse | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const messages = useQuery({ queryKey: ["messages", documentId], queryFn: () => getMessages(documentId) });
  const suggestions = useMemo(() => buildSuggestions(entities), [entities]);
  const ask = useMutation({
    mutationFn: (question: string) => askDocument(documentId, question),
    onSuccess: (response) => {
      setLastAnswer(response);
      onAnswer?.(response);
      setDraft("");
      queryClient.invalidateQueries({ queryKey: ["messages", documentId] });
    },
  });

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.data, ask.isPending]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) return;
    ask.mutate(draft.trim());
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border-subtle px-5 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gold-surface">
            <Shield className="h-3.5 w-3.5 text-gold" />
          </div>
          <h2 className="font-heading text-sm font-semibold text-text-primary">Policy Assistant</h2>
          <span className="h-2 w-2 rounded-full bg-emerald" />
        </div>
        <button className="flex h-7 w-7 items-center justify-center rounded-full text-text-muted hover:bg-panel" aria-label="More options">
          <MoreVertical className="h-4 w-4" />
        </button>
      </div>

      {/* Suggestion chips */}
      <div className="flex flex-wrap gap-2 border-b border-border-subtle px-5 py-3">
        {suggestions.map((text) => (
          <button
            key={text}
            disabled={disabled || ask.isPending}
            onClick={() => ask.mutate(text)}
            className="suggestion-chip"
          >
            {text}
          </button>
        ))}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-auto px-5 py-4 bg-surface-warm" style={{ minHeight: 300, maxHeight: 500 }}>
        <div className="space-y-4">
          {(messages.data || []).map((message) => (
            <div key={message.id} className={`flex ${message.role === "USER" ? "justify-end" : "justify-start"}`}>
              {message.role === "ASSISTANT" && (
                <div className="mr-2 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gold-surface">
                  <Shield className="h-3 w-3 text-gold" />
                </div>
              )}
              <div
                className={`max-w-[85%] px-4 py-3 text-sm ${
                  message.role === "USER"
                    ? "bubble-user bg-gradient-to-br from-accent to-accent-light text-white"
                    : "bubble-ai border border-line bg-white text-text-primary"
                }`}
              >
                {message.role === "ASSISTANT" ? (
                  <div className="prose prose-sm max-w-none text-text-primary">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{message.content}</p>
                )}
              </div>
            </div>
          ))}

          {/* Thinking indicator */}
          {ask.isPending && (
            <div className="flex items-start gap-2">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gold-surface">
                <Shield className="h-3 w-3 text-gold" />
              </div>
              <div className="bubble-ai border border-line bg-white px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <span className="thinking-dot" />
                    <span className="thinking-dot" />
                    <span className="thinking-dot" />
                  </div>
                  <span className="text-body-sm text-gold italic">Analyzing policy clauses...</span>
                </div>
              </div>
            </div>
          )}

          {/* Last answer details */}
          {lastAnswer && (
            <div className="flex items-start gap-2">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gold-surface">
                <Shield className="h-3 w-3 text-gold" />
              </div>
              <div className="bubble-ai border border-line bg-white px-4 py-3 max-w-[85%]">
                {lastAnswer.answer.startsWith("General knowledge, not from your policy:") && (
                  <div className="mb-3 rounded-input border border-warning/20 bg-warning-surface px-3 py-2 text-xs text-warning">
                    ⚠ General knowledge, not from your policy
                  </div>
                )}
                <div className="prose prose-sm max-w-none text-text-primary">
                  <ReactMarkdown>{lastAnswer.answer}</ReactMarkdown>
                </div>

                {/* Confidence & citation badges */}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge
                    variant={lastAnswer.confidence >= 0.8 ? "success" : lastAnswer.confidence >= 0.6 ? "warning" : "failed"}
                    className="!text-[11px]"
                  >
                    {lastAnswer.confidence >= 0.8 ? <Check className="h-3 w-3" /> : <CircleAlert className="h-3 w-3" />}
                    {confidenceLabel(lastAnswer.confidence)}
                  </Badge>
                  {lastAnswer.citations.slice(0, 3).map((citation, i) => (
                    <Badge key={i} variant="default" className="!text-[11px]">
                      📄 Sec {citation.citationLabel || `p.${citation.pageNumber || "?"}`}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>
      </div>

      {/* Chat input */}
      <div className="border-t border-border-subtle px-5 py-3">
        <form onSubmit={submit} className="flex items-center gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={disabled || ask.isPending}
            placeholder={disabled ? "Document is not ready yet" : "Ask a question about this policy..."}
            className="flex-1 h-11 rounded-button border border-line bg-white px-4 text-body-sm text-text-primary outline-none transition-all focus:border-gold focus:shadow-gold-glow"
          />
          <button
            type="submit"
            disabled={disabled || ask.isPending || !draft.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald text-white transition-all hover:bg-emerald-light disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
        <p className="mt-1.5 text-center text-[11px] text-text-muted">
          AI responses may need human review for legal accuracy.
        </p>
      </div>
    </div>
  );
}

function buildSuggestions(entities: Entity[]) {
  const suggestions: string[] = [];
  const diseases = entities.filter((entity) => entity.entityType === "disease").slice(0, 3);

  for (const disease of diseases) {
    const label = normalizeLabel(disease.entityValue);
    suggestions.push(`Is ${label} covered?`);
    suggestions.push(`What is the waiting period for ${label}?`);
    suggestions.push(`Are there exclusions for ${label}?`);
  }

  for (const entity of entities.slice(0, 3)) {
    const label = normalizeLabel(entity.entityValue);
    suggestions.push(`What does the policy say about ${label}?`);
  }

  const deduped = Array.from(new Set(suggestions.filter(Boolean)));
  return deduped.slice(0, 5).length > 0 ? deduped.slice(0, 5) : fallbackSuggestions;
}

function normalizeLabel(value: string) {
  return value.trim().replace(/\s+/g, " ");
}

function confidenceLabel(confidence: number) {
  if (confidence >= 0.8) return "High Confidence";
  if (confidence >= 0.6) return "Moderate";
  return "Low Confidence";
}
