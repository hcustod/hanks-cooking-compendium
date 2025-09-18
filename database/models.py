from sqlalchemy import Table, Column, Text, Integer, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from .db import metadata

recipes = Table(
    "recipes",
    metadata,
    Column("id", PGUUID(as_uuid=True), primary_key=True),
    Column("user_id", PGUUID(as_uuid=True), nullable=False, index=True),
    Column("title", Text, nullable=False),
    Column("description", Text),
    Column("servings", String),
    Column("prep_time_min", Integer),
    Column("cook_time_min", Integer),
    Column("total_time_min", Integer),
    Column("ingredients", JSONB, nullable=False),
    Column("steps", JSONB, nullable=False),
    Column("source_url", Text, nullable=False),
    Column("source_host", Text),
    Column("extraction", String, nullable=False),
    Column("legal_note", Text, nullable=False),
    Column("raw_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_id", "source_url", name="uq_user_source"),
)
