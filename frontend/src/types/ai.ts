export interface Entity {
  name: string;
  type?: string | null;
  matched_table?: string | null;
  matched_column?: string | null;
}

export interface Metric {
  name: string;
  aggregation?: string | null;
  matched_column?: string | null;
}

export interface Filter {
  column: string;
  operator: string;
  value?: any;
  raw_text?: string | null;
}

export interface Grouping {
  column: string;
  raw_text?: string | null;
}

export interface Sorting {
  column: string;
  direction: 'asc' | 'desc';
}

export interface ClarificationOption {
  id: string;
  label: string;
  description?: string | null;
}

export interface ClarificationDetails {
  question: string;
  reason?: string | null;
  options: ClarificationOption[];
  allow_custom_answer?: boolean;
}

export interface ValidationResult {
  valid: boolean;
  invalid_fields: string[];
  warnings: string[];
}

export interface IntentAnalysis {
  intent: string;
  summary: string;
  status: 'ready' | 'clarification_required' | 'invalid_intent' | 'max_rounds_exceeded';
  entities: Entity[];
  metrics: Metric[];
  filters: Filter[];
  grouping: Grouping[];
  sorting?: Sorting | null;
  limit?: number | null;
  time_range?: string | null;
  relevant_tables: string[];
  relevant_columns: string[];
  needs_clarification: boolean;
  clarification?: ClarificationDetails | null;
  unsupported_request: boolean;
  unsupported_reason?: string | null;
  confidence: number;
}

export interface AIAnalysisRequest {
  dataset_id: string;
  question: string;
  previous_turns?: Array<{ question: string; clarification?: string }>;
  clarification_round?: number;
}

export interface AIClarificationRequest {
  dataset_id: string;
  original_question: string;
  clarification: string;
  previous_turns?: Array<{ question: string; clarification?: string }>;
  clarification_round?: number;
}

export interface AIAnalysisResponse {
  success: boolean;
  status?: 'ready' | 'clarification_required' | 'invalid_intent' | 'max_rounds_exceeded' | 'error';
  analysis?: IntentAnalysis | null;
  validation_result?: ValidationResult | null;
  clarification_round?: number;
  dataset_id: string;
  error?: string | null;
  debug_info?: {
    processing_time_ms: number;
    relevant_tables: string[];
    tokens_matched_tables: string[];
    detected_metrics: string[];
    detected_filters: string[];
    needs_clarification: boolean;
    confidence: number;
  } | null;
}

export interface AIHealthResponse {
  status: string;
  configured: boolean;
  provider: string;
  model: string;
  message: string;
}

export interface SQLGenerationRequest {
  dataset_id: string;
  question: string;
  intent: IntentAnalysis;
}

export interface SQLGenerationResult {
  sql: string;
  dialect: string;
  tables_used: string[];
  columns_used: string[];
  explanation: string;
  confidence: number;
}

export interface SQLGenerationResponse {
  success: boolean;
  status: 'generated' | 'generation_failed' | 'generation_rejected' | 'error';
  sql_result?: SQLGenerationResult | null;
  dataset_id: string;
  question: string;
  error?: string | null;
  generation_time_ms?: number | null;
}

export interface ValidationErrorDetail {
  code: string;
  message: string;
  target?: string | null;
}

export interface SQLValidationRequest {
  dataset_id: string;
  sql: string;
}

export interface SQLValidationResponse {
  valid: boolean;
  status: 'approved' | 'rejected' | 'error';
  dialect: string;
  statement_type: string;
  tables_used: string[];
  columns_used: string[];
  warnings: string[];
  errors: ValidationErrorDetail[];
  dataset_id: string;
  sql: string;
  validation_time_ms?: number | null;
}

export interface QueryResultColumn {
  name: string;
  type: string;
}

export interface QueryExecutionRequest {
  dataset_id: string;
  sql: string;
}

export interface QueryExecutionResponse {
  success: boolean;

  status: 'success' | 'validation_failed' | 'execution_failed' | 'timeout' | 'error';
  columns: QueryResultColumn[];
  rows: Array<Record<string, any>>;
  row_count: number;
  truncated: boolean;
  execution_time_ms: number;
  dataset_id: string;
  sql: string;
  error?: string | null;
}

export interface ChartRecommendation {
  chart_type: 'bar' | 'line' | 'area' | 'pie' | 'kpi' | 'scatter' | 'none';
  x_axis?: string | null;
  y_axis?: string | null;
  title?: string | null;
  reason?: string | null;
}

export interface AIInsightResult {
  summary_insight: string;
  key_highlights: string[];
}

export interface FullAnalysisRequest {
  dataset_id: string;
  question: string;
  sql: string;
  intent?: IntentAnalysis | null;
  conversation_id?: string | null;
}

export interface FullQueryAnalysisResponse {
  execution: QueryExecutionResponse;
  chart: ChartRecommendation;
  insight?: AIInsightResult | null;
  validation?: SQLValidationResponse | null;
  query_id?: string | null;
  conversation_id?: string | null;
}

export interface QueryHistoryItem {
  id: string;
  conversation_id: string;
  dataset_id: string;
  user_question: string;
  intent_json?: Record<string, any> | null;
  generated_sql?: string | null;
  execution_status: string;
  row_count: number;
  chart_type: string;
  insight_summary?: string | null;
  created_at: string;
}

export interface QueryHistoryListResponse {
  items: QueryHistoryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FollowupQueryRequest {
  dataset_id: string;
  conversation_id: string;
  question: string;
  previous_intent?: Record<string, any> | null;
  previous_question?: string | null;
  clarification_round?: number;
}

export interface InsightRequest {
  question: string;
  columns: QueryResultColumn[];
  rows: Array<Record<string, any>>;
  intent?: Record<string, any> | null;
}

export interface ConversationTurn {
  id: string;
  question: string;
  response?: AIAnalysisResponse | null;
  fullAnalysis?: FullQueryAnalysisResponse | null;
  sqlResponse?: SQLGenerationResponse | null;
  validationResponse?: SQLValidationResponse | null;
  status: 'idle' | 'analyzing' | 'clarifying' | 'generating_sql' | 'validating' | 'executing' | 'completed' | 'error';
  error?: string | null;
  timestamp: string;
}




