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

export default function HomePage() {
  const [ownerId, setOwnerId] = useState<string | null>(null);
  const [ownerReady, setOwnerReady] = useState(false);
  const [idInput, setIdInput] = useState("");
  const [idError, setIdError] = useState<string | null>(null);

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

  // Load a previously validated id from localStorage on first render.
  useEffect(() => {
    const stored =
      typeof window !== "undefined"
        ? window.localStorage.getItem(OWNER_ID_STORAGE_KEY)
        : null;
    if (stored && OWNER_ID_RE.test(stored)) {
      setOwnerId(stored);
    }
    setOwnerReady(true);
  }, []);

  // Whenever the active id changes, (re)load its documents + schemas.
  useEffect(() => {
    if (ownerId) refresh(ownerId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ownerId]);

  function submitId(e: React.FormEvent) {
    e.preventDefault();
    const candidate = idInput.trim();
    if (!OWNER_ID_RE.test(candidate)) {
      setIdError(
        "Use 3-128 characters: letters, numbers, hyphen or underscore."
      );
      return;
    }
    setIdError(null);
    window.localStorage.setItem(OWNER_ID_STORAGE_KEY, candidate);
    setDocs([]);
    setError(null);
    setOwnerId(candidate);
  }

  function changeId() {
    window.localStorage.removeItem(OWNER_ID_STORAGE_KEY);
    setIdInput(ownerId ?? "");
    setDocs([]);
    setError(null);
    setOwnerId(null);
  }

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

  // Avoid a flash of the wrong screen before localStorage is read.
  if (!ownerReady) return null;

  // ID gate: require a validated id before showing any files.
  if (!ownerId) {
    return (
      <div className="mx-auto max-w-md space-y-6">
        <section>
          <h1 className="text-3xl font-semibold tracking-tight">
            Enter your ID
          </h1>
          <p className="mt-2 text-(--muted)">
            Your documents are scoped to this ID. Enter it to view and upload
            files linked to it.
          </p>
        </section>

        <form
          onSubmit={submitId}
          className="space-y-4 rounded-2xl border border-(--border) bg-(--surface) p-6 shadow-(--shadow)"
        >
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium text-(--muted)">ID</span>
            <input
              autoFocus
              value={idInput}
              onChange={(e) => setIdInput(e.target.value)}
              placeholder="e.g. acme-team-01"
              className="rounded-lg border border-(--border) bg-(--surface-2) px-3 py-2 text-(--text)"
            />
          </label>

          {idError && (
            <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-500">
              {idError}
            </p>
          )}

          <button
            type="submit"
            className="w-full rounded-lg bg-(--accent) px-3 py-2 font-medium text-(--accent-foreground) transition-colors hover:bg-(--accent-hover)"
          >
            Continue
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">
            Extract structured data
          </h1>
          <div className="flex items-center gap-2 text-sm text-(--muted)">
            <span>
              ID: <span className="font-medium text-(--text)">{ownerId}</span>
            </span>
            <button
              onClick={changeId}
              className="rounded-lg border border-(--border) bg-(--surface-2) px-3 py-1.5 font-medium text-(--text) transition-colors hover:bg-(--surface)"
            >
              Change
            </button>
          </div>
        </div>
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
