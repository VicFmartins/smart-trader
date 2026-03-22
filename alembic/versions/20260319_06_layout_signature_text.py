"""expand layout signature columns to text

Revision ID: 20260319_06
Revises: 20260318_05
Create Date: 2026-03-19 04:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260319_06"
down_revision = "20260318_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ingestion_reports") as batch_op:
        batch_op.alter_column(
            "layout_signature",
            existing_type=sa.String(length=500),
            type_=sa.Text(),
            existing_nullable=True,
        )

    with op.batch_alter_table("accepted_column_mappings") as batch_op:
        batch_op.alter_column(
            "layout_signature",
            existing_type=sa.String(length=500),
            type_=sa.Text(),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("accepted_column_mappings") as batch_op:
        batch_op.alter_column(
            "layout_signature",
            existing_type=sa.Text(),
            type_=sa.String(length=500),
            existing_nullable=False,
        )

    with op.batch_alter_table("ingestion_reports") as batch_op:
        batch_op.alter_column(
            "layout_signature",
            existing_type=sa.Text(),
            type_=sa.String(length=500),
            existing_nullable=True,
        )
