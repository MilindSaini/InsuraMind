"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());
  useEffect(() => {
    const onError = (ev: ErrorEvent) => {
      const msg = ev?.error?.message || ev?.message || "";
      if (typeof msg === "string" && (msg.includes("Loading chunk") || msg.includes("ChunkLoadError"))) {
        // stale cached chunk — reload to fetch newest build
        console.warn("ChunkLoadError detected, reloading to recover");
        window.location.reload();
      }
    };

    const onReject = (ev: PromiseRejectionEvent) => {
      const reason = (ev?.reason && (ev.reason.message || ev.reason)) || "";
      if (typeof reason === "string" && reason.includes("Loading chunk")) {
        console.warn("Unhandled promise rejection for chunk load, reloading");
        window.location.reload();
      }
    };

    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onReject);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onReject);
    };
  }, []);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
