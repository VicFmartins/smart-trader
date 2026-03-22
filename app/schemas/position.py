from datetime import date
from decimal import Decimal

from app.schemas.common import ORMModel


class PositionRead(ORMModel):
    id: int
    account_id: int
    asset_id: int
    quantity: Decimal
    avg_price: Decimal
    total_value: Decimal
    reference_date: date
