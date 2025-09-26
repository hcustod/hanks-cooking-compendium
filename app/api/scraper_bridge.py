import os
import sys
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database.db import get_engine
from database.models import recipes as recipes_table

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from packages.recipe_scraper import scrape 

DEFAULT_USER = UUID(os.getenv("HCC_DEFAULT_USER", "00000000-0000-0000-0000-000000000000"))

def upsert_recipe(user_id: UUID, rec: dict) -> UUID:
    """
    Insert or update a recipe based on (user_id, source_url) unique constraint.
    Return the recipe ID.
    """
    now = datetime.now(tz=timezone.utc)

    row = {
        "user_id": user_id,
        "title": rec.get("title"),
        "description": rec.get("description"),
        "servings": rec.get("servings"),
        "prep_time_min": rec.get("prep_time_min"),
        "cook_time_min": rec.get("cook_time_min"),
        "total_time_min": rec.get("total_time_min"),
        "ingredients": rec.get("ingredients") or [],
        "steps": rec.get("steps") or [],
        "source_url": rec["source_url"],
        "source_host": rec.get("source_host"),
        "extraction": (rec.get("extraction") or "structured").lower(),
        "legal_note": rec.get("legal_note")
            or "For personal use/research only. Do not republish; see the original source link.",
        "raw_json": rec,
        "created_at": now,
        "updated_at": now,
    }

    engine = get_engine()
    stmt = (
        pg_insert(recipes_table)
        .values(**row)
        .on_conflict_do_update(
            index_elements=[recipes_table.c.user_id, recipes_table.c.source_url],
            set_={
                "title": row["title"],
                "description": row["description"],
                "servings": row["servings"],
                "prep_time_min": row["prep_time_min"],
                "cook_time_min": row["cook_time_min"],
                "total_time_min": row["total_time_min"],
                "ingredients": row["ingredients"],
                "steps": row["steps"],
                "source_host": row["source_host"],
                "extraction": row["extraction"],
                "legal_note": row["legal_note"],
                "raw_json": row["raw_json"],
                "updated_at": now,
            },
        )
        .returning(recipes_table.c.id)
    )

    with engine.begin() as conn:
        rid = conn.execute(stmt).scalar_one()
        return rid

def import_url(url: str, user_id: UUID | None = None) -> UUID:
    rec = scrape(url)
    return upsert_recipe(user_id or DEFAULT_USER, rec)
