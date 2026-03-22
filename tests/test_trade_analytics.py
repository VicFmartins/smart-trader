from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.setup import Setup
from app.models.trade import Trade
from app.models.trading_enums import AssetClass, OperationType, TradeAsset, TradeSourceType, TradeStatus
from app.repositories.trade_analytics import TradeAnalyticsRow
from app.schemas.trade_analytics import TradeAnalyticsFilters
from app.services.trade_analytics import TradeAnalyticsCalculator, TradeAnalyticsService


def test_trade_analytics_calculator_returns_expected_metrics() -> None:
    calculator = TradeAnalyticsCalculator()
    rows = [
        TradeAnalyticsRow(
            trade_id=1,
            trade_date=date(2026, 3, 16),
            asset=TradeAsset.WIN,
            broker="XP",
            setup_id=1,
            setup_name="Breakout",
            source_type=TradeSourceType.MANUAL,
            created_at=datetime(2026, 3, 16, 9, 5, tzinfo=UTC),
            trade_time=None,
            gross_result=Decimal("100.00"),
            net_result=Decimal("95.00"),
        ),
        TradeAnalyticsRow(
            trade_id=2,
            trade_date=date(2026, 3, 16),
            asset=TradeAsset.WDO,
            broker="XP",
            setup_id=2,
            setup_name="Reversal",
            source_type=TradeSourceType.MANUAL,
            created_at=datetime(2026, 3, 16, 10, 30, tzinfo=UTC),
            trade_time=None,
            gross_result=Decimal("-50.00"),
            net_result=Decimal("-55.00"),
        ),
        TradeAnalyticsRow(
            trade_id=3,
            trade_date=date(2026, 3, 17),
            asset=TradeAsset.WIN,
            broker="CLEAR",
            setup_id=None,
            setup_name=None,
            source_type=TradeSourceType.PDF_IMPORT,
            created_at=datetime(2026, 3, 17, 11, 10, tzinfo=UTC),
            trade_time=None,
            gross_result=Decimal("200.00"),
            net_result=Decimal("190.00"),
        ),
        TradeAnalyticsRow(
            trade_id=4,
            trade_date=date(2026, 3, 18),
            asset=TradeAsset.WDO,
            broker="CLEAR",
            setup_id=1,
            setup_name="Breakout",
            source_type=TradeSourceType.MANUAL,
            created_at=datetime(2026, 3, 18, 15, 0, tzinfo=UTC),
            trade_time=None,
            gross_result=Decimal("-100.00"),
            net_result=Decimal("-105.00"),
        ),
    ]

    snapshot = calculator.calculate(rows)

    assert snapshot.summary.total_trades == 4
    assert snapshot.summary.win_rate == 50.0
    assert snapshot.summary.gross_pnl == 150.0
    assert snapshot.summary.net_pnl == 125.0
    assert snapshot.summary.average_win == 142.5
    assert snapshot.summary.average_loss == -80.0
    assert snapshot.summary.profit_factor == 1.7813
    assert snapshot.summary.expectancy == 31.25

    assert [point.model_dump() for point in snapshot.equity_curve] == [
        {"trade_date": date(2026, 3, 16), "daily_net_pnl": 40.0, "equity": 40.0},
        {"trade_date": date(2026, 3, 17), "daily_net_pnl": 190.0, "equity": 230.0},
        {"trade_date": date(2026, 3, 18), "daily_net_pnl": -105.0, "equity": 125.0},
    ]

    assert snapshot.drawdown_curve[-1].drawdown == -105.0
    assert snapshot.drawdown_curve[-1].drawdown_pct == -45.6522

    assert [point.model_dump() for point in snapshot.pnl_by_asset] == [
        {"label": "WIN", "pnl": 285.0, "trades": 2},
        {"label": "WDO", "pnl": -160.0, "trades": 2},
    ]

    assert snapshot.pnl_by_weekday[0].model_dump() == {"label": "Monday", "pnl": 40.0, "trades": 2}
    assert snapshot.pnl_by_weekday[1].model_dump() == {"label": "Tuesday", "pnl": 190.0, "trades": 1}
    assert snapshot.pnl_by_weekday[2].model_dump() == {"label": "Wednesday", "pnl": -105.0, "trades": 1}

    assert snapshot.pnl_by_hour[9].model_dump() == {"hour": 9, "pnl": 95.0, "trades": 1}
    assert snapshot.pnl_by_hour[10].model_dump() == {"hour": 10, "pnl": -55.0, "trades": 1}
    assert snapshot.pnl_by_hour[11].model_dump() == {"hour": 11, "pnl": 190.0, "trades": 1}
    assert snapshot.pnl_by_hour[15].model_dump() == {"hour": 15, "pnl": -105.0, "trades": 1}

    assert [point.model_dump() for point in snapshot.pnl_by_setup] == [
        {"label": "Unassigned", "pnl": 190.0, "trades": 1},
        {"label": "Breakout", "pnl": -10.0, "trades": 2},
        {"label": "Reversal", "pnl": -55.0, "trades": 1},
    ]


def test_trade_analytics_calculator_handles_empty_rows() -> None:
    snapshot = TradeAnalyticsCalculator().calculate([])

    assert snapshot.summary.model_dump() == {
        "total_trades": 0,
        "win_rate": 0.0,
        "gross_pnl": 0.0,
        "net_pnl": 0.0,
        "average_win": 0.0,
        "average_loss": 0.0,
        "profit_factor": None,
        "expectancy": 0.0,
    }
    assert snapshot.equity_curve == []
    assert snapshot.drawdown_curve == []
    assert len(snapshot.pnl_by_weekday) == 7
    assert len(snapshot.pnl_by_hour) == 24
    assert all(point.pnl == 0.0 for point in snapshot.pnl_by_weekday)
    assert all(point.pnl == 0.0 for point in snapshot.pnl_by_hour)


def test_trade_analytics_service_ignores_drafts_and_applies_filters(tmp_path) -> None:
    database_path = tmp_path / "trade_analytics.db"
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    session: Session = SessionLocal()
    try:
        setup = Setup(name="Trend Day", asset_class_scope=AssetClass.MINI_INDEX)
        session.add(setup)
        session.flush()

        session.add_all(
            [
                Trade(
                    trade_date=date(2026, 3, 20),
                    asset=TradeAsset.WIN,
                    asset_class=AssetClass.MINI_INDEX,
                    operation_type=OperationType.BUY,
                    status=TradeStatus.CLOSED,
                    quantity=1,
                    entry_price=Decimal("125000.0"),
                    exit_price=Decimal("125100.0"),
                    gross_result=Decimal("20.00"),
                    fees=Decimal("3.00"),
                    net_result=Decimal("17.00"),
                    broker="XP",
                    setup_id=setup.id,
                    source_type=TradeSourceType.MANUAL,
                    created_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
                ),
                Trade(
                    trade_date=date(2026, 3, 20),
                    asset=TradeAsset.WIN,
                    asset_class=AssetClass.MINI_INDEX,
                    operation_type=OperationType.BUY,
                    status=TradeStatus.DRAFT,
                    quantity=1,
                    entry_price=Decimal("125000.0"),
                    exit_price=None,
                    gross_result=None,
                    fees=Decimal("0.00"),
                    net_result=None,
                    broker="XP",
                    setup_id=setup.id,
                    source_type=TradeSourceType.MANUAL,
                    created_at=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
                ),
                Trade(
                    trade_date=date(2026, 3, 21),
                    asset=TradeAsset.WDO,
                    asset_class=AssetClass.MINI_DOLLAR,
                    operation_type=OperationType.SELL,
                    status=TradeStatus.CLOSED,
                    quantity=1,
                    entry_price=Decimal("5.7200"),
                    exit_price=Decimal("5.7100"),
                    gross_result=Decimal("0.10"),
                    fees=Decimal("0.00"),
                    net_result=Decimal("0.10"),
                    broker="CLEAR",
                    setup_id=None,
                    source_type=TradeSourceType.PDF_IMPORT,
                    imported_file_name="batch.pdf",
                    import_batch_id="batch-1",
                    confidence_score=0.88,
                    created_at=datetime(2026, 3, 21, 11, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 21, 11, 0, tzinfo=UTC),
                ),
            ]
        )
        session.commit()

        service = TradeAnalyticsService(session)
        snapshot = service.build_snapshot(filters=TradeAnalyticsFilters(asset=TradeAsset.WIN, broker="xp"))

        assert snapshot.summary.total_trades == 1
        assert snapshot.summary.net_pnl == 17.0
        assert snapshot.pnl_by_asset[0].label == "WIN"
    finally:
        session.close()
        engine.dispose()
