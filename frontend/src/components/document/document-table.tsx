"use client";

import { FileText, Image, FileSpreadsheet, File } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { formatBytes, formatDate } from "@/lib/utils";
import type { DocumentItem } from "@/types";

export function DocumentTable({
  documents,
  onDelete,
  deletingId,
}: {
  documents: DocumentItem[];
  onDelete?: (id: string) => void;
  deletingId?: string | null;
}) {
  return (
    <div className="overflow-hidden rounded-card border border-line bg-white">
      {/* Table header */}
      <div className="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-border-subtle px-6 py-3 md:grid-cols-[1fr_120px_auto]">
        <span className="text-caption font-semibold uppercase text-text-muted">Document Name</span>
        <span className="text-caption font-semibold uppercase text-text-muted">Status</span>
        <span className="hidden text-caption font-semibold uppercase text-text-muted md:block">Actions</span>
      </div>

      {/* Rows */}
      {documents.length === 0 ? (
        <div className="p-8 text-center text-body-sm text-text-muted">No documents uploaded yet.</div>
      ) : (
        <div className="divide-y divide-border-subtle">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="group grid grid-cols-[1fr_auto_auto] items-center gap-4 px-6 py-4 transition-all duration-200 hover:bg-gold-surface/30 md:grid-cols-[1fr_120px_auto]"
              style={{ borderLeft: "3px solid transparent" }}
              onMouseEnter={(e) => (e.currentTarget.style.borderLeftColor = "#C9A84C")}
              onMouseLeave={(e) => (e.currentTarget.style.borderLeftColor = "transparent")}
            >
              <Link href={`/documents/${doc.id}`} className="flex min-w-0 items-center gap-3">
                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-input ${fileIconBg(doc)}`}>
                  {fileIcon(doc)}
                </div>
                <div className="min-w-0">
                  <p className="truncate font-heading text-sm font-semibold text-text-primary">{doc.fileName}</p>
                  <p className="text-caption text-text-muted">
                    {formatBytes(doc.sizeBytes)} · Uploaded {formatRelativeTime(doc.createdAt)}
                  </p>
                </div>
              </Link>

              <Badge variant={statusVariant(doc.status)}>
                {doc.status === "PROCESSING" && (
                  <span className="mr-1 inline-block h-2 w-2 animate-spin rounded-full border border-accent border-t-transparent" />
                )}
                {doc.status === "READY" && <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-emerald" />}
                {doc.status === "FAILED" && <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-danger" />}
                {doc.status}
              </Badge>

              <div className="flex items-center">
                {onDelete && (
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      if (confirm(`Delete "${doc.fileName}"? This cannot be undone.`)) {
                        onDelete(doc.id);
                      }
                    }}
                    disabled={deletingId === doc.id}
                    className="flex h-8 w-8 items-center justify-center rounded-full text-text-muted transition-all hover:bg-danger-surface hover:text-danger disabled:opacity-40"
                    title="Delete document"
                    aria-label={`Delete ${doc.fileName}`}
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function statusVariant(status: DocumentItem["status"]): "success" | "processing" | "failed" | "default" {
  if (status === "READY") return "success";
  if (status === "PROCESSING") return "processing";
  if (status === "FAILED") return "failed";
  return "default";
}

function fileIconBg(doc: DocumentItem) {
  const ext = doc.fileName.split(".").pop()?.toLowerCase();
  if (ext === "pdf") return "bg-gold-surface";
  if (["jpg", "jpeg", "png"].includes(ext || "")) return "bg-danger-surface";
  if (ext === "docx") return "bg-accent-surface";
  return "bg-surface-secondary";
}

function fileIcon(doc: DocumentItem) {
  const ext = doc.fileName.split(".").pop()?.toLowerCase();
  if (ext === "pdf") return <FileText className="h-5 w-5 text-gold" />;
  if (["jpg", "jpeg", "png"].includes(ext || "")) return <Image className="h-5 w-5 text-danger" />;
  if (ext === "docx") return <FileSpreadsheet className="h-5 w-5 text-accent" />;
  return <File className="h-5 w-5 text-text-muted" />;
}

function formatRelativeTime(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
