from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.repositories.taxes import DayTradeTaxRepository, DayTradeTaxRow
from app.schemas.day_trade_tax import DayTradeTaxMonthBreakdown, DayTradeTaxReport


DAY_TRADE_TAX_RATE = Decimal("0.20")
DAY_TRADE_DARF_CODE = "6015"


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class DayTradeTaxMonthResult:
    month: date
    gross_profit: Decimal
    gross_loss: Decimal
    net_result: Decimal
    prior_loss_carryforward: Decimal
    used_loss_offset: Decimal
    remaining_loss_carryforward: Decimal
    taxable_profit: Decimal
    estimated_tax: Decimal
    darf_code: str = DAY_TRADE_DARF_CODE


class DayTradeTaxCalculator:
    """Pure monthly day-trade tax calculation based on closed-trade net results."""

    def calculate(self, rows: list[DayTradeTaxRow]) -> list[DayTradeTaxMonthResult]:
        if not rows:
            return []

        monthly_results: dict[date, list[Decimal]] = defaultdict(list)
        for row in rows:
            monthly_results[_month_start(row.trade_date)].append(Decimal(row.net_result))

        carryforward = Decimal("0.00")
        breakdown: list[DayTradeTaxMonthResult] = []
        for month in sorted(monthly_results):
            month_values = monthly_results[month]
            gross_profit = sum((value for value in month_values if value > 0), Decimal("0.00"))
            negative_sum = sum((value for value in month_values if value < 0), Decimal("0.00"))
            gross_loss = abs(negative_sum)
            net_result = gross_profit - gross_loss

            prior_loss_carryforward = carryforward
            used_loss_offset = Decimal("0.00")
            taxable_profit = Decimal("0.00")

            if net_result > 0:
                used_loss_offset = min(prior_loss_carryforward, net_result)
                taxable_profit = net_result - used_loss_offset
                carryforward = prior_loss_carryforward - used_loss_offset
            elif net_result < 0:
                carryforward = prior_loss_carryforward + abs(net_result)

            estimated_tax = taxable_profit * DAY_TRADE_TAX_RATE
            breakdown.append(
                DayTradeTaxMonthResult(
                    month=month,
                    gross_profit=_round_money(gross_profit),
                    gross_loss=_round_money(gross_loss),
                    net_result=_round_money(net_result),
                    prior_loss_carryforward=_round_money(prior_loss_carryforward),
                    used_loss_offset=_round_money(used_loss_offset),
                    remaining_loss_carryforward=_round_money(carryforward),
                    taxable_profit=_round_money(taxable_profit),
                    estimated_tax=_round_money(estimated_tax),
                )
            )
        return breakdown


class DayTradeTaxReportFormatter:
    def format(self, months: list[DayTradeTaxMonthResult]) -> DayTradeTaxReport:
        generated_from = months[0].month if months else None
        generated_to = months[-1].month if months else None
        return DayTradeTaxReport(
            tax_rate=DAY_TRADE_TAX_RATE,
            generated_from=generated_from,
            generated_to=generated_to,
            months=[
                DayTradeTaxMonthBreakdown(
                    month=result.month.strftime("%Y-%m"),
                    gross_profit=result.gross_profit,
                    gross_loss=result.gross_loss,
                    net_result=result.net_result,
                    prior_loss_carryforward=result.prior_loss_carryforward,
                    used_loss_offset=result.used_loss_offset,
                    remaining_loss_carryforward=result.remaining_loss_carryforward,
                    taxable_profit=result.taxable_profit,
                    estimated_tax=result.estimated_tax,
                    darf_code=result.darf_code,
                )
                for result in months
            ],
        )


class TaxCalculationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = DayTradeTaxRepository(db)
        self.calculator = DayTradeTaxCalculator()
        self.formatter = DayTradeTaxReportFormatter()

    def build_day_trade_report(self) -> DayTradeTaxReport:
        rows = self.repository.fetch_rows()
        month_results = self.calculator.calculate(rows)
        return self.formatter.format(month_results)
