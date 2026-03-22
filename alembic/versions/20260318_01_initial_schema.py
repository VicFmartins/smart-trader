"""initial schema baseline

Revision ID: 20260318_01
Revises:
Create Date: 2026-03-18 18:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260318_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("risk_profile", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clients_id"), "clients", ["id"], unique=False)
    op.create_index(op.f("ix_clients_name"), "clients", ["name"], unique=True)

    op.create_table(
        "assets_master",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=50), nullable=True),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("asset_class", sa.String(length=50), nullable=False),
        sa.Column("cnpj", sa.String(length=18), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name", "asset_class", name="uq_assets_master_normalized_class"),
        sa.UniqueConstraint("ticker", name="uq_assets_master_ticker"),
    )
    op.create_index(op.f("ix_assets_master_asset_class"), "assets_master", ["asset_class"], unique=False)
    op.create_index(op.f("ix_assets_master_id"), "assets_master", ["id"], unique=False)
    op.create_index(op.f("ix_assets_master_normalized_name"), "assets_master", ["normalized_name"], unique=False)
    op.create_index(op.f("ix_assets_master_ticker"), "assets_master", ["ticker"], unique=False)

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("broker", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "broker", name="uq_account_client_broker"),
    )
    op.create_index(op.f("ix_accounts_client_id"), "accounts", ["client_id"], unique=False)
    op.create_index(op.f("ix_accounts_id"), "accounts", ["id"], unique=False)

    op.create_table(
        "positions_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=24, scale=8, asdecimal=True), nullable=False),
        sa.Column("avg_price", sa.Numeric(precision=24, scale=8, asdecimal=True), nullable=False),
        sa.Column("total_value", sa.Numeric(precision=24, scale=8, asdecimal=True), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.CheckConstraint("avg_price >= 0", name="ck_positions_history_avg_price_non_negative"),
        sa.CheckConstraint("quantity >= 0", name="ck_positions_history_quantity_non_negative"),
        sa.CheckConstraint("total_value >= 0", name="ck_positions_history_total_value_non_negative"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["assets_master.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "asset_id", "reference_date", name="uq_position_snapshot"),
    )
    op.create_index(op.f("ix_positions_history_account_id"), "positions_history", ["account_id"], unique=False)
    op.create_index(op.f("ix_positions_history_asset_id"), "positions_history", ["asset_id"], unique=False)
    op.create_index(op.f("ix_positions_history_id"), "positions_history", ["id"], unique=False)
    op.create_index(op.f("ix_positions_history_reference_date"), "positions_history", ["reference_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_positions_history_reference_date"), table_name="positions_history")
    op.drop_index(op.f("ix_positions_history_id"), table_name="positions_history")
    op.drop_index(op.f("ix_positions_history_asset_id"), table_name="positions_history")
    op.drop_index(op.f("ix_positions_history_account_id"), table_name="positions_history")
    op.drop_table("positions_history")

    op.drop_index(op.f("ix_accounts_id"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_client_id"), table_name="accounts")
    op.drop_table("accounts")

    op.drop_index(op.f("ix_assets_master_ticker"), table_name="assets_master")
    op.drop_index(op.f("ix_assets_master_normalized_name"), table_name="assets_master")
    op.drop_index(op.f("ix_assets_master_id"), table_name="assets_master")
    op.drop_index(op.f("ix_assets_master_asset_class"), table_name="assets_master")
    op.drop_table("assets_master")

    op.drop_index(op.f("ix_clients_name"), table_name="clients")
    op.drop_index(op.f("ix_clients_id"), table_name="clients")
    op.drop_table("clients")
