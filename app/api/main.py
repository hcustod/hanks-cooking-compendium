import os
from uuid import UUID
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Result

from database.db import get_engine
from database.models import recipes as recipes_table
from .scraper_bridge import import_url

app = FastAPI(title="HCC API", version="0.1.0")

# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321", "http://localhost:3000", "http://127.0.0.1:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"ok": True}


def row_to_dict(row) -> dict:
    return dict(row.mapping)

@app.get("/get/recipes")
def list_recipes(
    q: str | None = Query(default=None, description="Search by title (ILIKE)"),
    host: str | None = None, 
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    engine = get_engine()
    stmt = select(recipes_table)
    if host: 
        stmt = stmt.where(recipes_table.c.source_host == host)
    if q:
        stmt = stmt.where(recipes_table.c.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(recipes_table.c.created_at.desc()).limit
    with engine.connect() as conn: 
        rows: Result = conn.execute(stmt).fetchall()
    return [row_to_dict(r) for r in rows]
        

@app.get("/api/recipes/{rid}")
def get_target_recipe(rid: UUID):
    engine = get_engine()
    with engine.connect() as conn: 
        row = conn.execute(
            select(recipes_table).where(recipes_table.c.id == rid)
        ).fetchone()
    if not row: 
        raise HTTPException(404, "Recipe not found")
    return row_to_dict(row)

# Scrape URL and insert into DB, return saved row
@app.post("/api/import")
def import_recipe(url: str):
    rid = import_url(url)
    engine = get_engine()
    with engine.connect() as conn: 
        row = conn.execute(
            select(recipes_table).where(recipes_table.c.id == rid)
        ).fetchone()
    if not row: 
        raise HTTPException(500, "Saved recipe not found after import")
    return row_to_dict(row)

app.include_router(recipes.router)
