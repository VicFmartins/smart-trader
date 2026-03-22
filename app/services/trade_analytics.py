from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.repositories.trade_analytics import TradeAnalyticsRepository, TradeAnalyticsRow
from app.schemas.trade_analytics import (
    BreakdownPoint,
    DrawdownCurvePoint,
    EquityCurvePoint,
    HourBreakdownPoint,
    TradeAnalyticsFilters,
    TradeAnalyticsSnapshot,
    TradeAnalyticsSummary,
)


WEEKDAY_LABELS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def _to_decimal(value: float | Decimal | int) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _round_money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _round_ratio(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


class TradeAnalyticsCalculator:
    def calculate(self, rows: list[TradeAnalyticsRow]) -> TradeAnalyticsSnapshot:
        if not rows:
            return TradeAnalyticsSnapshot(
                summary=TradeAnalyticsSummary(),
                equity_curve=[],
                drawdown_curve=[],
                pnl_by_asset=[],
                pnl_by_weekday=self._empty_weekday_breakdown(),
                pnl_by_hour=self._empty_hour_breakdown(),
                pnl_by_setup=[],
            )

        equity_curve = self._build_equity_curve(rows)
        return TradeAnalyticsSnapshot(
            summary=self._build_summary(rows),
            equity_curve=equity_curve,
            drawdown_curve=self._build_drawdown_curve(equity_curve),
            pnl_by_asset=self._build_asset_breakdown(rows),
            pnl_by_weekday=self._build_weekday_breakdown(rows),
            pnl_by_hour=self._build_hour_breakdown(rows),
            pnl_by_setup=self._build_setup_breakdown(rows),
        )

    def _build_summary(self, rows: list[TradeAnalyticsRow]) -> TradeAnalyticsSummary:
        net_results = [_to_decimal(row.net_result) for row in rows]
        gross_results = [_to_decimal(row.gross_result) for row in rows]
        wins = [result for result in net_results if result > 0]
        losses = [result for result in net_results if result < 0]

        total_trades = len(rows)
        gross_pnl = sum(gross_results, Decimal("0"))
        net_pnl = sum(net_results, Decimal("0"))
        gross_profit = sum(wins, Decimal("0"))
        gross_loss_abs = abs(sum(losses, Decimal("0")))

        profit_factor = None if gross_loss_abs == 0 else _round_ratio(gross_profit / gross_loss_abs)
        win_rate = ((Decimal(len(wins)) / Decimal(total_trades)) * Decimal("100")) if total_trades else Decimal("0")
        average_win = sum(wins, Decimal("0")) / Decimal(len(wins)) if wins else Decimal("0")
        average_loss = sum(losses, Decimal("0")) / Decimal(len(losses)) if losses else Decimal("0")
        expectancy = net_pnl / Decimal(total_trades) if total_trades else Decimal("0")

        return TradeAnalyticsSummary(
            total_trades=total_trades,
            win_rate=_round_ratio(win_rate),
            gross_pnl=_round_money(gross_pnl),
            net_pnl=_round_money(net_pnl),
            average_win=_round_money(average_win),
            average_loss=_round_money(average_loss),
            profit_factor=profit_factor,
            expectancy=_round_money(expectancy),
        )

    def _build_equity_curve(self, rows: list[TradeAnalyticsRow]) -> list[EquityCurvePoint]:
        daily_pnl: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
        for row in rows:
            daily_pnl[row.trade_date] += _to_decimal(row.net_result)

        equity = Decimal("0")
        points: list[EquityCurvePoint] = []
        for trade_date in sorted(daily_pnl):
            daily_result = daily_pnl[trade_date]
            equity += daily_result
            points.append(
                EquityCurvePoint(
                    trade_date=trade_date,
                    daily_net_pnl=_round_money(daily_result),
                    equity=_round_money(equity),
                )
            )
        return points

    def _build_drawdown_curve(self, equity_curve: list[EquityCurvePoint]) -> list[DrawdownCurvePoint]:
        peak = Decimal("0")
        points: list[DrawdownCurvePoint] = []
        for point in equity_curve:
            equity = _to_decimal(point.equity)
            if equity > peak:
                peak = equity
            drawdown = equity - peak
            drawdown_pct = ((drawdown / peak) * Decimal("100")) if peak > 0 else Decimal("0")
            points.append(
                DrawdownCurvePoint(
                    trade_date=point.trade_date,
                    equity=point.equity,
                    peak_equity=_round_money(peak),
                    drawdown=_round_money(drawdown),
                    drawdown_pct=_round_ratio(drawdown_pct),
                )
            )
        return points

    def _build_asset_breakdown(self, rows: list[TradeAnalyticsRow]) -> list[BreakdownPoint]:
        grouped: dict[str, dict[str, Decimal | int]] = {}
        for row in rows:
            label = row.asset.value
            if label not in grouped:
                grouped[label] = {"pnl": Decimal("0"), "trades": 0}
            grouped[label]["pnl"] += _to_decimal(row.net_result)
            grouped[label]["trades"] += 1
        return self._sorted_breakdown(grouped)

    def _build_weekday_breakdown(self, rows: list[TradeAnalyticsRow]) -> list[BreakdownPoint]:
        grouped: dict[int, dict[str, Decimal | int]] = {weekday: {"pnl": Decimal("0"), "trades": 0} for weekday in range(7)}
        for row in rows:
            weekday = row.trade_date.weekday()
            grouped[weekday]["pnl"] += _to_decimal(row.net_result)
            grouped[weekday]["trades"] += 1
        return [
            BreakdownPoint(label=WEEKDAY_LABELS[weekday], pnl=_round_money(grouped[weekday]["pnl"]), trades=int(grouped[weekday]["trades"]))
            for weekday in range(7)
        ]

    def _build_hour_breakdown(self, rows: list[TradeAnalyticsRow]) -> list[HourBreakdownPoint]:
        grouped: dict[int, dict[str, Decimal | int]] = {hour: {"pnl": Decimal("0"), "trades": 0} for hour in range(24)}
        for row in rows:
            hour = row.trade_time.hour if row.trade_time is not None else row.created_at.hour
            grouped[hour]["pnl"] += _to_decimal(row.net_result)
            grouped[hour]["trades"] += 1
        return [
            HourBreakdownPoint(hour=hour, pnl=_round_money(grouped[hour]["pnl"]), trades=int(grouped[hour]["trades"]))
            for hour in range(24)
        ]

    def _build_setup_breakdown(self, rows: list[TradeAnalyticsRow]) -> list[BreakdownPoint]:
        grouped: dict[str, dict[str, Decimal | int]] = {}
        for row in rows:
            label = row.setup_name or "Unassigned"
            if label not in grouped:
                grouped[label] = {"pnl": Decimal("0"), "trades": 0}
            grouped[label]["pnl"] += _to_decimal(row.net_result)
            grouped[label]["trades"] += 1
        return self._sorted_breakdown(grouped)

    def _sorted_breakdown(self, grouped: dict[str, dict[str, Decimal | int]]) -> list[BreakdownPoint]:
        items = [
            BreakdownPoint(label=label, pnl=_round_money(values["pnl"]), trades=int(values["trades"]))
            for label, values in grouped.items()
        ]
        return sorted(items, key=lambda item: (-item.pnl, item.label))

    def _empty_weekday_breakdown(self) -> list[BreakdownPoint]:
        return [BreakdownPoint(label=WEEKDAY_LABELS[weekday], pnl=0.0, trades=0) for weekday in range(7)]

    def _empty_hour_breakdown(self) -> list[HourBreakdownPoint]:
        return [HourBreakdownPoint(hour=hour, pnl=0.0, trades=0) for hour in range(24)]


class TradeAnalyticsService:
    def __init__(self, db: Session) -> None:
        self.repository = TradeAnalyticsRepository(db)
        self.calculator = TradeAnalyticsCalculator()

    def build_snapshot(self, *, filters: TradeAnalyticsFilters | None = None) -> TradeAnalyticsSnapshot:
        rows = self.repository.fetch_rows(filters=filters)
        return self.calculator.calculate(rows)
