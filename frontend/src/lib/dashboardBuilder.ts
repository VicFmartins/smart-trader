import type { PortfolioSnapshotApi } from "./api";
import { joinSnapshot, sanitizePortfolioRecords } from "./reportBuilder";
import type { BreakdownItem, DashboardData, DashboardFilters, MetricCard, PortfolioRecord, TimelinePoint } from "../types/report";

function uniqueSorted(values: string[]) {
  return [...new Set(values.filter(Boolean))].sort((left, right) => left.localeCompare(right, "pt-BR"));
}

function buildBreakdown(records: PortfolioRecord[], getKey: (record: PortfolioRecord) => string): BreakdownItem[] {
  const total = records.reduce((sum, record) => sum + record.totalValue, 0) || 1;
  const grouped = new Map<string, number>();

  records.forEach((record) => {
    const key = getKey(record);
    grouped.set(key, (grouped.get(key) ?? 0) + record.totalValue);
  });

  return [...grouped.entries()]
    .map(([label, value]) => ({ label, value, share: value / total }))
    .sort((left, right) => right.value - left.value);
}

function buildTimeline(records: PortfolioRecord[]): TimelinePoint[] {
  const grouped = new Map<string, number>();
  records.forEach((record) => {
    grouped.set(record.referenceDate, (grouped.get(record.referenceDate) ?? 0) + record.totalValue);
  });

  return [...grouped.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([date, value]) => ({ date, value }));
}

function buildTopAssets(records: PortfolioRecord[]): BreakdownItem[] {
  return buildBreakdown(records, (record) => record.ticker || record.assetName).slice(0, 8);
}

function buildMetrics(records: PortfolioRecord[]): MetricCard[] {
  const totalValue = records.reduce((sum, record) => sum + record.totalValue, 0);
  const totalClients = new Set(records.map((record) => record.clientName)).size;
  const totalAssets = new Set(records.map((record) => record.ticker || record.assetName)).size;
  const totalAccounts = new Set(records.map((record) => `${record.clientName}|${record.broker}`)).size;

  return [
    {
      label: "Total Portfolio Value",
      value: totalValue,
      tone: "blue",
      format: "currency",
      helper: "Valor consolidado no recorte atual",
      icon: "PV",
      trendLabel: "Snapshot atual"
    },
    {
      label: "Number of Clients",
      value: totalClients,
      tone: "teal",
      format: "number",
      helper: "Clientes com posicoes neste corte",
      icon: "CL",
      trendLabel: "Base ativa"
    },
    {
      label: "Tracked Assets",
      value: totalAssets,
      tone: "gold",
      format: "number",
      helper: "Ativos unicos monitorados",
      icon: "AT",
      trendLabel: "Universo atual"
    },
    {
      label: "Active Accounts",
      value: totalAccounts,
      tone: "slate",
      format: "number",
      helper: "Relacionamentos cliente-corretora",
      icon: "AC",
      trendLabel: "Custodia viva"
    }
  ];
}

export function buildDashboardData(snapshot: PortfolioSnapshotApi, filters: DashboardFilters): DashboardData {
  const records = sanitizePortfolioRecords(joinSnapshot(snapshot.clients, snapshot.accounts, snapshot.assets, snapshot.positions));
  const availableClients = uniqueSorted(records.map((record) => record.clientName));
  const availableAssetClasses = uniqueSorted(records.map((record) => record.assetClass));

  const scopedRecords = records.filter((record) => {
    if (filters.clientName && record.clientName !== filters.clientName) return false;
    if (filters.assetClass && record.assetClass !== filters.assetClass) return false;
    return true;
  });

  const availableReferenceDates = uniqueSorted(scopedRecords.map((record) => record.referenceDate)).sort((left, right) =>
    right.localeCompare(left)
  );
  const effectiveReferenceDate = filters.referenceDate || availableReferenceDates[0] || "";
  const currentRecords = scopedRecords
    .filter((record) => (!effectiveReferenceDate ? true : record.referenceDate === effectiveReferenceDate))
    .sort((left, right) => right.totalValue - left.totalValue);

  return {
    asOfDate: effectiveReferenceDate || null,
    metrics: buildMetrics(currentRecords),
    assetAllocation: buildBreakdown(currentRecords, (record) => record.assetClass).slice(0, 8),
    clientAllocation: buildBreakdown(currentRecords, (record) => record.clientName).slice(0, 8),
    topAssets: buildTopAssets(currentRecords),
    timeline: buildTimeline(scopedRecords),
    positions: currentRecords.slice(0, 20),
    availableClients,
    availableAssetClasses,
    availableReferenceDates
  };
}
