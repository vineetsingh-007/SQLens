import time
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.schemas.ai import (
    IntentAnalysis,
    SQLGenerationResult,
    SQLGenerationResponse,
    SQLGenerationRequest
)
from app.services.schema import SchemaService
from app.services.ai.base_provider import BaseAIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.schema_selector import SchemaSelector

logger = logging.getLogger("sqlens.text_to_sql_service")

# Forbidden SQL keywords for read-only safety guard
FORBIDDEN_SQL_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bALTER\b", r"\bCREATE\b", r"\bTRUNCATE\b", r"\bGRANT\b",
    r"\bREVOKE\b", r"\bEXEC\b", r"\bEXECUTE\b", r"\bPG_SLEEP\b"
]


class TextToSQLService:
    """
    Dedicated Phase 6 Text-to-SQL Generation Engine.
    Receives dataset_id, question, and Phase 5 validated intent.
    Retrieves Phase 3 database schema context, invokes Gemini,
    runs basic PostgreSQL structural and read-only safety checks,
    and returns SQLGenerationResponse without executing the query.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self.provider = provider or GeminiProvider()

    def _validate_sql_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Runs basic structural and read-only safety checks on the generated SQL string.
        """
        if not sql or not sql.strip():
            return False, "Generated SQL is empty."

        clean_sql = sql.strip()

        # Must start with SELECT or WITH (case-insensitive)
        if not (clean_sql.upper().startswith("SELECT") or clean_sql.upper().startswith("WITH")):
            return False, "Only read-only SELECT queries are allowed."

        # Check for forbidden destructive keywords
        for pattern in FORBIDDEN_SQL_KEYWORDS:
            if re.search(pattern, clean_sql, re.IGNORECASE):
                matched = re.search(pattern, clean_sql, re.IGNORECASE).group(0)
                logger.warning(f"Forbidden keyword '{matched}' detected in generated SQL: {clean_sql}")
                return False, f"Destructive or unsafe command '{matched}' is not permitted. Only read-only SELECT queries are allowed."

        return True, None

    async def generate_sql(
        self,
        dataset_id: str,
        question: str,
        intent: IntentAnalysis,
        db: Session
    ) -> SQLGenerationResponse:
        """
        Main entry point for Phase 6 Text-to-SQL generation.
        """
        start_time = time.time()

        # 1. Input Guard: Clarification Check
        if intent.needs_clarification:
            return SQLGenerationResponse(
                success=False,
                status="generation_rejected",
                dataset_id=dataset_id,
                question=question,
                error="Cannot generate SQL: user clarification is still required for this question."
            )

        if intent.status in ["clarification_required", "invalid_intent"]:
            return SQLGenerationResponse(
                success=False,
                status="generation_rejected",
                dataset_id=dataset_id,
                question=question,
                error=f"Cannot generate SQL: Intent status is '{intent.status}'."
            )

        # 2. Fetch full dataset schema from Phase 3
        try:
            full_schema = SchemaService.get_full_schema(dataset_id, db)
        except Exception as e:
            logger.error(f"Error retrieving schema for dataset {dataset_id}: {e}")
            return SQLGenerationResponse(
                success=False,
                status="error",
                dataset_id=dataset_id,
                question=question,
                error=f"Dataset '{dataset_id}' was not found or could not be loaded."
            )

        tables_orm = full_schema.get("tables", [])
        if not tables_orm:
            return SQLGenerationResponse(
                success=False,
                status="generation_failed",
                dataset_id=dataset_id,
                question=question,
                error="No database tables found in this dataset to construct SQL."
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

        # 3. Select relevant schema and build context
        schema_selection = SchemaSelector.select_relevant_schema(
            tables_metadata=tables,
            relationships_metadata=rel_dicts,
            question=question
        )

        schema_text = schema_selection["schema_text"]

        # Build foreign keys relationship string text
        rel_lines = []
        for r in rel_dicts:
            rel_lines.append(f"{r['from_table']}.{r['from_column']} -> {r['to_table']}.{r['to_column']}")
        relationships_text = "\n".join(rel_lines)

        intent_dict = intent.model_dump()

        # 4. Invoke LLM for SQL generation
        try:
            sql_result = await self.provider.generate_sql(
                question=question,
                intent=intent_dict,
                schema_text=schema_text,
                relationships_text=relationships_text
            )
        except Exception as e:
            logger.error(f"Error calling Gemini for SQL generation: {e}")
            return SQLGenerationResponse(
                success=False,
                status="generation_failed",
                dataset_id=dataset_id,
                question=question,
                error=str(e) if "timed out" in str(e) or "configured" in str(e) else "SQL generation service is temporarily unavailable."
            )

        # 5. Basic SQL Structural & Read-Only Safety Check
        is_safe, safety_err = self._validate_sql_safety(sql_result.sql)
        duration_ms = int((time.time() - start_time) * 1000)

        if not is_safe:
            return SQLGenerationResponse(
                success=False,
                status="generation_rejected",
                dataset_id=dataset_id,
                question=question,
                error=safety_err,
                generation_time_ms=duration_ms
            )

        # 6. Return Clean Success Response (SQL is generated but NOT executed)
        return SQLGenerationResponse(
            success=True,
            status="generated",
            sql_result=sql_result,
            dataset_id=dataset_id,
            question=question,
            generation_time_ms=duration_ms
        )
