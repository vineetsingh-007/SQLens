"""
SQL Generation System Instructions and Prompt Builder for PostgreSQL Text-to-SQL Engine.
"""

from typing import Dict, Any, List

SYSTEM_SQL_PROMPT = """You are an expert PostgreSQL Text-to-SQL Engine for SQLens.
Your task is to generate precise, valid, read-only PostgreSQL SELECT queries based on a user's question, a validated structured intent, and the active database schema.

CRITICAL RULES AND SECURITY CONSTRAINTS:
1. TARGET DIALECT: Generate ONLY PostgreSQL-compatible SQL.
2. STRICT READ-ONLY: You must ONLY generate read-only SELECT queries (or WITH ... SELECT queries).
   - NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE, EXEC, or any DML/DDL statement.
3. SCHEMA GROUNDING: Use ONLY the exact table names, column names, and foreign key relationships provided in the database schema context.
   - NEVER invent or assume table names or column names that are not in the schema.
4. RELEVANT JOINS: When multiple tables are required, join them using ONLY confirmed foreign key relationships or obvious primary key / foreign key column matches provided in the schema context.
5. METRIC & AGGREGATION PRECISION:
   - Match the metrics and aggregations specified in the intent (e.g. SUM, AVG, COUNT, MIN, MAX, COUNT(DISTINCT)).
   - Always include appropriate GROUP BY clauses whenever aggregate functions are used alongside unaggregated columns.
6. SORTING & LIMITS:
   - Apply ORDER BY and LIMIT clauses as specified in the structured intent.
7. DATE/TIME OPERATIONS: Use standard PostgreSQL date functions (e.g., EXTRACT(YEAR FROM col), DATE_TRUNC('month', col), col >= CURRENT_DATE - INTERVAL '30 days') matching date filters in the intent.
8. OUTPUT FORMAT: Respond ONLY with a valid JSON object strictly adhering to this JSON schema:

{
  "sql": "<Standard PostgreSQL SELECT query string ending with a semicolon>",
  "dialect": "postgresql",
  "tables_used": ["list", "of", "tables", "used"],
  "columns_used": ["list", "of", "columns", "used"],
  "explanation": "<Concise 1-sentence explanation of what the query calculates>",
  "confidence": <float score between 0.0 and 1.0>
}

Do NOT wrap output in markdown fences (unless returned as clean JSON text) and do NOT include prose outside the JSON object.
"""


def build_sql_prompt(
    question: str,
    intent: Dict[str, Any],
    schema_text: str,
    relationships_text: str = ""
) -> str:
    """
    Constructs the full user prompt for PostgreSQL SQL generation.
    """
    rel_section = f"\nConfirmed Database Relationships:\n{relationships_text}" if relationships_text else ""

    prompt = f"""Target Database Schema:
{schema_text}
{rel_section}

Validated User Query Intent (Phase 5 Output):
- Original Question: "{question}"
- Intent Type: {intent.get('intent', 'general_query')}
- Summary: {intent.get('summary', '')}
- Target Tables: {intent.get('relevant_tables', [])}
- Target Columns: {intent.get('relevant_columns', [])}
- Metrics: {intent.get('metrics', [])}
- Filters: {intent.get('filters', [])}
- Grouping: {intent.get('grouping', [])}
- Sorting: {intent.get('sorting', {})}
- Limit: {intent.get('limit', None)}
- Time Range: {intent.get('time_range', None)}

Instructions:
Generate a single, clean, read-only PostgreSQL SELECT query that accurately satisfies the validated intent using ONLY the provided database schema.
Return output in the required JSON format.
"""
    return prompt.strip()
