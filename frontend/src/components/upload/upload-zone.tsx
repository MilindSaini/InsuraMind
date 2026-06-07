"use client";

import { UploadCloud } from "lucide-react";
import { ChangeEvent, useRef, useState } from "react";

export function UploadZone({ onUpload }: { onUpload: (file: File) => Promise<void> }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  async function handleFile(file?: File) {
    if (!file) return;
    setBusy(true);
    try {
      await onUpload(file);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function onChange(event: ChangeEvent<HTMLInputElement>) {
    void handleFile(event.target.files?.[0]);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        void handleFile(e.dataTransfer.files?.[0]);
      }}
      className={`flex min-h-[280px] flex-col items-center justify-center rounded-card border-2 border-dashed p-8 text-center transition-all duration-300 ${
        dragOver
          ? "border-gold bg-gold-surface shadow-gold-glow"
          : "border-gold/30 bg-gold-surface/50 hover:border-gold hover:bg-gold-surface"
      }`}
    >
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gold-surface">
        <UploadCloud className={`h-8 w-8 text-gold transition-transform ${dragOver ? "scale-110" : ""}`} />
      </div>
      <p className="font-heading text-lg font-semibold text-text-primary">Drop your document here</p>
      <p className="mt-1.5 text-body-sm text-text-muted">
        Supports PDF, DOCX, JPG, and PNG up to 50MB
      </p>
      <input ref={inputRef} type="file" hidden onChange={onChange} accept=".pdf,.png,.jpg,.jpeg,.docx,.zip" />
      <button
        type="button"
        className="btn-secondary mt-6 !h-10 !text-sm"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
      >
        {busy ? "Uploading..." : "Browse Files"}
      </button>
    </div>
  );
}
