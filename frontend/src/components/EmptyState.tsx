import type { ApiStatus } from "../types/report";

type EmptyStateProps = {
  apiStatus: ApiStatus;
  loadingLiveData: boolean;
  onLoadLiveData: () => void | Promise<void>;
  onFillMockData: () => void;
  onUploadSpreadsheet: () => void;
};

export default function EmptyState({
  apiStatus,
  loadingLiveData,
  onLoadLiveData,
  onFillMockData,
  onUploadSpreadsheet
}: EmptyStateProps) {
  return (
    <section className="print-surface flex min-h-[calc(100vh-2rem)] flex-col justify-center rounded-[32px] border border-white/8 bg-white/[0.04] p-6 shadow-soft backdrop-blur md:p-10 lg:p-14">
      <div className="mx-auto max-w-4xl">
        <div className="mb-10 inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-slate-300">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              apiStatus.connected ? "bg-emerald-400 shadow-[0_0_18px_rgba(52,211,153,0.7)]" : "bg-amber-400"
            }`}
          />
          {apiStatus.message}
        </div>

        <div className="grid gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          <div>
            <p className="mb-3 text-sm font-semibold uppercase tracking-[0.34em] text-cyan-200/80">
              CarteiraConsol Workspace
            </p>
            <h1 className="max-w-3xl font-display text-4xl font-extrabold leading-tight text-white md:text-5xl">
              Construa uma análise de portfólio com estética executiva e narrativa de consultoria.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-300">
              Use uma planilha local, um snapshot já consolidado no backend ou dados demonstrativos para montar um
              preview de relatório pronto para apresentação.
            </p>

            <div className="mt-10 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={onUploadSpreadsheet}
                className="rounded-2xl bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 px-6 py-3 text-sm font-semibold text-slate-950 shadow-[0_18px_40px_rgba(56,189,248,0.35)] transition hover:translate-y-[-1px]"
              >
                Carregar planilha
              </button>
              <button
                type="button"
                onClick={onFillMockData}
                className="rounded-2xl border border-white/10 bg-white/[0.04] px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/[0.08]"
              >
                Usar mock data
              </button>
              <button
                type="button"
                onClick={() => void onLoadLiveData()}
                disabled={!apiStatus.connected || loadingLiveData}
                className="rounded-2xl border border-cyan-300/20 bg-cyan-300/5 px-6 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/10 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {loadingLiveData ? "Sincronizando snapshot..." : "Usar snapshot da API"}
              </button>
            </div>
          </div>

          <div className="rounded-[28px] border border-white/8 bg-gradient-to-br from-white/[0.08] via-white/[0.03] to-white/[0.01] p-6 shadow-soft">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-400">Preview Structure</p>
                <h2 className="mt-2 font-display text-2xl font-bold text-white">Narrativa recomendada</h2>
              </div>
              <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 text-xs font-medium text-cyan-100">
                Fintech-grade
              </div>
            </div>

            <div className="space-y-3">
              {[
                "KPIs estratégicos com leitura executiva",
                "Alocação patrimonial e concentração por classe",
                "Exposição por corretora e cliente",
                "Trajetória temporal com visão de evolução",
                "Ledger detalhado para leitura operacional"
              ].map((item, index) => (
                <div
                  key={item}
                  className="flex items-start gap-4 rounded-2xl border border-white/7 bg-white/[0.03] px-4 py-4"
                >
                  <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-xl bg-slate-950/50 text-sm font-bold text-cyan-200">
                    {index + 1}
                  </div>
                  <p className="text-sm leading-7 text-slate-300">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
