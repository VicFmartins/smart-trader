import { formatDateTime, formatPercent } from "../lib/formatters";
import type { IngestionReport, ReviewQueueFilter, ReviewStatus } from "../types/report";

type ReviewQueueWorkspaceProps = {
  reports: IngestionReport[];
  hiddenTechnicalReportsCount: number;
  selectedReport: IngestionReport | null;
  loading: boolean;
  actionLoading: boolean;
  error: string | null;
  feedback: string | null;
  activeFilter: ReviewQueueFilter;
  onFilterChange: (value: ReviewQueueFilter) => void;
  onRefresh: () => void;
  onSelectReport: (reportId: number) => void;
  onReviewAction: (reviewStatus: ReviewStatus) => void;
  onApproveAndReprocess: () => void;
};

function StatusBadge({
  label,
  tone
}: {
  label: string;
  tone: "slate" | "amber" | "emerald" | "rose" | "blue";
}) {
  const tones = {
    slate: "bg-slate-200 text-slate-700",
    amber: "bg-amber-100 text-amber-700",
    emerald: "bg-emerald-100 text-emerald-700",
    rose: "bg-rose-100 text-rose-700",
    blue: "bg-sky-100 text-sky-700"
  } as const;

  return (
    <span className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${tones[tone]}`}>
      {label}
    </span>
  );
}

function statusTone(status: string) {
  if (status === "success" || status === "approved") return "emerald";
  if (status === "review_required" || status === "pending") return "amber";
  if (status === "error" || status === "rejected") return "rose";
  return "slate";
}

function reviewStatusLabel(status: ReviewStatus) {
  if (status === "not_required") return "not required";
  return status;
}

function reportStatusLabel(status: string) {
  if (status === "review_required") return "needs review";
  if (status === "error") return "technical error";
  return status;
}

function filterLabel(filter: ReviewQueueFilter) {
  if (filter === "pending") return "Pendentes";
  if (filter === "review_required") return "Needs review";
  return "Recentes";
}

function confidenceLabel(confidence: number | null) {
  if (confidence === null || confidence === undefined) {
    return "n/a";
  }
  return formatPercent(confidence);
}

function mappingSource(mapping: Record<string, unknown>) {
  const value = mapping.original_name ?? mapping.source_column ?? mapping.source ?? mapping.column_name ?? mapping.normalized_name;
  return typeof value === "string" && value ? value : "coluna";
}

function mappingTarget(mapping: Record<string, unknown>) {
  const value = mapping.canonical_name ?? mapping.canonical_field ?? mapping.target_field;
  return typeof value === "string" && value ? value : "-";
}

function mappingScore(mapping: Record<string, unknown>) {
  const value = mapping.score ?? mapping.confidence;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export default function ReviewQueueWorkspace({
  reports,
  hiddenTechnicalReportsCount,
  selectedReport,
  loading,
  actionLoading,
  error,
  feedback,
  activeFilter,
  onFilterChange,
  onRefresh,
  onSelectReport,
  onReviewAction,
  onApproveAndReprocess
}: ReviewQueueWorkspaceProps) {
  const filters: ReviewQueueFilter[] = ["pending", "review_required", "recent"];
  const selectedReportIsTechnicalError = selectedReport?.status === "error";

  return (
    <section className="rounded-[32px] border border-slate-200 bg-[#f8fafc] p-6 shadow-[0_24px_70px_rgba(15,23,42,0.18)] md:p-8 lg:p-10">
      <header className="rounded-[28px] bg-[radial-gradient(circle_at_top_right,rgba(250,204,21,0.14),transparent_22%),linear-gradient(145deg,#081223_0%,#0e1b31_55%,#14223a_100%)] p-8 text-white">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.34em] text-amber-100/70">Smart Ingestion Review</p>
            <h1 className="mt-3 font-display text-4xl font-extrabold tracking-tight">Operational review queue</h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300">
              Inspecione arquivos com baixa confianca, entenda o mapeamento aplicado e atualize o status operacional
              sem sair do workspace executivo.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Fila visivel</p>
              <p className="mt-2 text-sm font-semibold text-white">{reports.length} itens</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Filtro ativo</p>
              <p className="mt-2 text-sm font-semibold text-white">{filterLabel(activeFilter)}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Selecionado</p>
              <p className="mt-2 text-sm font-semibold text-white">{selectedReport ? `#${selectedReport.id}` : "Nenhum item"}</p>
            </div>
          </div>
        </div>
      </header>

      <div className="mt-8 grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Review Queue</p>
              <p className="mt-2 text-lg font-semibold text-slate-950">Arquivos para triagem</p>
            </div>
            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
              className="rounded-full border border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Refresh
            </button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {filters.map((filter) => {
              const active = filter === activeFilter;
              return (
                <button
                  key={filter}
                  type="button"
                  onClick={() => onFilterChange(filter)}
                  className={`rounded-full px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] transition ${
                    active ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {filterLabel(filter)}
                </button>
              );
            })}
          </div>

          {!loading && !error && hiddenTechnicalReportsCount > 0 && activeFilter !== "recent" ? (
            <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm leading-7 text-slate-600">
              {hiddenTechnicalReportsCount} historical technical failure
              {hiddenTechnicalReportsCount > 1 ? "s are" : " is"} hidden from this operational queue. Use the
              Recent filter if you need to audit legacy failures.
            </div>
          ) : null}

          {loading ? <div className="mt-6 text-sm text-slate-500">Carregando fila de revisao...</div> : null}
          {error ? <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">{error}</div> : null}

          {!loading && !error && !reports.length ? (
            <div className="mt-6 rounded-[24px] border border-dashed border-slate-200 bg-slate-50 px-5 py-6 text-sm leading-7 text-slate-500">
              Nenhum relatorio encontrado para este filtro. Quando uma ingestao precisar de revisao, ela vai aparecer aqui.
            </div>
          ) : null}

          <div className="mt-4 space-y-3">
            {reports.map((report) => {
              const selected = selectedReport?.id === report.id;
              return (
                <button
                  key={report.id}
                  type="button"
                  onClick={() => onSelectReport(report.id)}
                  className={`w-full rounded-[22px] border px-4 py-4 text-left transition ${
                    selected
                      ? "border-sky-200 bg-sky-50 shadow-[0_12px_30px_rgba(14,165,233,0.08)]"
                      : "border-slate-200 bg-slate-50 hover:bg-white"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-slate-950">{report.filename}</div>
                      <div className="mt-1 text-xs text-slate-500">{formatDateTime(report.processedAt ?? report.createdAt)}</div>
                    </div>
                    <StatusBadge label={reviewStatusLabel(report.reviewStatus)} tone={statusTone(report.reviewStatus)} />
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <StatusBadge label={reportStatusLabel(report.status)} tone={statusTone(report.status)} />
                    <StatusBadge label={report.detectedType} tone="blue" />
                  </div>

                  <div className="mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
                    <span>Confidence: {confidenceLabel(report.detectionConfidence)}</span>
                    <span>Parser: {report.parserName ?? "generic"}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
          {!selectedReport ? (
            <div className="rounded-[24px] border border-dashed border-slate-200 bg-slate-50 px-6 py-10 text-sm leading-7 text-slate-500">
              Selecione um relatorio de ingestao para inspecionar colunas detectadas, mappings aplicados e tomar uma decisao operacional.
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-5 border-b border-slate-100 pb-6 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Review Detail</p>
                  <h2 className="mt-2 font-display text-3xl font-extrabold tracking-tight text-slate-950">
                    {selectedReport.filename}
                  </h2>
                  <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-500">{selectedReport.message}</p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <StatusBadge label={reportStatusLabel(selectedReport.status)} tone={statusTone(selectedReport.status)} />
                  <StatusBadge label={reviewStatusLabel(selectedReport.reviewStatus)} tone={statusTone(selectedReport.reviewStatus)} />
                  {selectedReport.reviewRequired ? <StatusBadge label="needs review" tone="amber" /> : null}
                </div>
              </div>

              {selectedReportIsTechnicalError ? (
                <div className="mt-6 rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-4 text-sm leading-7 text-rose-700">
                  Este item representa uma falha tecnica historica de ingestao. Ele permanece visivel para auditoria, mas
                  nao deve ser tratado como um caso normal de aprovacao por mapping.
                </div>
              ) : null}

              <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Detected type</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">{selectedReport.detectedType}</div>
                </div>
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Parser</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">{selectedReport.parserName ?? "generic"}</div>
                </div>
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Confidence</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">{confidenceLabel(selectedReport.detectionConfidence)}</div>
                </div>
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Rows processed</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">{selectedReport.rowsProcessed}</div>
                </div>
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Rows skipped</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">{selectedReport.rowsSkipped}</div>
                </div>
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Processed at</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">
                    {formatDateTime(selectedReport.processedAt ?? selectedReport.createdAt)}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Reprocessed at</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">
                    {selectedReport.reprocessedAt ? formatDateTime(selectedReport.reprocessedAt) : "-"}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Reprocess count</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">{selectedReport.reprocessCount}</div>
                </div>
              </div>

              <div className="mt-6 rounded-[24px] border border-slate-200 bg-slate-50 px-5 py-5">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Review actions</div>
                <div className="mt-4 flex flex-wrap gap-3">
                  {(["approved", "rejected", "not_required", "pending"] as ReviewStatus[]).map((status) => (
                    <button
                      key={status}
                      type="button"
                      onClick={() => onReviewAction(status)}
                      disabled={actionLoading || (selectedReportIsTechnicalError && status === "approved")}
                      className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] transition ${
                        selectedReport.reviewStatus === status
                          ? "bg-slate-900 text-white"
                          : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
                      } disabled:cursor-not-allowed disabled:opacity-60`}
                    >
                      {reviewStatusLabel(status)}
                    </button>
                  ))}
                  {!selectedReportIsTechnicalError &&
                  (selectedReport.reviewStatus === "pending" || selectedReport.reviewStatus === "approved") ? (
                    <button
                      type="button"
                      onClick={onApproveAndReprocess}
                      disabled={actionLoading}
                      className="rounded-full bg-gradient-to-r from-cyan-500 via-sky-500 to-blue-600 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-white transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      Approve & Reprocess
                    </button>
                  ) : null}
                </div>
                {feedback ? <div className="mt-4 text-sm text-emerald-700">{feedback}</div> : null}
              </div>

              <div className="mt-6 grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
                <div className="rounded-[24px] border border-slate-200 bg-white p-5">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Review reasons</div>
                  {selectedReport.reviewReasons.length ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {selectedReport.reviewReasons.map((reason) => (
                        <StatusBadge key={reason} label={reason.replace(/_/g, " ")} tone="amber" />
                      ))}
                    </div>
                  ) : (
                    <div className="mt-4 text-sm text-slate-500">Sem motivos explicitos de revisao para este item.</div>
                  )}

                  <div className="mt-6 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Detected columns</div>
                  {selectedReport.detectedColumns.length ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {selectedReport.detectedColumns.map((column) => (
                        <span key={column} className="rounded-full bg-slate-100 px-3 py-2 text-xs font-medium text-slate-700">
                          {column}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-4 text-sm text-slate-500">Nenhuma coluna detectada foi registrada.</div>
                  )}
                </div>

                <div className="rounded-[24px] border border-slate-200 bg-white p-5">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">File references</div>
                  <div className="mt-4 grid gap-4">
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Raw file</div>
                      <div className="mt-2 break-all text-sm text-slate-700">{selectedReport.rawFile ?? "-"}</div>
                    </div>
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Processed file</div>
                      <div className="mt-2 break-all text-sm text-slate-700">{selectedReport.processedFile ?? "-"}</div>
                    </div>
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Layout signature</div>
                      <div className="mt-2 break-all text-sm text-slate-700">{selectedReport.layoutSignature ?? "-"}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 rounded-[24px] border border-slate-200 bg-white p-5">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Applied mappings</div>
                  <div className="text-xs text-slate-400">{selectedReport.appliedMappings.length} registros</div>
                </div>

                {selectedReport.appliedMappings.length ? (
                  <div className="mt-4 overflow-x-auto">
                    <table className="min-w-full border-separate border-spacing-y-2 text-left text-sm">
                      <thead>
                        <tr className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                          <th className="px-3">Source</th>
                          <th className="px-3">Canonical</th>
                          <th className="px-3 text-right">Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedReport.appliedMappings.map((mapping, index) => (
                          <tr key={`${mappingSource(mapping)}-${index}`}>
                            <td className="rounded-l-2xl bg-slate-50 px-3 py-3 text-slate-700">{mappingSource(mapping)}</td>
                            <td className="bg-slate-50 px-3 py-3 font-semibold text-slate-950">{mappingTarget(mapping)}</td>
                            <td className="rounded-r-2xl bg-slate-50 px-3 py-3 text-right text-slate-700">
                              {mappingScore(mapping) === null ? "-" : `${mappingScore(mapping)?.toFixed(1)}`}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="mt-4 text-sm text-slate-500">Nenhum mapping aplicado foi registrado para este item.</div>
                )}
              </div>
            </>
          )}
        </article>
      </div>
    </section>
  );
}
