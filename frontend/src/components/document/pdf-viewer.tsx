"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, FileText } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getDocumentPreviewBlob } from "@/services/api";
import type { Chunk, Citation } from "@/types";

type HighlightItem = {
  id: string;
  label: string;
  pageNumber?: number;
  sectionType: string;
  text: string;
  riskLevel?: string;
  source: "answer" | "insight";
};

export function PdfViewer({
  documentId,
  highlights = [],
  citations = [],
}: {
  documentId: string;
  highlights?: Chunk[];
  citations?: Citation[];
}) {
  const previewBlob = useQuery({
    queryKey: ["document-preview", documentId],
    queryFn: () => getDocumentPreviewBlob(documentId),
    staleTime: 10 * 60 * 1000,
  });
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [selectedPage, setSelectedPage] = useState(1);
  const [zoom, setZoom] = useState(100);

  const highlightItems = useMemo(() => mergeHighlights(highlights, citations), [highlights, citations]);
  const highlightPages = useMemo(() => {
    const pages = Array.from(
      new Set(highlightItems.map((item) => item.pageNumber).filter((page): page is number => Boolean(page)))
    );
    return pages.sort((a, b) => a - b);
  }, [highlightItems]);
  const pageItems = highlightItems.filter((item) => item.pageNumber === selectedPage);
  const iframeSrc = previewUrl ? `${previewUrl}#page=${selectedPage}` : "";

  useEffect(() => {
    const firstCitationPage = citations.find((citation) => citation.pageNumber)?.pageNumber;
    const firstHighlightPage = highlightPages[0];
    const firstPage = firstCitationPage || firstHighlightPage;
    if (firstPage && !highlightPages.includes(selectedPage)) {
      setSelectedPage(firstPage);
    }
  }, [citations, highlightPages, selectedPage]);

  useEffect(() => {
    if (!previewBlob.data) {
      setPreviewUrl(null);
      setPreviewError(null);
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    const sourceBlob = previewBlob.data;

    async function preparePreview() {
      const blob = sourceBlob;
      const header = await blob.slice(0, 5).text();
      if (cancelled) return;

      if (header !== "%PDF-") {
        const sample = await blob.slice(0, 160).text().catch(() => "");
        if (cancelled) return;
        setPreviewError(
          sample
            ? `Preview endpoint did not return a PDF. Response starts with: ${sample.slice(0, 80)}`
            : "Preview endpoint did not return a readable PDF."
        );
        setPreviewUrl(null);
        return;
      }

      const pdfBlob = blob.type === "application/pdf" ? blob : new Blob([blob], { type: "application/pdf" });
      objectUrl = URL.createObjectURL(pdfBlob);
      setPreviewUrl(objectUrl);
      setPreviewError(null);
    }

    void preparePreview();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [previewBlob.data]);

  if (previewBlob.isLoading) {
    return (
      <div className="flex h-full items-center justify-center rounded-card border border-line bg-white p-12">
        <div className="text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gold-surface">
            <FileText className="h-6 w-6 text-gold animate-pulse" />
          </div>
          <p className="text-body-sm text-text-muted">Loading document...</p>
        </div>
      </div>
    );
  }

  if (previewBlob.isError || previewError || !previewUrl) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-card border border-line bg-white px-6 py-12 text-center">
        <FileText className="mb-3 h-10 w-10 text-text-muted/40" />
        <p className="text-body-sm text-text-muted">Document preview is unavailable.</p>
        {previewError && <p className="mt-2 max-w-xl text-sm text-danger">{previewError}</p>}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center justify-between rounded-card border border-line bg-white px-4 py-2.5">
        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <button
            onClick={() => setZoom((z) => Math.max(50, z - 25))}
            className="flex h-8 w-8 items-center justify-center rounded-input border border-line text-text-muted hover:bg-panel hover:text-text-primary disabled:opacity-40"
            disabled={zoom <= 50}
            aria-label="Zoom out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="min-w-[3rem] text-center text-body-sm font-medium text-text-primary">{zoom}%</span>
          <button
            onClick={() => setZoom((z) => Math.min(200, z + 25))}
            className="flex h-8 w-8 items-center justify-center rounded-input border border-line text-text-muted hover:bg-panel hover:text-text-primary disabled:opacity-40"
            disabled={zoom >= 200}
            aria-label="Zoom in"
          >
            <ZoomIn className="h-4 w-4" />
          </button>

          <div className="mx-2 h-5 w-px bg-line" />

          {/* Page navigation */}
          <button
            className="flex h-8 w-8 items-center justify-center rounded-input border border-line text-text-muted hover:bg-panel disabled:opacity-40"
            onClick={() => setSelectedPage((page) => previousPage(page, highlightPages))}
            disabled={highlightPages.length === 0 || selectedPage <= (highlightPages[0] ?? 1)}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-2 text-body-sm font-medium">
            <span>Page</span>
            <select
              value={selectedPage}
              onChange={(event) => setSelectedPage(Number(event.target.value))}
              className="h-8 rounded-input border border-line bg-white px-2 text-sm outline-none focus:border-gold"
            >
              {pageOptions(highlightPages, selectedPage).map((page) => (
                <option key={page} value={page}>
                  {page}
                </option>
              ))}
            </select>
            {highlightPages.length > 0 && (
              <span className="text-text-muted">of {highlightPages[highlightPages.length - 1]}</span>
            )}
          </div>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-input border border-line text-text-muted hover:bg-panel disabled:opacity-40"
            onClick={() => setSelectedPage((page) => nextPage(page, highlightPages))}
            disabled={highlightPages.length === 0 || selectedPage >= highlightPages[highlightPages.length - 1]}
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* PDF Viewer */}
      <div className="overflow-hidden rounded-card border border-line bg-white p-3">
        <div
          className="overflow-auto rounded-input border border-border-subtle bg-surface-secondary"
          style={{ height: 680 }}
        >
          <iframe
            key={`${selectedPage}-${zoom}`}
            title="PDF preview"
            src={iframeSrc}
            className="w-full border-none"
            style={{
              height: `${680 * (zoom / 100)}px`,
              transform: `scale(${zoom / 100})`,
              transformOrigin: "top left",
              width: `${100 / (zoom / 100)}%`,
            }}
          />
        </div>
      </div>

      {/* Highlights section */}
      <div className="rounded-card border border-line bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-heading text-sm font-semibold text-text-primary">
            Highlights on page {selectedPage}
          </h2>
          <span className="text-caption text-text-muted">{pageItems.length} source matches</span>
        </div>
        {pageItems.length === 0 ? (
          <p className="text-body-sm text-text-muted">
            No cited or high-risk clauses are mapped to page {selectedPage}.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {pageItems.map((item) => (
              <article
                key={item.id}
                className={`rounded-input border p-3 ${
                  item.source === "answer"
                    ? "border-accent/20 bg-accent-surface"
                    : "border-line bg-surface-secondary"
                }`}
              >
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <span className="text-caption font-semibold text-accent">{item.label}</span>
                </div>
                <p className="line-clamp-3 text-body-sm text-text-secondary">{item.text}</p>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function mergeHighlights(chunks: Chunk[], citations: Citation[]): HighlightItem[] {
  const items: HighlightItem[] = [
    ...citations.map((citation, index) => ({
      id: `answer-${citation.citationLabel || index}`,
      label: citation.citationLabel || `p.${citation.pageNumber || "?"}`,
      pageNumber: citation.pageNumber,
      sectionType: citation.sectionType,
      text: citation.text,
      source: "answer" as const,
    })),
    ...chunks.map((chunk) => ({
      id: `insight-${chunk.id}`,
      label: chunk.citationLabel || `p.${chunk.pageNumber || "?"}`,
      pageNumber: chunk.pageNumber,
      sectionType: chunk.sectionType,
      text: chunk.text,
      riskLevel: chunk.riskLevel,
      source: "insight" as const,
    })),
  ];

  const seen = new Set<string>();
  return items.filter((item) => {
    const key = `${item.pageNumber}-${item.label}-${item.text.slice(0, 80)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function pageOptions(highlightPages: number[], selectedPage: number) {
  const pages = new Set(highlightPages.length ? highlightPages : [selectedPage]);
  pages.add(selectedPage);
  return Array.from(pages).sort((a, b) => a - b);
}

function previousPage(current: number, pages: number[]) {
  const options = pageOptions(pages, current);
  const previous = [...options].reverse().find((page) => page < current);
  return previous || current;
}

function nextPage(current: number, pages: number[]) {
  const options = pageOptions(pages, current);
  const next = options.find((page) => page > current);
  return next || current;
}
