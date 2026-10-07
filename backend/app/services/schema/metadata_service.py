import logging
from typing import List, Dict, Any
from sqlalchemy import Engine, inspect, text

logger = logging.getLogger("sqlens.metadata_service")

def normalize_data_type(raw_type: str) -> str:
    """Normalize database data type strings for frontend display."""
    if not raw_type:
        return "Text"
    
    t = str(raw_type).lower()
    if any(k in t for k in ["int", "serial", "bigint", "smallint"]):
        return "Integer"
    elif any(k in t for k in ["float", "double", "numeric", "decimal", "real"]):
        return "Decimal"
    elif any(k in t for k in ["bool"]):
        return "Boolean"
    elif "timestamp" in t or "datetime" in t:
        return "DateTime"
    elif "date" in t:
        return "Date"
    else:
        return "Text"

class MetadataService:
    @staticmethod
    def discover_schema(schema_name: str, engine: Engine) -> List[Dict[str, Any]]:
        """
        Inspect PostgreSQL schema (or SQLite prefixed tables) using SQLAlchemy inspector.
        Returns list of table definitions with columns, PKs, FKs, and row counts.
        """
        inspector = inspect(engine)
        tables_meta = []

        try:
            if engine.name == "postgresql":
                table_names = inspector.get_table_names(schema=schema_name)
            else:
                # SQLite fallback
                all_tables = inspector.get_table_names()
                table_names = [t[len(schema_name)+2:] for t in all_tables if t.startswith(f"{schema_name}__")]

            with engine.connect() as conn:
                for tbl in table_names:
                    # Determine full SQL table reference
                    if engine.name == "postgresql":
                        full_table_ref = f'"{schema_name}"."{tbl}"'
                        cols_info = inspector.get_columns(tbl, schema=schema_name)
                        pk_info = inspector.get_pk_constraint(tbl, schema=schema_name)
                        fk_list = inspector.get_foreign_keys(tbl, schema=schema_name)
                    else:
                        actual_tbl = f"{schema_name}__{tbl}"
                        full_table_ref = f'"{actual_tbl}"'
                        cols_info = inspector.get_columns(actual_tbl)
                        pk_info = inspector.get_pk_constraint(actual_tbl)
                        fk_list = inspector.get_foreign_keys(actual_tbl)

                    # Execute count
                    count_res = conn.execute(text(f'SELECT COUNT(*) FROM {full_table_ref}')).scalar()
                    row_count = count_res if count_res is not None else 0

                    pk_cols = set(pk_info.get("constrained_columns", [])) if pk_info else set()
                    
                    # Map foreign keys
                    fk_map = {}
                    for fk in fk_list:
                        ref_tbl = fk.get("referred_table", "")
                        if engine.name == "sqlite" and ref_tbl.startswith(f"{schema_name}__"):
                            ref_tbl = ref_tbl[len(schema_name)+2:]
                        
                        constrained = fk.get("constrained_columns", [])
                        referred = fk.get("referred_columns", [])
                        for c_col, r_col in zip(constrained, referred):
                            fk_map[c_col] = {
                                "referenced_table": ref_tbl,
                                "referenced_column": r_col
                            }

                    # Build column metadata list
                    columns_json = []
                    for c in cols_info:
                        col_name = c["name"]
                        raw_t = str(c["type"])
                        norm_t = normalize_data_type(raw_t)
                        is_pk = col_name in pk_cols
                        fk_data = fk_map.get(col_name)

                        columns_json.append({
                            "name": col_name,
                            "display_name": c.get("display_name", col_name),
                            "type": norm_t,
                            "raw_type": raw_t,
                            "nullable": c.get("nullable", True),
                            "default_value": str(c.get("default")) if c.get("default") is not None else None,
                            "is_primary_key": is_pk,
                            "is_foreign_key": fk_data is not None,
                            "referenced_table": fk_data["referenced_table"] if fk_data else None,
                            "referenced_column": fk_data["referenced_column"] if fk_data else None
                        })

                    tables_meta.append({
                        "table_name": tbl,
                        "display_name": tbl,
                        "row_count": row_count,
                        "column_count": len(columns_json),
                        "columns_json": columns_json,
                        "primary_keys_json": list(pk_cols),
                        "foreign_keys_json": [
                            {
                                "column": k,
                                "referenced_table": v["referenced_table"],
                                "referenced_column": v["referenced_column"]
                            }
                            for k, v in fk_map.items()
                        ]
                    })

        except Exception as e:
            logger.error(f"Error inspecting database metadata for schema '{schema_name}': {e}")
            raise RuntimeError(f"Metadata extraction failed: {e}")

        return tables_meta
