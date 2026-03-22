import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import DashboardWorkspace from "./components/DashboardWorkspace";
import EmptyState from "./components/EmptyState";
import LoginScreen from "./components/LoginScreen";
import ReportCanvas from "./components/ReportCanvas";
import ReviewQueueWorkspace from "./components/ReviewQueueWorkspace";
import Sidebar from "./components/Sidebar";
import WorkspaceErrorBoundary from "./components/WorkspaceErrorBoundary";
import { useAuth } from "./contexts/AuthContext";
import { mockPortfolioRecords } from "./data/mockReport";
import {
  downloadPortfolioPdfReport,
  fetchPortfolioSnapshot,
  fetchIngestionReport,
  fetchIngestionReports,
  reprocessIngestionReport,
  updateIngestionReportReview,
  uploadPortfolioFile
} from "./lib/api";
import { buildDashboardData } from "./lib/dashboardBuilder";
import { buildReport, loadLiveRecords } from "./lib/reportBuilder";
import type {
  ApiStatus,
  DashboardData,
  DashboardFilters,
  IngestionReport,
  PortfolioRecord,
  PortfolioReport,
  ReviewQueueFilter,
  ReviewStatus,
  UploadHistoryItem,
  UploadLifecycleState,
  UploadSummary,
  WorkspaceView
} from "./types/report";

const initialApiStatus: ApiStatus = {
  connected: false,
  message: "Verificando conexao com a API"
};

const SNAPSHOT_REFRESH_DELAY_MS = 350;
const SNAPSHOT_REFRESH_ATTEMPTS = 3;
const SNAPSHOT_REFRESH_BACKOFF_MS = 500;
const MAX_UPLOAD_HISTORY_ITEMS = 5;

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function detectFileTypeFromName(filename: string) {
  const suffix = filename.split(".").pop()?.toLowerCase();
  if (suffix === "csv") return "csv";
  if (suffix === "xlsx" || suffix === "xls") return "excel";
  if (suffix === "json") return "json";
  return suffix || "unknown";
}

function resolveReviewFilters(filter: ReviewQueueFilter) {
  if (filter === "pending") {
    return { reviewStatus: "pending" as const, limit: 50 };
  }
  if (filter === "review_required") {
    return { reviewRequired: true, limit: 50 };
  }
  return { limit: 50 };
}

function sortReviewReports(reports: IngestionReport[]) {
  return [...reports].sort((left, right) => {
    const rightDate = new Date(right.processedAt ?? right.createdAt).getTime();
    const leftDate = new Date(left.processedAt ?? left.createdAt).getTime();
    return rightDate - leftDate;
  });
}

function isLegacyTechnicalFailure(report: IngestionReport) {
  return report.status === "error";
}

function filterVisibleReviewReports(reports: IngestionReport[], filter: ReviewQueueFilter) {
  if (filter === "recent") {
    return reports;
  }

  return reports.filter((report) => !isLegacyTechnicalFailure(report));
}

function pickPreferredReviewReport(
  reports: IngestionReport[],
  options?: {
    preferredReportId?: number;
    currentSelectedId?: number | null;
    fallbackSelected?: IngestionReport | null;
  }
) {
  const targetId = options?.preferredReportId ?? options?.currentSelectedId ?? null;
  const targetedReport = targetId ? reports.find((item) => item.id === targetId) ?? null : null;
  if (targetedReport) {
    return targetedReport;
  }

  if (options?.fallbackSelected) {
    const fallbackFromList = reports.find((item) => item.id === options.fallbackSelected?.id) ?? null;
    if (fallbackFromList) {
      return fallbackFromList;
    }
  }

  return reports.find((item) => !isLegacyTechnicalFailure(item)) ?? reports[0] ?? null;
}

export default function App() {
  const { user, isAuthenticated, loading: authLoading, login, logout } = useAuth();
  const [clientName, setClientName] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [records, setRecords] = useState<PortfolioRecord[] | null>(null);
  const [report, setReport] = useState<PortfolioReport | null>(null);
  const [uploadName, setUploadName] = useState<string | null>(null);
  const [reportSourceLabel, setReportSourceLabel] = useState("Workspace executivo de analise");
  const [apiStatus, setApiStatus] = useState<ApiStatus>(initialApiStatus);
  const [loadingLiveData, setLoadingLiveData] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const [uploadState, setUploadState] = useState<UploadLifecycleState>("idle");
  const [uploadSummary, setUploadSummary] = useState<UploadSummary | null>(null);
  const [uploadHistory, setUploadHistory] = useState<UploadHistoryItem[]>([]);
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>("report");
  const [reviewFilter, setReviewFilter] = useState<ReviewQueueFilter>("pending");
  const [reviewReports, setReviewReports] = useState<IngestionReport[]>([]);
  const [hiddenReviewReportsCount, setHiddenReviewReportsCount] = useState(0);
  const [selectedReviewReport, setSelectedReviewReport] = useState<IngestionReport | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewActionLoading, setReviewActionLoading] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewFeedback, setReviewFeedback] = useState<string | null>(null);
  const [dashboardSnapshot, setDashboardSnapshot] = useState<Awaited<ReturnType<typeof fetchPortfolioSnapshot>> | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardPdfLoading, setDashboardPdfLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [dashboardActionError, setDashboardActionError] = useState<string | null>(null);
  const [dashboardFilters, setDashboardFilters] = useState<DashboardFilters>({
    clientName: "",
    assetClass: "",
    referenceDate: ""
  });
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function checkHealth() {
      try {
        const response = await fetch("/health");
        if (!response.ok) {
          throw new Error("API indisponivel");
        }

        if (isMounted) {
          setApiStatus({
            connected: true,
            message: "API CarteiraConsol conectada"
          });
        }
      } catch {
        if (isMounted) {
          setApiStatus({
            connected: false,
            message: "API offline. Use mock data ou aguarde o backend para upload real."
          });
        }
      }
    }

    void checkHealth();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!records?.length) {
      setReport(null);
      return;
    }

    try {
      setReport(
        buildReport(records, {
          clientName,
          diagnosis,
          sourceLabel: reportSourceLabel
        })
      );
    } catch (error) {
      setReport(null);
      setLastError(error instanceof Error ? error.message : "Nao foi possivel montar a previa executiva.");
    }
  }, [clientName, diagnosis, records, reportSourceLabel]);

  const sourceContext = useMemo(() => {
    if (workspaceView === "dashboard") {
      return "Painel executivo com KPIs e alocacao construidos a partir do snapshot vivo da API";
    }
    if (workspaceView === "review") {
      return selectedReviewReport
        ? `Revisando ingestao #${selectedReviewReport.id} - ${selectedReviewReport.filename}`
        : "Fila de revisao operacional para ingestao inteligente";
    }
    if (uploadName) {
      return `Arquivo processado: ${uploadName}`;
    }
    return report?.sourceLabel ?? reportSourceLabel;
  }, [report?.sourceLabel, reportSourceLabel, selectedReviewReport, uploadName, workspaceView]);

  const reviewQueueCount = useMemo(
    () => reviewReports.filter((item) => !isLegacyTechnicalFailure(item) && (item.reviewStatus === "pending" || item.reviewRequired)).length,
    [reviewReports]
  );

  const dashboardData: DashboardData | null = useMemo(() => {
    if (!dashboardSnapshot) {
      return null;
    }
    try {
      return buildDashboardData(dashboardSnapshot, dashboardFilters);
    } catch (error) {
      console.error("Dashboard snapshot render failure", error);
      return null;
    }
  }, [dashboardFilters, dashboardSnapshot]);

  function appendUploadHistory(item: UploadHistoryItem) {
    setUploadHistory((current) => [item, ...current].slice(0, MAX_UPLOAD_HISTORY_ITEMS));
  }

  function buildHistoryItem(
    summary: UploadSummary,
    status: "success" | "review_required" | "error",
    messageOverride?: string
  ): UploadHistoryItem {
    return {
      ...summary,
      id: `${summary.filename}-${summary.processedAt}-${status}`,
      status,
      message: messageOverride ?? summary.message,
      timestamp: summary.processedAt
    };
  }

  function mountPreview(nextRecords: PortfolioRecord[], sourceLabel: string) {
    setRecords(nextRecords);
    setReportSourceLabel(sourceLabel);
    setLastError(null);
  }

  async function loadReviewQueue(
    filter = reviewFilter,
    options?: {
      preferredReportId?: number;
      fallbackSelected?: IngestionReport | null;
      silent?: boolean;
    }
  ) {
    if (!options?.silent) {
      setReviewLoading(true);
      setReviewError(null);
    }

    try {
      const fetchedReports = sortReviewReports(await fetchIngestionReports(resolveReviewFilters(filter)));
      const visibleReports = filterVisibleReviewReports(fetchedReports, filter);
      setHiddenReviewReportsCount(Math.max(fetchedReports.length - visibleReports.length, 0));
      setReviewReports(visibleReports);
      setSelectedReviewReport(
        pickPreferredReviewReport(visibleReports, {
          preferredReportId: options?.preferredReportId,
          currentSelectedId: selectedReviewReport?.id ?? null,
          fallbackSelected: options?.fallbackSelected ?? null
        })
      );
    } catch (error) {
      setHiddenReviewReportsCount(0);
      if (!options?.silent) {
        setReviewError(error instanceof Error ? error.message : "Nao foi possivel carregar a fila de revisao.");
      }
    } finally {
      if (!options?.silent) {
        setReviewLoading(false);
      }
    }
  }

  async function loadDashboardSnapshot(options?: { silent?: boolean }) {
    if (!options?.silent) {
      setDashboardLoading(true);
      setDashboardError(null);
    }

    try {
      const snapshot = await fetchPortfolioSnapshot();
      setDashboardSnapshot(snapshot);
      setDashboardActionError(null);
    } catch (error) {
      if (!options?.silent) {
        setDashboardError(error instanceof Error ? error.message : "Nao foi possivel carregar o dashboard ao vivo.");
      }
    } finally {
      if (!options?.silent) {
        setDashboardLoading(false);
      }
    }
  }

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    void loadReviewQueue("pending", { silent: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    if (workspaceView !== "review") {
      return;
    }
    void loadReviewQueue(reviewFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, workspaceView, reviewFilter]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    if (workspaceView !== "dashboard") {
      return;
    }
    if (dashboardSnapshot) {
      return;
    }
    void loadDashboardSnapshot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashboardSnapshot, isAuthenticated, workspaceView]);

  function handleFillMockData() {
    setUploadName(null);
    setUploadState("idle");
    setWorkspaceView("report");
    mountPreview(mockPortfolioRecords, "Snapshot demonstrativo com mock data");
  }

  function handleDownloadTemplate() {
    window.open("/templates/modelo-carteira.csv", "_blank", "noopener,noreferrer");
  }

  function handleSelectUpload() {
    fileInputRef.current?.click();
  }

  async function refreshSnapshotAfterUpload() {
    await sleep(SNAPSHOT_REFRESH_DELAY_MS);

    let lastRefreshError: Error | null = null;
    for (let attempt = 1; attempt <= SNAPSHOT_REFRESH_ATTEMPTS; attempt += 1) {
      try {
        const nextRecords = await loadLiveRecords();
        if (!nextRecords.length) {
          throw new Error("O backend respondeu, mas o snapshot ainda nao trouxe posicoes.");
        }
        return nextRecords;
      } catch (error) {
        lastRefreshError = error instanceof Error ? error : new Error("Falha ao atualizar o snapshot.");
        if (attempt < SNAPSHOT_REFRESH_ATTEMPTS) {
          await sleep(SNAPSHOT_REFRESH_BACKOFF_MS * attempt);
        }
      }
    }

    throw lastRefreshError ?? new Error("Falha ao atualizar o snapshot.");
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadState("uploading");
    setLastError(null);
    setReviewFeedback(null);
    let latestSummary: UploadSummary | null = null;

    try {
      const uploadResult = await uploadPortfolioFile(file);
      setUploadName(uploadResult.filename);
      latestSummary = {
        outcome: uploadResult.review_required ? "review_required" : "success",
        ingestionReportId: uploadResult.ingestion_report_id,
        filename: uploadResult.filename,
        detectedType: uploadResult.detected_type,
        rowsProcessed: uploadResult.rows_processed,
        rowsSkipped: uploadResult.rows_skipped,
        message: uploadResult.message,
        processedAt: uploadResult.processed_at,
        rawFile: uploadResult.raw_file,
        processedFile: uploadResult.processed_file,
        detectionConfidence: uploadResult.detection_confidence ?? null,
        reviewRequired: uploadResult.review_required ?? false,
        reviewStatus: uploadResult.review_status ?? null,
        reviewReasons: uploadResult.review_reasons ?? [],
        reprocessedAt: uploadResult.reprocessed_at ?? null,
        reprocessCount: uploadResult.reprocess_count ?? 0
      };
      setUploadSummary(latestSummary);
      appendUploadHistory(buildHistoryItem(latestSummary, latestSummary.outcome ?? "success"));

      setUploadState("processing");
      void loadReviewQueue(reviewFilter, {
        preferredReportId: uploadResult.ingestion_report_id,
        silent: workspaceView !== "review"
      });
      void loadDashboardSnapshot({ silent: workspaceView !== "dashboard" });

      try {
        const nextRecords = await refreshSnapshotAfterUpload();
        mountPreview(nextRecords, "Snapshot atualizado apos upload no backend");
      } catch (refreshError) {
        const refreshMessage =
          refreshError instanceof Error ? refreshError.message : "A previa ainda nao foi recarregada automaticamente.";
        setLastError(`O arquivo foi processado, mas a previa ainda nao foi recarregada automaticamente. ${refreshMessage}`);
      }

      setUploadState("success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Nao foi possivel enviar a planilha para o backend.";
      if (!latestSummary) {
        setUploadState("error");
        setLastError(message);
        const fallbackSummary: UploadSummary = {
          outcome: "error",
          filename: file.name,
          detectedType: detectFileTypeFromName(file.name),
          rowsProcessed: 0,
          rowsSkipped: 0,
          message,
          processedAt: new Date().toISOString(),
          rawFile: "",
          processedFile: ""
        };
        setUploadSummary(fallbackSummary);
        appendUploadHistory(buildHistoryItem(fallbackSummary, "error", message));
      } else {
        setUploadState("success");
        setLastError(`O arquivo foi processado, mas o workspace nao conseguiu concluir a atualizacao visual. ${message}`);
      }
    } finally {
      event.target.value = "";
    }
  }

  async function handleLoadLiveData() {
    setLoadingLiveData(true);
    try {
      const nextRecords = await loadLiveRecords();
      setUploadName(null);
      setUploadState("idle");
      setWorkspaceView("report");
      mountPreview(nextRecords, "Snapshot conectado ao backend CarteiraConsol");
      void loadDashboardSnapshot({ silent: true });
    } catch (error) {
      setLastError(error instanceof Error ? error.message : "Nao foi possivel carregar os dados atuais da plataforma.");
    } finally {
      setLoadingLiveData(false);
    }
  }

  async function handleSelectReviewReport(reportId: number) {
    const preview = reviewReports.find((item) => item.id === reportId) ?? null;
    if (preview) {
      setSelectedReviewReport(preview);
    }
    setReviewError(null);
    setReviewFeedback(null);

    try {
      const detail = await fetchIngestionReport(reportId);
      setSelectedReviewReport(detail);
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Nao foi possivel carregar o detalhe da revisao.");
    }
  }

  async function handleReviewAction(reviewStatus: ReviewStatus) {
    if (!selectedReviewReport) {
      return;
    }

    setReviewActionLoading(true);
    setReviewError(null);
    setReviewFeedback(null);

    try {
      const updated = await updateIngestionReportReview(selectedReviewReport.id, {
        reviewStatus
      });
      setSelectedReviewReport(updated);
      setReviewFeedback(`Relatorio #${updated.id} atualizado para ${updated.reviewStatus}.`);
      await loadReviewQueue(reviewFilter, {
        preferredReportId: updated.id,
        fallbackSelected: updated
      });
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Nao foi possivel atualizar a revisao.");
    } finally {
      setReviewActionLoading(false);
    }
  }

  async function handleApproveAndReprocess() {
    if (!selectedReviewReport) {
      return;
    }

    setReviewActionLoading(true);
    setReviewError(null);
    setReviewFeedback(null);

    try {
      let workingReport = selectedReviewReport;
      if (workingReport.reviewStatus !== "approved") {
        workingReport = await updateIngestionReportReview(workingReport.id, {
          reviewStatus: "approved"
        });
        setSelectedReviewReport(workingReport);
      }

      const reprocessResult = await reprocessIngestionReport(workingReport.id);
      const refreshedReport = await fetchIngestionReport(workingReport.id);
      setSelectedReviewReport(refreshedReport);
      setReviewFeedback(
        `Relatorio #${refreshedReport.id} reprocessado com sucesso. ${reprocessResult.rows_processed} linhas processadas.`
      );
      await loadReviewQueue(reviewFilter, {
        preferredReportId: refreshedReport.id,
        fallbackSelected: refreshedReport
      });
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Nao foi possivel aprovar e reprocessar a ingestao.");
    } finally {
      setReviewActionLoading(false);
    }
  }

  function handleGeneratePdf() {
    if (!report) {
      setLastError("Gere uma previa antes de exportar o relatorio em PDF.");
      return;
    }
    window.print();
  }

  function handleDashboardFilterChange(field: keyof DashboardFilters, value: string) {
    setDashboardFilters((current) => {
      const next = { ...current, [field]: value };
      if (field === "clientName" || field === "assetClass") {
        next.referenceDate = "";
      }
      return next;
    });
  }

  function handleDashboardResetFilters() {
    setDashboardFilters({
      clientName: "",
      assetClass: "",
      referenceDate: ""
    });
  }

  async function handleDownloadDashboardPdf() {
    setDashboardPdfLoading(true);
    setDashboardActionError(null);
    try {
      await downloadPortfolioPdfReport({
        clientName: dashboardFilters.clientName || undefined,
        assetClass: dashboardFilters.assetClass || undefined,
        referenceDate: dashboardFilters.referenceDate || undefined
      });
    } catch (error) {
      setDashboardActionError(error instanceof Error ? error.message : "Nao foi possivel gerar o PDF executivo.");
    } finally {
      setDashboardPdfLoading(false);
    }
  }

  const workspaceResetKey = [
    workspaceView,
    report?.latestReferenceDate ?? "no-report",
    uploadSummary?.processedAt ?? "no-upload",
    String(selectedReviewReport?.id ?? "no-review"),
    dashboardData?.asOfDate ?? "no-dashboard"
  ].join("|");

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.10),transparent_28%),linear-gradient(180deg,#07101f_0%,#081320_100%)] px-6 py-8 text-slate-200">
        <div className="rounded-[28px] border border-white/8 bg-white/[0.03] px-8 py-6 shadow-soft">
          Validando sessao segura do workspace...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginScreen loading={authLoading} onLogin={login} />;
  }

  return (
    <div className="min-h-screen px-4 py-4 md:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1680px] gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls,.json"
          className="hidden"
          onChange={(event) => void handleUpload(event)}
        />

        <Sidebar
          clientName={clientName}
          diagnosis={diagnosis}
          apiStatus={apiStatus}
          loadingLiveData={loadingLiveData}
          uploadState={uploadState}
          sourceContext={sourceContext}
          workspaceView={workspaceView}
          reviewQueueCount={reviewQueueCount}
          uploadSummary={uploadSummary}
          uploadHistory={uploadHistory}
          lastError={lastError}
          currentUserName={user?.fullName ?? "Workspace User"}
          currentUserEmail={user?.email ?? ""}
          onClientNameChange={setClientName}
          onDiagnosisChange={setDiagnosis}
          onWorkspaceViewChange={setWorkspaceView}
          onFillMockData={handleFillMockData}
          onDownloadTemplate={handleDownloadTemplate}
          onUploadSpreadsheet={handleSelectUpload}
          onGeneratePdf={handleGeneratePdf}
          onLogout={logout}
        />

        <main className="min-w-0">
          <WorkspaceErrorBoundary
            resetKey={workspaceResetKey}
            onReset={() => {
              setLastError("O workspace foi recuperado apos uma resposta inesperada.");
              setDashboardActionError(null);
            }}
          >
            {workspaceView === "review" ? (
              <ReviewQueueWorkspace
                reports={reviewReports}
                hiddenTechnicalReportsCount={hiddenReviewReportsCount}
                selectedReport={selectedReviewReport}
                loading={reviewLoading}
                actionLoading={reviewActionLoading}
                error={reviewError}
                feedback={reviewFeedback}
                activeFilter={reviewFilter}
                onFilterChange={setReviewFilter}
                onRefresh={() => void loadReviewQueue(reviewFilter)}
                onSelectReport={(reportId) => void handleSelectReviewReport(reportId)}
                onReviewAction={(status) => void handleReviewAction(status)}
                onApproveAndReprocess={() => void handleApproveAndReprocess()}
              />
            ) : workspaceView === "dashboard" ? (
              <DashboardWorkspace
                data={dashboardData}
                filters={dashboardFilters}
                loading={dashboardLoading}
                pdfLoading={dashboardPdfLoading}
                error={dashboardError}
                actionError={dashboardActionError}
                onRefresh={() => void loadDashboardSnapshot()}
                onDownloadPdf={() => void handleDownloadDashboardPdf()}
                onResetFilters={handleDashboardResetFilters}
                onFilterChange={handleDashboardFilterChange}
              />
            ) : !report ? (
              <EmptyState
                apiStatus={apiStatus}
                loadingLiveData={loadingLiveData}
                onLoadLiveData={handleLoadLiveData}
                onFillMockData={handleFillMockData}
                onUploadSpreadsheet={handleSelectUpload}
              />
            ) : (
              <ReportCanvas report={report} />
            )}
          </WorkspaceErrorBoundary>
        </main>
      </div>
    </div>
  );
}
