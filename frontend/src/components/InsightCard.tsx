import type { InsightItem } from "../types/report";

type InsightCardProps = {
  insight: InsightItem;
};

export default function InsightCard({ insight }: InsightCardProps) {
  return (
    <article className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-[0_20px_40px_rgba(15,23,42,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Insight</p>
      <h3 className="mt-3 font-display text-xl font-bold text-slate-950">{insight.title}</h3>
      <p className="mt-3 text-sm leading-7 text-slate-600">{insight.body}</p>
    </article>
  );
}
