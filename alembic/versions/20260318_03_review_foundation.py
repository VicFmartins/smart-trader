"""add review status and accepted mapping memory

Revision ID: 20260318_03
Revises: 20260318_02
Create Date: 2026-03-19 00:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260318_03"
down_revision = "20260318_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_reports", sa.Column("layout_signature", sa.String(length=500), nullable=True))
    op.add_column(
        "ingestion_reports",
        sa.Column("review_status", sa.String(length=30), nullable=False, server_default="not_required"),
    )
    op.create_index(op.f("ix_ingestion_reports_layout_signature"), "ingestion_reports", ["layout_signature"], unique=False)
    op.create_index(op.f("ix_ingestion_reports_review_status"), "ingestion_reports", ["review_status"], unique=False)

    op.execute(
        sa.text(
            """
            UPDATE ingestion_reports
            SET review_status = CASE
                WHEN review_required IS TRUE THEN 'pending'
                ELSE 'not_required'
            END
            """
        )
    )

    op.create_table(
        "accepted_column_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution_name", sa.String(length=255), nullable=True),
        sa.Column("layout_signature", sa.String(length=500), nullable=False),
        sa.Column("source_column", sa.String(length=255), nullable=False),
        sa.Column("canonical_field", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_name",
            "layout_signature",
            "source_column",
            name="uq_accepted_column_mapping_signature_source",
        ),
    )
    op.create_index(op.f("ix_accepted_column_mappings_id"), "accepted_column_mappings", ["id"], unique=False)
    op.create_index(
        op.f("ix_accepted_column_mappings_institution_name"),
        "accepted_column_mappings",
        ["institution_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_column_mappings_layout_signature"),
        "accepted_column_mappings",
        ["layout_signature"],
        unique=False,
    )
    op.create_index(
        op.f("ix_accepted_column_mappings_canonical_field"),
        "accepted_column_mappings",
        ["canonical_field"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_accepted_column_mappings_canonical_field"), table_name="accepted_column_mappings")
    op.drop_index(op.f("ix_accepted_column_mappings_layout_signature"), table_name="accepted_column_mappings")
    op.drop_index(op.f("ix_accepted_column_mappings_institution_name"), table_name="accepted_column_mappings")
    op.drop_index(op.f("ix_accepted_column_mappings_id"), table_name="accepted_column_mappings")
    op.drop_table("accepted_column_mappings")

    op.drop_index(op.f("ix_ingestion_reports_review_status"), table_name="ingestion_reports")
    op.drop_index(op.f("ix_ingestion_reports_layout_signature"), table_name="ingestion_reports")
    op.drop_column("ingestion_reports", "review_status")
    op.drop_column("ingestion_reports", "layout_signature")
