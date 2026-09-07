export interface DocumentSummary {
  id: string;
  filename: string;
  kind: string;
  size_bytes: number;
  created_at: string | null;
  run_count: number;
  runs?: RunSummary[];
}

export interface RunSummary {
  id: string;
  doc_type: string;
  overall_confidence: number;
  created_at: string | null;
}

export interface FieldIssue {
  severity: "error" | "warning";
  message: string;
}

export interface ExtractedField {
  value: unknown;
  type: string;
  many: boolean;
  confidence: number;
  needs_review: boolean;
  page: number | null;
  source_text: string | null;
  issues: FieldIssue[];
  corrected?: boolean;
}

export interface ExtractionResult {
  doc_type: string;
  schema_name: string;
  schema_version: string;
  meta: {
    pages: number;
    chunks: number;
    used_ocr: boolean;
    provider: string;
    model: string;
    errors: string[];
  };
  fields: Record<string, ExtractedField>;
  data: Record<string, unknown>;
  review: {
    overall_confidence: number;
    needs_review_fields: string[];
    review_threshold: number;
  };
}

export interface ExtractionRun {
  id: string;
  document_id: string;
  doc_type: string;
  provider: string;
  model: string;
  status: string;
  overall_confidence: number;
  created_at: string | null;
  result: ExtractionResult;
}

export interface DocSchema {
  key: string;
  name: string;
  description: string;
  version: string;
  fields: { name: string; type: string; required: boolean; many: boolean }[];
}
