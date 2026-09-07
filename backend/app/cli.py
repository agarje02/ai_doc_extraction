"""Typer CLI for running extractions from the terminal.

Examples::

    python -m app.cli extract ./samples/invoice.txt --doc-type invoice
    python -m app.cli schemas
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from app.core.ingestion import detect_kind
from app.schemas.registry import get_schema, list_schemas
from app.workflows.pipeline import run_on_path

app = typer.Typer(help="AI Document Intelligence & Entity Extraction CLI")


@app.command()
def schemas() -> None:
    """List available document-type schemas."""
    for s in list_schemas():
        field_names = ", ".join(f.name for f in s.fields)
        typer.echo(f"{s.key:10s} {s.name} -> {field_names}")


@app.command()
def extract(
    path: Path = typer.Argument(..., exists=True, readable=True),
    doc_type: str = typer.Option("generic", "--doc-type", "-t"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write JSON here"),
    data_only: bool = typer.Option(False, "--data-only", help="Print only clean values"),
) -> None:
    """Extract structured data from a single document."""
    try:
        schema = get_schema(doc_type)
    except KeyError as exc:
        raise typer.BadParameter(str(exc))

    kind = detect_kind(path.name)
    result = run_on_path(path, kind, schema)
    payload = result["data"] if data_only else result
    text = json.dumps(payload, indent=2, ensure_ascii=False)

    if output:
        output.write_text(text, encoding="utf-8")
        typer.echo(f"Wrote {output}")
    else:
        typer.echo(text)


if __name__ == "__main__":
    app()
