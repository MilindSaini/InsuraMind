"use client";

import {
  LayoutDashboard,
  FileText,
  Sparkles,
  Scale,
  Settings,
  LogOut,
  Menu,
  X,
  Shield,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { logout, currentUser } from "@/services/api";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/documents", label: "AI Assistant", icon: Sparkles },
  { href: "/documents", label: "Claims", icon: Scale },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const user = currentUser();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const initials = user?.fullName
    ? user.fullName
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "U";

  return (
    <div className="min-h-screen bg-surface-secondary">
      {/* ── Mobile top bar ── */}
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-line bg-white/90 px-4 backdrop-blur-xl lg:hidden">
        <button
          onClick={() => setSidebarOpen(true)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-input text-text-secondary hover:bg-panel"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <Link href="/dashboard" className="flex items-center gap-2 font-heading text-lg font-bold text-gold">
          <Shield className="h-5 w-5" />
          InsuraMind
        </Link>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-surface text-sm font-semibold text-emerald">
          {initials}
        </div>
      </header>

      {/* ── Mobile sidebar overlay ── */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" onClick={() => setSidebarOpen(false)}>
          <div className="absolute inset-0 bg-navy/40 backdrop-blur-sm" />
        </div>
      )}

      {/* ── Sidebar ── */}
      <aside
        className={`fixed top-0 left-0 z-50 flex h-screen w-sidebar flex-col border-r border-line bg-gold-surface transition-transform duration-300 lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Close button (mobile) */}
        <button
          onClick={() => setSidebarOpen(false)}
          className="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-full text-text-muted hover:bg-panel lg:hidden"
          aria-label="Close menu"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Logo */}
        <div className="flex items-center gap-2 px-6 pt-6 pb-2">
          <Shield className="h-6 w-6 text-gold" />
          <span className="font-heading text-xl font-bold text-gold">InsuraMind</span>
        </div>

        {/* User profile */}
        <div className="flex items-center gap-3 px-6 py-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-surface text-sm font-bold text-emerald">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-text-primary">{user?.fullName || "User"}</p>
            <p className="text-caption text-text-muted">Premium Member</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="mt-2 flex-1 space-y-1 px-3">
          {navItems.map((item) => {
            const isActive =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : item.label === "Documents"
                ? pathname.startsWith("/documents")
                : false;
            return (
              <Link
                key={item.label}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 rounded-input px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "nav-active bg-gold-surface text-gold"
                    : "text-text-secondary hover:bg-panel hover:text-text-primary"
                }`}
              >
                <item.icon className={`h-5 w-5 ${isActive ? "text-gold" : ""}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Bottom section */}
        <div className="space-y-1 border-t border-line px-3 py-4">
          <button
            onClick={() => {
              setSidebarOpen(false);
            }}
            className="flex w-full items-center gap-3 rounded-input px-3 py-2.5 text-sm font-medium text-text-secondary transition-all hover:bg-panel hover:text-text-primary"
          >
            <Settings className="h-5 w-5" />
            Settings
          </button>
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-input px-3 py-2.5 text-sm font-medium text-text-secondary transition-all hover:bg-panel hover:text-danger"
          >
            <LogOut className="h-5 w-5" />
            Logout
          </button>
        </div>

        <div className="px-6 pb-4">
          <p className="text-caption text-text-muted">v2.1.0</p>
        </div>
      </aside>

      {/* ── Main content area ── */}
      <div className="lg:ml-sidebar">
        {/* Desktop top nav */}
        <header className="sticky top-0 z-20 hidden h-16 items-center justify-end border-b border-line bg-white/90 px-6 backdrop-blur-xl lg:flex">
          <div className="flex items-center gap-3">
            {user && <span className="text-sm text-text-secondary">{user.fullName}</span>}
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald text-xs font-bold text-white">
              {initials}
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1280px] px-4 py-6 lg:px-6">{children}</main>

        {/* Footer */}
        <footer className="border-t border-line bg-navy py-4">
          <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-4 px-4 lg:px-6">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-gold" />
              <span className="font-heading text-sm font-bold text-gold">InsuraMind</span>
            </div>
            <p className="text-caption text-text-on-dark-muted">
              © 2024 InsuraMind AI Intelligence. All rights reserved.
            </p>
            <div className="flex flex-wrap gap-4 text-caption text-text-on-dark-muted">
              <span className="cursor-pointer hover:text-text-on-dark">Privacy Policy</span>
              <span className="cursor-pointer hover:text-text-on-dark">Terms of Service</span>
              <span className="cursor-pointer hover:text-text-on-dark">Security</span>
              <span className="cursor-pointer hover:text-text-on-dark">Contact Support</span>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
