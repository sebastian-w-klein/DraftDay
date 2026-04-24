"""add historical ingest batch tracking

Revision ID: 0006_historical_ingest_batches
Revises: 0005_draft_order_picks
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_historical_ingest_batches"
down_revision: str | None = "0005_draft_order_picks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "historical_ingest_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("data_family", sa.String(64), nullable=False),
        sa.Column("source_key", sa.String(128), nullable=False),
        sa.Column("year_start", sa.Integer(), nullable=True),
        sa.Column("year_end", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("rows_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("artifact_path", sa.String(1024), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_historical_ingest_batches_data_family", "historical_ingest_batches", ["data_family"])
    op.create_index("ix_historical_ingest_batches_source_key", "historical_ingest_batches", ["source_key"])
    op.create_index("ix_historical_ingest_batches_year_start", "historical_ingest_batches", ["year_start"])
    op.create_index("ix_historical_ingest_batches_year_end", "historical_ingest_batches", ["year_end"])
    op.create_index("ix_historical_ingest_batches_status", "historical_ingest_batches", ["status"])


def downgrade() -> None:
    op.drop_index("ix_historical_ingest_batches_status", table_name="historical_ingest_batches")
    op.drop_index("ix_historical_ingest_batches_year_end", table_name="historical_ingest_batches")
    op.drop_index("ix_historical_ingest_batches_year_start", table_name="historical_ingest_batches")
    op.drop_index("ix_historical_ingest_batches_source_key", table_name="historical_ingest_batches")
    op.drop_index("ix_historical_ingest_batches_data_family", table_name="historical_ingest_batches")
    op.drop_table("historical_ingest_batches")
