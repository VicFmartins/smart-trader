import { formatCurrency, formatDate, formatNumber, formatPercent } from "../lib/formatters";
import { assetClassLabel } from "../lib/presentation";
import type { PortfolioReport } from "../types/report";
import InsightCard from "./InsightCard";
import KpiCard from "./KpiCard";
import DonutChart from "./charts/DonutChart";
import HorizontalBars from "./charts/HorizontalBars";
import TimelineChart from "./charts/TimelineChart";

type ReportCanvasProps = {
  report: PortfolioReport;
};

function SectionHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div className="mb-5 flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">{eyebrow}</p>
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <h2 className="font-display text-2xl font-extrabold tracking-tight text-slate-950">{title}</h2>
        <p className="max-w-2xl text-sm leading-7 text-slate-500">{description}</p>
      </div>
    </div>
  );
}

export default function ReportCanvas({ report }: ReportCanvasProps) {
  return (
    <section className="print-surface rounded-[32px] border border-slate-200 bg-[#f8fafc] p-6 shadow-[0_24px_70px_rgba(15,23,42,0.18)] md:p-8 lg:p-10">
      <header className="rounded-[28px] bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.16),transparent_22%),linear-gradient(145deg,#081223_0%,#0e1b31_55%,#14223a_100%)] p-8 text-white">
        <div className="flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.34em] text-cyan-100/70">Portfolio Analysis Report</p>
            <h1 className="mt-3 font-display text-4xl font-extrabold tracking-tight">{report.clientName}</h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300">{report.diagnosis}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Fonte</p>
              <p className="mt-2 text-sm font-semibold text-white">{report.sourceLabel}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Referência</p>
              <p className="mt-2 text-sm font-semibold text-white">{formatDate(report.latestReferenceDate)}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Gerado em</p>
              <p className="mt-2 text-sm font-semibold text-white">{formatDate(report.generatedAt)}</p>
            </div>
          </div>
        </div>
      </header>

      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {report.metrics.map((item) => (
          <KpiCard key={item.label} item={item} />
        ))}
      </div>

      <div className="mt-10 grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
        <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
          <SectionHeader
            eyebrow="Allocation Overview"
            title="Capital Allocation"
            description="Distribuição consolidada do patrimônio por classe de ativo no snapshot mais recente."
          />
          <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-center">
            <DonutChart items={report.allocation.map((item) => ({ ...item, label: assetClassLabel(item.label) }))} />
            <div className="space-y-3">
              {report.allocation.map((item) => (
                <div key={item.label} className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{assetClassLabel(item.label)}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">{formatPercent(item.share)}</p>
                    </div>
                    <p className="text-sm font-semibold text-slate-700">{formatCurrency(item.value)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </article>

        <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
          <SectionHeader
            eyebrow="Broker Exposure"
            title="Broker Exposure"
            description="Leitura rápida da concentração por plataforma e do peso relativo de cada custódia."
          />
          <HorizontalBars items={report.brokerExposure} />
        </article>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
        <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
          <SectionHeader
            eyebrow="Client Exposure"
            title="Client Exposure"
            description="Participação relativa por cliente dentro do recorte consolidado disponível para análise."
          />
          <HorizontalBars items={report.clientExposure} tone="teal" />
        </article>

        <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
          <SectionHeader
            eyebrow="Portfolio Timeline"
            title="Portfolio Trajectory"
            description="Evolução do valor consolidado entre os snapshots capturados pelo pipeline."
          />
          <TimelineChart items={report.timeline} />
        </article>
      </div>

      <div className="mt-6">
        <SectionHeader
          eyebrow="Summary Insights"
          title="Executive Highlights"
          description="Síntese narrativa pronta para sustentação executiva, com foco em concentração, custódia e evolução."
        />
        <div className="grid gap-4 xl:grid-cols-3">
          {report.insights.map((insight) => (
            <InsightCard key={insight.title} insight={insight} />
          ))}
        </div>
      </div>

      <div className="mt-6 rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
        <SectionHeader
          eyebrow="Detailed Positions"
          title="Position Ledger"
          description="Vista operacional das maiores posições do snapshot mais recente, pronta para drill-down e revisão fina."
        />

        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-3 text-left">
            <thead>
              <tr className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                <th className="px-4">Ativo</th>
                <th className="px-4">Ticker</th>
                <th className="px-4">Classe</th>
                <th className="px-4">Corretora</th>
                <th className="px-4 text-right">Quantidade</th>
                <th className="px-4 text-right">Preço médio</th>
                <th className="px-4 text-right">Valor total</th>
              </tr>
            </thead>
            <tbody>
              {report.positions.slice(0, 12).map((position) => (
                <tr key={`${position.referenceDate}-${position.ticker}-${position.broker}`} className="text-sm text-slate-700">
                  <td className="rounded-l-2xl bg-slate-50 px-4 py-4">
                    <div className="font-semibold text-slate-950">{position.assetName}</div>
                    <div className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">{position.clientName}</div>
                  </td>
                  <td className="bg-slate-50 px-4 py-4 font-semibold text-slate-900">{position.ticker || "-"}</td>
                  <td className="bg-slate-50 px-4 py-4">{assetClassLabel(position.assetClass)}</td>
                  <td className="bg-slate-50 px-4 py-4">{position.broker}</td>
                  <td className="bg-slate-50 px-4 py-4 text-right">
                    {formatNumber(position.quantity, position.quantity < 1 ? 4 : 2)}
                  </td>
                  <td className="bg-slate-50 px-4 py-4 text-right">{formatCurrency(position.avgPrice)}</td>
                  <td className="rounded-r-2xl bg-slate-50 px-4 py-4 text-right font-semibold text-slate-950">
                    {formatCurrency(position.totalValue)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
