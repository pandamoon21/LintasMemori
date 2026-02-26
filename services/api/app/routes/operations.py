from __future__ import annotations

from fastapi import APIRouter

from ..operation_catalog import catalog_entries

router = APIRouter(prefix="/api/operations", tags=["operations"])


@router.get("/catalog")
def get_operation_catalog() -> list[dict]:
    return catalog_entries()
