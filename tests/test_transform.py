from decimal import Decimal

import pandas as pd
import pytest

from app.core.exceptions import ETLValidationError
from app.etl.enrich.asset_enricher import enrich_assets
from app.etl.transform.classifier import apply_asset_classification
from app.etl.transform.normalizer import normalize_portfolio_frame


def test_portfolio_frame_normalization_and_enrichment() -> None:
    raw_frame = pd.DataFrame(
        [
            {
                "Cliente": "Maria Oliveira",
                "Corretora": "XP Investimentos",
                "Ativo": "Tesouro Selic 2029",
                "Ticker": "SELIC29",
                "Qtd": "15",
                "Preco Medio": "10.250,33",
                "Valor Total": "153.754,95",
                "Data de Referencia": "15/03/2026",
                "Perfil": "Moderado",
            },
            {
                "Cliente": "Ana Costa",
                "Corretora": "Avenue Securities",
                "Ativo": "Bitcoin",
                "Ticker": "BTC",
                "Qtd": "0,35",
                "Preco Medio": "412.000,00",
                "Valor Total": "144.200,00",
                "Data de Referencia": "15/03/2026",
                "Perfil": "Arrojado",
            },
        ]
    )

    normalized = normalize_portfolio_frame(raw_frame)
    classified = apply_asset_classification(normalized)
    enriched = enrich_assets(classified)

    assert normalized.loc[0, "broker"] == "XP"
    assert normalized.loc[0, "quantity"] == Decimal("15")
    assert normalized.loc[0, "avg_price"] == Decimal("10250.33")
    assert normalized.loc[1, "broker"] == "AVENUE"
    assert normalized.loc[1, "quantity"] == Decimal("0.35")
    assert classified.loc[0, "asset_class"] == "fixed_income"
    assert classified.loc[1, "asset_class"] == "crypto"
    assert enriched.loc[0, "cnpj"] is not None
    assert enriched.loc[1, "maturity_date"] is None


def test_normalizer_handles_extended_column_aliases() -> None:
    raw_frame = pd.DataFrame(
        [
            {
                "Nome do Investidor": "Carlos Pereira",
                "Instituicao Financeira": "Itaú Corretora",
                "Descricao do Ativo": "Fundo Multimercado Alpha",
                "Codigo do Ativo": "ALPHAFIM",
                "Quantidade Disponivel": "125",
                "Average Price": "15.25",
                "Market Value": "1906.25",
                "Position Date": "2026-03-15",
                "Suitability": "Moderado",
            }
        ]
    )

    normalized = normalize_portfolio_frame(raw_frame)

    assert normalized.loc[0, "broker"] == "ITAU"
    assert normalized.loc[0, "quantity"] == Decimal("125")
    assert normalized.loc[0, "avg_price"] == Decimal("15.25")
    assert normalized.loc[0, "reference_date"].isoformat() == "2026-03-15"


def test_normalizer_drops_invalid_rows_and_tracks_skips() -> None:
    raw_frame = pd.DataFrame(
        [
            {
                "Cliente": "Valid Client",
                "Corretora": "BTG",
                "Ativo": "PETR4",
                "Qtd": "10",
                "Preco Medio": "30,50",
                "Data de Referencia": "15/03/2026",
            },
            {
                "Cliente": "",
                "Corretora": "BTG",
                "Ativo": "PETR4",
                "Qtd": "invalid",
                "Preco Medio": "30,50",
                "Data de Referencia": "",
            },
        ]
    )

    normalized = normalize_portfolio_frame(raw_frame)

    assert len(normalized) == 1
    assert normalized.attrs["rows_skipped"] == 1


def test_normalizer_raises_clear_error_for_missing_required_columns() -> None:
    raw_frame = pd.DataFrame(
        [
            {
                "Documento": "abc",
                "Descricao Livre": "sem colunas de portfolio",
            }
        ]
    )

    with pytest.raises(ETLValidationError, match="Suggested mapping"):
        normalize_portfolio_frame(raw_frame)


def test_normalizer_infers_missing_broker_from_source_filename_and_marks_review() -> None:
    raw_frame = pd.DataFrame(
        [
            {
                "Cliente": "Maria Oliveira",
                "Ativo": "Tesouro Selic 2029",
                "Qtd": "15",
                "Preco Medio": "10.250,33",
                "Data de Referencia": "15/03/2026",
                "AdvisorCode": "XP-001",
            }
        ]
    )
    raw_frame.attrs["source_filename"] = "XP_client_positions_20260319.csv"

    normalized = normalize_portfolio_frame(raw_frame)

    assert normalized.loc[0, "broker"] == "XP"
    assert normalized.attrs["review_required"] is True
    assert "broker_inferred" in normalized.attrs["review_reasons"]


def test_normalizer_defaults_missing_broker_to_unknown_and_marks_review() -> None:
    raw_frame = pd.DataFrame(
        [
            {
                "Cliente": "Lead BTG",
                "Ativo": "CDB Banco Itau 2028",
                "Qtd": "5",
                "Preco Medio": "1.000,00",
                "Data de Referencia": "15/03/2026",
            }
        ]
    )

    normalized = normalize_portfolio_frame(raw_frame)

    assert normalized.loc[0, "broker"] == "UNKNOWN"
    assert normalized.attrs["review_required"] is True
    assert "broker_defaulted_unknown" in normalized.attrs["review_reasons"]
