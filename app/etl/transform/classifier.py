from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class AssetClassificationRule:
    asset_class: str
    keywords: tuple[str, ...] = ()
    exact_tickers: tuple[str, ...] = ()
    ticker_prefixes: tuple[str, ...] = ()
    ticker_suffixes: tuple[str, ...] = ()


CLASSIFICATION_RULES: tuple[AssetClassificationRule, ...] = (
    AssetClassificationRule(
        asset_class="crypto",
        keywords=("BITCOIN", "ETHEREUM", "CRYPTO", "USDT", "SOLANA"),
        exact_tickers=("BTC", "ETH", "SOL", "USDT"),
    ),
    AssetClassificationRule(
        asset_class="fixed_income",
        keywords=("CDB", "LCI", "LCA", "TESOURO", "DEBENTURE", "CRI", "CRA", "BOND", "RENDA FIXA", "RDB"),
        ticker_prefixes=("CDB", "LCI", "LCA", "TD", "NTN"),
    ),
    AssetClassificationRule(
        asset_class="funds",
        keywords=("FII", "FUNDO", "ETF", "FUND", "PREV", "MULTIMERCADO"),
        exact_tickers=("XPML11", "HGLG11", "IVVB11"),
        ticker_suffixes=("11",),
    ),
    AssetClassificationRule(
        asset_class="equities",
        keywords=("ACAO", "ACOES", "EQUITY", "STOCK", "BDR"),
        ticker_suffixes=("3", "4", "5", "6"),
    ),
)


def classify_asset(asset_name: str, ticker: str | None) -> str:
    normalized_ticker = (ticker or "").upper()
    searchable_text = f"{asset_name} {normalized_ticker}".upper()

    for rule in CLASSIFICATION_RULES:
        if _matches_rule(rule, searchable_text, normalized_ticker):
            return rule.asset_class

    return "others"


def _matches_rule(rule: AssetClassificationRule, searchable_text: str, ticker: str) -> bool:
    if any(keyword in searchable_text for keyword in rule.keywords):
        return True
    if ticker and ticker in rule.exact_tickers:
        return True
    if ticker and any(ticker.startswith(prefix) for prefix in rule.ticker_prefixes):
        return True
    if ticker and any(ticker.endswith(suffix) for suffix in rule.ticker_suffixes):
        return True
    return False


def apply_asset_classification(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()
    frame["asset_class"] = frame.apply(
        lambda row: classify_asset(row["normalized_name"], row["ticker"]),
        axis=1,
    )
    return frame
