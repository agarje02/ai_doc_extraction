# AI Document Intelligence & Entity Extraction

An AI-powered document processing pipeline that extracts structured, application-ready
information from unstructured documents (PDFs, scans/images, DOCX, TXT).

It ingests a document, extracts text (with an OCR fallback for scans), chunks it,
runs LLM-based entity extraction against a configurable schema, then validates,
scores confidence, and post-processes the result into consistent JSON. A Next.js
review UI lets a human inspect low-confidence fields side-by-side with the source
document and correct them.

```
ingestion -> text extraction (+OCR) -> chunking -> LLM extraction ->
validation -> confidence scoring -> post-processing -> structured JSON
```

## Features

- **Multi-format ingestion** - PDF (native text), scanned PDFs & images (OCR via Tesseract), DOCX, TXT/MD.
- **Provider-agnostic LLM layer** - OpenAI, Anthropic, local Ollama, or a built-in offline `mock` provider, selected purely via config.
- **Schema-driven extraction** - built-in `invoice`, `resume`, `contract` types plus a `generic` "bring-your-own JSON schema" mode. New types are a few lines of declarative fields.
- **Confidence + provenance** - every field carries a confidence score (model self-report blended with a source-text heuristic) and the page/snippet it came from.
- **Validation & post-processing** - type/format/regex/enum validation, plus normalization of dates (ISO), currency/numbers, phones, and emails.
- **Human-in-the-loop review UI** - document preview beside editable fields, low-confidence highlighting, one-click corrections, re-run, and JSON/CSV export.
- **Reusable workflows** - register a doc type once and reuse it; batch documents through the API or CLI.
- **Three entry points** - REST API, Typer CLI, and web UI, all sharing one pipeline. Runs and corrections are persisted in SQLite.

## Layout

```
ai_doc_extraction/
  backend/            FastAPI + pipeline (Python)
    app/
      core/           ingestion, text_extraction, chunking, prompts,
                      extract, validation, confidence, postprocess, llm/
      schemas/        declarative doc-type schemas + registry
      models/         SQLAlchemy models (SQLite)
      workflows/      pipeline + service (pipeline + persistence)
      api/routes/     documents, extractions, schemas endpoints
      cli.py          Typer CLI
    samples/          example documents
    tests/            pytest smoke + unit tests (use the mock provider)
  frontend/           Next.js review UI (TypeScript + Tailwind)
  docs/ARCHITECTURE.md
```

## Quickstart

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env       # defaults to the offline mock provider
.\.venv\Scripts\python.exe run_api.py
```

API is now at http://localhost:8000 (interactive docs at `/docs`).

Try the CLI without any API key (uses the `mock` provider):

```powershell
.\.venv\Scripts\python.exe -m app.cli extract .\samples\invoice.txt --doc-type invoice
.\.venv\Scripts\python.exe -m app.cli schemas
```

### 2. Frontend

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local   # NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev
```

Open http://localhost:3000, upload a document, and review the extracted fields.

## Choosing an LLM provider

Set these in `backend/.env`:

| Provider    | `LLM_PROVIDER` | Needs                                   |
| ----------- | -------------- | --------------------------------------- |
| Offline mock| `mock`         | nothing (deterministic, for demos/tests)|
| OpenAI      | `openai`       | `OPENAI_API_KEY`, e.g. `LLM_MODEL=gpt-4o-mini` |
| Anthropic   | `anthropic`    | `ANTHROPIC_API_KEY`, e.g. `LLM_MODEL=claude-3-5-sonnet-latest` |
| Ollama      | `ollama`       | local Ollama, e.g. `LLM_MODEL=llama3.1` |

## Database (SQLite, Postgres, or Supabase)

Persistence goes through SQLAlchemy and a single `DATABASE_URL`, so switching
databases needs no code changes.

- **SQLite (default)** - `DATABASE_URL=sqlite:///./ai_doc_extraction.db`, nothing to install.
- **PostgreSQL / Supabase** - install the driver and point `DATABASE_URL` at your instance:

```powershell
.\.venv\Scripts\python.exe -m pip install "psycopg[binary]"   # or: pip install .[postgres]
```

In Supabase, copy **Project Settings -> Database -> Connection string -> URI** into `.env`:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_REF.supabase.co:5432/postgres
```

A bare `postgres://` / `postgresql://` URL is automatically upgraded to the
psycopg (v3) driver, `pool_pre_ping` is enabled for hosted databases, and JSON
columns are stored as `JSONB` on Postgres. Tables are created automatically on
first run. For serverless/edge deployments, use Supabase's transaction pooler
URL (port `6543`).

## OCR (scanned PDFs & images)

OCR uses [Tesseract](https://github.com/tesseract-ocr/tesseract) and
[Poppler](https://poppler.freedesktop.org/) (for rendering PDF pages).
Install both, then set `TESSERACT_CMD` and `POPPLER_PATH` in `.env` if they are
not on your PATH. OCR only kicks in when a page has little/no native text.

## REST API (summary)

| Method | Path                              | Purpose                          |
| ------ | --------------------------------- | -------------------------------- |
| POST   | `/documents`                      | Upload a document                |
| GET    | `/documents`                      | List documents                   |
| GET    | `/documents/{id}/file`            | Download/preview the raw file    |
| POST   | `/extractions`                    | Run extraction on a document     |
| GET    | `/extractions/{id}`               | Get a run + full result          |
| POST   | `/extractions/{id}/corrections`   | Save a human correction          |
| GET    | `/extractions/{id}/export?format=`| Export result as `json` or `csv` |
| GET    | `/schemas`                        | List doc-type schemas            |
| POST   | `/schemas`                        | Register a reusable schema       |

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

The tests run entirely on the offline `mock` provider, so no API keys or network
access are required.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a deeper walkthrough.
