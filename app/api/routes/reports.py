from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import optional_string
from app.core.config import get_settings
from app.db.session import get_db
from app.services.analytics import PortfolioAnalyticsService


router = APIRouter(prefix="/reports")


@router.get("/portfolio/pdf", response_class=StreamingResponse)
def download_portfolio_pdf_report(
    db: Session = Depends(get_db),
    client_name: Annotated[str | None, Query(description="Optional exact client name filter")] = None,
    asset_class: Annotated[str | None, Query(description="Optional asset class filter")] = None,
    reference_date: Annotated[date | None, Query(description="Optional reference date filter (YYYY-MM-DD)")] = None,
) -> StreamingResponse:
    resolved_client_name = optional_string(client_name)
    resolved_asset_class = optional_string(asset_class)

    pdf_bytes = PortfolioAnalyticsService(db).generate_pdf(
        client_name=resolved_client_name,
        asset_class=resolved_asset_class,
        reference_date=reference_date,
    )
    project_slug = get_settings().project_name.strip().lower().replace(" ", "_")
    filename = f"{project_slug}_executive_report.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)
