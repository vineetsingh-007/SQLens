import logging
from typing import List, Dict, Any, Set, Tuple
from app.schemas.ai import IntentAnalysis, ValidationResult

logger = logging.getLogger("sqlens.intent_validator")


class IntentValidator:
    """
    Validation service verifying that AI-generated intent references actual, existing
    Phase 3 database schema attributes (tables, columns, metrics, filters, grouping, sorting).
    Returns structured ValidationResult.
    """

    @classmethod
    def validate_intent(
        cls,
        analysis: IntentAnalysis,
        actual_tables: List[Dict[str, Any]]
    ) -> Tuple[IntentAnalysis, ValidationResult]:
        """
        Validates analysis against actual_tables schema metadata.
        Filters out invalid references and returns updated IntentAnalysis and ValidationResult.
        """
        invalid_fields: List[str] = []
        warnings: List[str] = []

        table_map = {t["table_name"]: t for t in actual_tables}
        column_map: Dict[str, Set[str]] = {}
        all_actual_columns: Set[str] = set()

        for t_name, t_meta in table_map.items():
            cols = {c["name"] for c in t_meta.get("columns", [])}
            column_map[t_name] = cols
            all_actual_columns.update(cols)

        # 1. Validate relevant_tables
        valid_tables = []
        for t in analysis.relevant_tables:
            if t in table_map:
                valid_tables.append(t)
            else:
                invalid_fields.append(f"table:{t}")
                warnings.append(f"Referenced table '{t}' does not exist in dataset schema.")

        analysis.relevant_tables = valid_tables

        # 2. Validate relevant_columns
        valid_columns = []
        for col in analysis.relevant_columns:
            if "." in col:
                t_name, c_name = col.split(".", 1)
                if t_name in column_map and c_name in column_map[t_name]:
                    valid_columns.append(col)
                else:
                    invalid_fields.append(f"column:{col}")
                    warnings.append(f"Referenced column '{col}' does not exist in table '{t_name}'.")
            elif col in all_actual_columns:
                valid_columns.append(col)
            else:
                invalid_fields.append(f"column:{col}")
                warnings.append(f"Referenced column '{col}' does not exist in dataset schema.")

        analysis.relevant_columns = valid_columns

        # 3. Validate entities
        for entity in analysis.entities:
            if entity.matched_table and entity.matched_table not in table_map:
                invalid_fields.append(f"entity_table:{entity.matched_table}")
                warnings.append(f"Entity table '{entity.matched_table}' not found.")
                entity.matched_table = None

            if entity.matched_column and entity.matched_column not in all_actual_columns:
                invalid_fields.append(f"entity_column:{entity.matched_column}")
                warnings.append(f"Entity column '{entity.matched_column}' not found.")
                entity.matched_column = None

        # 4. Validate metrics
        for metric in analysis.metrics:
            if metric.matched_column and metric.matched_column not in all_actual_columns:
                invalid_fields.append(f"metric_column:{metric.matched_column}")
                warnings.append(f"Metric column '{metric.matched_column}' for metric '{metric.name}' not found.")
                metric.matched_column = None

        # 5. Validate filters
        valid_filters = []
        for f in analysis.filters:
            col = f.column
            if "." in col:
                t_name, c_name = col.split(".", 1)
                if t_name in column_map and c_name in column_map[t_name]:
                    valid_filters.append(f)
                else:
                    invalid_fields.append(f"filter_column:{col}")
                    warnings.append(f"Filter column '{col}' not found.")
            elif col in all_actual_columns:
                valid_filters.append(f)
            else:
                invalid_fields.append(f"filter_column:{col}")
                warnings.append(f"Filter column '{col}' not found.")

        analysis.filters = valid_filters

        # 6. Validate grouping
        valid_grouping = []
        for g in analysis.grouping:
            col = g.column
            if "." in col:
                t_name, c_name = col.split(".", 1)
                if t_name in column_map and c_name in column_map[t_name]:
                    valid_grouping.append(g)
                else:
                    invalid_fields.append(f"group_column:{col}")
                    warnings.append(f"Grouping column '{col}' not found.")
            elif col in all_actual_columns:
                valid_grouping.append(g)
            else:
                invalid_fields.append(f"group_column:{col}")
                warnings.append(f"Grouping column '{col}' not found.")

        analysis.grouping = valid_grouping

        # 7. Validate sorting
        if analysis.sorting:
            col = analysis.sorting.column
            if "." in col:
                t_name, c_name = col.split(".", 1)
                if t_name not in column_map or c_name not in column_map[t_name]:
                    invalid_fields.append(f"sort_column:{col}")
                    warnings.append(f"Sort column '{col}' not found.")
                    analysis.sorting = None
            elif col not in all_actual_columns:
                invalid_fields.append(f"sort_column:{col}")
                warnings.append(f"Sort column '{col}' not found.")
                analysis.sorting = None

        validation_result = ValidationResult(
            valid=len(invalid_fields) == 0,
            invalid_fields=invalid_fields,
            warnings=warnings
        )

        return analysis, validation_result
