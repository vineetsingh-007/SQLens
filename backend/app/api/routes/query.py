import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ai import (
    QueryExecutionRequest,
    QueryExecutionResponse,
    FullQueryAnalysisResponse,
    IntentAnalysis,
    QueryHistoryListResponse,
    QueryHistoryItem,
    FollowupQueryRequest,
    AIAnalysisResponse,
    InsightRequest,
    AIInsightResult
)
from app.services.query.query_execution_service import QueryExecutionService
from app.services.query.chart_engine import ChartRecommendationEngine
from app.services.ai.insight_service import InsightService
from app.services.ai.ai_service import AIService
from app.services.query.query_history_service import QueryHistoryService

logger = logging.getLogger("sqlens.query_route")
router = APIRouter()

query_execution_service = QueryExecutionService()
insight_service = InsightService()
ai_service = AIService()


class FullAnalysisRequest(QueryExecutionRequest):
    question: str
    intent: Optional[IntentAnalysis] = None
    conversation_id: Optional[str] = None


@router.post("/execute", response_model=QueryExecutionResponse, summary="Execute Validated PostgreSQL SELECT Query")
async def execute_query(
    request: QueryExecutionRequest,
    db: Session = Depends(get_db)
):
    """
    Phase 8: Safely executes a read-only PostgreSQL query against dataset isolated schema.
    Mandatorily re-runs Phase 7 security validation before executing.
    Enforces 15-second timeout and 1000-row limit safeguards.
    """
    try:
        response = query_execution_service.execute_query(
            dataset_id=request.dataset_id,
            sql=request.sql,
            db=db
        )
        return response
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return QueryExecutionResponse(
            success=False,
            status="error",
            columns=[],
            rows=[],
            row_count=0,
            truncated=False,
            execution_time_ms=0,
            dataset_id=request.dataset_id,
            sql=request.sql,
            error="Database query execution failed."
        )


@router.post("/full-analysis", response_model=FullQueryAnalysisResponse, summary="Execute Query, Recommend Chart, and Generate Insights")
async def execute_full_analysis(
    request: FullAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Orchestrates Phase 8 end-to-end flow & saves interaction to QueryHistory:
    1. Re-validates & executes query.
    2. Deterministically recommends chart type.
    3. Generates AI insight summaries from returned result data.
    4. Records interaction in dataset-isolated QueryHistory.
    """
    conv_id = request.conversation_id or str(uuid.uuid4())

    exec_res = query_execution_service.execute_query(
        dataset_id=request.dataset_id,
        sql=request.sql,
        db=db
    )

    intent_dict = request.intent.model_dump() if request.intent else None

    if not exec_res.success or not exec_res.rows:
        chart_rec = ChartRecommendationEngine.recommend_chart([], [], request.intent)
        
        # Save attempt to history if sql was executed
        history_item = QueryHistoryService.create_history_item(
            db=db,
            dataset_id=request.dataset_id,
            conversation_id=conv_id,
            user_question=request.question,
            intent_json=intent_dict,
            generated_sql=request.sql,
            execution_status=exec_res.status,
            row_count=exec_res.row_count,
            chart_type=chart_rec.chart_type,
            insight_summary=None
        )

        return FullQueryAnalysisResponse(
            execution=exec_res,
            chart=chart_rec,
            insight=None,
            query_id=history_item.id,
            conversation_id=conv_id
        )

    # Recommend chart
    chart_rec = ChartRecommendationEngine.recommend_chart(
        columns=exec_res.columns,
        rows=exec_res.rows,
        intent=request.intent
    )

    # Generate insights based on returned data
    insight_res = await insight_service.generate_result_insights(
        question=request.question,
        columns=exec_res.columns,
        rows=exec_res.rows,
        intent=request.intent
    )

    # Record history
    history_item = QueryHistoryService.create_history_item(
        db=db,
        dataset_id=request.dataset_id,
        conversation_id=conv_id,
        user_question=request.question,
        intent_json=intent_dict,
        generated_sql=request.sql,
        execution_status="success",
        row_count=exec_res.row_count,
        chart_type=chart_rec.chart_type,
        insight_summary=insight_res.summary_insight if insight_res else None
    )

    return FullQueryAnalysisResponse(
        execution=exec_res,
        chart=chart_rec,
        insight=insight_res,
        query_id=history_item.id,
        conversation_id=conv_id
    )


@router.post("/generate-insight", response_model=Optional[AIInsightResult], summary="Asynchronously Generate Data Insights")
async def generate_insight(request: InsightRequest):
    """
    Phase 10: Non-blocking asynchronous AI insight generation.
    Allows query execution & charts to render immediately while AI insights load in parallel.
    """
    try:
        intent_obj = None
        if request.intent:
            try:
                intent_obj = IntentAnalysis.model_validate(request.intent)
            except Exception:
                pass

        return await insight_service.generate_result_insights(
            question=request.question,
            columns=request.columns,
            rows=request.rows,
            intent=intent_obj
        )
    except Exception as e:
        logger.warning(f"Async insight generation error: {e}")
        return None


@router.post("/follow-up", response_model=AIAnalysisResponse, summary="Process Context-Aware Follow-up Question")
async def process_followup(
    request: FollowupQueryRequest,
    db: Session = Depends(get_db)
):
    """
    Phase 9: Refines previous query intent based on user follow-up instruction and context.
    """
    try:
        response = await ai_service.process_followup(
            dataset_id=request.dataset_id,
            conversation_id=request.conversation_id,
            question=request.question,
            db=db,
            previous_intent=request.previous_intent,
            previous_question=request.previous_question,
            clarification_round=request.clarification_round
        )
        return response
    except Exception as e:
        logger.error(f"Error processing follow-up: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process follow-up question: {str(e)}"
        )


@router.get("/history/{dataset_id}", response_model=QueryHistoryListResponse, summary="Get Dataset Query History")
def get_query_history(
    dataset_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Retrieves paginated query history scoped strictly to dataset_id.
    """
    return QueryHistoryService.get_history_by_dataset(
        db=db,
        dataset_id=dataset_id,
        page=page,
        page_size=page_size,
        search=search
    )


@router.get("/history/{dataset_id}/{query_id}", response_model=QueryHistoryItem, summary="Get Single Query History Item")
def get_query_history_item(
    dataset_id: str,
    query_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves a single query history item, enforcing dataset isolation.
    """
    item = QueryHistoryService.get_history_item(db=db, dataset_id=dataset_id, query_id=query_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query history item '{query_id}' not found for dataset '{dataset_id}'."
        )
    return QueryHistoryItem(
        id=item.id,
        conversation_id=item.conversation_id,
        dataset_id=item.dataset_id,
        user_question=item.user_question,
        intent_json=item.intent_json,
        generated_sql=item.generated_sql,
        execution_status=item.execution_status,
        row_count=item.row_count,
        chart_type=item.chart_type,
        insight_summary=item.insight_summary,
        created_at=item.created_at.isoformat()
    )


@router.delete("/history/{dataset_id}/{query_id}", summary="Delete Query History Item")
def delete_query_history_item(
    dataset_id: str,
    query_id: str,
    db: Session = Depends(get_db)
):
    """
    Deletes a single query history item, enforcing dataset isolation.
    Does NOT delete dataset tables or uploaded files.
    """
    deleted = QueryHistoryService.delete_history_item(db=db, dataset_id=dataset_id, query_id=query_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query history item '{query_id}' not found for dataset '{dataset_id}'."
        )
    return {"success": True, "message": f"Query history item '{query_id}' deleted successfully."}


@router.post("/rerun/{dataset_id}/{query_id}", response_model=FullQueryAnalysisResponse, summary="Re-Run Previous Query Safely")
async def rerun_query(
    dataset_id: str,
    query_id: str,
    db: Session = Depends(get_db)
):
    """
    Re-runs a historical query securely:
    1. Retrieves stored SQL.
    2. MANDATORILY re-runs Phase 7 security validation.
    3. Executes safely via Phase 8.
    4. Computes dynamic chart recommendation and AI insights.
    5. Saves a fresh QueryHistory record.
    """
    history_item = QueryHistoryService.get_history_item(db=db, dataset_id=dataset_id, query_id=query_id)
    if not history_item or not history_item.generated_sql:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query history item '{query_id}' with SQL not found for dataset '{dataset_id}'."
        )

    # Mandatory Phase 7 security re-validation & Phase 8 execution
    exec_res = query_execution_service.execute_query(
        dataset_id=dataset_id,
        sql=history_item.generated_sql,
        db=db
    )

    intent_obj = None
    if history_item.intent_json:
        try:
            intent_obj = IntentAnalysis.model_validate(history_item.intent_json)
        except Exception:
            pass

    chart_rec = ChartRecommendationEngine.recommend_chart(
        columns=exec_res.columns,
        rows=exec_res.rows,
        intent=intent_obj
    )

    insight_res = None
    if exec_res.success and exec_res.rows:
        insight_res = await insight_service.generate_result_insights(
            question=history_item.user_question,
            columns=exec_res.columns,
            rows=exec_res.rows,
            intent=intent_obj
        )

    # Save re-run instance in query history
    new_history = QueryHistoryService.create_history_item(
        db=db,
        dataset_id=dataset_id,
        conversation_id=history_item.conversation_id,
        user_question=f"[Re-run] {history_item.user_question}",
        intent_json=history_item.intent_json,
        generated_sql=history_item.generated_sql,
        execution_status=exec_res.status,
        row_count=exec_res.row_count,
        chart_type=chart_rec.chart_type,
        insight_summary=insight_res.summary_insight if insight_res else None
    )

    return FullQueryAnalysisResponse(
        execution=exec_res,
        chart=chart_rec,
        insight=insight_res,
        query_id=new_history.id,
        conversation_id=history_item.conversation_id
    )
