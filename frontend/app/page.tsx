"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { DocSchema, DocumentSummary } from "@/lib/types";
import ThemedSelect from "./themed-select";

// Built-in doc types (mirror backend/app/schemas/registry.py) so the dropdown
// always has selectable options even if the /schemas request fails on prod.
const FALLBACK_SCHEMAS: Pick<DocSchema, "key" | "name">[] = [
  { key: "invoice", name: "Invoice" },
  { key: "resume", name: "Resume" },
  { key: "contract", name: "Contract" },
  { key: "generic", name: "Generic" },
];

// localStorage key + validation rule kept in sync with the backend
// (`_OWNER_ID_RE` in backend/app/api/routes/documents.py).
const OWNER_ID_STORAGE_KEY = "ownerId";
const OWNER_ID_RE = /^[A-Za-z0-9_-]{3,128}$/;

// Random, browser-local id. Data is scoped to this id, so it is tied to the
// browser: clearing storage or switching browsers starts a fresh workspace.
function generateOwnerId(): string {
  const rand = globalThis.crypto?.randomUUID?.();
  if (rand) return rand;
  // Fallback for older browsers without crypto.randomUUID.
  return `id-${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
}

export default function HomePage() {
  const [ownerId, setOwnerId] = useState<string | null>(null);
  const [ownerReady, setOwnerReady] = useState(false);

  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [schemas, setSchemas] = useState<DocSchema[]>([]);
  const [schemaWarning, setSchemaWarning] = useState<string | null>(null);
  const [docType, setDocType] = useState("generic");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Always render a non-empty list; prefer live schemas, fall back to built-ins.
  const docTypeOptions = useMemo(
    () =>
      schemas.length > 0
        ? schemas.map((s) => ({ key: s.key, name: s.name }))
        : FALLBACK_SCHEMAS,
    [schemas]
  );

  // Keep the selected type valid against whatever list is shown.
  useEffect(() => {
    if (!docTypeOptions.some((o) => o.key === docType)) {
      setDocType(docTypeOptions[0]?.key ?? "generic");
    }
  }, [docTypeOptions, docType]);

  async function refresh(id: string | null = ownerId) {
    if (id) {
      try {
        const d = await api.listDocuments(id);
        setDocs(d);
      } catch (e) {
        setError((e as Error).message);
      }
    }
    try {
      const s = await api.listSchemas();
      setSchemas(s);
      setSchemaWarning(null);
    } catch {
      setSchemaWarning(
        "Could not load document types from the API. Showing built-in types."
      );
    }
  }

  // Load the browser-local id from localStorage, creating one on first visit.
  useEffect(() => {
    if (typeof window === "undefined") return;
    let id = window.localStorage.getItem(OWNER_ID_STORAGE_KEY);
    if (!id || !OWNER_ID_RE.test(id)) {
      id = generateOwnerId();
      window.localStorage.setItem(OWNER_ID_STORAGE_KEY, id);
    }
    setOwnerId(id);
    setOwnerReady(true);
  }, []);

  // Whenever the active id changes, (re)load its documents + schemas.
  useEffect(() => {
    if (ownerId) refresh(ownerId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ownerId]);

  async function handleUpload(file: File, runAfter: boolean) {
    if (!ownerId) return;
    setBusy(true);
    setError(null);
    try {
      const doc = await api.uploadDocument(file, ownerId);
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

  // Avoid a flash before the browser-local id is resolved from localStorage.
  if (!ownerReady) return null;

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-3xl font-semibold tracking-tight">
          Extract structured data
        </h1>
        <p className="mt-2 max-w-2xl text-(--muted)">
          Upload a document, pick a type, and get application-ready JSON with
          confidence scores and provenance.
        </p>
      </section>

      <section className="rounded-2xl border border-(--border) bg-(--surface) p-6 shadow-(--shadow)">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium text-(--muted)">Document type</span>
            <ThemedSelect
              inputId="doc-type"
              ariaLabel="Document type"
              value={docType}
              onChange={setDocType}
              options={docTypeOptions.map((s) => ({
                value: s.key,
                label: s.name,
              }))}
            />
          </label>

          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium text-(--muted)">File</span>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleUpload(f, true);
              }}
              disabled={busy}
              className="rounded-lg border border-(--border) bg-(--surface-2) px-3 py-2 text-(--text) file:mr-3 file:rounded-md file:border-0 file:bg-(--accent) file:px-3 file:py-1 file:font-medium file:text-(--accent-foreground) hover:file:bg-(--accent-hover)"
            />
          </label>

          <span className="pb-2 text-sm text-(--muted)">
            {busy ? "Working..." : "Uploading runs extraction automatically."}
          </span>
        </div>

        {schemaWarning && (
          <p className="mt-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-500">
            {schemaWarning}
          </p>
        )}

        {error && (
          <p className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-500">
            {error}
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Documents</h2>
        {docs.length === 0 ? (
          <p className="rounded-xl border border-dashed border-(--border) bg-(--surface) px-4 py-8 text-center text-(--muted)">
            No documents yet.
          </p>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-(--border) shadow-(--shadow)">
            <table className="w-full text-left text-sm">
              <thead className="bg-(--surface-2) text-(--muted)">
                <tr>
                  <th className="px-4 py-3 font-medium">File</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Runs</th>
                  <th className="px-4 py-3 font-medium">Uploaded</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr
                    key={d.id}
                    className="border-t border-(--border) bg-(--surface) transition-colors hover:bg-(--surface-2)"
                  >
                    <td className="px-4 py-3 font-medium">{d.filename}</td>
                    <td className="px-4 py-3 uppercase text-(--muted)">
                      {d.kind}
                    </td>
                    <td className="px-4 py-3">{d.run_count}</td>
                    <td className="px-4 py-3 text-(--muted)">
                      {d.created_at
                        ? new Date(d.created_at).toLocaleString()
                        : "-"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => runOn(d.id)}
                        disabled={busy}
                        className="rounded-lg bg-(--accent) px-3 py-1.5 font-medium text-(--accent-foreground) transition-colors hover:bg-(--accent-hover) disabled:opacity-50"
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
    </div>
  );
}
