"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type {
  DocumentSummary,
  ExtractedField,
  ExtractionRun,
} from "@/lib/types";

function confidenceColor(c: number): string {
  if (c >= 0.8) return "#3fb950";
  if (c >= 0.6) return "#d29922";
  return "#f85149";
}

function ConfidenceBadge({ value }: { value: number }) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-semibold"
      style={{
        color: confidenceColor(value),
        border: `1px solid ${confidenceColor(value)}55`,
        background: `${confidenceColor(value)}18`,
      }}
    >
      {Math.round(value * 100)}%
    </span>
  );
}

function toEditString(field: ExtractedField): string {
  if (field.value == null) return "";
  if (Array.isArray(field.value)) return field.value.join("\n");
  return String(field.value);
}

function parseEditValue(field: ExtractedField, raw: string): unknown {
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  if (field.many) {
    return raw
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
  }
  if (["number", "integer", "currency"].includes(field.type)) {
    const n = Number(trimmed.replace(/[^\d.\-]/g, ""));
    return Number.isNaN(n) ? trimmed : n;
  }
  return trimmed;
}

function FieldRow({
  name,
  field,
  onSave,
}: {
  name: string;
  field: ExtractedField;
  onSave: (value: unknown) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(toEditString(field));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(toEditString(field));
  }, [field]);

  async function save() {
    setSaving(true);
    await onSave(parseEditValue(field, draft));
    setSaving(false);
    setEditing(false);
  }

  return (
    <div
      className="rounded-xl border p-4 shadow-(--shadow)"
      style={{
        borderColor: field.needs_review ? "#f8514955" : "var(--border)",
        background: field.needs_review ? "#f8514910" : "var(--surface)",
      }}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-medium">{name}</span>
          <span className="text-xs text-(--muted)">{field.type}</span>
          {field.corrected && (
            <span className="rounded-full border border-(--accent) px-2 py-0.5 text-xs text-(--accent)">
              corrected
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <ConfidenceBadge value={field.confidence} />
          {field.page != null && (
            <span className="text-xs text-(--muted)">p.{field.page}</span>
          )}
        </div>
      </div>

      {editing ? (
        <div className="space-y-2">
          {field.many ? (
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={4}
              className="w-full rounded-lg border border-(--border) bg-(--surface-2) px-3 py-2 text-sm"
            />
          ) : (
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="w-full rounded-lg border border-(--border) bg-(--surface-2) px-3 py-2 text-sm"
            />
          )}
          <div className="flex gap-2">
            <button
              onClick={save}
              disabled={saving}
              className="rounded-lg bg-(--accent) px-3 py-1 text-sm font-medium text-(--accent-foreground) transition-colors hover:bg-(--accent-hover) disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              onClick={() => {
                setEditing(false);
                setDraft(toEditString(field));
              }}
              className="rounded-lg border border-(--border) px-3 py-1 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div
          onClick={() => setEditing(true)}
          className="cursor-text rounded-lg bg-(--surface-2) px-3 py-2 text-sm"
        >
          {field.value == null || field.value === "" ? (
            <span className="text-(--muted)">— (click to add)</span>
          ) : Array.isArray(field.value) ? (
            <ul className="list-inside list-disc space-y-0.5">
              {field.value.map((v, i) => (
                <li key={i}>{String(v)}</li>
              ))}
            </ul>
          ) : (
            String(field.value)
          )}
        </div>
      )}

      {field.source_text && (
        <p className="mt-2 text-xs text-(--muted)">
          source: <span className="italic">“{field.source_text}”</span>
        </p>
      )}
      {field.issues.length > 0 && (
        <ul className="mt-2 space-y-1">
          {field.issues.map((iss, i) => (
            <li
              key={i}
              className={
                iss.severity === "error"
                  ? "text-xs text-red-400"
                  : "text-xs text-amber-400"
              }
            >
              {iss.severity}: {iss.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function DocumentViewer({ doc }: { doc: DocumentSummary | null }) {
  if (!doc) return null;
  const url = api.fileUrl(doc.id);
  if (doc.kind === "image") {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt={doc.filename} className="w-full rounded-lg" />;
  }
  if (doc.kind === "pdf" || doc.kind === "text") {
    return (
      <iframe
        src={url}
        title={doc.filename}
        className="h-[70vh] w-full rounded-lg border border-(--border) bg-white"
      />
    );
  }
  return (
    <div className="rounded-lg border border-(--border) bg-(--surface-2) p-4 text-sm text-(--muted)">
      Preview not available for {doc.kind}.{" "}
      <a href={url} className="text-(--accent)" target="_blank" rel="noreferrer">
        Download {doc.filename}
      </a>
    </div>
  );
}

export default function ReviewPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = use(params);
  const [run, setRun] = useState<ExtractionRun | null>(null);
  const [doc, setDoc] = useState<DocumentSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reRunning, setReRunning] = useState(false);

  async function load() {
    try {
      const r = await api.getExtraction(runId);
      setRun(r);
      const d = await api.getDocument(r.document_id);
      setDoc(d);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const fields = useMemo(
    () => (run ? Object.entries(run.result.fields) : []),
    [run]
  );

  async function saveField(name: string, value: unknown) {
    const updated = await api.correctField(runId, name, value);
    setRun(updated);
  }

  async function reRun() {
    if (!run) return;
    setReRunning(true);
    try {
      const fresh = await api.runExtraction(run.document_id, run.doc_type);
      window.location.href = `/review/${fresh.id}`;
    } catch (e) {
      setError((e as Error).message);
      setReRunning(false);
    }
  }

  if (error) {
    return (
      <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-red-300">
        {error}
      </p>
    );
  }
  if (!run) return <p className="text-(--muted)">Loading…</p>;

  const review = run.result.review;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/" className="text-sm text-(--accent)">
            ← Documents
          </Link>
          <h1 className="mt-1 text-xl font-semibold">
            {run.result.schema_name}{" "}
            <span className="text-(--muted)">· {doc?.filename}</span>
          </h1>
          <p className="text-sm text-(--muted)">
            {run.result.meta.provider}/{run.result.meta.model} ·{" "}
            {run.result.meta.pages} page(s) · {run.result.meta.chunks} chunk(s)
            {run.result.meta.used_ocr ? " · OCR" : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="mr-2 text-right">
            <div className="text-xs text-(--muted)">Overall</div>
            <ConfidenceBadge value={review.overall_confidence} />
          </div>
          <a
            href={api.exportUrl(runId, "json")}
            className="rounded-lg border border-(--border) bg-(--surface) px-3 py-1.5 text-sm transition-colors hover:border-(--accent)"
          >
            Export JSON
          </a>
          <a
            href={api.exportUrl(runId, "csv")}
            className="rounded-lg border border-(--border) bg-(--surface) px-3 py-1.5 text-sm transition-colors hover:border-(--accent)"
          >
            Export CSV
          </a>
          <button
            onClick={reRun}
            disabled={reRunning}
            className="rounded-lg bg-(--accent) px-3 py-1.5 text-sm font-medium text-(--accent-foreground) transition-colors hover:bg-(--accent-hover) disabled:opacity-50"
          >
            {reRunning ? "Re-running…" : "Re-run"}
          </button>
        </div>
      </div>

      {review.needs_review_fields.length > 0 && (
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
          {review.needs_review_fields.length} field(s) flagged for review:{" "}
          {review.needs_review_fields.join(", ")}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="lg:sticky lg:top-6 lg:self-start">
          <h2 className="mb-2 text-sm font-semibold text-(--muted)">
            Source document
          </h2>
          <DocumentViewer doc={doc} />
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-(--muted)">
            Extracted fields
          </h2>
          {fields.map(([name, field]) => (
            <FieldRow
              key={name}
              name={name}
              field={field}
              onSave={(v) => saveField(name, v)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
