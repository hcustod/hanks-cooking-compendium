from uuid import UUID
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.engine import Result

from database.db import get_engine
from database.models import recipes as recipes_table
from ..scraper_bridge import import_url

router = APIRouter(tags=["recipes"])

def row_to_dict(row) -> dict[str, Any]:
    return dict(row._mapping)

# GET /api/recipes
@router.get("/api/recipes")
def list_recipes(
    q: str | None = Query(default=None, description="Search by title (ILIKE)"),
    host: str | None = Query(default=None, description="Filter by source_host"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    engine = get_engine()
    stmt = select(recipes_table)
    if host:
        stmt = stmt.where(recipes_table.c.source_host == host)
    if q:
        stmt = stmt.where(recipes_table.c.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(recipes_table.c.created_at.desc()).limit(limit).offset(offset)

    with engine.connect() as conn:
        rows: Result = conn.execute(stmt).fetchall()
    return [row_to_dict(r) for r in rows]

# GET /api/recipes/{rid}
@router.get("/api/recipes/{rid}")
def get_recipe(rid: UUID):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(recipes_table).where(recipes_table.c.id == rid)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return row_to_dict(row)

# POST /api/import
@router.post("/api/import")
def import_recipe(url: HttpUrl = Query(..., description="Recipe URL to scrape")):
    # scrape + upsert - returns the recipe ID
    rid = import_url(str(url))
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(recipes_table).where(recipes_table.c.id == rid)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Saved recipe not found after import")
    return row_to_dict(row)
