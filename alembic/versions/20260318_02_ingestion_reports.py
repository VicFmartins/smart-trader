"""add ingestion reports audit table

Revision ID: 20260318_02
Revises: 20260318_01
Create Date: 2026-03-18 23:50:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260318_02"
down_revision = "20260318_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("source_file", sa.String(length=512), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("detected_type", sa.String(length=50), nullable=False),
        sa.Column("raw_file", sa.String(length=512), nullable=True),
        sa.Column("processed_file", sa.String(length=512), nullable=True),
        sa.Column("parser_name", sa.String(length=100), nullable=True),
        sa.Column("detection_confidence", sa.Float(), nullable=True),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_reasons", sa.JSON(), nullable=False),
        sa.Column("detected_columns", sa.JSON(), nullable=False),
        sa.Column("applied_mappings", sa.JSON(), nullable=False),
        sa.Column("structure_detection", sa.JSON(), nullable=False),
        sa.Column("rows_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingestion_reports_id"), "ingestion_reports", ["id"], unique=False)
    op.create_index(op.f("ix_ingestion_reports_filename"), "ingestion_reports", ["filename"], unique=False)
    op.create_index(op.f("ix_ingestion_reports_source_type"), "ingestion_reports", ["source_type"], unique=False)
    op.create_index(op.f("ix_ingestion_reports_detected_type"), "ingestion_reports", ["detected_type"], unique=False)
    op.create_index(op.f("ix_ingestion_reports_parser_name"), "ingestion_reports", ["parser_name"], unique=False)
    op.create_index(op.f("ix_ingestion_reports_review_required"), "ingestion_reports", ["review_required"], unique=False)
    op.create_index(op.f("ix_ingestion_reports_status"), "ingestion_reports", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ingestion_reports_status"), table_name="ingestion_reports")
    op.drop_index(op.f("ix_ingestion_reports_review_required"), table_name="ingestion_reports")
    op.drop_index(op.f("ix_ingestion_reports_parser_name"), table_name="ingestion_reports")
    op.drop_index(op.f("ix_ingestion_reports_detected_type"), table_name="ingestion_reports")
    op.drop_index(op.f("ix_ingestion_reports_source_type"), table_name="ingestion_reports")
    op.drop_index(op.f("ix_ingestion_reports_filename"), table_name="ingestion_reports")
    op.drop_index(op.f("ix_ingestion_reports_id"), table_name="ingestion_reports")
    op.drop_table("ingestion_reports")
