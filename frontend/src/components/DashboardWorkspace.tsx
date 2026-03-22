import { formatCurrency, formatDate, formatNumber } from "../lib/formatters";
import { assetClassLabel } from "../lib/presentation";
import type { DashboardData, DashboardFilters } from "../types/report";
import KpiCard from "./KpiCard";
import DonutChart from "./charts/DonutChart";
import HorizontalBars from "./charts/HorizontalBars";
import TimelineChart from "./charts/TimelineChart";

type DashboardWorkspaceProps = {
  data: DashboardData | null;
  filters: DashboardFilters;
  loading: boolean;
  pdfLoading: boolean;
  error: string | null;
  actionError: string | null;
  onRefresh: () => void;
  onDownloadPdf: () => void;
  onResetFilters: () => void;
  onFilterChange: (field: keyof DashboardFilters, value: string) => void;
};

function SectionHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div className="mb-6 flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">{eyebrow}</p>
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <h2 className="font-display text-[1.9rem] font-extrabold tracking-tight text-slate-950">{title}</h2>
        <p className="max-w-2xl text-sm leading-7 text-slate-500">{description}</p>
      </div>
    </div>
  );
}

function DashboardSelect({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</div>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-sky-200 focus:shadow-[0_0_0_4px_rgba(14,165,233,0.08)]"
      >
        {options.map((option) => (
          <option key={`${label}-${option.value || "all"}`} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function LoadingSkeleton() {
  return (
    <section className="rounded-[32px] border border-slate-200 bg-[#f8fafc] p-6 shadow-[0_24px_70px_rgba(15,23,42,0.18)] md:p-8 lg:p-10">
      <div className="animate-pulse space-y-6">
        <div className="h-44 rounded-[28px] bg-slate-200/70" />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-40 rounded-[24px] bg-white" />
          ))}
        </div>
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="h-[420px] rounded-[28px] bg-white" />
          <div className="h-[420px] rounded-[28px] bg-white" />
        </div>
      </div>
    </section>
  );
}

function StateCard({
  title,
  body,
  tone = "slate",
  actionLabel,
  onAction
}: {
  title: string;
  body: string;
  tone?: "slate" | "rose";
  actionLabel?: string;
  onAction?: () => void;
}) {
  const tones = {
    slate: "border-slate-200 bg-white text-slate-700",
    rose: "border-rose-200 bg-rose-50 text-rose-700"
  } as const;

  return (
    <section className="rounded-[32px] border border-slate-200 bg-[#f8fafc] p-8 shadow-[0_24px_70px_rgba(15,23,42,0.18)]">
      <div className={`rounded-[28px] border px-6 py-16 text-center ${tones[tone]}`}>
        <h2 className="font-display text-2xl font-bold tracking-tight">{title}</h2>
        <p className="mx-auto mt-4 max-w-2xl text-sm leading-7">{body}</p>
        {actionLabel && onAction ? (
          <button
            type="button"
            onClick={onAction}
            className="mt-6 rounded-2xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
          >
            {actionLabel}
          </button>
        ) : null}
      </div>
    </section>
  );
}

export default function DashboardWorkspace({
  data,
  filters,
  loading,
  pdfLoading,
  error,
  actionError,
  onRefresh,
  onDownloadPdf,
  onResetFilters,
  onFilterChange
}: DashboardWorkspaceProps) {
  const hasActiveFilters = Boolean(filters.clientName || filters.assetClass || filters.referenceDate);

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <StateCard
        title="Unable to load the executive dashboard"
        body={error}
        tone="rose"
        actionLabel="Retry dashboard load"
        onAction={onRefresh}
      />
    );
  }

  if (!data || !data.positions.length) {
    return (
      <StateCard
        title="No portfolio data available"
        body="Ainda nao existem posicoes visiveis para este recorte. Envie um arquivo ou ajuste os filtros para montar o painel executivo."
        actionLabel={hasActiveFilters ? "Clear filters" : "Refresh dashboard"}
        onAction={hasActiveFilters ? onResetFilters : onRefresh}
      />
    );
  }

  return (
    <section className="rounded-[32px] border border-slate-200 bg-[#f8fafc] p-6 shadow-[0_24px_70px_rgba(15,23,42,0.18)] md:p-8 lg:p-10">
      <header className="rounded-[30px] bg-[radial-gradient(circle_at_top_right,rgba(20,184,166,0.16),transparent_20%),linear-gradient(145deg,#07111f_0%,#0c182d_58%,#10213a_100%)] p-8 text-white shadow-[0_28px_60px_rgba(2,6,23,0.32)]">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.34em] text-cyan-100/70">Executive Dashboard</p>
            <h1 className="mt-3 font-display text-4xl font-extrabold tracking-tight">Portfolio command center</h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300">
              Um painel de leitura executiva com valor consolidado, distribuicao e exposicao construido diretamente
              sobre os dados vivos do CarteiraConsol.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">As of date</p>
              <p className="mt-2 text-sm font-semibold text-white">{data.asOfDate ? formatDate(data.asOfDate) : "-"}</p>
            </div>
            <div className="grid gap-3">
              <button
                type="button"
                onClick={onRefresh}
                className="rounded-2xl border border-cyan-300/18 bg-cyan-300/[0.08] px-4 py-4 text-left text-sm font-semibold text-cyan-50 transition hover:bg-cyan-300/[0.14]"
              >
                Refresh live data
                <div className="mt-1 text-xs font-medium text-cyan-50/70">Atualiza o snapshot visivel no dashboard</div>
              </button>
              <button
                type="button"
                onClick={onDownloadPdf}
                disabled={pdfLoading}
                className="rounded-2xl border border-emerald-300/18 bg-emerald-300/[0.1] px-4 py-4 text-left text-sm font-semibold text-emerald-50 transition hover:bg-emerald-300/[0.14] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {pdfLoading ? "Generating PDF..." : "Download executive PDF"}
                <div className="mt-1 text-xs font-medium text-emerald-50/70">
                  Gera um relatorio premium com o mesmo recorte executivo do painel.
                </div>
              </button>
            </div>
          </div>
        </div>
      </header>

      {actionError ? (
        <div className="mt-6 rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-700 shadow-[0_12px_30px_rgba(190,24,93,0.06)]">
          <div className="font-semibold">PDF generation needs attention</div>
          <div className="mt-2 leading-7">{actionError}</div>
        </div>
      ) : null}

      <div className="mt-8 rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
        <SectionHeader
          eyebrow="Filters"
          title="Executive Cut"
          description="Refine a leitura do portfolio por cliente, classe e data de referencia sem perder o contexto executivo."
        />
        <div className="grid gap-4 md:grid-cols-[1fr_1fr_1fr_auto] md:items-end">
          <DashboardSelect
            label="Client"
            value={filters.clientName}
            options={[{ value: "", label: "All clients" }, ...data.availableClients.map((item) => ({ value: item, label: item }))]}
            onChange={(value) => onFilterChange("clientName", value)}
          />
          <DashboardSelect
            label="Asset Class"
            value={filters.assetClass}
            options={[
              { value: "", label: "All asset classes" },
              ...data.availableAssetClasses.map((item) => ({ value: item, label: assetClassLabel(item) }))
            ]}
            onChange={(value) => onFilterChange("assetClass", value)}
          />
          <DashboardSelect
            label="Reference Date"
            value={filters.referenceDate}
            options={[
              { value: "", label: "Latest snapshot" },
              ...data.availableReferenceDates.map((item) => ({ value: item, label: formatDate(item) }))
            ]}
            onChange={(value) => onFilterChange("referenceDate", value)}
          />
          <button
            type="button"
            onClick={onResetFilters}
            disabled={!hasActiveFilters}
            className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-3 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Clear filters
          </button>
        </div>
      </div>

      <div className="mt-10">
        <SectionHeader
          eyebrow="Overview"
          title="Executive Snapshot"
          description="Indicadores centrais para leitura rapida do tamanho, base e cobertura do portfolio."
        />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {data.metrics.map((item) => (
            <KpiCard key={item.label} item={item} />
          ))}
        </div>
      </div>

      <div className="mt-10">
        <SectionHeader
          eyebrow="Allocation"
          title="Portfolio Distribution"
          description="Visual executivo da composicao patrimonial por classe de ativo e cliente."
        />
        <div className="grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
          <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
            <div className="mb-5">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Allocation</div>
              <h3 className="mt-2 font-display text-2xl font-extrabold tracking-tight text-slate-950">Asset class mix</h3>
              <p className="mt-2 text-sm leading-7 text-slate-500">
                Distribuicao do valor consolidado entre classes no snapshot filtrado.
              </p>
            </div>
            <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-center">
              <DonutChart items={data.assetAllocation.map((item) => ({ ...item, label: assetClassLabel(item.label) }))} />
              <div className="space-y-3">
                {data.assetAllocation.map((item) => (
                  <div key={item.label} className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{assetClassLabel(item.label)}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">
                          {formatNumber(item.share * 100, 1)}% do portfolio
                        </p>
                      </div>
                      <p className="text-sm font-semibold text-slate-700">{formatCurrency(item.value)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </article>

          <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
            <div className="mb-5">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Client view</div>
              <h3 className="mt-2 font-display text-2xl font-extrabold tracking-tight text-slate-950">Allocation by client</h3>
              <p className="mt-2 text-sm leading-7 text-slate-500">
                Participacao relativa dos clientes no patrimonio visivel neste corte.
              </p>
            </div>
            <HorizontalBars items={data.clientAllocation} tone="teal" />
          </article>
        </div>
      </div>

      <div className="mt-10">
        <SectionHeader
          eyebrow="Top Positions"
          title="Concentration and priority assets"
          description="Veja rapidamente onde o valor esta concentrado e quais posicoes lideram a exposicao do portfolio."
        />
        <div className="grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
          <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
            <div className="mb-5">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Top assets</div>
              <h3 className="mt-2 font-display text-2xl font-extrabold tracking-tight text-slate-950">Top assets by allocation</h3>
              <p className="mt-2 text-sm leading-7 text-slate-500">
                Ativos ou tickers ordenados do maior para o menor valor consolidado.
              </p>
            </div>
            <HorizontalBars items={data.topAssets} />
          </article>

          <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
            <div className="mb-5">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Portfolio evolution</div>
              <h3 className="mt-2 font-display text-2xl font-extrabold tracking-tight text-slate-950">Portfolio evolution</h3>
              <p className="mt-2 text-sm leading-7 text-slate-500">
                Evolucao do valor consolidado ao longo das datas de referencia disponiveis.
              </p>
            </div>
            <TimelineChart items={data.timeline} />
          </article>
        </div>
      </div>

      <div className="mt-10 rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
        <SectionHeader
          eyebrow="Top Positions"
          title="Top 20 positions"
          description="Tabela executiva das maiores posicoes do snapshot atual, pronta para leitura com clientes ou stakeholders."
        />

        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-2 text-left">
            <thead>
              <tr className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                <th className="px-4">Client</th>
                <th className="px-4">Asset</th>
                <th className="px-4">Ticker</th>
                <th className="px-4">Class</th>
                <th className="px-4 text-right">Quantity</th>
                <th className="px-4 text-right">Average Price</th>
                <th className="px-4 text-right">Total Value</th>
                <th className="px-4 text-right">Reference Date</th>
              </tr>
            </thead>
            <tbody>
              {data.positions.map((position, index) => (
                <tr
                  key={`${position.referenceDate}-${position.ticker}-${position.broker}-${position.clientName}`}
                  className="text-sm text-slate-700"
                >
                  <td className={`rounded-l-2xl px-4 py-4 font-semibold text-slate-950 ${index % 2 === 0 ? "bg-slate-50" : "bg-slate-100/80"}`}>
                    {position.clientName}
                  </td>
                  <td className={`${index % 2 === 0 ? "bg-slate-50" : "bg-slate-100/80"} px-4 py-4`}>{position.assetName}</td>
                  <td className={`${index % 2 === 0 ? "bg-slate-50" : "bg-slate-100/80"} px-4 py-4 font-semibold text-slate-900`}>
                    {position.ticker || "-"}
                  </td>
                  <td className={`${index % 2 === 0 ? "bg-slate-50" : "bg-slate-100/80"} px-4 py-4`}>{assetClassLabel(position.assetClass)}</td>
                  <td className={`${index % 2 === 0 ? "bg-slate-50" : "bg-slate-100/80"} px-4 py-4 text-right`}>
                    {formatNumber(position.quantity, position.quantity < 1 ? 4 : 2)}
                  </td>
                  <td className={`${index % 2 === 0 ? "bg-slate-50" : "bg-slate-100/80"} px-4 py-4 text-right`}>
                    {formatCurrency(position.avgPrice)}
                  </td>
                  <td
                    className={`${index % 2 === 0 ? "bg-slate-50" : "bg-slate-100/80"} px-4 py-4 text-right font-semibold text-slate-950`}
                  >
                    {formatCurrency(position.totalValue)}
                  </td>
                  <td className={`rounded-r-2xl px-4 py-4 text-right ${index % 2 === 0 ? "bg-slate-50" : "bg-slate-100/80"}`}>
                    {formatDate(position.referenceDate)}
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
