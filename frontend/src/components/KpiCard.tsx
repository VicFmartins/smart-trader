import { formatCurrency, formatNumber } from "../lib/formatters";
import type { MetricCard } from "../types/report";

const toneStyles: Record<MetricCard["tone"], string> = {
  blue: "from-sky-500/18 to-cyan-400/8 text-sky-600",
  teal: "from-teal-500/18 to-emerald-400/8 text-teal-600",
  gold: "from-amber-400/20 to-yellow-300/8 text-amber-600",
  slate: "from-slate-300/50 to-slate-100 text-slate-700"
};

type KpiCardProps = {
  item: MetricCard;
};

export default function KpiCard({ item }: KpiCardProps) {
  return (
    <article className="h-full rounded-[26px] border border-slate-200/90 bg-[linear-gradient(180deg,#ffffff_0%,#f8fbff_100%)] p-5 shadow-[0_18px_36px_rgba(15,23,42,0.05)]">
      <div className="flex items-start justify-between gap-4">
        <div
          className={`inline-flex rounded-2xl bg-gradient-to-br px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] ${toneStyles[item.tone]}`}
        >
          {item.label}
        </div>
        {item.icon ? (
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
            {item.icon}
          </div>
        ) : null}
      </div>

      <div className="mt-6 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
        {item.helper ?? "Snapshot atual"}
      </div>
      <div className="mt-2 font-display text-3xl font-extrabold tracking-tight text-slate-950 sm:text-[2rem]">
        {item.format === "currency" ? formatCurrency(item.value) : formatNumber(item.value)}
      </div>
      <div className="mt-5 flex items-center justify-between gap-3 border-t border-slate-100 pt-4">
        <div className="text-xs leading-6 text-slate-500">Atualizado para leitura executiva.</div>
        <div className="rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-700">
          {item.trendLabel ?? "Stable"}
        </div>
      </div>
    </article>
  );
}
