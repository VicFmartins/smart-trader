import { formatCurrency, formatPercent } from "../../lib/formatters";
import { chartPalette } from "../../lib/presentation";
import type { BreakdownItem } from "../../types/report";

type DonutChartProps = {
  items: BreakdownItem[];
};

export default function DonutChart({ items }: DonutChartProps) {
  const radius = 82;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <svg viewBox="0 0 220 220" className="h-[220px] w-[220px] -rotate-90">
          <circle cx="110" cy="110" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="24" />
          {items.map((item, index) => {
            const dash = circumference * item.share;
            const currentOffset = offset;
            offset += dash;

            return (
              <circle
                key={item.label}
                cx="110"
                cy="110"
                r={radius}
                fill="none"
                stroke={chartPalette[index % chartPalette.length]}
                strokeWidth="24"
                strokeDasharray={`${dash} ${circumference - dash}`}
                strokeDashoffset={-currentOffset}
                strokeLinecap="round"
              >
                <title>{`${item.label}: ${formatCurrency(item.value)} (${formatPercent(item.share)})`}</title>
              </circle>
            );
          })}
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Total Portfolio</p>
          <p className="mt-2 max-w-[120px] font-display text-xl font-bold leading-tight text-slate-950">
            {formatCurrency(items.reduce((sum, item) => sum + item.value, 0))}
          </p>
          <p className="mt-2 text-[11px] uppercase tracking-[0.16em] text-slate-400">{items.length} segmentos</p>
        </div>
      </div>

      <div className="mt-6 w-full space-y-3">
        {items.map((item, index) => (
          <div key={item.label} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm">
            <div className="flex items-center gap-3">
              <span
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: chartPalette[index % chartPalette.length] }}
              />
              <span className="font-medium text-slate-700">{item.label}</span>
            </div>
            <div className="text-right">
              <div className="font-semibold text-slate-950">{formatPercent(item.share)}</div>
              <div className="text-xs text-slate-400">{formatCurrency(item.value)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
