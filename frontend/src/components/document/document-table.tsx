"use client";

import { FileText } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatBytes, formatDate } from "@/lib/utils";
import type { DocumentItem } from "@/types";

export function DocumentTable({ documents }: { documents: DocumentItem[] }) {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Documents</h2>
      </CardHeader>
      <CardContent className="p-0">
        {documents.length === 0 ? (
          <div className="p-6 text-sm text-muted">No documents uploaded yet.</div>
        ) : (
          <div className="divide-y divide-line">
            {documents.map((doc) => (
              <Link
                key={doc.id}
                href={`/documents/${doc.id}`}
                className="grid grid-cols-[1fr_auto] gap-4 px-4 py-3 transition hover:bg-panel md:grid-cols-[1fr_120px_140px_160px]"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <FileText className="h-5 w-5 shrink-0 text-brand" />
                  <div className="min-w-0">
                    <p className="truncate font-medium">{doc.fileName}</p>
                    <p className="text-xs text-muted">{formatBytes(doc.sizeBytes)}</p>
                  </div>
                </div>
                <Badge className={statusClass(doc.status)}>{doc.status}</Badge>
                <span className="hidden text-sm capitalize text-muted md:block">{doc.documentType || "pending"}</span>
                <span className="hidden text-sm text-muted md:block">{formatDate(doc.createdAt)}</span>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function statusClass(status: DocumentItem["status"]) {
  if (status === "READY") return "border-green-200 bg-green-50 text-ok";
  if (status === "FAILED") return "border-red-200 bg-red-50 text-risk";
  if (status === "PROCESSING") return "border-blue-200 bg-blue-50 text-brand";
  return "";
}
