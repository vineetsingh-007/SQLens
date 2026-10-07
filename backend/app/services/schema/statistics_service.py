import logging
from typing import Dict, Any, List
from sqlalchemy import Engine, text

logger = logging.getLogger("sqlens.statistics_service")

class StatisticsService:
    @staticmethod
    def calculate_table_statistics(
        schema_name: str,
        table_name: str,
        columns_meta: List[Dict[str, Any]],
        engine: Engine
    ) -> Dict[str, Any]:
        """
        Calculate data quality and type-specific statistics for a single dataset table.
        """
        if engine.name == "postgresql":
            full_ref = f'"{schema_name}"."{table_name}"'
        else:
            full_ref = f'"{schema_name}__{table_name}"'

        columns_stats = []
        total_missing = 0
        total_rows = 0

        try:
            with engine.connect() as conn:
                # 1. Fetch total rows
                total_rows = conn.execute(text(f'SELECT COUNT(*) FROM {full_ref}')).scalar() or 0

                for col in columns_meta:
                    c_name = col["name"]
                    c_type = col.get("type", "Text")
                    display_name = col.get("display_name", c_name)
                    c_ref = f'"{c_name}"'

                    # Fetch null count
                    null_cnt = conn.execute(
                        text(f'SELECT COUNT(*) FROM {full_ref} WHERE {c_ref} IS NULL')
                    ).scalar() or 0

                    non_null_cnt = max(0, total_rows - null_cnt)
                    total_missing += null_cnt

                    min_val = None
                    max_val = None
                    avg_val = None
                    distinct_cnt = None
                    true_cnt = None
                    false_cnt = None
                    sample_vals = []

                    if non_null_cnt > 0:
                        try:
                            # 2. Type-specific aggregations
                            if c_type in ("Integer", "Decimal"):
                                row = conn.execute(
                                    text(f'SELECT MIN({c_ref}), MAX({c_ref}), AVG({c_ref}) FROM {full_ref}')
                                ).fetchone()
                                if row:
                                    min_val = row[0]
                                    max_val = row[1]
                                    avg_val = round(float(row[2]), 2) if row[2] is not None else None

                            elif c_type in ("Date", "DateTime"):
                                row = conn.execute(
                                    text(f'SELECT MIN({c_ref}), MAX({c_ref}) FROM {full_ref}')
                                ).fetchone()
                                if row:
                                    min_val = str(row[0]) if row[0] is not None else None
                                    max_val = str(row[1]) if row[1] is not None else None

                            elif c_type == "Boolean":
                                t_cnt = conn.execute(
                                    text(f'SELECT COUNT(*) FROM {full_ref} WHERE {c_ref} = TRUE OR {c_ref} = 1')
                                ).scalar() or 0
                                true_cnt = t_cnt
                                false_cnt = max(0, non_null_cnt - t_cnt)

                            # Fetch distinct count & sample values for Text / Categories
                            if c_type == "Text":
                                d_cnt = conn.execute(
                                    text(f'SELECT COUNT(DISTINCT {c_ref}) FROM {full_ref}')
                                ).scalar() or 0
                                distinct_cnt = d_cnt

                                samples = conn.execute(
                                    text(f'SELECT DISTINCT {c_ref} FROM {full_ref} WHERE {c_ref} IS NOT NULL LIMIT 3')
                                ).fetchall()
                                sample_vals = [str(s[0]) for s in samples if s[0] is not None]

                        except Exception as stat_err:
                            logger.warning(f"Error calculating stats for column {c_name} in {table_name}: {stat_err}")

                    columns_stats.append({
                        "column_name": c_name,
                        "display_name": display_name,
                        "data_type": c_type,
                        "null_count": null_cnt,
                        "non_null_count": non_null_cnt,
                        "min_value": min_val,
                        "max_value": max_val,
                        "avg_value": avg_val,
                        "distinct_count": distinct_cnt,
                        "true_count": true_cnt,
                        "false_count": false_cnt,
                        "sample_values": sample_vals
                    })

        except Exception as e:
            logger.error(f"Failed to calculate table statistics for {table_name}: {e}")

        return {
            "table_name": table_name,
            "display_name": table_name,
            "total_rows": total_rows,
            "total_columns": len(columns_meta),
            "total_missing_values": total_missing,
            "columns_stats": columns_stats
        }
