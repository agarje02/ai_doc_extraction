import type {
  DocSchema,
  DocumentSummary,
  ExtractionRun,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listSchemas: () =>
    fetch(`${API_BASE}/schemas`, { cache: "no-store" }).then((r) =>
      json<DocSchema[]>(r)
    ),

  listDocuments: () =>
    fetch(`${API_BASE}/documents`, { cache: "no-store" }).then((r) =>
      json<DocumentSummary[]>(r)
    ),

  getDocument: (id: string) =>
    fetch(`${API_BASE}/documents/${id}`, { cache: "no-store" }).then((r) =>
      json<DocumentSummary>(r)
    ),

  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${API_BASE}/documents`, {
      method: "POST",
      body: form,
    }).then((r) => json<DocumentSummary>(r));
  },

  runExtraction: (documentId: string, docType: string) =>
    fetch(`${API_BASE}/extractions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: documentId, doc_type: docType }),
    }).then((r) => json<ExtractionRun>(r)),

  getExtraction: (runId: string) =>
    fetch(`${API_BASE}/extractions/${runId}`, { cache: "no-store" }).then((r) =>
      json<ExtractionRun>(r)
    ),

  correctField: (runId: string, fieldName: string, value: unknown) =>
    fetch(`${API_BASE}/extractions/${runId}/corrections`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field_name: fieldName, value }),
    }).then((r) => json<ExtractionRun>(r)),

  exportUrl: (runId: string, format: "json" | "csv") =>
    `${API_BASE}/extractions/${runId}/export?format=${format}`,

  fileUrl: (documentId: string) => `${API_BASE}/documents/${documentId}/file`,
};
