"use client";

import { FileText, LogOut, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { logout, currentUser } from "@/services/api";

export function AppShell({ children }: { children: React.ReactNode }) {
  const user = currentUser();
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold text-ink">
            <ShieldCheck className="h-5 w-5 text-brand" />
            InsuraMind
          </Link>
          <div className="flex items-center gap-3 text-sm text-muted">
            <Link href="/dashboard" className="flex items-center gap-1 hover:text-ink">
              <FileText className="h-4 w-4" />
              Documents
            </Link>
            {user && <span>{user.fullName}</span>}
            <button onClick={logout} className="inline-flex items-center gap-1 hover:text-ink">
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}
