import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ai import (
    AIAnalysisRequest,
    AIClarificationRequest,
    AIAnalysisResponse,
    AIHealthResponse,
    SQLGenerationRequest,
    SQLGenerationResponse,
    SQLValidationRequest,
    SQLValidationResponse
)
from app.services.ai.ai_service import AIService
from app.services.ai.text_to_sql_service import TextToSQLService
from app.services.ai.sql_validator import SQLValidationService

logger = logging.getLogger("sqlens")
router = APIRouter()
ai_service = AIService()
text_to_sql_service = TextToSQLService()
sql_validator = SQLValidationService()


@router.get("/health", response_model=AIHealthResponse, summary="Check AI Service and Provider Connection")
async def get_ai_health():
    """
    Checks if Gemini provider is configured, API key exists, and connection works.
    """
    return await ai_service.check_health()


@router.post("/analyze", response_model=AIAnalysisResponse, summary="Analyze Natural Language User Question")
async def analyze_question(
    request: AIAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Receives user question and dataset ID, retrieves dataset schema from Phase 3,
    runs intent analysis via Gemini, validates schema references, detects ambiguity, and returns structured analysis.
    """
    try:
        response = await ai_service.analyze_question(
            dataset_id=request.dataset_id,
            question=request.question,
            db=db,
            previous_turns=request.previous_turns,
            clarification_round=request.clarification_round
        )
        if not response.success and "not found" in (response.error or "").lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.error)
        return response
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error analyzing question: {e}")
        return AIAnalysisResponse(
            success=False,
            status="error",
            dataset_id=request.dataset_id,
            error="SQLens couldn't analyze your question right now."
        )


@router.post("/clarify", response_model=AIAnalysisResponse, summary="Submit User Clarification for Ambiguous Question")
async def submit_clarification(
    request: AIClarificationRequest,
    db: Session = Depends(get_db)
):
    """
    Receives user's selected clarification or custom text for an ambiguous question
    and re-runs intent analysis with the clarification context.
    """
    try:
        response = await ai_service.analyze_question(
            dataset_id=request.dataset_id,
            question=request.original_question,
            db=db,
            clarification_context=request.clarification,
            previous_turns=request.previous_turns,
            clarification_round=request.clarification_round + 1
        )
        return response
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing clarification: {e}")
        return AIAnalysisResponse(
            success=False,
            status="error",
            dataset_id=request.dataset_id,
            error="SQLens couldn't process your clarification right now."
        )


@router.post("/generate-sql", response_model=SQLGenerationResponse, summary="Generate PostgreSQL SELECT Statement from Validated Intent")
async def generate_sql(
    request: SQLGenerationRequest,
    db: Session = Depends(get_db)
):
    """
    Phase 6: Receives dataset ID, user question, and Phase 5 validated intent (needs_clarification must be false).
    Generates PostgreSQL SELECT statement using Gemini and runs basic structural & read-only safety checks.
    Does NOT execute the query against the database.
    """
    try:
        response = await text_to_sql_service.generate_sql(
            dataset_id=request.dataset_id,
            question=request.question,
            intent=request.intent,
            db=db
        )
        if not response.success and "not found" in (response.error or "").lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.error)
        return response
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generating SQL: {e}")
        return SQLGenerationResponse(
            success=False,
            status="error",
            dataset_id=request.dataset_id,
            question=request.question,
            error="SQLens couldn't generate SQL for your question right now."
        )


@router.post("/validate-sql", response_model=SQLValidationResponse, summary="Validate & Security Check Generated SQL")
async def validate_sql(
    request: SQLValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Phase 7: Validates untrusted generated SQL using SQLGlot AST analysis.
    Enforces single-statement rules, read-only policies, CTE security, schema isolation,
    system catalog protection, table/column metadata grounding, and complexity limits.
    Does NOT execute the SQL query against the database.
    """
    try:
        response = sql_validator.validate_sql(
            dataset_id=request.dataset_id,
            sql=request.sql,
            db=db
        )
        return response
    except Exception as e:
        logger.error(f"Error validating SQL: {e}")
        return SQLValidationResponse(
            valid=False,
            status="error",
            dataset_id=request.dataset_id,
            sql=request.sql,
            errors=[{"code": "VALIDATION_ERROR", "message": "SQLens encountered an error while validating the SQL statement."}]
        )



