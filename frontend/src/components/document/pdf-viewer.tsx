"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { getFileUrl } from "@/services/api";

export function PdfViewer({ documentId }: { documentId: string }) {
  const fileUrl = useQuery({
    queryKey: ["file-url", documentId],
    queryFn: () => getFileUrl(documentId),
    staleTime: 10 * 60 * 1000
  });

  if (fileUrl.isLoading) {
    return <div className="flex h-full items-center justify-center text-sm text-muted">Loading document...</div>;
  }

  if (!fileUrl.data?.url) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-sm text-muted">
        <FileText className="mb-2 h-8 w-8" />
        Document preview is unavailable.
      </div>
    );
  }

  return (
    <iframe
      title="Document preview"
      src={fileUrl.data.url}
      className="h-full min-h-[620px] w-full rounded-lg border border-line bg-white"
    />
  );
}
