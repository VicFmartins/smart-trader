from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import APIResponse
from app.schemas.day_trade_tax import DayTradeTaxReport
from app.services.taxes import TaxCalculationService


router = APIRouter(prefix="/analytics/taxes")


@router.get("", response_model=APIResponse[DayTradeTaxReport])
def get_day_trade_tax_report(db: Session = Depends(get_db)) -> APIResponse[DayTradeTaxReport]:
    report = TaxCalculationService(db).build_day_trade_report()
    return APIResponse(data=report)
