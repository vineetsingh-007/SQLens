import re
import pandas as pd
import numpy as np
from typing import List, Set, Any

SQL_RESERVED_WORDS = {
    "select", "from", "where", "join", "left", "right", "full", "inner", "outer",
    "on", "group", "by", "order", "having", "limit", "offset", "union", "all",
    "table", "create", "drop", "alter", "insert", "update", "delete", "into",
    "values", "set", "as", "is", "null", "not", "and", "or", "in", "like",
    "between", "exists", "case", "when", "then", "else", "end", "user", "role",
    "grant", "revoke", "primary", "foreign", "key", "references", "check", "default"
}

def sanitize_identifier(raw_name: str, is_table: bool = False) -> str:
    """
    Sanitize raw strings into safe SQL identifiers:
    - Lowercase
    - Replace spaces, hyphens, slashes, and dots with underscores
    - Remove non-alphanumeric characters except underscores
    - Prefix with 'col_' or 'table_' if starts with digit
    - Append suffix if matches SQL reserved keywords
    """
    if not raw_name or not str(raw_name).strip():
        base = "table_data" if is_table else "unnamed_col"
    else:
        name = str(raw_name).strip().lower()
        name = re.sub(r'[\s\-\/\.]+', '_', name)
        name = re.sub(r'[^a-z0-9_]', '', name)
        name = re.sub(r'_+', '_', name).strip('_')
        base = name if name else ("table_data" if is_table else "unnamed_col")

    if base[0].isdigit():
        prefix = "table_" if is_table else "col_"
        base = f"{prefix}{base}"

    if base in SQL_RESERVED_WORDS:
        suffix = "_tbl" if is_table else "_col"
        base = f"{base}{suffix}"

    return base[:63]

def normalize_column_names(raw_columns: List[Any]) -> List[dict]:
    """
    Normalize a list of raw column names and handle duplicate names safely.
    Returns list of dicts: [{"name": str, "display_name": str}]
    """
    seen: Set[str] = set()
    normalized_list = []

    for idx, raw_col in enumerate(raw_columns):
        display_name = str(raw_col).strip() if raw_col is not None and str(raw_col).strip() else f"Column_{idx + 1}"
        clean_name = sanitize_identifier(display_name, is_table=False)

        candidate = clean_name
        counter = 2
        while candidate in seen:
            candidate = f"{clean_name}_{counter}"
            counter += 1

        seen.add(candidate)
        normalized_list.append({
            "name": candidate,
            "display_name": display_name
        })

    return normalized_list

def map_pandas_dtype_to_sql(dtype: Any) -> str:
    """Map pandas dtype to PostgreSQL/SQL data type string."""
    dtype_str = str(dtype).lower()
    if "int" in dtype_str:
        return "INTEGER" if "64" not in dtype_str else "BIGINT"
    elif "float" in dtype_str:
        return "DOUBLE PRECISION"
    elif "bool" in dtype_str:
        return "BOOLEAN"
    elif "datetime" in dtype_str:
        return "TIMESTAMP"
    elif "date" in dtype_str:
        return "DATE"
    else:
        return "TEXT"

def sanitize_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Sanitize DataFrame column names, format data types, and handle missing values safely.
    Returns (cleaned_df, columns_metadata).
    """
    original_cols = list(df.columns)
    col_metadata = normalize_column_names(original_cols)
    
    # Rename DataFrame columns to sanitized SQL identifiers
    new_col_names = [col["name"] for col in col_metadata]
    df.columns = new_col_names
    
    # Enrich metadata with SQL types before object conversion
    for col in col_metadata:
        col_name = col["name"]
        col["type"] = map_pandas_dtype_to_sql(df[col_name].dtype)

    # Convert datetimes to ISO strings for consistent database storage
    for col_name in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col_name]):
            df[col_name] = df[col_name].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Replace NaN, NaT, Inf with None so SQL receives NULL
    df = df.astype(object).where(pd.notnull(df), None)

    return df, col_metadata
