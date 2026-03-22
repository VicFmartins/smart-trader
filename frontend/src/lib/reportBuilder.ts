import { fetchPortfolioSnapshot, type AccountApi, type AssetApi, type ClientApi, type PositionApi } from "./api";
import type { BreakdownItem, InsightItem, PortfolioRecord, PortfolioReport } from "../types/report";

const columnAliases: Record<string, string[]> = {
  clientName: ["cliente", "nome do cliente", "client", "client_name", "investidor"],
  broker: ["corretora", "broker", "instituicao", "instituicao", "plataforma"],
  assetName: ["ativo", "produto", "asset", "descricao", "description", "nome do ativo"],
  ticker: ["ticker", "codigo", "codigo", "symbol", "sigla"],
  quantity: ["qtd", "qtde", "quantidade", "quantity", "saldo", "closingquantity"],
  avgPrice: ["preco medio", "preco medio", "avg price", "average price", "unit price", "closingunitprice"],
  totalValue: ["valor total", "valor atual", "market value", "total value", "closingvalue", "grossvalue"],
  referenceDate: ["data referencia", "data de referencia", "reference date", "date", "effectivedate"],
  riskProfile: ["perfil", "risk profile", "suitability", "risk_profile"]
};

function slugify(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, " ")
    .trim()
    .toLowerCase();
}

function resolveColumn(columns: string[], key: keyof typeof columnAliases) {
  const aliases = columnAliases[key];
  return columns.find((column) => aliases.includes(slugify(column)));
}

function parseNumber(value: unknown): number {
  if (value === null || value === undefined || value === "") return 0;

  const text = String(value).trim().replace(/\s/g, "").replace(/R\$/g, "");
  if (!text) return 0;

  const normalized =
    text.includes(",") && text.includes(".")
      ? text.lastIndexOf(",") > text.lastIndexOf(".")
        ? text.replace(/\./g, "").replace(",", ".")
        : text.replace(/,/g, "")
      : text.includes(",")
        ? text.replace(".", "").replace(",", ".")
        : text;

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

function ensureFiniteNumber(value: number, fallback = 0) {
  return Number.isFinite(value) ? value : fallback;
}

function sanitizeText(value: unknown, fallback: string) {
  const text = typeof value === "string" ? value.trim() : String(value ?? "").trim();
  return text || fallback;
}

function classifyAsset(assetName: string, ticker: string) {
  const value = `${assetName} ${ticker}`.toUpperCase();

  if (/(TESOURO|CDB|LCA|LFT|LTN|NTN|DEBENTURE|CRA|CRI|CPRF)/.test(value)) return "fixed_income";
  if (/(BTC|BITCOIN|ETH|ETHEREUM|SOL|CRYPTO)/.test(value)) return "crypto";
  if (/(FII|FUND|FUNDO|ETF|LISTADO)/.test(value)) return "funds";
  if (/(ON|PN|\d{1,2}|ACAO|ACAO)/.test(value)) return "equities";
  return "others";
}

function parseDate(value: unknown) {
  if (!value) return new Date().toISOString().slice(0, 10);

  const text = String(value).trim();
  if (!text) return new Date().toISOString().slice(0, 10);
  if (text.includes("T")) return text.slice(0, 10);

  const [first, second, third] = text.split(/[/-]/);
  if (third) {
    if (first.length === 4) return `${first}-${second.padStart(2, "0")}-${third.padStart(2, "0")}`;
    return `${third.padStart(4, "20")}-${second.padStart(2, "0")}-${first.padStart(2, "0")}`;
  }

  return text;
}

function normalizeReferenceDate(value: unknown) {
  const fallback = new Date().toISOString().slice(0, 10);
  if (!value) return fallback;

  const normalized = parseDate(value);
  const candidate = normalized.includes("T") || normalized.endsWith("Z") ? new Date(normalized) : new Date(`${normalized}T00:00:00`);
  if (Number.isNaN(candidate.getTime())) {
    return fallback;
  }

  return candidate.toISOString().slice(0, 10);
}

export function sanitizePortfolioRecords(records: PortfolioRecord[]) {
  return records
    .map((record) => ({
      clientName: sanitizeText(record.clientName, "Cliente consolidado"),
      riskProfile: sanitizeText(record.riskProfile, "moderado"),
      broker: sanitizeText(record.broker, "UNKNOWN"),
      assetClass: sanitizeText(record.assetClass, "others"),
      ticker: sanitizeText(record.ticker, ""),
      assetName: sanitizeText(record.assetName, sanitizeText(record.ticker, "Ativo")),
      quantity: ensureFiniteNumber(record.quantity),
      avgPrice: ensureFiniteNumber(record.avgPrice),
      totalValue: ensureFiniteNumber(record.totalValue),
      referenceDate: normalizeReferenceDate(record.referenceDate)
    }))
    .filter((record) => Boolean(record.assetName));
}

function groupBreakdown(records: PortfolioRecord[], field: "assetClass" | "broker" | "clientName"): BreakdownItem[] {
  const total = records.reduce((sum, record) => sum + record.totalValue, 0) || 1;
  const grouped = new Map<string, number>();

  records.forEach((record) => {
    grouped.set(record[field], (grouped.get(record[field]) ?? 0) + record.totalValue);
  });

  return [...grouped.entries()]
    .map(([label, value]) => ({ label, value, share: value / total }))
    .sort((left, right) => right.value - left.value);
}

function buildInsights(latestRecords: PortfolioRecord[], timeline: { date: string; value: number }[]): InsightItem[] {
  const allocation = groupBreakdown(latestRecords, "assetClass")[0];
  const broker = groupBreakdown(latestRecords, "broker")[0];
  const lastTwo = timeline.slice(-2);
  const trend =
    lastTwo.length === 2
      ? ((lastTwo[1].value - lastTwo[0].value) / Math.max(lastTwo[0].value, 1)) * 100
      : 0;

  return [
    {
      title: "Composicao dominante",
      body: allocation
        ? `A classe ${allocation.label.replace("_", " ")} concentra ${(allocation.share * 100).toFixed(1)}% do patrimonio analisado.`
        : "A composicao ainda nao oferece sinal relevante de concentracao."
    },
    {
      title: "Dependencia de plataforma",
      body: broker
        ? `${broker.label} responde pela maior fatia da custodia consolidada neste recorte.`
        : "Ainda nao ha concentracao material por corretora."
    },
    {
      title: "Trajetoria recente",
      body:
        lastTwo.length === 2
          ? `A carteira variou ${trend >= 0 ? "+" : ""}${trend.toFixed(1)}% entre os dois ultimos snapshots.`
          : "O historico ainda tem poucos pontos para leitura de tendencia."
    }
  ];
}

export function buildReport(
  records: PortfolioRecord[],
  options: { clientName?: string; diagnosis?: string; sourceLabel: string }
): PortfolioReport {
  const sanitizedRecords = sanitizePortfolioRecords(records);
  const sortedDates = [...new Set(sanitizedRecords.map((record) => record.referenceDate))].sort();
  const latestReferenceDate = sortedDates[sortedDates.length - 1] ?? new Date().toISOString().slice(0, 10);
  const latestRecords = sanitizedRecords.filter((record) => record.referenceDate === latestReferenceDate);
  const totalAum = latestRecords.reduce((sum, record) => sum + record.totalValue, 0);
  const timeline = sortedDates.map((date) => ({
    date,
    value: sanitizedRecords.filter((record) => record.referenceDate === date).reduce((sum, record) => sum + record.totalValue, 0)
  }));
  const clientLabel = options.clientName?.trim() || latestRecords[0]?.clientName || "Cliente em analise";
  const diagnosis =
    options.diagnosis?.trim() ||
    "A carteira apresenta diversificacao relevante entre classes, com leitura executiva voltada para concentracao, liquidez e posicionamento tatico.";

  return {
    clientName: clientLabel,
    diagnosis,
    sourceLabel: options.sourceLabel,
    generatedAt: new Date().toISOString(),
    latestReferenceDate,
    metrics: [
      { label: "Patrimonio Consolidado", value: totalAum, tone: "blue", format: "currency" },
      { label: "Base de Clientes", value: new Set(latestRecords.map((record) => record.clientName)).size, tone: "teal", format: "number" },
      { label: "Rede de Corretoras", value: new Set(latestRecords.map((record) => record.broker)).size, tone: "gold", format: "number" },
      { label: "Posicoes Monitoradas", value: latestRecords.length, tone: "slate", format: "number" }
    ],
    allocation: groupBreakdown(latestRecords, "assetClass"),
    brokerExposure: groupBreakdown(latestRecords, "broker"),
    clientExposure: groupBreakdown(latestRecords, "clientName"),
    timeline,
    positions: [...latestRecords].sort((left, right) => right.totalValue - left.totalValue),
    insights: buildInsights(latestRecords, timeline)
  };
}

function toRecord(row: Record<string, unknown>): PortfolioRecord {
  const columns = Object.keys(row);
  const clientColumn = resolveColumn(columns, "clientName");
  const brokerColumn = resolveColumn(columns, "broker");
  const assetColumn = resolveColumn(columns, "assetName");
  const tickerColumn = resolveColumn(columns, "ticker");
  const quantityColumn = resolveColumn(columns, "quantity");
  const avgPriceColumn = resolveColumn(columns, "avgPrice");
  const totalValueColumn = resolveColumn(columns, "totalValue");
  const referenceDateColumn = resolveColumn(columns, "referenceDate");
  const riskColumn = resolveColumn(columns, "riskProfile");

  const assetName = sanitizeText(row[assetColumn ?? ""], "Ativo");
  const ticker = sanitizeText(row[tickerColumn ?? ""], "");
  const broker = sanitizeText(row[brokerColumn ?? ""], "XP");
  const clientName = sanitizeText(row[clientColumn ?? ""], "Cliente em analise");
  const quantity = parseNumber(row[quantityColumn ?? ""]);
  const avgPrice = parseNumber(row[avgPriceColumn ?? ""]);
  const totalValue = parseNumber(row[totalValueColumn ?? ""]) || quantity * avgPrice;

  return {
    clientName,
    riskProfile: sanitizeText(row[riskColumn ?? ""], "moderado"),
    broker,
    assetClass: classifyAsset(assetName, ticker),
    ticker,
    assetName,
    quantity: ensureFiniteNumber(quantity),
    avgPrice: ensureFiniteNumber(avgPrice),
    totalValue: ensureFiniteNumber(totalValue),
    referenceDate: normalizeReferenceDate(row[referenceDateColumn ?? ""])
  };
}

export async function parseSpreadsheet(file: File) {
  const XLSX = await import("xlsx");
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });
  const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(firstSheet, { defval: "" });
  const records = sanitizePortfolioRecords(rows.map(toRecord)).filter((record) => record.assetName && record.totalValue > 0);

  if (!records.length) {
    throw new Error("A planilha nao possui colunas reconheciveis para montar a previa do relatorio.");
  }

  return records;
}

export async function loadLiveRecords() {
  const snapshot = await fetchPortfolioSnapshot();
  return joinSnapshot(snapshot.clients, snapshot.accounts, snapshot.assets, snapshot.positions);
}

export function joinSnapshot(clients: ClientApi[], accounts: AccountApi[], assets: AssetApi[], positions: PositionApi[]): PortfolioRecord[] {
  const clientMap = new Map(clients.map((client) => [client.id, client]));
  const accountMap = new Map(accounts.map((account) => [account.id, account]));
  const assetMap = new Map(assets.map((asset) => [asset.id, asset]));

  return sanitizePortfolioRecords(
    positions
      .map((position) => {
        const account = accountMap.get(position.account_id);
        const client = account ? clientMap.get(account.client_id) : undefined;
        const asset = assetMap.get(position.asset_id);
        if (!account || !asset) return null;

        return {
          clientName: sanitizeText(client?.name, "Cliente consolidado"),
          riskProfile: sanitizeText(client?.risk_profile, "moderado"),
          broker: sanitizeText(account.broker, "UNKNOWN"),
          assetClass: sanitizeText(asset.asset_class, "others"),
          ticker: sanitizeText(asset.ticker, ""),
          assetName: sanitizeText(asset.normalized_name, sanitizeText(asset.original_name, "Ativo")),
          quantity: ensureFiniteNumber(Number(position.quantity)),
          avgPrice: ensureFiniteNumber(Number(position.avg_price)),
          totalValue: ensureFiniteNumber(Number(position.total_value)),
          referenceDate: normalizeReferenceDate(position.reference_date)
        } satisfies PortfolioRecord;
      })
      .filter((record): record is PortfolioRecord => record !== null)
  );
}
