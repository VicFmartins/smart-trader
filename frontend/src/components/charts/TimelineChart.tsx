import { formatCurrency, formatDate } from "../../lib/formatters";
import type { TimelinePoint } from "../../types/report";

type TimelineChartProps = {
  items: TimelinePoint[];
};

export default function TimelineChart({ items }: TimelineChartProps) {
  if (!items.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-sm text-slate-400">
        Sem historico suficiente para visualizar a evolucao do portfolio.
      </div>
    );
  }

  const values = items.map((item) => item.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);

  const coordinates = items.map((item, index) => {
    const x = items.length === 1 ? 30 : 30 + (index * 320) / (items.length - 1);
    const y = 160 - ((item.value - min) / range) * 120;
    return { ...item, x, y };
  });

  const points = coordinates.map((item) => `${item.x},${item.y}`).join(" ");
  const fillPath = `M30 160 L ${points} L 350 160 Z`;

  return (
    <div>
      <svg viewBox="0 0 380 190" className="h-[220px] w-full overflow-visible">
        <defs>
          <linearGradient id="timelineStroke" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0ea5e9" />
            <stop offset="100%" stopColor="#1d4ed8" />
          </linearGradient>
          <linearGradient id="timelineFill" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="rgba(14,165,233,0.18)" />
            <stop offset="100%" stopColor="rgba(29,78,216,0.02)" />
          </linearGradient>
        </defs>
        <path d="M30 160H350" stroke="#e2e8f0" strokeWidth="1.5" strokeDasharray="4 6" />
        <path d={fillPath} fill="url(#timelineFill)" />
        <polyline
          fill="none"
          stroke="url(#timelineStroke)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
        />
        {coordinates.map((item) => (
          <g key={item.date}>
            <circle cx={item.x} cy={item.y} r="5.5" fill="#0f172a" stroke="#38bdf8" strokeWidth="3">
              <title>{`${formatDate(item.date)}: ${formatCurrency(item.value)}`}</title>
            </circle>
            <text x={item.x} y={182} textAnchor="middle" className="fill-slate-400 text-[11px] font-medium">
              {formatDate(item.date)}
            </text>
          </g>
        ))}
      </svg>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {items.slice(-3).map((item) => (
          <div key={item.date} className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{formatDate(item.date)}</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">{formatCurrency(item.value)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
