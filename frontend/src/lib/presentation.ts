const assetClassLabels: Record<string, string> = {
  fixed_income: "Renda fixa",
  equities: "Ações",
  crypto: "Cripto",
  funds: "Fundos",
  others: "Outros"
};

export function assetClassLabel(value: string) {
  return assetClassLabels[value] ?? value.replace(/_/g, " ");
}

export const chartPalette = ["#0f766e", "#0ea5e9", "#1d4ed8", "#14b8a6", "#0891b2", "#334155", "#16a34a", "#f59e0b"];
