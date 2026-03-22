from __future__ import annotations

import logging
from collections.abc import Iterable

import pandas as pd
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.etl.contracts import PositionRecord
from app.models.account import Account
from app.models.asset_master import AssetMaster
from app.models.client import Client
from app.models.position_history import PositionHistory


logger = logging.getLogger(__name__)


class PortfolioLoader:
    def __init__(self, db: Session) -> None:
        self.db = db

    def load(self, dataframe: pd.DataFrame) -> dict[str, int]:
        stats = {
            "clients_created": 0,
            "accounts_created": 0,
            "assets_created": 0,
            "positions_upserted": 0,
        }
        records = self._build_records(dataframe)
        if not records:
            logger.info("No records to load after transformation.")
            return stats

        try:
            clients = self._upsert_clients(records, stats)
            accounts = self._upsert_accounts(records, clients, stats)
            assets = self._upsert_assets(records, stats)
            self._upsert_positions(records, clients, accounts, assets, stats)
            self.db.commit()
            logger.info("Loaded %s rows into the portfolio database.", len(records))
            return stats
        except Exception:
            self.db.rollback()
            logger.exception("Error while loading data into the portfolio database.")
            raise

    def _build_records(self, dataframe: pd.DataFrame) -> list[PositionRecord]:
        return [
            PositionRecord(
                client_name=row["client_name"],
                broker=row["broker"],
                original_name=row["original_name"],
                normalized_name=row["normalized_name"],
                ticker=row["ticker"],
                quantity=row["quantity"],
                avg_price=row["avg_price"],
                total_value=row["total_value"],
                reference_date=row["reference_date"],
                risk_profile=row["risk_profile"],
                asset_class=row["asset_class"],
                cnpj=row["cnpj"],
                maturity_date=row["maturity_date"],
            )
            for row in dataframe.to_dict(orient="records")
        ]

    def _upsert_clients(self, records: list[PositionRecord], stats: dict[str, int]) -> dict[str, Client]:
        client_names = sorted({record.client_name for record in records})
        existing_clients = {
            client.name: client
            for client in self.db.scalars(select(Client).where(Client.name.in_(client_names))).all()
        }

        for record in records:
            client = existing_clients.get(record.client_name)
            if client is None:
                client = Client(name=record.client_name, risk_profile=record.risk_profile)
                self.db.add(client)
                self.db.flush()
                existing_clients[record.client_name] = client
                stats["clients_created"] += 1
            elif client.risk_profile != record.risk_profile:
                client.risk_profile = record.risk_profile

        return existing_clients

    def _upsert_accounts(
        self,
        records: list[PositionRecord],
        clients: dict[str, Client],
        stats: dict[str, int],
    ) -> dict[tuple[int, str], Account]:
        account_keys = {(clients[record.client_name].id, record.broker) for record in records}
        client_ids = {client_id for client_id, _ in account_keys}
        brokers = {broker for _, broker in account_keys}
        existing_accounts = {
            (account.client_id, account.broker): account
            for account in self.db.scalars(
                select(Account).where(Account.client_id.in_(client_ids), Account.broker.in_(brokers))
            ).all()
        }

        for client_id, broker in account_keys:
            if (client_id, broker) in existing_accounts:
                continue
            account = Account(client_id=client_id, broker=broker)
            self.db.add(account)
            self.db.flush()
            existing_accounts[(client_id, broker)] = account
            stats["accounts_created"] += 1

        return existing_accounts

    def _upsert_assets(
        self,
        records: list[PositionRecord],
        stats: dict[str, int],
    ) -> dict[tuple[str | None, str, str], AssetMaster]:
        tickers = sorted({record.ticker for record in records if record.ticker})
        normalized_names = sorted({record.normalized_name for record in records})
        existing_assets = self._fetch_existing_assets(tickers, normalized_names)

        for record in records:
            asset = self._resolve_asset(existing_assets, record)
            if asset is None:
                asset = AssetMaster(
                    ticker=record.ticker,
                    original_name=record.original_name,
                    normalized_name=record.normalized_name,
                    asset_class=record.asset_class,
                    cnpj=record.cnpj,
                    maturity_date=record.maturity_date,
                )
                self.db.add(asset)
                self.db.flush()
                stats["assets_created"] += 1
            else:
                if record.ticker and asset.ticker != record.ticker:
                    asset.ticker = record.ticker
                asset.original_name = record.original_name
                asset.normalized_name = record.normalized_name
                asset.asset_class = record.asset_class
                asset.cnpj = record.cnpj
                asset.maturity_date = record.maturity_date

            existing_assets[self._asset_cache_key(asset.ticker, asset.normalized_name, asset.asset_class)] = asset
            existing_assets[self._asset_cache_key(None, asset.normalized_name, asset.asset_class)] = asset
            if asset.ticker:
                existing_assets[self._asset_ticker_key(asset.ticker)] = asset

        return existing_assets

    def _fetch_existing_assets(
        self,
        tickers: Iterable[str],
        normalized_names: Iterable[str],
    ) -> dict[tuple[str | None, str, str], AssetMaster]:
        conditions = []
        tickers = list(tickers)
        normalized_names = list(normalized_names)
        if tickers:
            conditions.append(AssetMaster.ticker.in_(tickers))
        if normalized_names:
            conditions.append(AssetMaster.normalized_name.in_(normalized_names))

        if not conditions:
            return {}

        assets = self.db.scalars(select(AssetMaster).where(or_(*conditions))).all()
        cache: dict[tuple[str | None, str, str], AssetMaster] = {}
        for asset in assets:
            cache[self._asset_cache_key(asset.ticker, asset.normalized_name, asset.asset_class)] = asset
            cache[self._asset_cache_key(None, asset.normalized_name, asset.asset_class)] = asset
            if asset.ticker:
                cache[self._asset_ticker_key(asset.ticker)] = asset
        return cache

    def _resolve_asset(
        self,
        existing_assets: dict[tuple[str | None, str, str], AssetMaster],
        record: PositionRecord,
    ) -> AssetMaster | None:
        for key in (
            self._asset_ticker_key(record.ticker),
            self._asset_cache_key(record.ticker, record.normalized_name, record.asset_class),
            self._asset_cache_key(None, record.normalized_name, record.asset_class),
        ):
            asset = existing_assets.get(key)
            if asset is not None:
                return asset
        return None

    def _asset_cache_key(self, ticker: str | None, normalized_name: str, asset_class: str) -> tuple[str | None, str, str]:
        return (ticker, normalized_name, asset_class)

    def _asset_ticker_key(self, ticker: str | None) -> tuple[str | None, str, str]:
        return (ticker, "", "")

    def _upsert_positions(
        self,
        records: list[PositionRecord],
        clients: dict[str, Client],
        accounts: dict[tuple[int, str], Account],
        assets: dict[tuple[str | None, str, str], AssetMaster],
        stats: dict[str, int],
    ) -> None:
        account_ids = {account.id for account in accounts.values()}
        asset_ids = {asset.id for asset in assets.values()}
        reference_dates = {record.reference_date for record in records}

        existing_positions = {
            (position.account_id, position.asset_id, position.reference_date): position
            for position in self.db.scalars(
                select(PositionHistory).where(
                    PositionHistory.account_id.in_(account_ids),
                    PositionHistory.asset_id.in_(asset_ids),
                    PositionHistory.reference_date.in_(reference_dates),
                )
            ).all()
        }

        for record in records:
            client = clients[record.client_name]
            account = accounts[(client.id, record.broker)]
            asset = assets[self._asset_cache_key(record.ticker, record.normalized_name, record.asset_class)]
            position_key = (account.id, asset.id, record.reference_date)
            position = existing_positions.get(position_key)

            if position is None:
                position = PositionHistory(
                    account_id=account.id,
                    asset_id=asset.id,
                    quantity=record.quantity,
                    avg_price=record.avg_price,
                    total_value=record.total_value,
                    reference_date=record.reference_date,
                )
                self.db.add(position)
                existing_positions[position_key] = position
            else:
                position.quantity = record.quantity
                position.avg_price = record.avg_price
                position.total_value = record.total_value

            stats["positions_upserted"] += 1
