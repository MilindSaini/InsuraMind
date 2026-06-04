"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { AuthGuard } from "@/components/auth-guard";
import { ChatPanel } from "@/components/chat/chat-panel";
import { PdfViewer } from "@/components/document/pdf-viewer";
import { InsightPanel } from "@/components/insights/insight-panel";
import { Badge } from "@/components/ui/badge";
import { getDocument, getInsights } from "@/services/api";
import type { ChatResponse } from "@/types";

export default function DocumentPage() {
  const params = useParams<{ id: string }>();
  const documentId = params.id;
  const [lastAnswer, setLastAnswer] = useState<ChatResponse | null>(null);
  const document = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId),
    refetchInterval: (query) => query.state.data?.status === "READY" ? false : 4000
  });
  const insights = useQuery({
    queryKey: ["insights", documentId],
    queryFn: () => getInsights(documentId),
    enabled: document.data?.status === "READY",
    refetchInterval: document.data?.status === "READY" ? false : 5000
  });

  const ready = document.data?.status === "READY";
  const documentHighlights = useMemo(() => {
    const chunks = insights.data?.allChunks || [];
    return chunks.filter((chunk) =>
      chunk.riskLevel === "high" ||
      ["exclusion", "waiting_period", "coverage"].includes(chunk.sectionType)
    );
  }, [insights.data?.allChunks]);

  return (
    <AuthGuard>
      <AppShell>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link href="/dashboard" className="mb-2 inline-flex items-center gap-1 text-sm text-muted hover:text-ink">
              <ArrowLeft className="h-4 w-4" />
              Back to documents
            </Link>
            <h1 className="text-xl font-semibold">{document.data?.fileName || "Document"}</h1>
            <p className="text-sm text-muted">{document.data?.processingMessage || "Preparing document intelligence"}</p>
          </div>
          <div className="flex items-center gap-2">
            {!ready && <RefreshCw className="h-4 w-4 animate-spin text-brand" />}
            <Badge className={ready ? "border-green-200 bg-green-50 text-ok" : ""}>{document.data?.status || "LOADING"}</Badge>
          </div>
        </div>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_420px]">
          <section className="min-h-[680px]">
            <PdfViewer
              documentId={documentId}
              highlights={documentHighlights}
              citations={lastAnswer?.citations || []}
            />
          </section>
          <aside className="space-y-5">
            <InsightPanel insights={insights.data} />
            <ChatPanel documentId={documentId} disabled={!ready} onAnswer={setLastAnswer} />
          </aside>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
