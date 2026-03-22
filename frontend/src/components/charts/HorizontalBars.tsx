import { formatCurrency, formatPercent } from "../../lib/formatters";
import { chartPalette } from "../../lib/presentation";
import type { BreakdownItem } from "../../types/report";

type HorizontalBarsProps = {
  items: BreakdownItem[];
  tone?: "blue" | "teal";
};

export default function HorizontalBars({ items, tone = "blue" }: HorizontalBarsProps) {
  const palette = tone === "blue" ? chartPalette : ["#14b8a6", "#0f766e", "#2dd4bf", "#34d399", "#99f6e4"];

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item.label} className="rounded-[22px] border border-slate-100 bg-slate-50 px-4 py-4" title={`${item.label}: ${formatCurrency(item.value)}`}>
          <div className="mb-3 flex items-center justify-between gap-4">
            <div className="flex min-w-0 items-start gap-3">
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white text-[11px] font-bold text-slate-500">
                {index + 1}
              </div>
              <div className="min-w-0">
              <div className="text-sm font-semibold text-slate-950">{item.label}</div>
                <div className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">{formatPercent(item.share)}</div>
              </div>
            </div>
            <div className="text-right text-sm font-semibold text-slate-700">{formatCurrency(item.value)}</div>
          </div>
          <div className="h-2.5 rounded-full bg-slate-200">
            <div
              className="h-2.5 rounded-full"
              style={{
                width: `${Math.max(item.share * 100, 6)}%`,
                background: `linear-gradient(90deg, ${palette[index % palette.length]}, ${palette[(index + 1) % palette.length]})`
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
