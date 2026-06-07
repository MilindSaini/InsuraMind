"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, RefreshCw, Download, Share2, Shield, Wifi } from "lucide-react";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { AuthGuard } from "@/components/auth-guard";
import { ChatPanel } from "@/components/chat/chat-panel";
import { PdfViewer } from "@/components/document/pdf-viewer";
import { InsightPanel } from "@/components/insights/insight-panel";
import { Badge } from "@/components/ui/badge";
import { getDocument, getInsights } from "@/services/api";
import { useDocumentStatus } from "@/hooks/useDocumentStatus";
import type { ChatResponse } from "@/types";

type SidebarTab = "insights" | "chat";

export default function DocumentPage() {
  const params = useParams<{ id: string }>();
  const documentId = params.id;
  const [lastAnswer, setLastAnswer] = useState<ChatResponse | null>(null);
  const [liveMessage, setLiveMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<SidebarTab>("insights");

  // Primary data fetch
  const document = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId),
    refetchInterval: (query) =>
      query.state.data?.status === "READY" || query.state.data?.status === "FAILED"
        ? false
        : 8000,
  });

  const ready = document.data?.status === "READY";
  const failed = document.data?.status === "FAILED";

  // Real-time status via SSE
  useDocumentStatus(documentId, {
    enabled: !ready && !failed,
    onStatusChange: (payload) => {
      setLiveMessage(payload.message);
    },
  });

  const insights = useQuery({
    queryKey: ["insights", documentId],
    queryFn: () => getInsights(documentId),
    enabled: ready,
  });

  const documentHighlights = useMemo(() => {
    const chunks = insights.data?.allChunks || [];
    return chunks.filter(
      (chunk) =>
        chunk.riskLevel === "high" ||
        ["exclusion", "waiting_period", "coverage"].includes(chunk.sectionType)
    );
  }, [insights.data?.allChunks]);

  return (
    <AuthGuard>
      <AppShell>
        <div className="animate-enter">
          {/* ── Top Bar ── */}
          <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
            <div>
              <Link
                href="/documents"
                className="mb-2 inline-flex items-center gap-1.5 text-body-sm text-accent hover:text-accent-light transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to documents
              </Link>
              <div className="flex items-center gap-3">
                <h1 className="font-heading text-xl font-semibold text-text-primary">
                  {document.data?.fileName || "Document"}
                </h1>
                <Badge
                  variant={ready ? "success" : failed ? "failed" : "processing"}
                >
                  {!ready && !failed && (
                    <>
                      <RefreshCw className="h-3 w-3 animate-spin" />
                      <Wifi className="h-3 w-3 text-emerald" />
                    </>
                  )}
                  {ready && <span className="h-1.5 w-1.5 rounded-full bg-emerald" />}
                  {document.data?.status || "LOADING"}
                </Badge>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="btn-ghost">
                <Download className="h-4 w-4" />
                Download
              </button>
              <button className="btn-primary-gradient !h-10 !text-sm !px-5">
                <Share2 className="h-4 w-4" />
                Share
              </button>
            </div>
          </div>

          {/* ── Main Content: PDF + Tabbed Sidebar ── */}
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_420px]">
            {/* Left: PDF Viewer */}
            <section className="min-h-[680px]">
              <PdfViewer
                documentId={documentId}
                highlights={documentHighlights}
                citations={lastAnswer?.citations || []}
              />
            </section>

            {/* Right: Tabbed Sidebar (Insights + Chat merged) */}
            <aside className="flex flex-col overflow-hidden rounded-card border border-line bg-white">
              {/* Tab headers */}
              <div className="flex border-b border-border-subtle">
                <button
                  onClick={() => setActiveTab("insights")}
                  className={`flex-1 py-3 text-center text-sm font-semibold transition-all duration-200 ${
                    activeTab === "insights"
                      ? "border-b-2 border-gold text-gold"
                      : "text-text-muted hover:text-text-primary hover:bg-panel"
                  }`}
                >
                  <span className="flex items-center justify-center gap-1.5">
                    <Shield className="h-4 w-4" />
                    Insights
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab("chat")}
                  className={`flex-1 py-3 text-center text-sm font-semibold transition-all duration-200 ${
                    activeTab === "chat"
                      ? "border-b-2 border-gold text-gold"
                      : "text-text-muted hover:text-text-primary hover:bg-panel"
                  }`}
                >
                  <span className="flex items-center justify-center gap-1.5">
                    💬 Policy Chat
                    <span className="h-2 w-2 rounded-full bg-emerald" />
                  </span>
                </button>
              </div>

              {/* Tab content */}
              <div className="flex-1 overflow-auto">
                {activeTab === "insights" ? (
                  <div className="p-5">
                    <InsightPanel insights={insights.data} />
                  </div>
                ) : (
                  <ChatPanel
                    documentId={documentId}
                    disabled={!ready}
                    onAnswer={setLastAnswer}
                    entities={insights.data?.entities || []}
                  />
                )}
              </div>
            </aside>
          </div>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
