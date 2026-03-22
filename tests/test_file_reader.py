from pathlib import Path

import pytest

from app.etl.extract.file_reader import FileReader


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp1252", "latin-1"])
def test_file_reader_preserves_accented_characters_for_supported_csv_encodings(
    tmp_path: Path, encoding: str
) -> None:
    file_path = tmp_path / f"portfolio_{encoding.replace('-', '_')}.csv"
    content = (
        "Cliente;Corretora;Ativo;Ticker;Qtd;Preço Médio;Valor Total;Data de Referência;Perfil\n"
        "João Mendes;Itaú;CDB Banco Itaú 2028;CDBITAU28;10;1.050,00;10.500,00;15/03/2026;moderado\n"
    )
    file_path.write_bytes(content.encode(encoding))

    dataframe = FileReader().read(file_path)

    assert dataframe.attrs["parser_name"] == "smart_tabular_reader"
    assert dataframe.loc[0, "client_name"] == "João Mendes"
    assert dataframe.loc[0, "broker"] == "Itaú"
    assert dataframe.loc[0, "avg_price"] == "1.050,00"
