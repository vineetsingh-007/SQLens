from typing import List, Optional, Any, Dict, Literal
from pydantic import BaseModel, Field


class Entity(BaseModel):
    name: str = Field(description="Name of the entity, e.g. products, customers")
    type: Optional[str] = Field(default=None, description="Entity category/type if applicable")
    matched_table: Optional[str] = Field(default=None, description="Matched database table name from schema")
    matched_column: Optional[str] = Field(default=None, description="Matched database column name if specific")


class Metric(BaseModel):
    name: str = Field(description="Metric being measured, e.g. revenue, count, sales")
    aggregation: Optional[str] = Field(default=None, description="Aggregation operation e.g. sum, count, avg, min, max")
    matched_column: Optional[str] = Field(default=None, description="Matched database column for the metric")


class Filter(BaseModel):
    column: str = Field(description="Column name being filtered")
    operator: str = Field(default="=", description="Filter operator e.g. =, >, <, LIKE, IN, BETWEEN")
    value: Optional[Any] = Field(default=None, description="Filter value")
    raw_text: Optional[str] = Field(default=None, description="Original natural text snippet corresponding to filter")


class Grouping(BaseModel):
    column: str = Field(description="Column used to group results")
    raw_text: Optional[str] = Field(default=None, description="Original text snippet for grouping")


class Sorting(BaseModel):
    column: str = Field(description="Column to sort by")
    direction: str = Field(default="desc", description="Sort direction: asc or desc")


class ClarificationOption(BaseModel):
    id: str = Field(description="Unique identifier for the option")
    label: str = Field(description="Short human-readable label for the user option button")
    description: Optional[str] = Field(default=None, description="Detailed explanation of this interpretation")


class ClarificationDetails(BaseModel):
    question: str = Field(description="Targeted clarification question to ask the user")
    reason: Optional[str] = Field(default=None, description="Reason why clarification is required")
    options: List[ClarificationOption] = Field(default_factory=list, description="Schema-backed distinct interpretations")
    allow_custom_answer: bool = Field(default=True, description="True if custom text entry is permitted")


class ValidationResult(BaseModel):
    valid: bool = Field(default=True, description="True if all referenced tables/columns exist in Phase 3 schema")
    invalid_fields: List[str] = Field(default_factory=list, description="List of non-existent table/column names referenced")
    warnings: List[str] = Field(default_factory=list, description="Human-readable warning messages")


class IntentAnalysis(BaseModel):
    intent: str = Field(description="Primary intent identifier e.g. count_records, revenue_analysis, ranking_analysis")
    summary: str = Field(description="Human-friendly summary of the AI understanding of the question")
    status: Literal["ready", "clarification_required", "invalid_intent", "max_rounds_exceeded"] = Field(
        default="ready",
        description="Phase 5 Intent Engine status: ready, clarification_required, invalid_intent, or max_rounds_exceeded"
    )
    entities: List[Entity] = Field(default_factory=list)
    metrics: List[Metric] = Field(default_factory=list)
    filters: List[Filter] = Field(default_factory=list)
    grouping: List[Grouping] = Field(default_factory=list)
    sorting: Optional[Sorting] = None
    limit: Optional[int] = Field(default=None, description="Optional result row limit extracted e.g. top 10")
    time_range: Optional[str] = None
    relevant_tables: List[str] = Field(default_factory=list, description="Validated database tables relevant to question")
    relevant_columns: List[str] = Field(default_factory=list, description="Validated database columns relevant to question")
    needs_clarification: bool = Field(default=False, description="True if prompt is ambiguous and requires user choice")
    clarification: Optional[ClarificationDetails] = None
    unsupported_request: bool = Field(default=False, description="True if question is completely unrelated to dataset schema")
    unsupported_reason: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PreviousTurn(BaseModel):
    question: str
    clarification: Optional[str] = None
    intent: Optional[str] = None


class AIAnalysisRequest(BaseModel):
    dataset_id: str = Field(description="UUID of uploaded dataset")
    question: str = Field(min_length=1, max_length=2000, description="User's natural language question")
    previous_turns: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional previous conversation context")
    clarification_round: int = Field(default=1, ge=1, le=10, description="Current clarification round count")


class AIClarificationRequest(BaseModel):
    dataset_id: str = Field(description="UUID of uploaded dataset")
    original_question: str = Field(min_length=1, max_length=2000, description="Original ambiguous question")
    clarification: str = Field(min_length=1, max_length=500, description="User selected or custom clarification")
    previous_turns: Optional[List[Dict[str, Any]]] = Field(default=None)
    clarification_round: int = Field(default=1, ge=1, le=10, description="Current clarification round count")


class AIAnalysisResponse(BaseModel):
    success: bool
    status: Literal["ready", "clarification_required", "invalid_intent", "max_rounds_exceeded", "error"] = Field(
        default="ready",
        description="Overall status of Phase 5 Intent Engine"
    )
    analysis: Optional[IntentAnalysis] = None
    validation_result: Optional[ValidationResult] = None
    clarification_round: int = Field(default=1, description="Clarification round number")
    dataset_id: str
    error: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None


class AIHealthResponse(BaseModel):
    status: str
    configured: bool
    provider: str
    model: str
    message: str


class SQLGenerationRequest(BaseModel):
    dataset_id: str = Field(description="UUID of uploaded dataset")
    question: str = Field(min_length=1, max_length=2000, description="User's original natural language question")
    intent: IntentAnalysis = Field(description="Validated intent analysis from Phase 5 (needs_clarification must be false)")


class SQLGenerationResult(BaseModel):
    sql: str = Field(description="Generated read-only PostgreSQL SELECT statement")
    dialect: str = Field(default="postgresql", description="Target SQL dialect")
    tables_used: List[str] = Field(default_factory=list, description="List of tables referenced in SQL")
    columns_used: List[str] = Field(default_factory=list, description="List of columns referenced in SQL")
    explanation: str = Field(default="", description="Short human-friendly explanation of the generated SQL")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="AI confidence score for the generated SQL")


class SQLGenerationResponse(BaseModel):
    success: bool
    status: Literal["generated", "generation_failed", "generation_rejected", "error"] = Field(
        default="generated",
        description="Text-to-SQL generation status"
    )
    sql_result: Optional[SQLGenerationResult] = None
    dataset_id: str
    question: str
    error: Optional[str] = None
    generation_time_ms: Optional[int] = None


class ValidationErrorDetail(BaseModel):
    code: str = Field(description="Error or warning code e.g. NON_READ_ONLY_QUERY, SYSTEM_SCHEMA_ACCESS")
    message: str = Field(description="Human-readable explanation of validation issue")
    target: Optional[str] = Field(default=None, description="Optional target table, column, or keyword causing the issue")


class SQLValidationRequest(BaseModel):
    dataset_id: str = Field(description="UUID of uploaded dataset")
    sql: str = Field(min_length=1, max_length=10000, description="SQL statement to validate")


class SQLValidationResponse(BaseModel):
    valid: bool = Field(description="True if SQL passed all Phase 7 security & schema checks")
    status: Literal["approved", "rejected", "error"] = Field(
        default="approved",
        description="Phase 7 validation status"
    )
    dialect: str = Field(default="postgresql", description="Target SQL dialect")
    statement_type: str = Field(default="SELECT", description="Parsed SQL statement type e.g. SELECT, WITH")
    tables_used: List[str] = Field(default_factory=list, description="Validated list of tables referenced")
    columns_used: List[str] = Field(default_factory=list, description="Validated list of columns referenced")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings e.g. Cartesian join detected")
    errors: List[ValidationErrorDetail] = Field(default_factory=list, description="List of validation errors preventing approval")
    dataset_id: str
    sql: str
    validation_time_ms: Optional[int] = None


class QueryResultColumn(BaseModel):
    name: str = Field(description="Column name or alias")
    type: str = Field(default="string", description="Inferred column data type e.g. integer, numeric, text, date")


class QueryExecutionRequest(BaseModel):
    dataset_id: str = Field(description="UUID of uploaded dataset")
    sql: str = Field(min_length=1, max_length=10000, description="Validated read-only SQL query to execute")


class QueryExecutionResponse(BaseModel):
    success: bool = Field(description="True if query executed successfully")
    status: Literal["success", "validation_failed", "execution_failed", "timeout", "error"] = Field(
        default="success",
        description="Execution status"
    )
    columns: List[QueryResultColumn] = Field(default_factory=list, description="Column names & types")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="List of result row dictionaries")
    row_count: int = Field(default=0, description="Number of rows returned")
    truncated: bool = Field(default=False, description="True if results were capped at MAX_RESULT_ROWS")
    execution_time_ms: int = Field(default=0, description="Execution duration in milliseconds")
    dataset_id: str
    sql: str
    error: Optional[str] = None


class ChartRecommendation(BaseModel):
    chart_type: Literal["bar", "line", "kpi", "scatter", "none"] = Field(
        default="none",
        description="Recommended visualization type: bar, line, kpi, scatter, or none"
    )
    x_axis: Optional[str] = Field(default=None, description="Recommended column for X axis or categories")
    y_axis: Optional[str] = Field(default=None, description="Recommended column for Y axis or metrics")
    title: Optional[str] = Field(default=None, description="Suggested chart title")
    reason: Optional[str] = Field(default=None, description="Explanation for chart recommendation")


class AIInsightResult(BaseModel):
    summary_insight: str = Field(description="1-2 sentence executive summary of query result findings")
    key_highlights: List[str] = Field(default_factory=list, description="Key data highlights or bullet points")


class FullQueryAnalysisResponse(BaseModel):
    execution: QueryExecutionResponse
    chart: ChartRecommendation
    insight: Optional[AIInsightResult] = None
    validation: Optional[SQLValidationResponse] = None
    query_id: Optional[str] = None
    conversation_id: Optional[str] = None


class QueryHistoryItem(BaseModel):
    id: str
    conversation_id: str
    dataset_id: str
    user_question: str
    intent_json: Optional[Dict[str, Any]] = None
    generated_sql: Optional[str] = None
    execution_status: str = "success"
    row_count: int = 0
    chart_type: str = "none"
    insight_summary: Optional[str] = None
    created_at: str


class QueryHistoryListResponse(BaseModel):
    items: List[QueryHistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class FollowupQueryRequest(BaseModel):
    dataset_id: str = Field(description="UUID of uploaded dataset")
    conversation_id: str = Field(description="Active conversation UUID")
    question: str = Field(min_length=1, max_length=2000, description="Follow-up question")
    previous_intent: Optional[Dict[str, Any]] = Field(default=None, description="Previous structured intent dictionary")
    previous_question: Optional[str] = Field(default=None, description="Previous question text")
    clarification_round: int = Field(default=1, ge=1, le=10, description="Current clarification round count")


class InsightRequest(BaseModel):
    question: str = Field(description="User question")
    columns: List[QueryResultColumn] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    intent: Optional[Dict[str, Any]] = None





