import { emitUnauthorizedSession, getStoredAccessToken } from "./auth";
import type { AuthSession, AuthenticatedUser } from "../types/auth";

type PaginatedResponse<T> = {
  status: string;
  data: T[];
  pagination: {
    total: number;
    offset: number;
    limit: number;
    count: number;
    has_more: boolean;
  };
};

type ObjectResponse<T> = {
  status: string;
  data: T;
};

type ErrorResponse = {
  status?: string;
  detail?: string;
  error_code?: string;
};

type ReviewStatusApi = "pending" | "approved" | "rejected" | "not_required";

type UserApi = {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
};

type LoginApi = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: UserApi;
};

export type ClientApi = {
  id: number;
  name: string;
  risk_profile: string;
};

export type AccountApi = {
  id: number;
  client_id: number;
  broker: string;
};

export type AssetApi = {
  id: number;
  ticker: string | null;
  original_name: string;
  normalized_name: string;
  asset_class: string;
  cnpj: string | null;
  maturity_date: string | null;
};

export type PositionApi = {
  id: number;
  account_id: number;
  asset_id: number;
  quantity: string;
  avg_price: string;
  total_value: string;
  reference_date: string;
};

export type PortfolioSnapshotApi = {
  clients: ClientApi[];
  accounts: AccountApi[];
  assets: AssetApi[];
  positions: PositionApi[];
};

export type UploadApi = {
  ingestion_report_id?: number;
  filename: string;
  detected_type: string;
  rows_processed: number;
  rows_skipped: number;
  message: string;
  processed_at: string;
  raw_file: string;
  processed_file: string;
  detection_confidence?: number | null;
  review_required?: boolean;
  review_status?: ReviewStatusApi | null;
  review_reasons?: string[];
  reprocessed_at?: string | null;
  reprocess_count?: number;
};

export type IngestionReportApi = {
  id: number;
  filename: string;
  source_file: string;
  source_type: string;
  detected_type: string;
  layout_signature: string | null;
  raw_file: string | null;
  processed_file: string | null;
  parser_name: string | null;
  detection_confidence: number | null;
  review_required: boolean;
  review_status: ReviewStatusApi;
  review_reasons: string[];
  detected_columns: string[];
  applied_mappings: Array<Record<string, unknown>>;
  structure_detection: Record<string, unknown>;
  rows_processed: number;
  rows_skipped: number;
  status: string;
  message: string;
  created_at: string;
  processed_at: string | null;
  reprocessed_at: string | null;
  reprocess_count: number;
};

export class ApiRequestError extends Error {
  statusCode: number;
  errorCode?: string;

  constructor(message: string, statusCode: number, errorCode?: string) {
    super(message);
    this.name = "ApiRequestError";
    this.statusCode = statusCode;
    this.errorCode = errorCode;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function buildPath(path: string, params?: Record<string, string | number | boolean | undefined>) {
  const searchParams = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.set(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `${path}?${queryString}` : path;
}

function assertUserPayload(value: unknown): UserApi {
  if (!isRecord(value)) {
    throw new Error("A resposta do backend para usuario veio em formato invalido.");
  }

  const requiredNumberFields = ["id"] as const;
  for (const field of requiredNumberFields) {
    if (typeof value[field] !== "number" || Number.isNaN(value[field])) {
      throw new Error(`A resposta do backend nao trouxe o campo numerico '${field}' corretamente.`);
    }
  }

  const requiredStringFields = ["email", "created_at"] as const;
  for (const field of requiredStringFields) {
    if (typeof value[field] !== "string" || !value[field]) {
      throw new Error(`A resposta do backend nao trouxe o campo obrigatorio '${field}'.`);
    }
  }

  if (value.full_name !== null && value.full_name !== undefined && typeof value.full_name !== "string") {
    throw new Error("A resposta do backend trouxe 'full_name' em formato invalido.");
  }

  if (typeof value.is_active !== "boolean" || typeof value.is_admin !== "boolean") {
    throw new Error("A resposta do backend trouxe flags de usuario em formato invalido.");
  }

  return value as UserApi;
}

function assertLoginPayload(value: unknown): LoginApi {
  if (!isRecord(value)) {
    throw new Error("A resposta do backend para login veio em formato invalido.");
  }

  const requiredStringFields = ["access_token", "token_type", "expires_at"] as const;
  for (const field of requiredStringFields) {
    if (typeof value[field] !== "string" || !value[field]) {
      throw new Error(`A resposta do backend nao trouxe o campo obrigatorio '${field}'.`);
    }
  }

  return {
    access_token: String(value.access_token),
    token_type: String(value.token_type),
    expires_at: String(value.expires_at),
    user: assertUserPayload(value.user)
  };
}

function assertUploadPayload(value: unknown): UploadApi {
  if (!isRecord(value)) {
    throw new Error("A resposta do backend para upload veio em formato invalido.");
  }

  const requiredStringFields = ["filename", "detected_type", "message", "processed_at", "raw_file", "processed_file"] as const;
  for (const field of requiredStringFields) {
    if (typeof value[field] !== "string" || !value[field]) {
      throw new Error(`A resposta do backend nao trouxe o campo obrigatorio '${field}'.`);
    }
  }

  const requiredNumberFields = ["rows_processed", "rows_skipped"] as const;
  for (const field of requiredNumberFields) {
    if (typeof value[field] !== "number" || Number.isNaN(value[field])) {
      throw new Error(`A resposta do backend nao trouxe o campo numerico '${field}' corretamente.`);
    }
  }

  if (value.ingestion_report_id !== undefined && typeof value.ingestion_report_id !== "number") {
    throw new Error("A resposta do backend trouxe 'ingestion_report_id' em formato invalido.");
  }

  if (value.detection_confidence !== undefined && value.detection_confidence !== null && typeof value.detection_confidence !== "number") {
    throw new Error("A resposta do backend trouxe 'detection_confidence' em formato invalido.");
  }

  if (value.review_required !== undefined && typeof value.review_required !== "boolean") {
    throw new Error("A resposta do backend trouxe 'review_required' em formato invalido.");
  }

  if (value.review_status !== undefined && value.review_status !== null && typeof value.review_status !== "string") {
    throw new Error("A resposta do backend trouxe 'review_status' em formato invalido.");
  }

  if (value.review_reasons !== undefined && !Array.isArray(value.review_reasons)) {
    throw new Error("A resposta do backend trouxe 'review_reasons' em formato invalido.");
  }

  if (value.reprocessed_at !== undefined && value.reprocessed_at !== null && typeof value.reprocessed_at !== "string") {
    throw new Error("A resposta do backend trouxe 'reprocessed_at' em formato invalido.");
  }

  if (value.reprocess_count !== undefined && (typeof value.reprocess_count !== "number" || Number.isNaN(value.reprocess_count))) {
    throw new Error("A resposta do backend trouxe 'reprocess_count' em formato invalido.");
  }

  return value as UploadApi;
}

function assertIngestionReportPayload(value: unknown): IngestionReportApi {
  if (!isRecord(value)) {
    throw new Error("A resposta do backend para relatorio de ingestao veio em formato invalido.");
  }

  const requiredNumberFields = ["id", "rows_processed", "rows_skipped", "reprocess_count"] as const;
  for (const field of requiredNumberFields) {
    if (typeof value[field] !== "number" || Number.isNaN(value[field])) {
      throw new Error(`A resposta do backend nao trouxe o campo numerico '${field}' corretamente.`);
    }
  }

  const requiredStringFields = [
    "filename",
    "source_file",
    "source_type",
    "detected_type",
    "review_status",
    "status",
    "message",
    "created_at"
  ] as const;
  for (const field of requiredStringFields) {
    if (typeof value[field] !== "string" || !value[field]) {
      throw new Error(`A resposta do backend nao trouxe o campo obrigatorio '${field}'.`);
    }
  }

  if (typeof value.review_required !== "boolean") {
    throw new Error("A resposta do backend nao trouxe 'review_required' corretamente.");
  }

  const arrayFields = ["review_reasons", "detected_columns", "applied_mappings"] as const;
  for (const field of arrayFields) {
    if (!Array.isArray(value[field])) {
      throw new Error(`A resposta do backend nao trouxe '${field}' em formato de lista.`);
    }
  }

  if (!isRecord(value.structure_detection)) {
    throw new Error("A resposta do backend nao trouxe 'structure_detection' em formato invalido.");
  }

  return value as IngestionReportApi;
}

function toAuthenticatedUser(value: UserApi): AuthenticatedUser {
  return {
    id: value.id,
    email: value.email,
    fullName: value.full_name,
    isActive: value.is_active,
    isAdmin: value.is_admin,
    createdAt: value.created_at
  };
}

function toAuthSession(value: LoginApi): AuthSession {
  return {
    accessToken: value.access_token,
    tokenType: value.token_type,
    expiresAt: value.expires_at,
    user: toAuthenticatedUser(value.user)
  };
}

async function parseErrorResponse(response: Response, fallbackMessage: string): Promise<{ message: string; errorCode?: string }> {
  try {
    const payload: ErrorResponse = await response.json();
    return {
      message: payload.detail || fallbackMessage,
      errorCode: payload.error_code
    };
  } catch {
    return { message: fallbackMessage };
  }
}

async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers ?? undefined);
  const token = getStoredAccessToken();

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(path, {
    ...init,
    headers
  });
}

async function throwApiError(response: Response, fallbackMessage: string): Promise<never> {
  const { message, errorCode } = await parseErrorResponse(response, fallbackMessage);
  if (response.status === 401 && getStoredAccessToken()) {
    emitUnauthorizedSession();
  }
  throw new ApiRequestError(message, response.status, errorCode);
}

async function fetchPaginated<T>(path: string): Promise<T[]> {
  const items: T[] = [];
  let offset = 0;
  const limit = 100;

  while (true) {
    const response = await apiFetch(`${path}${path.includes("?") ? "&" : "?"}offset=${offset}&limit=${limit}`);
    if (!response.ok) {
      await throwApiError(response, `Falha ao consultar ${path}`);
    }

    const payload: PaginatedResponse<T> = await response.json();
    if (!payload || payload.status !== "success" || !Array.isArray(payload.data) || !payload.pagination) {
      throw new Error(`A resposta de ${path} veio em formato inesperado.`);
    }

    items.push(...payload.data);
    if (!payload.pagination.has_more) {
      break;
    }
    offset += limit;
  }

  return items;
}

function toIngestionReport(value: IngestionReportApi) {
  return {
    id: value.id,
    filename: value.filename,
    sourceFile: value.source_file,
    sourceType: value.source_type,
    detectedType: value.detected_type,
    layoutSignature: value.layout_signature,
    rawFile: value.raw_file,
    processedFile: value.processed_file,
    parserName: value.parser_name,
    detectionConfidence: value.detection_confidence,
    reviewRequired: value.review_required,
    reviewStatus: value.review_status,
    reviewReasons: value.review_reasons,
    detectedColumns: value.detected_columns,
    appliedMappings: value.applied_mappings,
    structureDetection: value.structure_detection,
    rowsProcessed: value.rows_processed,
    rowsSkipped: value.rows_skipped,
    status: value.status,
    message: value.message,
    createdAt: value.created_at,
    processedAt: value.processed_at,
    reprocessedAt: value.reprocessed_at,
    reprocessCount: value.reprocess_count
  };
}

export async function loginWithPassword(email: string, password: string): Promise<AuthSession> {
  let response: Response;
  try {
    response = await apiFetch("/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ email, password })
    });
  } catch {
    throw new Error("Nao foi possivel conectar ao backend para validar suas credenciais.");
  }

  if (!response.ok) {
    await throwApiError(response, "Nao foi possivel autenticar o usuario informado.");
  }

  const payload: ObjectResponse<unknown> = await response.json();
  if (!payload || payload.status !== "success") {
    throw new Error("O backend respondeu ao login sem confirmar sucesso.");
  }

  return toAuthSession(assertLoginPayload(payload.data));
}

export async function fetchCurrentUser(): Promise<AuthenticatedUser> {
  const response = await apiFetch("/auth/me");
  if (!response.ok) {
    await throwApiError(response, "Nao foi possivel validar a sessao atual.");
  }

  const payload: ObjectResponse<unknown> = await response.json();
  if (!payload || payload.status !== "success") {
    throw new Error("O backend respondeu sem confirmar a sessao autenticada.");
  }

  return toAuthenticatedUser(assertUserPayload(payload.data));
}

export async function uploadPortfolioFile(file: File): Promise<UploadApi> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await apiFetch("/upload", {
      method: "POST",
      body: formData
    });
  } catch {
    throw new Error("Nao foi possivel conectar ao backend para enviar o arquivo.");
  }

  if (!response.ok) {
    const fallbackMessage =
      response.status >= 500
        ? "O backend nao conseguiu concluir o processamento do arquivo."
        : "O upload foi recusado. Revise o arquivo e tente novamente.";
    await throwApiError(response, fallbackMessage);
  }

  const payload: ObjectResponse<unknown> = await response.json();
  if (!payload || payload.status !== "success") {
    throw new Error("O backend respondeu ao upload sem confirmar sucesso.");
  }

  return assertUploadPayload(payload.data);
}

export async function fetchIngestionReports(filters?: {
  reviewRequired?: boolean;
  reviewStatus?: ReviewStatusApi;
  limit?: number;
}) {
  const response = await apiFetch(
    buildPath("/ingestion-reports", {
      review_required: filters?.reviewRequired,
      review_status: filters?.reviewStatus,
      limit: filters?.limit ?? 50
    })
  );

  if (!response.ok) {
    await throwApiError(response, "Nao foi possivel carregar a fila de revisao.");
  }

  const payload: PaginatedResponse<unknown> = await response.json();
  if (!payload || payload.status !== "success" || !Array.isArray(payload.data)) {
    throw new Error("A resposta da fila de revisao veio em formato inesperado.");
  }

  return payload.data.map((item) => toIngestionReport(assertIngestionReportPayload(item)));
}

export async function fetchIngestionReport(reportId: number) {
  const response = await apiFetch(`/ingestion-reports/${reportId}`);
  if (!response.ok) {
    await throwApiError(response, "Nao foi possivel carregar o detalhe da revisao.");
  }

  const payload: ObjectResponse<unknown> = await response.json();
  if (!payload || payload.status !== "success") {
    throw new Error("O backend respondeu sem confirmar o detalhamento da revisao.");
  }

  return toIngestionReport(assertIngestionReportPayload(payload.data));
}

export async function updateIngestionReportReview(
  reportId: number,
  payload: { reviewStatus: ReviewStatusApi; approvedBy?: string }
) {
  const response = await apiFetch(`/ingestion-reports/${reportId}/review`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      review_status: payload.reviewStatus,
      approved_by: payload.approvedBy
    })
  });

  if (!response.ok) {
    await throwApiError(response, "Nao foi possivel atualizar o status da revisao.");
  }

  const responsePayload: ObjectResponse<unknown> = await response.json();
  if (!responsePayload || responsePayload.status !== "success") {
    throw new Error("O backend respondeu sem confirmar a atualizacao da revisao.");
  }

  return toIngestionReport(assertIngestionReportPayload(responsePayload.data));
}

export async function reprocessIngestionReport(reportId: number) {
  const response = await apiFetch(`/ingestion-reports/${reportId}/reprocess`, {
    method: "POST"
  });

  if (!response.ok) {
    await throwApiError(response, "Nao foi possivel reprocessar a ingestao.");
  }

  const responsePayload: ObjectResponse<unknown> = await response.json();
  if (!responsePayload || responsePayload.status !== "success") {
    throw new Error("O backend respondeu sem confirmar o reprocessamento.");
  }

  return assertUploadPayload(responsePayload.data);
}

export async function fetchPortfolioSnapshot(): Promise<PortfolioSnapshotApi> {
  const [clients, accounts, assets, positions] = await Promise.all([
    fetchPaginated<ClientApi>("/clients"),
    fetchPaginated<AccountApi>("/accounts"),
    fetchPaginated<AssetApi>("/assets"),
    fetchPaginated<PositionApi>("/positions")
  ]);

  return { clients, accounts, assets, positions };
}

function resolveDownloadFilename(response: Response, fallback: string) {
  const disposition = response.headers.get("content-disposition");
  const match = disposition?.match(/filename="?([^"]+)"?/i);
  return match?.[1] || fallback;
}

async function buildValidatedPdfBlob(response: Response) {
  const contentType = response.headers.get("content-type")?.toLowerCase() || "";
  const buffer = await response.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  const signature = new TextDecoder("ascii").decode(bytes.slice(0, 4));

  if (signature === "%PDF") {
    return new Blob([buffer], { type: "application/pdf" });
  }

  const text = new TextDecoder("utf-8").decode(bytes);
  try {
    const payload = JSON.parse(text) as ErrorResponse;
    throw new Error(payload.detail || "O backend nao retornou um PDF valido.");
  } catch {
    const contentHint = contentType ? ` Conteudo recebido: ${contentType}.` : "";
    throw new Error(`O backend respondeu sem um PDF valido para download.${contentHint}`);
  }
}

export async function downloadPortfolioPdfReport(filters?: {
  clientName?: string;
  assetClass?: string;
  referenceDate?: string;
}) {
  let response: Response;
  try {
    response = await apiFetch(
      buildPath("/reports/portfolio/pdf", {
        client_name: filters?.clientName || undefined,
        asset_class: filters?.assetClass || undefined,
        reference_date: filters?.referenceDate || undefined
      }),
      {
        headers: {
          Accept: "application/pdf"
        },
        cache: "no-store"
      }
    );
  } catch {
    throw new Error("Nao foi possivel conectar ao backend para gerar o PDF executivo.");
  }

  if (!response.ok) {
    await throwApiError(response, "Nao foi possivel gerar o PDF executivo do portfolio.");
  }

  const blob = await buildValidatedPdfBlob(response);
  const filename = resolveDownloadFilename(response, "carteiraconsol_executive_portfolio_report.pdf");
  const url = window.URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  window.document.body.appendChild(anchor);
  anchor.click();
  window.setTimeout(() => {
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }, 3000);
}
