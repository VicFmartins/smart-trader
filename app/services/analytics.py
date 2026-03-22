from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ApplicationError
from app.repositories.analytics import AnalyticsRepository
from app.repositories.pagination import PagedResult
from app.repositories.positions import PositionRepository
from app.schemas.common import PaginationParams


@dataclass(frozen=True, slots=True)
class PortfolioPositionRow:
    client_name: str
    risk_profile: str
    broker: str
    asset_class: str
    ticker: str
    asset_name: str
    quantity: Decimal
    avg_price: Decimal
    total_value: Decimal
    reference_date: date


@dataclass(frozen=True, slots=True)
class BreakdownRow:
    label: str
    value: Decimal
    share: float


@dataclass(frozen=True, slots=True)
class TimelineRow:
    reference_date: date
    value: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioExecutiveReport:
    generated_at: datetime
    as_of_date: date
    total_portfolio_value: Decimal
    total_clients: int
    total_assets: int
    total_accounts: int
    asset_allocation: list[BreakdownRow]
    top_assets: list[BreakdownRow]
    timeline: list[TimelineRow]
    top_positions: list[PortfolioPositionRow]
    pending_reviews: int


class PositionQueryService:
    def __init__(self, db: Session) -> None:
        self.positions = PositionRepository(db)

    def list_positions(
        self,
        *,
        pagination: PaginationParams,
        account_id: int | None = None,
        asset_id: int | None = None,
        reference_date: date | None = None,
    ) -> PagedResult:
        return self.positions.list_positions(
            pagination=pagination,
            account_id=account_id,
            asset_id=asset_id,
            reference_date=reference_date,
        )


class PortfolioAnalyticsService:
    def __init__(self, db: Session) -> None:
        self.settings = get_settings()
        self.analytics = AnalyticsRepository(db)
        self.styles = self._build_styles()

    def generate_pdf(
        self,
        *,
        client_name: str | None = None,
        asset_class: str | None = None,
        reference_date: date | None = None,
    ) -> bytes:
        report = self.build_report(
            client_name=client_name,
            asset_class=asset_class,
            reference_date=reference_date,
        )
        return self._render_pdf(report)

    def build_report(
        self,
        *,
        client_name: str | None = None,
        asset_class: str | None = None,
        reference_date: date | None = None,
    ) -> PortfolioExecutiveReport:
        scoped_rows = self._fetch_portfolio_rows(client_name=client_name, asset_class=asset_class)
        if not scoped_rows:
            raise ApplicationError(
                "No portfolio data available to generate the executive PDF report.",
                error_code="report_data_unavailable",
            )

        available_dates = sorted({row.reference_date for row in scoped_rows})
        as_of_date = reference_date or available_dates[-1]
        current_rows = [row for row in scoped_rows if row.reference_date == as_of_date]
        if not current_rows:
            raise ApplicationError(
                f"No portfolio positions are available for reference date {as_of_date.isoformat()}.",
                error_code="report_data_unavailable",
            )

        total_value = sum((row.total_value for row in current_rows), Decimal("0"))
        total_clients = len({row.client_name for row in current_rows})
        total_assets = len({row.ticker or row.asset_name for row in current_rows})
        total_accounts = len({(row.client_name, row.broker) for row in current_rows})

        return PortfolioExecutiveReport(
            generated_at=datetime.now(UTC),
            as_of_date=as_of_date,
            total_portfolio_value=total_value,
            total_clients=total_clients,
            total_assets=total_assets,
            total_accounts=total_accounts,
            asset_allocation=self._build_breakdown(current_rows, key=lambda row: row.asset_class)[:8],
            top_assets=self._build_breakdown(current_rows, key=lambda row: row.ticker or row.asset_name)[:8],
            timeline=self._build_timeline(scoped_rows),
            top_positions=sorted(current_rows, key=lambda row: row.total_value, reverse=True)[:12],
            pending_reviews=self.analytics.count_pending_reviews(),
        )

    def _fetch_portfolio_rows(
        self,
        *,
        client_name: str | None = None,
        asset_class: str | None = None,
    ) -> list[PortfolioPositionRow]:
        rows = self.analytics.fetch_portfolio_rows(client_name=client_name, asset_class=asset_class)
        return [
            PortfolioPositionRow(
                client_name=row[0],
                risk_profile=row[1],
                broker=row[2],
                asset_class=row[3],
                ticker=row[4] or "",
                asset_name=row[5],
                quantity=row[6],
                avg_price=row[7],
                total_value=row[8],
                reference_date=row[9],
            )
            for row in rows
        ]

    def _build_breakdown(
        self,
        rows: list[PortfolioPositionRow],
        *,
        key,
    ) -> list[BreakdownRow]:
        total = sum((row.total_value for row in rows), Decimal("0")) or Decimal("1")
        grouped: dict[str, Decimal] = {}
        for row in rows:
            label = key(row)
            grouped[label] = grouped.get(label, Decimal("0")) + row.total_value
        return sorted(
            [BreakdownRow(label=label, value=value, share=float(value / total)) for label, value in grouped.items()],
            key=lambda item: item.value,
            reverse=True,
        )

    def _build_timeline(self, rows: list[PortfolioPositionRow]) -> list[TimelineRow]:
        grouped: dict[date, Decimal] = {}
        for row in rows:
            grouped[row.reference_date] = grouped.get(row.reference_date, Decimal("0")) + row.total_value
        return [
            TimelineRow(reference_date=reference_date, value=value)
            for reference_date, value in sorted(grouped.items(), key=lambda item: item[0])
        ]

    def _render_pdf(self, report: PortfolioExecutiveReport) -> bytes:
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
        )

        story = [self._build_header(report), Spacer(1, 10), self._build_kpi_grid(report), Spacer(1, 12)]

        if report.pending_reviews:
            story.extend(
                [
                    self._build_note_box(
                        "Processing note",
                        f"There are {report.pending_reviews} ingestion runs pending human review. Validate them before sharing the final portfolio pack externally.",
                    ),
                    Spacer(1, 12),
                ]
            )

        story.extend(
            [
                self._build_section_heading("Allocation by Asset Class", "Current distribution of portfolio value across the tracked investment classes."),
                self._build_breakdown_table(report.asset_allocation, label_header="Asset Class"),
                Spacer(1, 12),
                self._build_section_heading("Top Assets by Value", "Leading positions by consolidated market value in the selected snapshot."),
                self._build_breakdown_table(report.top_assets, label_header="Asset"),
                Spacer(1, 12),
                self._build_section_heading("Portfolio Evolution", "Best-effort timeline of portfolio value across available reference dates."),
                self._build_timeline_table(report.timeline),
                Spacer(1, 12),
                self._build_section_heading("Top Positions", "Largest positions in the current portfolio cut, sorted by total value."),
                self._build_positions_table(report.top_positions),
            ]
        )

        document.build(story, onFirstPage=self._draw_footer, onLaterPages=self._draw_footer)
        return buffer.getvalue()

    def _build_header(self, report: PortfolioExecutiveReport) -> Table:
        heading = Paragraph(f"{self.settings.project_name} Executive Report", self.styles["hero_title"])
        subtitle = Paragraph(
            f"Generated on {self._format_datetime(report.generated_at)} • Snapshot date {self._format_date(report.as_of_date)}",
            self.styles["hero_subtitle"],
        )
        body = Paragraph(
            "A concise operating summary built from the local journal dataset, ready for review and daily decision support.",
            self.styles["hero_body"],
        )
        table = Table([[heading], [subtitle], [body]], colWidths=[178 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
                    ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#0F172A")),
                    ("INNERPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 16),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ]
            )
        )
        return table

    def _build_kpi_grid(self, report: PortfolioExecutiveReport) -> Table:
        cards = [
            self._metric_card("Total Portfolio Value", self._format_currency(report.total_portfolio_value), "Current AUM snapshot"),
            self._metric_card("Number of Clients", str(report.total_clients), "Clients represented in this cut"),
            self._metric_card("Tracked Assets", str(report.total_assets), "Unique tickers or product lines"),
            self._metric_card("Active Accounts", str(report.total_accounts), "Client-broker relationships"),
        ]
        table = Table([cards[:2], cards[2:]], colWidths=[87 * mm, 87 * mm], rowHeights=[27 * mm, 27 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        return table

    def _metric_card(self, label: str, value: str, helper: str) -> Table:
        table = Table(
            [[Paragraph(label, self.styles["metric_label"])], [Paragraph(value, self.styles["metric_value"])], [Paragraph(helper, self.styles["metric_helper"])]],
            colWidths=[84 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D7E2EE")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _build_note_box(self, title: str, body: str) -> Table:
        table = Table([[Paragraph(title, self.styles["note_title"])], [Paragraph(body, self.styles["note_body"])]], colWidths=[178 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#FDBA74")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _build_section_heading(self, title: str, description: str) -> Table:
        table = Table([[Paragraph(title, self.styles["section_title"])], [Paragraph(description, self.styles["section_body"])]], colWidths=[178 * mm])
        table.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        return table

    def _build_breakdown_table(self, rows: list[BreakdownRow], *, label_header: str) -> Table:
        data = [[label_header, "Value", "Share"]]
        for row in rows:
            data.append([row.label.replace("_", " ").title(), self._format_currency(row.value), self._format_percent(row.share)])
        return self._styled_table(data, right_aligned_columns=[1, 2])

    def _build_timeline_table(self, rows: list[TimelineRow]) -> Table:
        data = [["Reference Date", "Total Value"]]
        for row in rows[-8:]:
            data.append([self._format_date(row.reference_date), self._format_currency(row.value)])
        return self._styled_table(data, right_aligned_columns=[1])

    def _build_positions_table(self, rows: list[PortfolioPositionRow]) -> Table:
        data = [["Client", "Asset", "Ticker", "Class", "Quantity", "Avg Price", "Total Value", "Date"]]
        for row in rows:
            data.append(
                [
                    row.client_name,
                    row.asset_name,
                    row.ticker or "-",
                    row.asset_class.replace("_", " ").title(),
                    self._format_number(row.quantity, row.quantity < 1),
                    self._format_currency(row.avg_price),
                    self._format_currency(row.total_value),
                    self._format_date(row.reference_date),
                ]
            )
        return self._styled_table(data, right_aligned_columns=[4, 5, 6, 7], font_size=8.4)

    def _styled_table(
        self,
        data: list[list[str]],
        *,
        right_aligned_columns: list[int],
        font_size: float = 9.2,
    ) -> Table:
        table = Table(data, repeatRows=1)
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7E2EE")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        for column in right_aligned_columns:
            style_commands.append(("ALIGN", (column, 0), (column, -1), "RIGHT"))
        table.setStyle(TableStyle(style_commands))
        return table

    def _draw_footer(self, canvas, document) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(16 * mm, 8 * mm, f"{self.settings.project_name} • Executive report")
        canvas.drawRightString(194 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    def _build_styles(self) -> dict[str, ParagraphStyle]:
        styles = getSampleStyleSheet()
        return {
            "hero_title": ParagraphStyle("hero_title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=28, textColor=colors.white, alignment=TA_LEFT),
            "hero_subtitle": ParagraphStyle("hero_subtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=13, textColor=colors.HexColor("#BAE6FD")),
            "hero_body": ParagraphStyle("hero_body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=15, textColor=colors.HexColor("#CBD5E1")),
            "metric_label": ParagraphStyle("metric_label", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.3, textColor=colors.HexColor("#475569")),
            "metric_value": ParagraphStyle("metric_value", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=17, leading=22, textColor=colors.HexColor("#0F172A")),
            "metric_helper": ParagraphStyle("metric_helper", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=11, textColor=colors.HexColor("#64748B")),
            "section_title": ParagraphStyle("section_title", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=colors.HexColor("#0F172A")),
            "section_body": ParagraphStyle("section_body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=14, textColor=colors.HexColor("#64748B")),
            "note_title": ParagraphStyle("note_title", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10.5, textColor=colors.HexColor("#9A3412")),
            "note_body": ParagraphStyle("note_body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=14, textColor=colors.HexColor("#9A3412")),
        }

    @staticmethod
    def _format_currency(value: Decimal) -> str:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _format_percent(value: float) -> str:
        return f"{value * 100:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _format_number(value: Decimal, high_precision: bool = False) -> str:
        precision = 4 if high_precision else 2
        return f"{value:,.{precision}f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _format_date(value: date) -> str:
        return value.strftime("%d/%m/%Y")

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        return value.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC")
