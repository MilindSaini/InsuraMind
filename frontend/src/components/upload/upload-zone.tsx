"use client";

import { UploadCloud } from "lucide-react";
import { ChangeEvent, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

export function UploadZone({ onUpload }: { onUpload: (file: File) => Promise<void> }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

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
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        void handleFile(e.dataTransfer.files?.[0]);
      }}
      className="flex min-h-40 flex-col items-center justify-center rounded-lg border border-dashed border-line bg-white p-6 text-center"
    >
      <UploadCloud className="mb-3 h-9 w-9 text-brand" />
      <p className="font-medium">Upload a policy or claim document</p>
      <p className="mt-1 text-sm text-muted">PDF, PNG, JPG, DOCX, or ZIP up to 50 MB</p>
      <input ref={inputRef} type="file" hidden onChange={onChange} accept=".pdf,.png,.jpg,.jpeg,.docx,.zip" />
      <Button type="button" className="mt-4" disabled={busy} onClick={() => inputRef.current?.click()}>
        {busy ? "Uploading..." : "Choose file"}
      </Button>
    </div>
  );
}
