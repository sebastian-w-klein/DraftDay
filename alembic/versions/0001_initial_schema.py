"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-23
"""

from collections.abc import Sequence

from alembic import op

from app.db.base import Base
from app.models import entities  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    initial_tables = [
        "sources",
        "authors",
        "draft_cycles",
        "teams",
        "players",
        "mock_articles",
        "mock_versions",
        "mock_picks",
        "source_accuracy",
        "manual_overrides",
        "ingestion_jobs",
        "player_aliases",
        "school_aliases",
    ]
    for table_name in initial_tables:
        Base.metadata.tables[table_name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    initial_tables = [
        "school_aliases",
        "player_aliases",
        "ingestion_jobs",
        "manual_overrides",
        "source_accuracy",
        "mock_picks",
        "mock_versions",
        "mock_articles",
        "players",
        "teams",
        "draft_cycles",
        "authors",
        "sources",
    ]
    for table_name in initial_tables:
        Base.metadata.tables[table_name].drop(bind=bind, checkfirst=True)
