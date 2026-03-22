function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function resolveDate(value: string) {
  if (!value) {
    return null;
  }

  const candidate = value.includes("T") || value.endsWith("Z") ? new Date(value) : new Date(`${value}T00:00:00`);
  return Number.isNaN(candidate.getTime()) ? null : candidate;
}

export function formatCurrency(value: number) {
  if (!isFiniteNumber(value)) {
    return "-";
  }

  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 2
  }).format(value);
}

export function formatNumber(value: number, maximumFractionDigits = 0) {
  if (!isFiniteNumber(value)) {
    return "-";
  }

  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits
  }).format(value);
}

export function formatPercent(value: number) {
  if (!isFiniteNumber(value)) {
    return "-";
  }

  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1
  }).format(value);
}

export function formatDate(value: string) {
  const date = resolveDate(value);
  if (!date) {
    return "Data indisponível";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  }).format(date);
}

export function formatDateTime(value: string) {
  const date = resolveDate(value);
  if (!date) {
    return "Data indisponível";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}
