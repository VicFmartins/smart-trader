from datetime import date
from decimal import Decimal

import pandas as pd

from app.core.config import clear_settings_cache
from app.db.session import clear_db_caches, get_session_factory, init_db
from app.etl.load.loader import PortfolioLoader
from app.models.asset_master import AssetMaster


def test_loader_reuses_asset_when_ticker_arrives_later(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "loader.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    clear_settings_cache()
    clear_db_caches()
    init_db()

    session = get_session_factory()()
    try:
        loader = PortfolioLoader(session)
        first_batch = pd.DataFrame(
            [
                {
                    "client_name": "Maria Oliveira",
                    "broker": "XP",
                    "original_name": "Tesouro Selic 2029",
                    "normalized_name": "TESOURO SELIC 2029",
                    "ticker": None,
                    "quantity": Decimal("10"),
                    "avg_price": Decimal("100"),
                    "total_value": Decimal("1000"),
                    "reference_date": date(2026, 3, 15),
                    "risk_profile": "moderado",
                    "asset_class": "fixed_income",
                    "cnpj": "00.000.000/0001-91",
                    "maturity_date": date(2029, 3, 1),
                }
            ]
        )
        second_batch = pd.DataFrame(
            [
                {
                    "client_name": "Maria Oliveira",
                    "broker": "XP",
                    "original_name": "Tesouro Selic 2029",
                    "normalized_name": "TESOURO SELIC 2029",
                    "ticker": "SELIC29",
                    "quantity": Decimal("12"),
                    "avg_price": Decimal("101"),
                    "total_value": Decimal("1212"),
                    "reference_date": date(2026, 3, 16),
                    "risk_profile": "moderado",
                    "asset_class": "fixed_income",
                    "cnpj": "00.000.000/0001-91",
                    "maturity_date": date(2029, 3, 1),
                }
            ]
        )

        loader.load(first_batch)
        loader.load(second_batch)

        assets = session.query(AssetMaster).all()
        assert len(assets) == 1
        assert assets[0].ticker == "SELIC29"
    finally:
        session.close()
        clear_db_caches()
        clear_settings_cache()
