import time
import re
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from sqlalchemy.orm import Session
import sqlglot
from sqlglot import exp, errors as sqlglot_errors


from app.schemas.ai import (
    SQLValidationResponse,
    ValidationErrorDetail
)
from app.services.schema import SchemaService

logger = logging.getLogger("sqlens.sql_validator")

# Centralized Security & Complexity Constants
MAX_SQL_LENGTH = 4000
MAX_JOINS = 10
MAX_CTES = 5
MAX_UNIONS = 5

FORBIDDEN_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast", "public"}

SAFE_SQL_FUNCTIONS = {
    "count", "sum", "avg", "min", "max", "coalesce", "nullif",
    "greatest", "least", "concat", "upper", "lower", "substring",
    "trim", "ltrim", "rtrim", "replace", "length", "round", "floor",
    "ceil", "ceiling", "abs", "extract", "date_trunc", "now",
    "current_date", "current_timestamp", "current_time", "cast",
    "type", "case", "when", "then", "else", "if", "to_char", "to_date",
    "to_number", "date_part", "age", "first_value", "last_value",
    "lead", "lag", "rank", "dense_rank", "row_number"
}


class SQLValidationService:
    """
    Phase 7 — SQL Validation & Security Engine.
    Parses untrusted SQL queries via SQLGlot AST analysis,
    enforces single-statement execution, read-only AST policies,
    schema isolation, table/column metadata grounding, and complexity limits.
    Does NOT execute SQL against the database.
    """

    def validate_sql(
        self,
        dataset_id: str,
        sql: str,
        db: Session
    ) -> SQLValidationResponse:
        """
        Main entry point for Phase 7 SQL Validation & Security Engine.
        """
        start_time = time.time()
        errors: List[ValidationErrorDetail] = []
        warnings: List[str] = []
        tables_used: List[str] = []
        columns_used: List[str] = []
        statement_type = "UNKNOWN"

        def make_response(valid: bool, status_val: str) -> SQLValidationResponse:
            duration_ms = int((time.time() - start_time) * 1000)
            return SQLValidationResponse(
                valid=valid,
                status=status_val,
                dialect="postgresql",
                statement_type=statement_type,
                tables_used=sorted(list(set(tables_used))),
                columns_used=sorted(list(set(columns_used))),
                warnings=warnings,
                errors=errors,
                dataset_id=dataset_id,
                sql=sql,
                validation_time_ms=duration_ms
            )

        # Step 1: Basic Input Validation
        if not sql or not sql.strip():
            errors.append(ValidationErrorDetail(
                code="SQL_EMPTY",
                message="SQL statement is empty."
            ))
            return make_response(False, "rejected")

        clean_sql = sql.strip()

        if len(clean_sql) > MAX_SQL_LENGTH:
            errors.append(ValidationErrorDetail(
                code="SQL_TOO_LONG",
                message=f"SQL statement exceeds maximum allowed length of {MAX_SQL_LENGTH} characters."
            ))
            return make_response(False, "rejected")

        # Fetch Phase 3 dataset schema metadata
        try:
            full_schema = SchemaService.get_full_schema(dataset_id, db)
            tables_orm = full_schema.get("tables", [])
            dataset_schema_name = full_schema.get("dataset", {}).schema_name if full_schema.get("dataset") else None
        except Exception as e:
            logger.error(f"Error fetching dataset schema for validation {dataset_id}: {e}")
            errors.append(ValidationErrorDetail(
                code="VALIDATION_ERROR",
                message=f"Dataset '{dataset_id}' was not found or schema could not be retrieved."
            ))
            return make_response(False, "error")

        if not tables_orm:
            errors.append(ValidationErrorDetail(
                code="INVALID_SCHEMA",
                message="Dataset schema contains no valid tables."
            ))
            return make_response(False, "rejected")

        # Map actual dataset tables & columns
        schema_tables: Dict[str, Set[str]] = {}
        for t in tables_orm:
            t_name = t.table_name.lower()
            cols = {c.get("column_name", "").lower() for c in (t.columns_json or []) if c.get("column_name")}
            schema_tables[t_name] = cols

        # Step 2: SQLGlot AST Parsing
        try:
            statements = sqlglot.parse(clean_sql, read="postgres")
        except sqlglot_errors.ParseError as pe:

            logger.warning(f"SQLGlot parsing error: {pe}")
            errors.append(ValidationErrorDetail(
                code="SQL_PARSE_ERROR",
                message=f"SQL syntax parse error: {str(pe)}"
            ))
            return make_response(False, "rejected")
        except Exception as e:
            logger.error(f"Unexpected error during SQL parsing: {e}")
            errors.append(ValidationErrorDetail(
                code="SQL_PARSE_ERROR",
                message="Failed to parse SQL statement AST."
            ))
            return make_response(False, "rejected")

        # Step 3: Single Statement Enforcement
        if not statements or len(statements) == 0:
            errors.append(ValidationErrorDetail(
                code="SQL_EMPTY",
                message="No valid SQL statements found."
            ))
            return make_response(False, "rejected")

        if len(statements) > 1:
            errors.append(ValidationErrorDetail(
                code="MULTIPLE_STATEMENTS",
                message="Multiple SQL statements detected. SQLens accepts exactly one statement per request."
            ))
            return make_response(False, "rejected")

        ast = statements[0]
        if ast is None:
            errors.append(ValidationErrorDetail(
                code="SQL_PARSE_ERROR",
                message="Failed to build AST for SQL query."
            ))
            return make_response(False, "rejected")

        # Determine Statement Type
        if isinstance(ast, exp.Select):
            statement_type = "SELECT"
        elif isinstance(ast, exp.Union):
            statement_type = "UNION"
        else:
            statement_type = ast.key.upper() if hasattr(ast, "key") else "UNKNOWN"

        # Step 4: AST Read-Only Policy Enforcement
        forbidden_ast_nodes = (
            exp.Insert, exp.Update, exp.Delete, exp.Drop,
            exp.Create, exp.Alter, exp.Merge, exp.Copy, exp.Command
        )


        if isinstance(ast, forbidden_ast_nodes) or statement_type not in ["SELECT", "UNION", "WITH"]:
            errors.append(ValidationErrorDetail(
                code="NON_READ_ONLY_QUERY",
                message=f"Statement type '{statement_type}' is forbidden. Only read-only SELECT queries are permitted.",
                target=statement_type
            ))
            return make_response(False, "rejected")

        # Check for non-read-only AST nodes nested inside CTEs or subqueries
        for node in ast.walk():
            if isinstance(node, forbidden_ast_nodes):
                forbidden_type = node.key.upper() if hasattr(node, "key") else str(type(node))
                errors.append(ValidationErrorDetail(
                    code="NON_READ_ONLY_QUERY",
                    message=f"Forbidden data manipulation / definition operation '{forbidden_type}' detected in query AST.",
                    target=forbidden_type
                ))
                return make_response(False, "rejected")

        # Step 5: CTE Security Check
        ctes = list(ast.find_all(exp.CTE))
        if len(ctes) > MAX_CTES:
            errors.append(ValidationErrorDetail(
                code="QUERY_TOO_COMPLEX",
                message=f"Query exceeds maximum allowed CTE count of {MAX_CTES}."
            ))
            return make_response(False, "rejected")

        cte_names = {c.alias_or_name.lower() for c in ctes if c.alias_or_name}

        # Step 6: Schema Isolation & System Catalog Protection
        ast_tables = list(ast.find_all(exp.Table))
        for tbl_node in ast_tables:
            tbl_name = tbl_node.name.lower()
            schema_qualifier = tbl_node.db.lower() if tbl_node.db else ""

            # Check if attempting to access forbidden system schemas
            if schema_qualifier in FORBIDDEN_SCHEMAS or tbl_name in FORBIDDEN_SCHEMAS:
                errors.append(ValidationErrorDetail(
                    code="SYSTEM_SCHEMA_ACCESS",
                    message=f"Access to system catalog/schema '{schema_qualifier or tbl_name}' is forbidden.",
                    target=schema_qualifier or tbl_name
                ))

            # Check if attempting cross-dataset schema access
            if schema_qualifier and dataset_schema_name and schema_qualifier != dataset_schema_name.lower():
                if schema_qualifier not in FORBIDDEN_SCHEMAS:
                    errors.append(ValidationErrorDetail(
                        code="CROSS_DATASET_ACCESS",
                        message=f"Cross-dataset schema access to '{schema_qualifier}' is forbidden.",
                        target=schema_qualifier
                    ))

            # Collect referenced tables (ignoring CTE alias names)
            if tbl_name and tbl_name not in cte_names:
                tables_used.append(tbl_name)

        if errors:
            return make_response(False, "rejected")

        # Step 7: Table & Column Grounding Checks
        valid_table_names = set(schema_tables.keys())
        all_dataset_columns = set().union(*schema_tables.values()) if schema_tables else set()

        for tbl_name in set(tables_used):
            if tbl_name not in valid_table_names:
                errors.append(ValidationErrorDetail(
                    code="INVALID_TABLE",
                    message=f"Table '{tbl_name}' does not exist in the active dataset schema.",
                    target=tbl_name
                ))

        if errors:
            return make_response(False, "rejected")

        # Collect referenced columns in AST
        ast_columns = list(ast.find_all(exp.Column))
        for col_node in ast_columns:
            c_name = col_node.name.lower()
            if c_name and c_name != "*":
                columns_used.append(c_name)
                # Verify column exists across dataset tables or CTE aliases
                if c_name not in all_dataset_columns and c_name not in cte_names:
                    # Non-fatal warning if column name might be a SELECT alias
                    warnings.append(f"Referenced column or alias '{c_name}' was not found directly in dataset metadata.")

        # Step 8: Function Safety & Complexity Safeguards
        joins = list(ast.find_all(exp.Join))
        if len(joins) > MAX_JOINS:
            errors.append(ValidationErrorDetail(
                code="QUERY_TOO_COMPLEX",
                message=f"Query exceeds maximum allowed JOIN count of {MAX_JOINS}."
            ))
            return make_response(False, "rejected")

        # Detect Cartesian / Cross Joins
        for j in joins:
            join_kind = j.kind.upper() if j.kind else ""
            if join_kind == "CROSS" or (not j.args.get("on") and not j.args.get("using")):
                warnings.append("Cartesian JOIN detected (JOIN without explicit ON/USING condition).")

        # Function Safety Checks
        funcs = list(ast.find_all(exp.Func))
        for fn in funcs:
            fn_name = fn.key.lower() if hasattr(fn, "key") else ""
            if fn_name and fn_name not in SAFE_SQL_FUNCTIONS:
                warnings.append(f"Function '{fn_name}' is used in query. Ensure it is a standard read-only PostgreSQL operation.")

        # Return Final Validation Result
        return make_response(True, "approved")
