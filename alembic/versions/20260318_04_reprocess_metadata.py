"""add reprocess metadata to ingestion reports

Revision ID: 20260318_04
Revises: 20260318_03
Create Date: 2026-03-18 23:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260318_04"
down_revision = "20260318_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_reports", sa.Column("reprocessed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "ingestion_reports",
        sa.Column("reprocess_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("ingestion_reports", "reprocess_count")
    op.drop_column("ingestion_reports", "reprocessed_at")
