"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, ExternalLink, FileText } from "lucide-react";
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
  citations = []
}: {
  documentId: string;
  highlights?: Chunk[];
  citations?: Citation[];
}) {
  const previewBlob = useQuery({
    queryKey: ["document-preview", documentId],
    queryFn: () => getDocumentPreviewBlob(documentId),
    staleTime: 10 * 60 * 1000
  });
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [selectedPage, setSelectedPage] = useState(1);

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
    return <div className="flex h-full items-center justify-center text-sm text-muted">Loading document...</div>;
  }

  if (previewBlob.isError || previewError || !previewUrl) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6 text-center text-sm text-muted">
        <FileText className="mb-2 h-8 w-8" />
        <p>Document preview is unavailable.</p>
        {previewError && <p className="mt-2 max-w-xl text-risk">{previewError}</p>}
      </div>
    );
  }

  return (
    <div className="grid min-h-[680px] gap-3 lg:grid-rows-[auto_1fr_auto]">
      <div className="flex items-center justify-between rounded-lg border border-line bg-white px-3 py-2">
        <div className="flex items-center gap-2">
          <button
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-line disabled:opacity-40"
            onClick={() => setSelectedPage((page) => previousPage(page, highlightPages))}
            disabled={highlightPages.length === 0 || selectedPage <= highlightPages[0]}
            aria-label="Previous highlighted page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <label className="flex items-center gap-2 text-sm font-medium">
            Page
            <select
              value={selectedPage}
              onChange={(event) => setSelectedPage(Number(event.target.value))}
              className="h-9 rounded-md border border-line bg-white px-2 text-sm outline-none focus:border-brand"
            >
              {pageOptions(highlightPages, selectedPage).map((page) => (
                <option key={page} value={page}>
                  {page}
                </option>
              ))}
            </select>
          </label>
          <button
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-line disabled:opacity-40"
            onClick={() => setSelectedPage((page) => nextPage(page, highlightPages))}
            disabled={highlightPages.length === 0 || selectedPage >= highlightPages[highlightPages.length - 1]}
            aria-label="Next highlighted page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
        <a
          href={previewUrl || undefined}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-panel"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          Open in new tab
        </a>
      </div>

      <div className="overflow-auto rounded-lg border border-line bg-white p-3">
        <div className="h-[760px] overflow-hidden rounded-md border border-line bg-slate-50">
          <iframe key={selectedPage} title="PDF preview" src={iframeSrc} className="h-full w-full" />
        </div>
      </div>

      <div className="rounded-lg border border-line bg-white p-3">
        <div className="mb-2 flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Highlights on page {selectedPage}</h2>
          <span className="text-xs text-muted">{pageItems.length} source matches</span>
        </div>
        {pageItems.length === 0 ? (
          <p className="text-sm text-muted">No cited or high-risk clauses are mapped to page {selectedPage}.</p>
        ) : (
          <div className="grid gap-2">
            {pageItems.map((item) => (
              <article
                key={item.id}
                className={`rounded-md border p-3 ${
                  item.source === "answer" ? "border-blue-200 bg-blue-50" : "border-line bg-panel"
                }`}
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="text-xs font-medium uppercase text-muted">{item.sectionType.replaceAll("_", " ")}</span>
                  <span className="text-xs text-muted">{item.label}</span>
                </div>
                <p className="line-clamp-3 text-sm text-ink">{item.text}</p>
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
      source: "answer" as const
    })),
    ...chunks.map((chunk) => ({
      id: `insight-${chunk.id}`,
      label: chunk.citationLabel || `p.${chunk.pageNumber || "?"}`,
      pageNumber: chunk.pageNumber,
      sectionType: chunk.sectionType,
      text: chunk.text,
      riskLevel: chunk.riskLevel,
      source: "insight" as const
    }))
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
