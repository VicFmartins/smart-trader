from datetime import date

from app.schemas.common import ORMModel


class AssetRead(ORMModel):
    id: int
    ticker: str | None
    original_name: str
    normalized_name: str
    asset_class: str
    cnpj: str | None
    maturity_date: date | None
