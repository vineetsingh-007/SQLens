import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.ai import (
    IntentAnalysis,
    AIAnalysisResponse,
    AIHealthResponse,
    ValidationResult,
    Entity,
    Metric,
    Filter,
    Grouping,
    Sorting
)
from app.services.schema import SchemaService, RelationshipService
from app.services.ai.base_provider import BaseAIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.schema_selector import SchemaSelector
from app.services.ai.intent_validator import IntentValidator
from app.services.ai.ambiguity_detector import AmbiguityDetector

logger = logging.getLogger("sqlens.ai_service")

MAX_CLARIFICATION_ROUNDS = 3


class AIService:
    """
    Facade service orchestrating natural-language question understanding, schema selection,
    LLM invocation, intent validation, ambiguity detection, and multi-round clarification refinement.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self.provider = provider or GeminiProvider()

    async def check_health(self) -> AIHealthResponse:
        """Checks AI provider connection and configuration status."""
        result = await self.provider.test_connection()
        return AIHealthResponse(
            status=result.get("status", "unknown"),
            configured=result.get("configured", False),
            provider=result.get("provider", "Gemini"),
            model=settings.GEMINI_MODEL,
            message=result.get("message", "AI provider status checked.")
        )

    def _normalize_question(self, question: str) -> str:
        """Cleans and normalizes user question string."""
        if not question:
            raise ValueError("Question cannot be empty.")
        cleaned = " ".join(question.strip().split())
        if len(cleaned) > 2000:
            raise ValueError("Question exceeds maximum length of 2000 characters.")
        return cleaned

    async def analyze_question(
        self,
        dataset_id: str,
        question: str,
        db: Session,
        clarification_context: Optional[str] = None,
        previous_turns: Optional[List[Dict[str, Any]]] = None,
        clarification_round: int = 1
    ) -> AIAnalysisResponse:
        """
        Full Phase 5 Intent & Clarification Pipeline:
        Dataset verification -> Schema retrieval -> Deterministic schema selection ->
        LLM Analysis or Refinement -> Schema Validation -> Ambiguity Detection & Grounding -> Response.
        """
        start_time = time.time()
        normalized_q = self._normalize_question(question)

        # 1. Fetch full dataset schema from Phase 3
        try:
            full_schema = SchemaService.get_full_schema(dataset_id, db)
        except Exception as e:
            logger.error(f"Error retrieving dataset schema for {dataset_id}: {e}")
            return AIAnalysisResponse(
                success=False,
                status="error",
                dataset_id=dataset_id,
                error=f"Dataset with ID '{dataset_id}' was not found or could not be loaded."
            )

        tables_orm = full_schema.get("tables", [])
        if not tables_orm:
            empty_analysis = IntentAnalysis(
                intent="empty_dataset",
                summary="This dataset doesn't contain usable tables for analysis.",
                status="ready",
                unsupported_request=True,
                unsupported_reason="No database tables found in dataset."
            )
            return AIAnalysisResponse(
                success=True,
                status="ready",
                dataset_id=dataset_id,
                analysis=empty_analysis,
                validation_result=ValidationResult(valid=True, invalid_fields=[], warnings=[])
            )

        tables = [
            {
                "table_name": t.table_name,
                "display_name": t.display_name,
                "row_count": t.row_count,
                "column_count": t.column_count,
                "columns": t.columns_json or [],
                "primary_keys": t.primary_keys_json or [],
                "foreign_keys": t.foreign_keys_json or []
            }
            for t in tables_orm
        ]

        relationships = full_schema.get("relationships", [])
        rel_dicts = [
            {
                "from_table": r.source_table,
                "from_column": r.source_column,
                "to_table": r.target_table,
                "to_column": r.target_column,
                "is_confirmed": r.is_confirmed
            }
            for r in relationships
        ]

        # 2. Select relevant schema deterministically
        schema_selection = SchemaSelector.select_relevant_schema(
            tables_metadata=tables,
            relationships_metadata=rel_dicts,
            question=normalized_q
        )

        schema_text = schema_selection["schema_text"]
        relevant_tables = schema_selection["relevant_table_names"]

        # 3. Check AI Provider availability
        health = await self.provider.test_connection()
        if not health.get("configured"):
            return AIAnalysisResponse(
                success=False,
                status="error",
                dataset_id=dataset_id,
                error="Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env"
            )

        # 4. Invoke LLM for initial analysis OR clarification refinement
        try:
            if clarification_context:
                raw_analysis = await self.provider.refine_intent_with_clarification(
                    original_question=normalized_q,
                    clarification_answer=clarification_context,
                    schema_text=schema_text,
                    previous_turns=previous_turns
                )
            else:
                raw_analysis = await self.provider.analyze_intent(
                    question=normalized_q,
                    schema_text=schema_text,
                    clarification_context=clarification_context,
                    previous_turns=previous_turns
                )
        except Exception as e:
            logger.error(f"AI Provider error during intent analysis: {e}")
            return AIAnalysisResponse(
                success=False,
                status="error",
                dataset_id=dataset_id,
                error=str(e) if "timed out" in str(e) or "configured" in str(e) else "AI service is temporarily unavailable. Please try again."
            )

        # 5. Validate Intent against Phase 3 schema
        validated_analysis, validation_result = IntentValidator.validate_intent(raw_analysis, tables)

        if not validated_analysis.relevant_tables:
            validated_analysis.relevant_tables = relevant_tables

        # 6. Ambiguity Detection & Grounding
        final_analysis = AmbiguityDetector.detect_and_ground_ambiguity(
            analysis=validated_analysis,
            question=normalized_q,
            actual_tables=tables,
            clarification_round=clarification_round
        )

        # 7. Check Max Clarification Rounds Guard
        if clarification_round >= MAX_CLARIFICATION_ROUNDS and final_analysis.needs_clarification:
            logger.warning(f"Clarification round limit ({MAX_CLARIFICATION_ROUNDS}) reached for question: '{question}'")
            final_analysis.needs_clarification = False
            final_analysis.status = "max_rounds_exceeded"
            final_analysis.summary = f"Maximum clarification attempts ({MAX_CLARIFICATION_ROUNDS}) reached. Please rephrase your question to be more specific."
            final_analysis.clarification = None

        response_status = final_analysis.status
        if not validation_result.valid:
            response_status = "invalid_intent"

        duration_ms = int((time.time() - start_time) * 1000)

        debug_info = {
            "processing_time_ms": duration_ms,
            "clarification_round": clarification_round,
            "status": response_status,
            "relevant_tables": final_analysis.relevant_tables,
            "tokens_matched_tables": relevant_tables,
            "validation_warnings": validation_result.warnings,
            "needs_clarification": final_analysis.needs_clarification,
            "confidence": final_analysis.confidence
        }

        return AIAnalysisResponse(
            success=True,
            status=response_status,
            dataset_id=dataset_id,
            analysis=final_analysis,
            validation_result=validation_result,
            clarification_round=clarification_round,
            debug_info=debug_info
        )

    async def process_followup(
        self,
        dataset_id: str,
        conversation_id: str,
        question: str,
        db: Session,
        previous_intent: Optional[Dict[str, Any]] = None,
        previous_question: Optional[str] = None,
        clarification_round: int = 1
    ) -> AIAnalysisResponse:
        """
        Process a follow-up question by merging context from previous_intent with the new question.
        """
        start_time = time.time()
        normalized_q = self._normalize_question(question)

        try:
            full_schema = SchemaService.get_full_schema(dataset_id, db)
        except Exception as e:
            return AIAnalysisResponse(
                success=False,
                status="error",
                dataset_id=dataset_id,
                error=f"Dataset with ID '{dataset_id}' was not found or could not be loaded."
            )

        tables_orm = full_schema.get("tables", [])
        tables = [
            {
                "table_name": t.table_name,
                "display_name": t.display_name,
                "row_count": t.row_count,
                "column_count": t.column_count,
                "columns": t.columns_json or [],
                "primary_keys": t.primary_keys_json or [],
                "foreign_keys": t.foreign_keys_json or []
            }
            for t in tables_orm
        ]

        relationships = full_schema.get("relationships", [])
        rel_dicts = [
            {
                "from_table": r.source_table,
                "from_column": r.source_column,
                "to_table": r.target_table,
                "to_column": r.target_column,
                "is_confirmed": r.is_confirmed
            }
            for r in relationships
        ]

        schema_selection = SchemaSelector.select_relevant_schema(
            tables_metadata=tables,
            relationships_metadata=rel_dicts,
            question=f"{previous_question or ''} {normalized_q}"
        )

        schema_text = schema_selection["schema_text"]
        relevant_tables = schema_selection["relevant_table_names"]

        try:
            raw_analysis = await self.provider.refine_intent_followup(
                question=normalized_q,
                previous_intent=previous_intent,
                previous_question=previous_question,
                schema_text=schema_text
            )
        except Exception as e:
            logger.error(f"Error refining followup intent: {e}")
            return AIAnalysisResponse(
                success=False,
                status="error",
                dataset_id=dataset_id,
                error=str(e)
            )

        validated_analysis, validation_result = IntentValidator.validate_intent(raw_analysis, tables)
        if not validated_analysis.relevant_tables:
            validated_analysis.relevant_tables = relevant_tables

        final_analysis = AmbiguityDetector.detect_and_ground_ambiguity(
            analysis=validated_analysis,
            question=normalized_q,
            actual_tables=tables,
            clarification_round=clarification_round
        )

        response_status = final_analysis.status
        if not validation_result.valid:
            response_status = "invalid_intent"

        duration_ms = int((time.time() - start_time) * 1000)

        return AIAnalysisResponse(
            success=True,
            status=response_status,
            dataset_id=dataset_id,
            analysis=final_analysis,
            validation_result=validation_result,
            clarification_round=clarification_round,
            debug_info={
                "processing_time_ms": duration_ms,
                "conversation_id": conversation_id,
                "status": response_status,
                "confidence": final_analysis.confidence
            }
        )

