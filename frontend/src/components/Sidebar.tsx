import { formatDateTime } from "../lib/formatters";
import type {
  ApiStatus,
  UploadHistoryItem,
  UploadLifecycleState,
  UploadSummary,
  WorkspaceView
} from "../types/report";

type SidebarProps = {
  clientName: string;
  diagnosis: string;
  apiStatus: ApiStatus;
  loadingLiveData: boolean;
  uploadState: UploadLifecycleState;
  sourceContext: string;
  workspaceView: WorkspaceView;
  reviewQueueCount: number;
  uploadSummary: UploadSummary | null;
  uploadHistory: UploadHistoryItem[];
  lastError: string | null;
  currentUserName: string;
  currentUserEmail: string;
  onClientNameChange: (value: string) => void;
  onDiagnosisChange: (value: string) => void;
  onWorkspaceViewChange: (value: WorkspaceView) => void;
  onFillMockData: () => void;
  onDownloadTemplate: () => void;
  onUploadSpreadsheet: () => void;
  onGeneratePdf: () => void;
  onLogout: () => void;
};

function ActionButton({
  label,
  helper,
  onClick,
  variant = "default",
  disabled = false
}: {
  label: string;
  helper: string;
  onClick: () => void;
  variant?: "default" | "primary" | "subtle";
  disabled?: boolean;
}) {
  const styles =
    variant === "primary"
      ? "border-transparent bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 text-slate-950 shadow-[0_16px_30px_rgba(56,189,248,0.28)]"
      : variant === "subtle"
        ? "border-white/8 bg-white/[0.03] text-slate-100"
        : "border-cyan-300/16 bg-cyan-300/[0.06] text-cyan-50";

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`w-full rounded-[22px] border px-4 py-4 text-left transition hover:translate-y-[-1px] hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-50 ${styles}`}
    >
      <div className="text-sm font-semibold">{label}</div>
      <div className="mt-1 text-xs leading-6 text-slate-400">{helper}</div>
    </button>
  );
}

function WorkspaceModeCard({
  workspaceView,
  reviewQueueCount,
  onWorkspaceViewChange
}: {
  workspaceView: WorkspaceView;
  reviewQueueCount: number;
  onWorkspaceViewChange: (value: WorkspaceView) => void;
}) {
  const modes: Array<{
    value: WorkspaceView;
    label: string;
    helper: string;
    badge?: string;
  }> = [
    {
      value: "report",
      label: "Report Builder",
      helper: "Upload, ETL e preview executivo da carteira."
    },
    {
      value: "dashboard",
      label: "Dashboard",
      helper: "KPIs, alocacao e exposicao com dados vivos da API."
    },
    {
      value: "review",
      label: "Review Queue",
      helper: "Fila para validar ingestoes com baixa confianca.",
      badge: reviewQueueCount > 0 ? String(reviewQueueCount) : undefined
    }
  ];

  return (
    <div className="mt-8 rounded-[24px] border border-white/8 bg-white/[0.03] p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Modo de trabalho</div>
      <div className="mt-4 grid gap-3">
        {modes.map((mode) => {
          const active = workspaceView === mode.value;
          return (
            <button
              key={mode.value}
              type="button"
              onClick={() => onWorkspaceViewChange(mode.value)}
              className={`rounded-[20px] border px-4 py-4 text-left transition ${
                active
                  ? "border-cyan-300/24 bg-cyan-300/[0.08] text-cyan-50"
                  : "border-white/8 bg-white/[0.02] text-slate-200 hover:bg-white/[0.06]"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-semibold">{mode.label}</div>
                {mode.badge ? (
                  <span className="rounded-full bg-amber-400/16 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-amber-100">
                    {mode.badge}
                  </span>
                ) : null}
              </div>
              <div className={`mt-2 text-xs leading-6 ${active ? "text-cyan-50/80" : "text-slate-400"}`}>{mode.helper}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function UploadStatusCard({
  uploadState,
  lastError
}: {
  uploadState: UploadLifecycleState;
  lastError: string | null;
}) {
  if (uploadState === "uploading") {
    return (
      <div className="mt-6 rounded-[22px] border border-cyan-300/18 bg-cyan-300/[0.08] px-4 py-4 text-sm text-cyan-50">
        <div className="font-semibold">Enviando arquivo</div>
        <div className="mt-2 leading-7 text-cyan-50/80">
          O upload esta sendo transmitido para o backend e a ingestao sera iniciada em seguida.
        </div>
      </div>
    );
  }

  if (uploadState === "processing") {
    return (
      <div className="mt-6 rounded-[22px] border border-sky-300/18 bg-sky-300/[0.09] px-4 py-4 text-sm text-sky-50">
        <div className="font-semibold">Processing portfolio...</div>
        <div className="mt-2 leading-7 text-sky-50/80">
          O ETL ja recebeu o arquivo. Agora estamos atualizando analytics e recarregando o snapshot consolidado.
        </div>
      </div>
    );
  }

  if (uploadState === "error" && lastError) {
    return (
      <div className="mt-6 rounded-[22px] border border-rose-400/14 bg-rose-400/[0.08] px-4 py-4 text-sm text-rose-100">
        <div className="font-semibold">Atencao no fluxo de upload</div>
        <div className="mt-2 leading-7 text-rose-100/85">{lastError}</div>
      </div>
    );
  }

  if (uploadState === "success" && lastError) {
    return (
      <div className="mt-6 rounded-[22px] border border-amber-300/18 bg-amber-300/[0.08] px-4 py-4 text-sm text-amber-100">
        <div className="font-semibold">Upload concluido com observacao</div>
        <div className="mt-2 leading-7 text-amber-100/85">{lastError}</div>
      </div>
    );
  }

  return null;
}

function ProcessingSummaryCard({ uploadSummary }: { uploadSummary: UploadSummary | null }) {
  if (!uploadSummary) {
    return null;
  }

  const tone =
    uploadSummary.outcome === "error"
      ? {
          wrapper: "border-rose-400/14 bg-rose-400/[0.08] text-rose-100",
          badge: "bg-rose-400/14 text-rose-100",
          label: "Error"
        }
      : uploadSummary.outcome === "review_required"
        ? {
            wrapper: "border-amber-300/18 bg-amber-300/[0.08] text-amber-100",
            badge: "bg-amber-300/16 text-amber-100",
            label: "Needs review"
          }
        : {
            wrapper: "border-emerald-400/14 bg-emerald-400/[0.08] text-emerald-50",
            badge: "bg-emerald-400/14 text-emerald-100",
            label: "Success"
          };

  return (
    <div className={`mt-6 rounded-[22px] border px-4 py-4 text-sm ${tone.wrapper}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="font-semibold">{uploadSummary.outcome === "error" ? "Last upload attempt" : "Last processing result"}</div>
        <div className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${tone.badge}`}>
          {tone.label}
        </div>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-emerald-100/60">Arquivo</div>
          <div className="mt-1 break-all font-medium">{uploadSummary.filename}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-emerald-100/60">Tipo detectado</div>
          <div className="mt-1 font-medium">{uploadSummary.detectedType}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-emerald-100/60">Registros processados</div>
          <div className="mt-1 font-medium">{uploadSummary.rowsProcessed}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-emerald-100/60">Linhas descartadas</div>
          <div className="mt-1 font-medium">{uploadSummary.rowsSkipped}</div>
        </div>
      </div>

      {uploadSummary.reviewRequired ? (
        <div className="mt-3 rounded-2xl border border-amber-300/18 bg-amber-300/[0.08] px-3 py-3 text-xs leading-6 text-amber-100">
          Este upload gerou um item para revisao humana.
        </div>
      ) : null}

      <div className="mt-3 text-[11px] uppercase tracking-[0.18em] text-current/60">Processado em</div>
      <div className="mt-1 font-medium">{formatDateTime(uploadSummary.processedAt)}</div>
      <div className="mt-3 leading-7 text-current/85">{uploadSummary.message}</div>
    </div>
  );
}

function UploadHistoryCard({ uploadHistory }: { uploadHistory: UploadHistoryItem[] }) {
  if (!uploadHistory.length) {
    return null;
  }

  return (
    <div className="mt-6 rounded-[22px] border border-white/8 bg-white/[0.03] px-4 py-4">
      <div className="flex items-center justify-between gap-3">
        <div className="font-semibold text-white">Recent upload runs</div>
        <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{uploadHistory.length} visiveis</div>
      </div>

      <div className="mt-4 space-y-3">
        {uploadHistory.map((item, index) => (
          <div key={item.id} className="rounded-[18px] border border-white/8 bg-white/[0.03] px-4 py-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-white">{item.filename}</div>
                <div className="mt-1 text-xs text-slate-400">{formatDateTime(item.timestamp)}</div>
              </div>
              <div className="flex items-center gap-2">
                {index === 0 ? (
                  <span className="rounded-full bg-cyan-300/12 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-100">
                    Latest
                  </span>
                ) : null}
                <span
                  className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${
                    item.status === "success"
                      ? "bg-emerald-400/12 text-emerald-100"
                      : item.status === "review_required"
                        ? "bg-amber-300/16 text-amber-100"
                        : "bg-rose-400/12 text-rose-100"
                  }`}
                >
                  {item.status}
                </span>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-400">
              <span>Tipo: {item.detectedType}</span>
              <span>Processados: {item.rowsProcessed}</span>
              <span>Descartados: {item.rowsSkipped}</span>
            </div>
            <div className="mt-3 text-xs leading-6 text-slate-400">{item.message}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Sidebar({
  clientName,
  diagnosis,
  apiStatus,
  loadingLiveData,
  uploadState,
  sourceContext,
  workspaceView,
  reviewQueueCount,
  uploadSummary,
  uploadHistory,
  lastError,
  currentUserName,
  currentUserEmail,
  onClientNameChange,
  onDiagnosisChange,
  onWorkspaceViewChange,
  onFillMockData,
  onDownloadTemplate,
  onUploadSpreadsheet,
  onGeneratePdf,
  onLogout
}: SidebarProps) {
  const uploadBusy = uploadState === "uploading" || uploadState === "processing";

  return (
    <aside className="print-hidden rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(7,14,28,0.96)_0%,rgba(9,18,34,0.94)_100%)] p-6 shadow-soft backdrop-blur">
      <div className="flex h-full flex-col">
        <div>
          <div className="inline-flex items-center gap-3 rounded-full border border-cyan-300/16 bg-cyan-300/[0.06] px-3 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-cyan-100">
            <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_rgba(103,232,249,0.7)]" />
            Report Builder
          </div>
          <h1 className="mt-5 font-display text-3xl font-extrabold tracking-tight text-white">
            Workspace de entrega para analise patrimonial.
          </h1>
          <p className="mt-3 text-sm leading-7 text-slate-400">
            Estruture o contexto do cliente, monte uma previa executiva e acompanhe a fila de revisao sem sair da
            base de dados consolidada.
          </p>
        </div>

        <WorkspaceModeCard
          workspaceView={workspaceView}
          reviewQueueCount={reviewQueueCount}
          onWorkspaceViewChange={onWorkspaceViewChange}
        />

        <div className="mt-6 rounded-[24px] border border-white/8 bg-white/[0.03] p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Sessao autenticada</p>
              <p className="mt-2 text-sm font-semibold text-white">{currentUserName}</p>
              <p className="mt-1 text-xs text-slate-500">{currentUserEmail}</p>
            </div>
            <button
              type="button"
              onClick={onLogout}
              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-200 transition hover:bg-white/[0.08]"
            >
              Logout
            </button>
          </div>
        </div>

        <div className="mt-8 rounded-[24px] border border-white/8 bg-white/[0.03] p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Status de integracao</p>
              <p className="mt-2 text-sm font-semibold text-white">{apiStatus.message}</p>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                apiStatus.connected ? "bg-emerald-500/16 text-emerald-200" : "bg-amber-500/14 text-amber-100"
              }`}
            >
              {apiStatus.connected ? "Online" : "Fallback"}
            </span>
          </div>
          <p className="mt-4 text-xs leading-6 text-slate-500">{sourceContext}</p>
        </div>

        <div className="mt-8 space-y-5">
          <div>
            <label htmlFor="clientName" className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
              Nome do cliente
            </label>
            <input
              id="clientName"
              value={clientName}
              onChange={(event) => onClientNameChange(event.target.value)}
              placeholder="Ex.: Atlas Family Office"
              className="w-full rounded-[20px] border border-white/8 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-300/30 focus:bg-white/[0.05]"
            />
          </div>

          <div>
            <label htmlFor="diagnosis" className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
              Diagnostico consultivo
            </label>
            <textarea
              id="diagnosis"
              value={diagnosis}
              onChange={(event) => onDiagnosisChange(event.target.value)}
              placeholder="Descreva a leitura estrategica da carteira, principais concentracoes, hipoteses e direcionamentos."
              rows={7}
              className="w-full rounded-[20px] border border-white/8 bg-white/[0.04] px-4 py-3 text-sm leading-7 text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-300/30 focus:bg-white/[0.05]"
            />
          </div>
        </div>

        <div className="mt-8">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Portfolio Data</p>
          <div className="mt-4 space-y-3">
            <ActionButton
              label="Fill with mock data"
              helper="Carrega um cenario premium de demonstracao para montar a narrativa do relatorio."
              onClick={onFillMockData}
              variant="primary"
            />
            <ActionButton
              label="Download spreadsheet template"
              helper="Baixe um CSV-base para estruturar a importacao do preview no mesmo formato do builder."
              onClick={onDownloadTemplate}
            />
            <ActionButton
              label={
                uploadState === "uploading"
                  ? "Enviando arquivo..."
                  : uploadState === "processing"
                    ? "Updating analytics..."
                    : "Upload spreadsheet"
              }
              helper="Envia o arquivo ao backend, dispara o ETL real e atualiza a previa com os dados consolidados."
              onClick={onUploadSpreadsheet}
              variant="subtle"
              disabled={uploadBusy}
            />
            <ActionButton
              label="Generate PDF"
              helper={loadingLiveData ? "Aguarde o snapshot concluir antes de exportar." : "Abre a visualizacao pronta para impressao e exportacao em PDF."}
              onClick={onGeneratePdf}
              disabled={loadingLiveData || uploadBusy}
            />
          </div>
        </div>

        <UploadStatusCard uploadState={uploadState} lastError={lastError} />
        <ProcessingSummaryCard uploadSummary={uploadSummary} />
        <UploadHistoryCard uploadHistory={uploadHistory} />

        <div className="mt-auto pt-8 text-xs leading-6 text-slate-500">
          O workspace agora combina entrega executiva com rastreabilidade operacional. Uploads recentes e itens de
          revisao continuam acessiveis sem quebrar o fluxo principal do produto.
        </div>
      </div>
    </aside>
  );
}
