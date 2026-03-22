from __future__ import annotations

from datetime import date

import pandas as pd


KNOWN_METADATA: dict[str, dict[str, str | date | None]] = {
    "BITCOIN": {"cnpj": None, "maturity_date": None},
    "ETHEREUM": {"cnpj": None, "maturity_date": None},
    "TESOURO SELIC 2029": {"cnpj": "00.000.000/0001-91", "maturity_date": date(2029, 3, 1)},
}


def build_mock_cnpj(asset_name: str) -> str | None:
    if asset_name in {"BITCOIN", "ETHEREUM"}:
        return None

    base = sum(ord(char) for char in asset_name) % 10_000_000_000
    digits = f"{base:014d}"
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def build_mock_maturity(asset_class: str, asset_name: str) -> date | None:
    if asset_class != "fixed_income":
        return None

    year_seed = 2027 + (sum(ord(char) for char in asset_name) % 5)
    return date(year_seed, 12, 15)


def enrich_assets(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()
    frame["cnpj"] = frame["normalized_name"].map(
        lambda name: KNOWN_METADATA.get(name, {}).get("cnpj") or build_mock_cnpj(name)
    )
    frame["maturity_date"] = frame.apply(
        lambda row: KNOWN_METADATA.get(row["normalized_name"], {}).get("maturity_date")
        or build_mock_maturity(row["asset_class"], row["normalized_name"]),
        axis=1,
    )
    frame.attrs["rows_skipped"] = dataframe.attrs.get("rows_skipped", 0)
    return frame
