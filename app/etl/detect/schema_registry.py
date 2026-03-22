from __future__ import annotations

from dataclasses import dataclass

from app.etl.transform.parsers import slugify_text


@dataclass(frozen=True, slots=True)
class SchemaField:
    canonical_name: str
    aliases: tuple[str, ...]
    required_for_confidence: bool = False

    @property
    def normalized_aliases(self) -> tuple[str, ...]:
        values = {slugify_text(self.canonical_name)}
        values.update(slugify_text(alias) for alias in self.aliases)
        return tuple(sorted(value for value in values if value))


CANONICAL_FIELDS: tuple[SchemaField, ...] = (
    SchemaField(
        canonical_name="client_name",
        aliases=(
            "cliente",
            "nome cliente",
            "nome do cliente",
            "investidor",
            "holder",
            "account holder",
            "client",
            "client name",
            "customer",
        ),
    ),
    SchemaField(
        canonical_name="broker",
        aliases=(
            "corretora",
            "instituicao",
            "institution",
            "instituicao financeira",
            "broker",
            "brokerage",
            "custodian",
            "platform",
            "banco",
        ),
    ),
    SchemaField(
        canonical_name="asset_name",
        aliases=(
            "ativo",
            "nome do ativo",
            "nome ativo",
            "descricao",
            "descricao do ativo",
            "produto",
            "papel",
            "security",
            "asset",
            "asset name",
            "instrument",
        ),
        required_for_confidence=True,
    ),
    SchemaField(
        canonical_name="ticker",
        aliases=(
            "ticker",
            "codigo",
            "codigo ativo",
            "codigo do ativo",
            "symbol",
            "asset code",
            "isin",
        ),
    ),
    SchemaField(
        canonical_name="asset_class",
        aliases=(
            "classe ativo",
            "classe do ativo",
            "asset class",
            "category",
            "tipo ativo",
        ),
    ),
    SchemaField(
        canonical_name="quantity",
        aliases=(
            "qtd",
            "qtde",
            "quantidade",
            "quantidade total",
            "saldo",
            "position",
            "quantity",
            "holding quantity",
        ),
        required_for_confidence=True,
    ),
    SchemaField(
        canonical_name="avg_price",
        aliases=(
            "preco medio",
            "preco médio",
            "avg price",
            "average price",
            "cost basis",
            "unit price",
            "preco unitario",
        ),
    ),
    SchemaField(
        canonical_name="total_value",
        aliases=(
            "valor total",
            "valor atual",
            "valor bruto",
            "total value",
            "market value",
            "gross value",
            "financial value",
        ),
    ),
    SchemaField(
        canonical_name="reference_date",
        aliases=(
            "data referencia",
            "data de referencia",
            "data referência",
            "data de referência",
            "reference date",
            "reference_date",
            "position date",
            "snapshot date",
            "date",
        ),
        required_for_confidence=True,
    ),
    SchemaField(
        canonical_name="risk_profile",
        aliases=("perfil", "perfil risco", "risk profile", "suitability"),
    ),
    SchemaField(
        canonical_name="cnpj",
        aliases=("cnpj", "issuer cnpj", "fund cnpj"),
    ),
    SchemaField(
        canonical_name="maturity_date",
        aliases=("vencimento", "data vencimento", "maturity", "maturity date", "due date"),
    ),
    SchemaField(
        canonical_name="indexador",
        aliases=("indexador", "benchmark", "index", "indexer"),
    ),
    SchemaField(
        canonical_name="taxa",
        aliases=("taxa", "yield", "rate", "coupon"),
    ),
)


class SchemaRegistry:
    def __init__(self, fields: tuple[SchemaField, ...] = CANONICAL_FIELDS) -> None:
        self.fields = fields

    def field_names(self) -> tuple[str, ...]:
        return tuple(field.canonical_name for field in self.fields)

    def alias_lookup(self) -> dict[str, set[str]]:
        return {field.canonical_name: set(field.normalized_aliases) for field in self.fields}

    def required_confidence_fields(self) -> tuple[str, ...]:
        return tuple(field.canonical_name for field in self.fields if field.required_for_confidence)
