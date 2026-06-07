"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AuthGuard } from "@/components/auth-guard";
import { DocumentTable } from "@/components/document/document-table";
import { UploadZone } from "@/components/upload/upload-zone";
import { deleteDocument, listDocuments, uploadDocument, currentUser } from "@/services/api";
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  Upload,
  Search,
  SlidersHorizontal,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const user = currentUser();
  const documents = useQuery({ queryKey: ["documents"], queryFn: listDocuments, refetchInterval: 5000 });
  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });
  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  const docs = documents.data || [];
  const totalDocs = docs.length;
  const analyzedDocs = docs.filter((d) => d.status === "READY").length;
  const riskAlerts = docs.filter((d) => d.status === "FAILED").length;

  const greeting = getGreeting();
  const firstName = user?.fullName?.split(" ")[0] || "there";

  return (
    <AuthGuard>
      <AppShell>
        <div className="space-y-6 animate-enter">
          {/* ── Hero Welcome Banner ── */}
          <section className="relative overflow-hidden rounded-card bg-gradient-to-br from-navy-teal to-navy p-8 text-white">
            <div className="relative z-10 flex flex-wrap items-center justify-between gap-4">
              <div>
                <h1 className="font-heading text-display-xl text-white">
                  {greeting}, {firstName}
                </h1>
                <p className="mt-2 text-body-md text-text-on-dark-muted">
                  You have {analyzedDocs} documents analyzed
                </p>
              </div>
              <button
                onClick={() => {
                  const el = document.getElementById("upload-zone");
                  el?.scrollIntoView({ behavior: "smooth" });
                }}
                className="btn-secondary !border-gold-light/40 !text-gold-light hover:!bg-gold-light/10 flex items-center gap-2"
              >
                <Upload className="h-5 w-5" />
                Upload new document
              </button>
            </div>
            {/* Ambient gradient overlay */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background:
                  "radial-gradient(ellipse at 70% 20%, rgba(201, 168, 76, 0.08) 0%, transparent 50%), radial-gradient(ellipse at 20% 80%, rgba(27, 122, 78, 0.06) 0%, transparent 50%)",
              }}
            />
          </section>

          {/* ── Stat Cards ── */}
          <section className="grid gap-4 sm:grid-cols-3">
            <StatCard
              icon={<FileText className="h-5 w-5 text-accent" />}
              label="Total Docs"
              value={totalDocs}
              bgColor="bg-accent-surface"
              delay="animate-enter-delay-1"
            />
            <StatCard
              icon={<CheckCircle2 className="h-5 w-5 text-emerald" />}
              label="Analyzed"
              value={analyzedDocs}
              bgColor="bg-emerald-surface"
              delay="animate-enter-delay-2"
            />
            <StatCard
              icon={<AlertTriangle className="h-5 w-5 text-warning" />}
              label="Risk Alerts"
              value={riskAlerts}
              bgColor="bg-warning-surface"
              delay="animate-enter-delay-3"
            />
          </section>

          {/* ── Main Content Grid ── */}
          <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
            {/* Left: Search + Document Table */}
            <div className="space-y-4">
              {/* Search bar */}
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-muted" />
                  <input
                    type="text"
                    placeholder="Search documents..."
                    className="h-12 w-full rounded-input border border-line bg-white pl-12 pr-4 text-body-md text-text-primary outline-none transition-all focus:border-gold focus:shadow-gold-glow"
                  />
                </div>
                <button className="btn-ghost">
                  <SlidersHorizontal className="h-4 w-4" />
                  Filter
                </button>
              </div>

              {/* Document table */}
              <DocumentTable
                documents={docs.slice(0, 5)}
                onDelete={(id) => remove.mutate(id)}
                deletingId={remove.isPending ? (remove.variables as string) : null}
              />

              {/* View all link */}
              {docs.length > 0 && (
                <div className="flex justify-center">
                  <Link
                    href="/documents"
                    className="inline-flex items-center gap-2 rounded-button border border-line bg-white px-6 py-2.5 text-sm font-medium text-text-secondary transition-all hover:border-gold hover:text-gold hover:shadow-sm"
                  >
                    View all documents
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              )}
            </div>

            {/* Right: Upload Zone */}
            <div id="upload-zone">
              <UploadZone onUpload={async (file) => { await upload.mutateAsync(file); }} />
              {upload.error && (
                <p className="mt-3 text-sm text-danger">Upload failed. Check backend and MinIO.</p>
              )}
            </div>
          </div>
        </div>
      </AppShell>
    </AuthGuard>
  );
}

function StatCard({
  icon,
  label,
  value,
  bgColor,
  delay = "",
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  bgColor: string;
  delay?: string;
}) {
  return (
    <div
      className={`animate-enter ${delay} rounded-card border border-line bg-white p-6 transition-all duration-200 hover:shadow-card-hover hover:-translate-y-0.5`}
    >
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-input ${bgColor}`}>
          {icon}
        </div>
        <span className="text-body-sm text-text-muted">{label}</span>
      </div>
      <p className="mt-3 font-heading text-[2.5rem] font-bold leading-none text-text-primary">{value}</p>
    </div>
  );
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
