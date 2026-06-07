"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useMemo, useRef } from "react";
import { AppShell } from "@/components/app-shell";
import { AuthGuard } from "@/components/auth-guard";
import { Badge } from "@/components/ui/badge";
import { listDocuments, deleteDocument, uploadDocument } from "@/services/api";
import { formatBytes, formatDate } from "@/lib/utils";
import {
  Search,
  ChevronDown,
  FileText,
  Image,
  FileSpreadsheet,
  File,
  MoreVertical,
  Plus,
  Trash2,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";
import type { DocumentItem } from "@/types";

const filterChips = ["All", "Policies", "Claims", "Invoices", "Recently Added"];

export default function AllDocumentsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("All");
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const documents = useQuery({ queryKey: ["documents"], queryFn: listDocuments, refetchInterval: 5000 });
  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });
  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  const filtered = useMemo(() => {
    let docs = documents.data || [];
    if (search.trim()) {
      const q = search.toLowerCase();
      docs = docs.filter((d) => d.fileName.toLowerCase().includes(q));
    }
    if (activeFilter === "Recently Added") {
      docs = [...docs].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
    }
    return docs;
  }, [documents.data, search, activeFilter]);

  return (
    <AuthGuard>
      <AppShell>
        <div className="animate-enter">
          {/* Header */}
          <div className="mb-6">
            <h1 className="font-heading text-display-xl text-text-primary">All Documents</h1>
            <p className="mt-1 text-body-md text-text-muted">
              Manage, search, and securely access all your legal and insurance files.
            </p>
          </div>

          {/* Search + Sort */}
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[240px]">
              <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search documents..."
                className="h-12 w-full rounded-input border border-line bg-surface-secondary pl-12 pr-4 text-body-md outline-none transition-all focus:border-gold focus:shadow-gold-glow"
              />
            </div>
            <div className="flex items-center gap-2 text-sm text-text-muted">
              <span>Sort by:</span>
              <button className="btn-ghost !h-10 gap-1.5">
                Date Added
                <ChevronDown className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Filter chips */}
          <div className="mb-6 flex flex-wrap gap-2">
            {filterChips.map((chip) => (
              <button
                key={chip}
                onClick={() => setActiveFilter(chip)}
                className={`rounded-badge px-4 py-1.5 text-sm font-medium transition-all duration-200 ${
                  activeFilter === chip
                    ? "bg-emerald text-white shadow-sm"
                    : "bg-surface-secondary text-text-secondary border border-line hover:border-gold hover:bg-gold-surface"
                }`}
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Document list */}
          <div className="space-y-3">
            {filtered.length === 0 ? (
              <div className="rounded-card border border-line bg-white p-12 text-center">
                <FileText className="mx-auto h-12 w-12 text-text-muted/40" />
                <p className="mt-3 text-body-md text-text-muted">No documents found.</p>
              </div>
            ) : (
              filtered.map((doc) => (
                <div
                  key={doc.id}
                  className="group relative flex items-center gap-4 rounded-card border border-line bg-white p-4 transition-all duration-200 hover:shadow-card-hover hover:-translate-y-0.5"
                >
                  {/* File icon */}
                  <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-input ${fileIconBg(doc)}`}>
                    {fileIcon(doc)}
                  </div>

                  {/* File info */}
                  <Link href={`/documents/${doc.id}`} className="flex-1 min-w-0">
                    <p className="truncate font-heading text-sm font-semibold text-text-primary">
                      {doc.fileName}
                    </p>
                    <p className="text-caption text-text-muted">
                      {formatBytes(doc.sizeBytes)} · {formatDate(doc.createdAt)}
                    </p>
                  </Link>

                  {/* Status badge */}
                  <Badge variant={statusVariant(doc.status)}>
                    {doc.status === "PROCESSING" && (
                      <span className="mr-1 inline-block h-2 w-2 animate-spin rounded-full border border-accent border-t-transparent" />
                    )}
                    {doc.status === "READY" && <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-emerald" />}
                    {doc.status === "FAILED" && <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-danger" />}
                    {doc.status}
                  </Badge>

                  {/* Menu */}
                  <div className="relative">
                    <button
                      onClick={() => setMenuOpenId(menuOpenId === doc.id ? null : doc.id)}
                      className="flex h-9 w-9 items-center justify-center rounded-full text-text-muted transition-all hover:bg-panel hover:text-text-primary"
                      aria-label="Document actions"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>
                    {menuOpenId === doc.id && (
                      <div className="absolute right-0 top-10 z-30 w-40 rounded-input border border-line bg-white py-1 shadow-lg">
                        <Link
                          href={`/documents/${doc.id}`}
                          className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-panel"
                          onClick={() => setMenuOpenId(null)}
                        >
                          <ExternalLink className="h-4 w-4" /> Open
                        </Link>
                        <button
                          onClick={() => {
                            if (confirm(`Delete "${doc.fileName}"?`)) {
                              remove.mutate(doc.id);
                            }
                            setMenuOpenId(null);
                          }}
                          className="flex w-full items-center gap-2 px-3 py-2 text-sm text-danger hover:bg-danger-surface"
                        >
                          <Trash2 className="h-4 w-4" /> Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* FAB: Upload */}
          <input
            ref={inputRef}
            type="file"
            hidden
            accept=".pdf,.png,.jpg,.jpeg,.docx,.zip"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload.mutate(file);
              if (inputRef.current) inputRef.current.value = "";
            }}
          />
          <button
            onClick={() => inputRef.current?.click()}
            className="fixed bottom-6 right-6 z-20 flex h-14 w-14 items-center justify-center rounded-full bg-emerald text-white shadow-lg transition-all duration-200 hover:bg-emerald-light hover:shadow-xl hover:-translate-y-1"
            aria-label="Upload document"
          >
            <Plus className="h-6 w-6" />
          </button>
        </div>
      </AppShell>
    </AuthGuard>
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
