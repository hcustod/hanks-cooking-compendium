import os
import sys
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from database.db import get_engine
from database.models import recipes as recipes_table

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(0, REPO_ROOT)

from packages.recipe_scraper import scrape

DEFAULT_USER = UUID(
    os.getenv("HCC_DEFAULT_USER", "00000000-0000-0000-0000-000000000000")
)

def upsert_recipe( user_id: UUID, rec: dict) -> UUID:
    now = datetime.now(tz=timezone.utc)
    row = {
        "user_id": user_id,
        "title": rec.get("title"),
        "description": rec.get("description"),
        "servings": rec.get("servings"),
        "prep_time_mins": rec.get("prep_time_mins"),
        "cook_time_mins": rec.get("cook_time_mins"),
        "total_time_mins": rec.get("total_time_mins"),
        "ingredients": rec.get("ingredients") or [],
        "steps": rec.get("steps") or [],
        "source_url": rec["source_url"],
        "source_host": rec.get("source_host"),
        "extraction": rec.get("extraction") or "Structured",
        "legal_note": rec.get("legal_note") or ( "For personal use only. Do not distribute or republish without permission." if rec.get("extraction") == "Structured" else None ),
        "raw_json": rec, 
        "created_at": now,
        "updated_at": now,
    }

    engine = get_engine()
    stmt = pg_insert(recipes_table).values(**ow).on_conflict_do_update(
        index_elements=[recipes_table.c.user_id, recipes_table.c.source_url],
        set_={
            "title": row["title"],
            "description": row["description"],
            "servings": row["servings"],
            "prep_time_mins": row["prep_time_mins"],
            "cook_time_mins": row["cook_time_mins"],
            "total_time_mins": row["total_time_mins"],
            "ingredients": row["ingredients"],
            "steps": row["steps"],
            "source_host": row["source_host"],
            "extraction": row["extraction"],
            "legal_note": row["legal_note"],
            "raw_json": row["raw_json"],
            "updated_at": now,
        },
    )

    with engine.begin() as conn:
        conn.execute(stmt)
        rid = conn.execute(
            select(recipes_table.c.id).where(
                (recipes_table.c.user_id == row[user_id])
                & (recipes_table.c.source_url == row["source_url"])
            )
        ).scalar_one()
        return rid
    
def import_url(url: str, user_id: UUID | None = None ) -> UUID:
    rec = scrape(url)
    return upsert_recipe(user_id or DEFAULT_USER, rec)

 