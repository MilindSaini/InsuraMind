"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { askDocument, getMessages } from "@/services/api";
import type { ChatResponse } from "@/types";

const suggestions = [
  "What are the exclusions?",
  "What can reject my claim?",
  "Is diabetes covered?",
  "What is the waiting period?",
  "Summarize my coverage"
];

export function ChatPanel({
  documentId,
  disabled,
  onAnswer
}: {
  documentId: string;
  disabled?: boolean;
  onAnswer?: (answer: ChatResponse) => void;
}) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [lastAnswer, setLastAnswer] = useState<ChatResponse | null>(null);
  const messages = useQuery({ queryKey: ["messages", documentId], queryFn: () => getMessages(documentId) });
  const ask = useMutation({
    mutationFn: (question: string) => askDocument(documentId, question),
    onSuccess: (response) => {
      setLastAnswer(response);
      onAnswer?.(response);
      setDraft("");
      queryClient.invalidateQueries({ queryKey: ["messages", documentId] });
    }
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) return;
    ask.mutate(draft.trim());
  }

  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold">AI Chat</h2>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex flex-wrap gap-2">
          {suggestions.map((text) => (
            <button
              key={text}
              disabled={disabled || ask.isPending}
              onClick={() => ask.mutate(text)}
              className="rounded-full border border-line bg-panel px-3 py-1 text-xs text-ink transition hover:border-brand disabled:opacity-50"
            >
              {text}
            </button>
          ))}
        </div>

        <div className="mb-4 max-h-80 space-y-3 overflow-auto rounded-md border border-line bg-panel p-3">
          {(messages.data || []).map((message) => (
            <div key={message.id} className={message.role === "USER" ? "text-right" : "text-left"}>
              <div className={`inline-block max-w-[85%] rounded-md px-3 py-2 text-sm ${message.role === "USER" ? "bg-brand text-white" : "bg-white text-ink"}`}>
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
            </div>
          ))}
          {ask.isPending && <p className="text-sm text-muted">Thinking through the policy text...</p>}
        </div>

        {lastAnswer && (
          <div className="mb-4 rounded-md border border-line bg-white p-3">
            <div className="mb-2 flex gap-2 text-xs text-muted">
              <span>Intent: {lastAnswer.intent}</span>
              <span>Confidence: {Math.round(lastAnswer.confidence * 100)}%</span>
              <span>{lastAnswer.verified ? "Verified" : "Needs review"}</span>
            </div>
            <div className="space-y-2">
              {lastAnswer.citations.slice(0, 3).map((citation, index) => (
                <p key={index} className="text-xs text-muted">
                  {citation.citationLabel || `p.${citation.pageNumber || "?"}`}: {citation.text.slice(0, 180)}
                </p>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={submit} className="flex gap-2">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            disabled={disabled || ask.isPending}
            placeholder={disabled ? "Document is not ready yet" : "Ask about coverage, exclusions, waiting periods, or claims"}
            className="min-h-11 flex-1 resize-none rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-blue-100"
          />
          <Button disabled={disabled || ask.isPending || !draft.trim()} className="h-11 w-11 px-0" aria-label="Send">
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
