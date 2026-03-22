from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.import_job import ImportJob
from app.models.trade import Trade
from app.models.trading_enums import AssetClass, ImportJobStatus, OperationType, TradeAsset, TradeSourceType, TradeStatus
from app.repositories.taxes import DayTradeTaxRow
from app.services.taxes import DayTradeTaxCalculator, TaxCalculationService


def test_day_trade_tax_calculator_handles_empty_rows() -> None:
    breakdown = DayTradeTaxCalculator().calculate([])

    assert breakdown == []


def test_day_trade_tax_calculator_offsets_losses_across_months() -> None:
    calculator = DayTradeTaxCalculator()
    rows = [
        DayTradeTaxRow(trade_date=date(2026, 1, 5), net_result=Decimal("1500.00")),
        DayTradeTaxRow(trade_date=date(2026, 1, 18), net_result=Decimal("-300.00")),
        DayTradeTaxRow(trade_date=date(2026, 2, 4), net_result=Decimal("-600.00")),
        DayTradeTaxRow(trade_date=date(2026, 3, 10), net_result=Decimal("400.00")),
        DayTradeTaxRow(trade_date=date(2026, 4, 3), net_result=Decimal("1000.00")),
        DayTradeTaxRow(trade_date=date(2026, 4, 22), net_result=Decimal("-100.00")),
    ]

    breakdown = calculator.calculate(rows)

    assert [month.month for month in breakdown] == [
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
        date(2026, 4, 1),
    ]
    assert breakdown[0] == type(breakdown[0])(
        month=date(2026, 1, 1),
        gross_profit=Decimal("1500.00"),
        gross_loss=Decimal("300.00"),
        net_result=Decimal("1200.00"),
        prior_loss_carryforward=Decimal("0.00"),
        used_loss_offset=Decimal("0.00"),
        remaining_loss_carryforward=Decimal("0.00"),
        taxable_profit=Decimal("1200.00"),
        estimated_tax=Decimal("240.00"),
    )
    assert breakdown[1].gross_loss == Decimal("600.00")
    assert breakdown[1].net_result == Decimal("-600.00")
    assert breakdown[1].remaining_loss_carryforward == Decimal("600.00")
    assert breakdown[1].estimated_tax == Decimal("0.00")

    assert breakdown[2].prior_loss_carryforward == Decimal("600.00")
    assert breakdown[2].used_loss_offset == Decimal("400.00")
    assert breakdown[2].remaining_loss_carryforward == Decimal("200.00")
    assert breakdown[2].taxable_profit == Decimal("0.00")
    assert breakdown[2].estimated_tax == Decimal("0.00")

    assert breakdown[3].gross_profit == Decimal("1000.00")
    assert breakdown[3].gross_loss == Decimal("100.00")
    assert breakdown[3].net_result == Decimal("900.00")
    assert breakdown[3].prior_loss_carryforward == Decimal("200.00")
    assert breakdown[3].used_loss_offset == Decimal("200.00")
    assert breakdown[3].remaining_loss_carryforward == Decimal("0.00")
    assert breakdown[3].taxable_profit == Decimal("700.00")
    assert breakdown[3].estimated_tax == Decimal("140.00")
    assert all(month.darf_code == "6015" for month in breakdown)


def test_tax_calculation_service_builds_monthly_report_from_closed_trades(tmp_path) -> None:
    database_path = tmp_path / "trade_taxes.db"
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    session: Session = SessionLocal()
    try:
        session.add_all(
            [
                ImportJob(
                    batch_id="batch-feb",
                    source_type=TradeSourceType.PDF_IMPORT,
                    status=ImportJobStatus.COMPLETED,
                    file_name="feb.pdf",
                    broker="XP",
                    total_trades=1,
                    imported_trades=1,
                    rejected_trades=0,
                    average_confidence_score=0.91,
                    estimated_total_fees=Decimal("5.00"),
                    created_at=datetime(2026, 2, 4, 9, 30, tzinfo=UTC),
                    updated_at=datetime(2026, 2, 4, 9, 30, tzinfo=UTC),
                ),
                Trade(
                    trade_date=date(2026, 1, 12),
                    asset=TradeAsset.WIN,
                    asset_class=AssetClass.MINI_INDEX,
                    operation_type=OperationType.BUY,
                    status=TradeStatus.CLOSED,
                    quantity=1,
                    entry_price=Decimal("125000.0"),
                    exit_price=Decimal("125050.0"),
                    gross_result=Decimal("12.00"),
                    fees=Decimal("2.00"),
                    net_result=Decimal("10.00"),
                    broker="XP",
                    source_type=TradeSourceType.MANUAL,
                    created_at=datetime(2026, 1, 12, 9, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 1, 12, 9, 0, tzinfo=UTC),
                ),
                Trade(
                    trade_date=date(2026, 2, 4),
                    asset=TradeAsset.WDO,
                    asset_class=AssetClass.MINI_DOLLAR,
                    operation_type=OperationType.SELL,
                    status=TradeStatus.CLOSED,
                    quantity=1,
                    entry_price=Decimal("5.7200"),
                    exit_price=Decimal("5.7250"),
                    gross_result=Decimal("-50.00"),
                    fees=Decimal("5.00"),
                    net_result=Decimal("-55.00"),
                    broker="XP",
                    source_type=TradeSourceType.PDF_IMPORT,
                    imported_file_name="feb.pdf",
                    import_batch_id="batch-feb",
                    confidence_score=0.91,
                    created_at=datetime(2026, 2, 4, 10, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 2, 4, 10, 0, tzinfo=UTC),
                ),
                Trade(
                    trade_date=date(2026, 2, 4),
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
                    source_type=TradeSourceType.MANUAL,
                    created_at=datetime(2026, 2, 4, 11, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 2, 4, 11, 0, tzinfo=UTC),
                ),
                Trade(
                    trade_date=date(2026, 3, 8),
                    asset=TradeAsset.WDO,
                    asset_class=AssetClass.MINI_DOLLAR,
                    operation_type=OperationType.BUY,
                    status=TradeStatus.CLOSED,
                    quantity=1,
                    entry_price=Decimal("5.7000"),
                    exit_price=Decimal("5.7150"),
                    gross_result=Decimal("150.00"),
                    fees=Decimal("10.00"),
                    net_result=Decimal("140.00"),
                    broker="CLEAR",
                    source_type=TradeSourceType.MANUAL,
                    created_at=datetime(2026, 3, 8, 14, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 8, 14, 0, tzinfo=UTC),
                ),
            ]
        )
        session.commit()

        report = TaxCalculationService(session).build_day_trade_report()

        assert report.tax_rate == Decimal("0.20")
        assert report.generated_from == date(2026, 1, 1)
        assert report.generated_to == date(2026, 3, 1)
        assert [month.month for month in report.months] == ["2026-01", "2026-02", "2026-03"]
        assert report.months[0].model_dump() == {
            "month": "2026-01",
            "gross_profit": Decimal("10.00"),
            "gross_loss": Decimal("0.00"),
            "net_result": Decimal("10.00"),
            "prior_loss_carryforward": Decimal("0.00"),
            "used_loss_offset": Decimal("0.00"),
            "remaining_loss_carryforward": Decimal("0.00"),
            "taxable_profit": Decimal("10.00"),
            "estimated_tax": Decimal("2.00"),
            "darf_code": "6015",
        }
        assert report.months[1].net_result == Decimal("-55.00")
        assert report.months[1].remaining_loss_carryforward == Decimal("55.00")
        assert report.months[2].prior_loss_carryforward == Decimal("55.00")
        assert report.months[2].used_loss_offset == Decimal("55.00")
        assert report.months[2].taxable_profit == Decimal("85.00")
        assert report.months[2].estimated_tax == Decimal("17.00")
    finally:
        session.close()
        engine.dispose()
