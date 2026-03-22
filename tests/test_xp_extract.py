from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.etl.extract.file_reader import FileReader
from app.etl.extract.xp_bundle_parser import XPBundleParser


def test_xp_position_parser_reads_position_workbook(tmp_path: Path) -> None:
    file_path = tmp_path / "XP_Posicao_Inicial_2026-03-15.xlsx"
    frame = pd.DataFrame(
        {
            "Cliente": ["Joao Mendes"],
            "Produto": ["Tesouro Selic 2029"],
            "Codigo": ["SELIC29"],
            "Quantidade": ["15"],
            "Preco Medio": ["10.250,33"],
            "Valor Financeiro": ["153.754,95"],
            "Data Posicao": ["15/03/2026"],
        }
    )
    frame.to_excel(file_path, index=False)

    parsed = FileReader().read(file_path)

    assert parsed.attrs["parser_name"] == "xp_position_parser"
    assert parsed.loc[0, "broker"] == "XP"
    assert parsed.loc[0, "client_name"] == "Joao Mendes"
    assert parsed.loc[0, "asset_name"] == "Tesouro Selic 2029"


def test_xp_bundle_parser_uses_movement_aggregation_when_no_snapshot_exists(tmp_path: Path) -> None:
    file_path = tmp_path / "XP_Movimentacoes_2026-03-15.xlsx"
    frame = pd.DataFrame(
        {
            "Cliente": ["Ana Costa", "Ana Costa"],
            "Produto": ["Bitcoin", "Bitcoin"],
            "Ticker": ["BTC", "BTC"],
            "Quantidade": ["1,50", "0,25"],
            "Preco Unitario": ["400.000,00", "420.000,00"],
            "Valor Financeiro": ["600.000,00", "105.000,00"],
            "Movimentacao": ["Compra", "Venda"],
            "Data Movimento": ["15/03/2026", "16/03/2026"],
        }
    )
    frame.to_excel(file_path, index=False)

    parsed = XPBundleParser().parse_directory(tmp_path)

    assert parsed.attrs["parser_name"] == "xp_bundle_parser"
    assert len(parsed) == 1
    assert parsed.loc[0, "broker"] == "XP"
    assert parsed.loc[0, "asset_name"] == "Bitcoin"
    assert parsed.loc[0, "quantity"] == Decimal("1.25")
