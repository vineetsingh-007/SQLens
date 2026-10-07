import time
import re
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import sqlglot
from sqlglot import exp

from app.core.database import engine
from app.schemas.ai import (
    QueryExecutionResponse,
    QueryResultColumn
)
from app.services.schema import SchemaService
from app.services.ai.sql_validator import SQLValidationService

logger = logging.getLogger("sqlens.query_execution_service")

QUERY_TIMEOUT_SECONDS = 15
MAX_RESULT_ROWS = 1000


class QueryExecutionService:
    """
    Phase 8 — Query Execution Service.
    Enforces Phase 7 re-validation, timeout limits, result row truncation (1000 rows),
    and JSON data normalization for safe database execution.
    """

    def __init__(self, validator: Optional[SQLValidationService] = None):
        self.validator = validator or SQLValidationService()

    def _adapt_sql_for_engine(
        self,
        sql: str,
        dataset_schema_name: str,
        table_names: List[str]
    ) -> str:
        """
        If PostgreSQL: query uses un-prefixed table names with search_path.
        If SQLite fallback: adapts table names in AST to dataset_schema_name__table_name.
        """
        if engine.name == "postgresql":
            return sql

        # SQLite fallback table mapping
        try:
            ast = sqlglot.parse_one(sql, read="postgres")
            valid_tables = set(table_names)
            for tbl_node in ast.find_all(exp.Table):
                if tbl_node.name.lower() in valid_tables:
                    prefix = f"{dataset_schema_name}__" if dataset_schema_name else ""
                    tbl_node.set("this", exp.to_identifier(f"{prefix}{tbl_node.name.lower()}"))
            return ast.sql(dialect="sqlite")
        except Exception as err:
            logger.warning(f"AST table rewrite fallback for SQLite: {err}")
            adapted = sql
            prefix = f"{dataset_schema_name}__" if dataset_schema_name else ""
            for t in table_names:
                adapted = re.sub(rf'\b{t}\b', f'"{prefix}{t}"', adapted, flags=re.IGNORECASE)
            return adapted

    def _normalize_value(self, val: Any) -> Any:
        """Converts database values into JSON-safe representations."""
        if val is None:
            return None
        elif isinstance(val, Decimal):
            return float(val) if val % 1 != 0 else int(val)
        elif isinstance(val, (datetime, date)):
            return val.isoformat()
        elif isinstance(val, (bytes, bytearray)):
            return f"<binary {len(val)} bytes>"
        elif hasattr(val, "isoformat"):
            return val.isoformat()
        return val

    def _infer_column_type(self, col_name: str, sample_rows: List[Dict[str, Any]]) -> str:
        """Infers a friendly data type label for a column based on sample row values."""
        for row in sample_rows:
            val = row.get(col_name)
            if val is not None:
                if isinstance(val, bool):
                    return "boolean"
                elif isinstance(val, int):
                    return "integer"
                elif isinstance(val, float):
                    return "numeric"
                elif isinstance(val, str):
                    if re.match(r"^\d{4}-\d{2}-\d{2}", val):
                        return "date"
                    return "text"
        return "text"

    def execute_query(
        self,
        dataset_id: str,
        sql: str,
        db: Session
    ) -> QueryExecutionResponse:
        """
        Re-validates SQL with Phase 7 and executes the approved query safely.
        """
        start_time = time.time()

        # Step 1: MANDATORY Phase 7 Security Re-Validation
        val_response = self.validator.validate_sql(dataset_id=dataset_id, sql=sql, db=db)
        if not val_response.valid:
            err_msg = val_response.errors[0].message if val_response.errors else "Query failed security validation."
            logger.warning(f"Security validation failed for execution attempt on dataset {dataset_id}: {err_msg}")
            return QueryExecutionResponse(
                success=False,
                status="validation_failed",
                columns=[],
                rows=[],
                row_count=0,
                truncated=False,
                execution_time_ms=int((time.time() - start_time) * 1000),
                dataset_id=dataset_id,
                sql=sql,
                error=f"Security Violation: {err_msg}"
            )

        # Step 2: Retrieve dataset schema & table names
        try:
            full_schema = SchemaService.get_full_schema(dataset_id, db)
            dataset_schema_name = full_schema.get("schema_name", "")
            if not dataset_schema_name:
                dataset_obj = full_schema.get("dataset")
                dataset_schema_name = getattr(dataset_obj, "schema_name", "") if dataset_obj else ""
                if not dataset_schema_name and isinstance(dataset_obj, dict):
                    dataset_schema_name = dataset_obj.get("schema_name", "")
            table_names = [t.table_name.lower() for t in full_schema.get("tables", [])]
        except Exception as e:

            logger.error(f"Failed to fetch dataset metadata for {dataset_id}: {e}")
            return QueryExecutionResponse(
                success=False,
                status="error",
                columns=[],
                rows=[],
                row_count=0,
                truncated=False,
                execution_time_ms=int((time.time() - start_time) * 1000),
                dataset_id=dataset_id,
                sql=sql,
                error=f"Dataset with ID '{dataset_id}' not found."
            )

        # Adapt SQL query for PostgreSQL schema search_path vs SQLite table names
        exec_sql = self._adapt_sql_for_engine(
            sql=sql,
            dataset_schema_name=dataset_schema_name,
            table_names=table_names
        )

        # Step 3: Execute query against database with timeout & row limit
        try:
            with engine.connect() as conn:
                if engine.name == "postgresql":
                    # Set PostgreSQL schema search path
                    conn.execute(text(f'SET search_path TO "{dataset_schema_name}", public;'))
                    conn.execute(text(f'SET statement_timeout = {QUERY_TIMEOUT_SECONDS * 1000};'))

                result = conn.execute(text(exec_sql))
                raw_columns = list(result.keys())

                # Fetch rows up to MAX_RESULT_ROWS + 1 to check for truncation
                raw_rows = result.fetchmany(MAX_RESULT_ROWS + 1)

                truncated = False
                if len(raw_rows) > MAX_RESULT_ROWS:
                    truncated = True
                    raw_rows = raw_rows[:MAX_RESULT_ROWS]

                # Step 4: JSON Normalization
                normalized_rows: List[Dict[str, Any]] = []
                for row_tuple in raw_rows:
                    row_dict = {}
                    for col_name, raw_val in zip(raw_columns, row_tuple):
                        row_dict[col_name] = self._normalize_value(raw_val)
                    normalized_rows.append(row_dict)

                # Infer Column Metadata
                columns_meta: List[QueryResultColumn] = [
                    QueryResultColumn(
                        name=col,
                        type=self._infer_column_type(col, normalized_rows)
                    )
                    for col in raw_columns
                ]

                duration_ms = int((time.time() - start_time) * 1000)

                return QueryExecutionResponse(
                    success=True,
                    status="success",
                    columns=columns_meta,
                    rows=normalized_rows,
                    row_count=len(normalized_rows),
                    truncated=truncated,
                    execution_time_ms=duration_ms,
                    dataset_id=dataset_id,
                    sql=sql
                )

        except Exception as exec_err:
            duration_ms = int((time.time() - start_time) * 1000)
            err_str = str(exec_err)
            logger.error(f"Database query execution error for dataset {dataset_id}: {err_str}")

            if "timeout" in err_str.lower() or "canceled" in err_str.lower():
                return QueryExecutionResponse(
                    success=False,
                    status="timeout",
                    columns=[],
                    rows=[],
                    row_count=0,
                    truncated=False,
                    execution_time_ms=duration_ms,
                    dataset_id=dataset_id,
                    sql=sql,
                    error=f"Query execution timed out after {QUERY_TIMEOUT_SECONDS} seconds. Please narrow your query filter conditions."
                )

            return QueryExecutionResponse(
                success=False,
                status="execution_failed",
                columns=[],
                rows=[],
                row_count=0,
                truncated=False,
                execution_time_ms=duration_ms,
                dataset_id=dataset_id,
                sql=sql,
                error="Database query execution failed. Please verify column parameters and query structure."
            )
