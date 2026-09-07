"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { DocSchema, DocumentSummary } from "@/lib/types";

export default function HomePage() {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [schemas, setSchemas] = useState<DocSchema[]>([]);
  const [docType, setDocType] = useState("generic");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    try {
      const [d, s] = await Promise.all([api.listDocuments(), api.listSchemas()]);
      setDocs(d);
      setSchemas(s);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleUpload(file: File, runAfter: boolean) {
    setBusy(true);
    setError(null);
    try {
      const doc = await api.uploadDocument(file);
      if (runAfter) {
        const run = await api.runExtraction(doc.id, docType);
        window.location.href = `/review/${run.id}`;
        return;
      }
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function runOn(documentId: string) {
    setBusy(true);
    setError(null);
    try {
      const run = await api.runExtraction(documentId, docType);
      window.location.href = `/review/${run.id}`;
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-semibold">Extract structured data</h1>
        <p className="mt-1 text-(--muted)">
          Upload a document, pick a type, and get application-ready JSON with
          confidence scores and provenance.
        </p>
      </section>

      <section className="rounded-xl border border-(--border) bg-(--surface) p-6">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-(--muted)">Document type</span>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="min-w-52 rounded-lg border border-(--border) bg-(--surface-2) px-3 py-2"
            >
              {schemas.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-(--muted)">File</span>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleUpload(f, true);
              }}
              disabled={busy}
              className="rounded-lg border border-(--border) bg-(--surface-2) px-3 py-2 file:mr-3 file:rounded file:border-0 file:bg-(--accent) file:px-3 file:py-1 file:text-[#0b0f17]"
            />
          </label>

          <span className="text-sm text-(--muted)">
            {busy ? "Working..." : "Uploading runs extraction automatically."}
          </span>
        </div>

        {error && (
          <p className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Documents</h2>
        {docs.length === 0 ? (
          <p className="text-(--muted)">No documents yet.</p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-(--border)">
            <table className="w-full text-left text-sm">
              <thead className="bg-(--surface-2) text-(--muted)">
                <tr>
                  <th className="px-4 py-2">File</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Runs</th>
                  <th className="px-4 py-2">Uploaded</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr
                    key={d.id}
                    className="border-t border-(--border) bg-(--surface)"
                  >
                    <td className="px-4 py-2 font-medium">{d.filename}</td>
                    <td className="px-4 py-2 uppercase text-(--muted)">
                      {d.kind}
                    </td>
                    <td className="px-4 py-2">{d.run_count}</td>
                    <td className="px-4 py-2 text-(--muted)">
                      {d.created_at
                        ? new Date(d.created_at).toLocaleString()
                        : "-"}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => runOn(d.id)}
                        disabled={busy}
                        className="rounded-lg bg-(--accent) px-3 py-1 font-medium text-[#0b0f17] disabled:opacity-50"
                      >
                        Extract
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="text-sm text-(--muted)">
        Tip: manage past runs from the API at{" "}
        <Link href="http://localhost:8000/docs" className="text-(--accent)">
          /docs
        </Link>
        .
      </section>
    </div>
  );
}
