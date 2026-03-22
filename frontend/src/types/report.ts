export type PortfolioRecord = {
  clientName: string;
  riskProfile: string;
  broker: string;
  assetClass: string;
  ticker: string;
  assetName: string;
  quantity: number;
  avgPrice: number;
  totalValue: number;
  referenceDate: string;
};

export type MetricCard = {
  label: string;
  value: number;
  tone: "blue" | "teal" | "gold" | "slate";
  format: "currency" | "number";
  helper?: string;
  icon?: string;
  trendLabel?: string;
};

export type BreakdownItem = {
  label: string;
  value: number;
  share: number;
};

export type TimelinePoint = {
  date: string;
  value: number;
};

export type InsightItem = {
  title: string;
  body: string;
};

export type DashboardFilters = {
  clientName: string;
  assetClass: string;
  referenceDate: string;
};

export type DashboardData = {
  asOfDate: string | null;
  metrics: MetricCard[];
  assetAllocation: BreakdownItem[];
  clientAllocation: BreakdownItem[];
  topAssets: BreakdownItem[];
  timeline: TimelinePoint[];
  positions: PortfolioRecord[];
  availableClients: string[];
  availableAssetClasses: string[];
  availableReferenceDates: string[];
};

export type PortfolioReport = {
  clientName: string;
  diagnosis: string;
  sourceLabel: string;
  generatedAt: string;
  latestReferenceDate: string;
  metrics: MetricCard[];
  allocation: BreakdownItem[];
  brokerExposure: BreakdownItem[];
  clientExposure: BreakdownItem[];
  timeline: TimelinePoint[];
  positions: PortfolioRecord[];
  insights: InsightItem[];
};

export type ApiStatus = {
  connected: boolean;
  message: string;
};

export type UploadSummary = {
  outcome?: "success" | "review_required" | "error";
  ingestionReportId?: number;
  filename: string;
  detectedType: string;
  rowsProcessed: number;
  rowsSkipped: number;
  message: string;
  processedAt: string;
  rawFile: string;
  processedFile: string;
  detectionConfidence?: number | null;
  reviewRequired?: boolean;
  reviewStatus?: ReviewStatus | null;
  reviewReasons?: string[];
  reprocessedAt?: string | null;
  reprocessCount?: number;
};

export type UploadLifecycleState = "idle" | "uploading" | "processing" | "success" | "error";

export type UploadHistoryItem = UploadSummary & {
  id: string;
  status: "success" | "review_required" | "error";
  timestamp: string;
};

export type WorkspaceView = "report" | "review" | "dashboard";

export type ReviewStatus = "pending" | "approved" | "rejected" | "not_required";

export type ReviewQueueFilter = "pending" | "review_required" | "recent";

export type AppliedMapping = {
  original_name?: string;
  normalized_name?: string;
  canonical_name?: string | null;
  matched_alias?: string | null;
  score?: number;
  accepted?: boolean;
  [key: string]: unknown;
};

export type IngestionReport = {
  id: number;
  filename: string;
  sourceFile: string;
  sourceType: string;
  detectedType: string;
  layoutSignature: string | null;
  rawFile: string | null;
  processedFile: string | null;
  parserName: string | null;
  detectionConfidence: number | null;
  reviewRequired: boolean;
  reviewStatus: ReviewStatus;
  reviewReasons: string[];
  detectedColumns: string[];
  appliedMappings: AppliedMapping[];
  structureDetection: Record<string, unknown>;
  rowsProcessed: number;
  rowsSkipped: number;
  status: string;
  message: string;
  createdAt: string;
  processedAt: string | null;
  reprocessedAt: string | null;
  reprocessCount: number;
};

export type BuilderState = {
  report: PortfolioReport | null;
  apiStatus: ApiStatus;
  loadingLiveData: boolean;
  uploadName: string | null;
  lastError: string | null;
};
