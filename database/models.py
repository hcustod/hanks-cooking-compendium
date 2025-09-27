from sqlalchemy import Table, Column, Text, Integer, DateTime, MetaData, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM

metadata = MetaData()

extraction_enum = ENUM(
    "structured",
    "readability",
    name="extraction_method",
    create_type=False,
)

recipes = Table(
    "recipes", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), nullable=False),
    Column("title", Text, nullable=False),
    Column("description", Text),
    Column("servings", Text),
    Column("prep_time_min", Integer),
    Column("cook_time_min", Integer),
    Column("total_time_min", Integer),
    Column("ingredients", JSONB, nullable=False),
    Column("steps", JSONB, nullable=False),
    Column("source_url", Text, nullable=False),
    Column("source_host", Text),
    Column("extraction", Text, nullable=False),
    Column("legal_note", Text, nullable=False),
    Column("raw_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
)
