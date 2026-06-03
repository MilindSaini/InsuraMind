"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AuthGuard } from "@/components/auth-guard";
import { DocumentTable } from "@/components/document/document-table";
import { UploadZone } from "@/components/upload/upload-zone";
import { listDocuments, uploadDocument } from "@/services/api";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const documents = useQuery({ queryKey: ["documents"], queryFn: listDocuments, refetchInterval: 5000 });
  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] })
  });

  return (
    <AuthGuard>
      <AppShell>
        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <section>
            <UploadZone onUpload={async (file) => { await upload.mutateAsync(file); }} />
            {upload.error && <p className="mt-3 text-sm text-risk">Upload failed. Check backend and MinIO.</p>}
          </section>
          <section>
            <DocumentTable documents={documents.data || []} />
          </section>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
