from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.etl.detect.column_mapper import FuzzyColumnMapper
from app.etl.detect.review_queue import evaluate_review_decision
from app.etl.detect.structure_detector import StructureDetector
from app.etl.detect.value_parsers import cleanup_ticker, parse_brazilian_decimal, parse_flexible_date
from app.etl.extract.file_reader import FileReader
from app.etl.transform.normalizer import normalize_portfolio_frame


def test_fuzzy_column_mapping_maps_common_messy_labels() -> None:
    mapper = FuzzyColumnMapper()

    results = mapper.map_columns(
        [
            "Cliente do Investidor",
            "Instituição Financeira",
            "Papel / Ativo",
            "Qtde Total",
            "Preço Médio (R$)",
            "Referência",
        ]
    )

    accepted = {result.original_name: result.canonical_name for result in results if result.accepted}
    assert accepted["Cliente do Investidor"] == "client_name"
    assert accepted["Instituição Financeira"] == "broker"
    assert accepted["Papel / Ativo"] == "asset_name"
    assert accepted["Qtde Total"] == "quantity"
    assert accepted["Preço Médio (R$)"] == "avg_price"
    assert accepted["Referência"] == "reference_date"


def test_structure_detector_finds_non_first_header_row_in_csv(tmp_path: Path) -> None:
    file_path = tmp_path / "messy_positions.csv"
    file_path.write_text(
        "\n".join(
            [
                "Relatorio XP;",
                "Gerado em;18/03/2026",
                "Cliente;Corretora;Ativo;Quantidade;Data Referencia",
                "Maria Oliveira;XP;Tesouro Selic 2029;15;18/03/2026",
            ]
        ),
        encoding="utf-8",
    )

    result = StructureDetector().read(file_path)

    assert result.detection.file_type == "csv"
    assert result.detection.header_row == 2
    assert result.dataframe.columns.tolist() == [
        "Cliente",
        "Corretora",
        "Ativo",
        "Quantidade",
        "Data Referencia",
    ]


def test_brazilian_value_parsers_handle_money_dates_and_tickers() -> None:
    assert parse_brazilian_decimal("R$ 5.000,00") == Decimal("5000.00")
    assert str(parse_flexible_date("18/03/2026")) == "2026-03-18"
    assert cleanup_ticker("PETR-4") == "PETR4"


def test_review_decision_requires_review_when_required_fields_are_missing() -> None:
    mapper = FuzzyColumnMapper()
    results = mapper.map_columns(["Cliente", "Corretora", "Valor Total"])

    decision = evaluate_review_decision(results)

    assert decision.review_required is True
    assert "asset_name" in decision.missing_required_fields
    assert "quantity" in decision.missing_required_fields
    assert "reference_date" in decision.missing_required_fields


def test_file_reader_and_normalizer_can_recover_messy_portfolio_csv(tmp_path: Path) -> None:
    file_path = tmp_path / "portfolio_messy.csv"
    file_path.write_text(
        "\n".join(
            [
                "Carteira consolidada XP;;;;;;",
                "Emitido em;18/03/2026;;;;;",
                "Cliente do Investidor;Instituição Financeira;Papel / Ativo;Qtde Total;Preço Médio (R$);Valor Total (R$);Referência",
                "Maria Oliveira;XP Investimentos;Tesouro Selic 2029;15;10.250,33;153.754,95;18/03/2026",
                "João Mendes;BTG Pactual;PETR-4;120;36,45;4.374,00;18/03/2026",
            ]
        ),
        encoding="utf-8",
    )

    dataframe = FileReader().read(file_path)
    normalized = normalize_portfolio_frame(dataframe)

    assert dataframe.attrs["parser_name"] == "smart_tabular_reader"
    assert dataframe.attrs["review_required"] is False
    assert dataframe.attrs["detection_confidence"] >= 65.0
    assert normalized.shape[0] == 2
    assert normalized.loc[0, "ticker"] is None
    assert normalized.loc[0, "quantity"] == Decimal("15")
    assert normalized.loc[0, "avg_price"] == Decimal("10250.33")
    assert normalized.loc[0, "total_value"] == Decimal("153754.95")
    assert str(normalized.loc[0, "reference_date"]) == "2026-03-18"
    assert normalized.loc[1, "normalized_name"] == "PETR-4"


def test_file_reader_and_normalizer_infer_broker_from_btg_filename_when_column_is_missing(tmp_path: Path) -> None:
    file_path = tmp_path / "BTG_leads_positions.csv"
    file_path.write_text(
        "\n".join(
            [
                "Relatorio Leads BTG;;;;",
                "Cliente;AdvisorCode;Ativo;Quantidade;Data Referencia",
                "Ana Costa;BTG-LEAD-001;CDB Banco Itau 2028;5;18/03/2026",
            ]
        ),
        encoding="utf-8",
    )

    dataframe = FileReader().read(file_path)
    normalized = normalize_portfolio_frame(dataframe)

    assert normalized.loc[0, "broker"] == "BTG"
    assert normalized.attrs["review_required"] is True
    assert "broker_inferred" in normalized.attrs["review_reasons"]
