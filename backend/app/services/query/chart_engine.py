import re
import logging
from typing import Dict, Any, List, Optional
from app.schemas.ai import (
    QueryResultColumn,
    ChartRecommendation,
    IntentAnalysis
)

logger = logging.getLogger("sqlens.chart_engine")


class ChartRecommendationEngine:
    """
    Phase 8 — Deterministic Chart Recommendation Engine.
    Inspects query result column data types, row counts, and intent metadata
    to select the best visualization type (Bar, Line, KPI, Scatter, or None).
    """

    @staticmethod
    def recommend_chart(
        columns: List[QueryResultColumn],
        rows: List[Dict[str, Any]],
        intent: Optional[IntentAnalysis] = None
    ) -> ChartRecommendation:
        """
        Pure, deterministic chart recommendation rules.
        """
        row_count = len(rows)
        if not columns or row_count == 0:
            return ChartRecommendation(
                chart_type="none",
                reason="No data rows returned to generate a visualization."
            )

        col_types = {col.name: col.type for col in columns}
        numeric_cols = [c.name for c in columns if c.type in ["numeric", "integer"]]
        date_cols = [c.name for c in columns if c.type in ["date", "timestamp"]]
        text_cols = [c.name for c in columns if c.type in ["text", "string", "boolean"]]

        # Fallback date detection from column names
        if not date_cols:
            for col in columns:
                if any(k in col.name.lower() for k in ["date", "month", "year", "time", "day", "created_at"]):
                    date_cols.append(col.name)

        # Rule 1: Single row + 1 numeric column -> KPI Card
        if row_count == 1 and len(numeric_cols) >= 1:
            metric_col = numeric_cols[0]
            title = intent.summary if intent and intent.summary else f"Total {metric_col.replace('_', ' ').title()}"
            return ChartRecommendation(
                chart_type="kpi",
                y_axis=metric_col,
                title=title,
                reason="Single aggregate row is best displayed as a KPI metric card."
            )

        # Rule 2: Date/Time column + Numeric column -> Line Chart (Time Series)
        if len(date_cols) >= 1 and len(numeric_cols) >= 1:
            x_col = date_cols[0]
            y_col = numeric_cols[0]
            title = f"{y_col.replace('_', ' ').title()} over Time"
            return ChartRecommendation(
                chart_type="line",
                x_axis=x_col,
                y_axis=y_col,
                title=title,
                reason="Time-series date column paired with numeric metric is best displayed as a Line Chart."
            )

        # Rule 3: Category/String column + Numeric column (rows <= 30) -> Bar Chart
        if len(text_cols) >= 1 and len(numeric_cols) >= 1:
            x_col = text_cols[0]
            y_col = numeric_cols[0]

            if row_count <= 30:
                title = f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}"
                return ChartRecommendation(
                    chart_type="bar",
                    x_axis=x_col,
                    y_axis=y_col,
                    title=title,
                    reason="Categorical column paired with numeric metric is best displayed as a Bar Chart."
                )
            else:
                return ChartRecommendation(
                    chart_type="none",
                    reason=f"Result contains {row_count} categories. Table view is clearer than a crowded chart."
                )

        # Rule 4: Two numeric columns -> Scatter / Bar Chart
        if len(numeric_cols) >= 2 and row_count <= 50:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            title = f"{y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}"
            return ChartRecommendation(
                chart_type="bar",
                x_axis=x_col,
                y_axis=y_col,
                title=title,
                reason="Comparison of two numeric metrics."
            )

        # Rule 5: Fallback Table view only
        return ChartRecommendation(
            chart_type="none",
            reason="Result structure is best represented as a data table."
        )
