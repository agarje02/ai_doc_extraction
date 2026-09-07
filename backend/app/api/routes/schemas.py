"""Doc-type schema endpoints: list built-ins and register reusable schemas."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.base import DocSchema, FieldSpec
from app.schemas.registry import get_schema, has_schema, list_schemas, register_schema

router = APIRouter(prefix="/schemas", tags=["schemas"])


class RegisterSchemaRequest(BaseModel):
    key: str
    name: str
    description: str = ""
    fields: list[FieldSpec]
    overwrite: bool = False


@router.get("")
def get_all_schemas() -> list[dict[str, Any]]:
    return [s.model_dump() for s in list_schemas()]


@router.get("/{key}")
def get_one_schema(key: str) -> dict[str, Any]:
    if not has_schema(key):
        raise HTTPException(status_code=404, detail=f"Unknown schema {key!r}")
    return get_schema(key).model_dump()


@router.post("", status_code=201)
def create_schema(req: RegisterSchemaRequest) -> dict[str, Any]:
    schema = DocSchema(
        key=req.key, name=req.name, description=req.description, fields=req.fields
    )
    try:
        register_schema(schema, overwrite=req.overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return schema.model_dump()
