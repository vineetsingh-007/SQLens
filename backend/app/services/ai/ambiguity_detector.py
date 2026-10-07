import re
import logging
from typing import List, Dict, Any, Optional
from app.schemas.ai import (
    IntentAnalysis,
    ClarificationDetails,
    ClarificationOption
)

logger = logging.getLogger("sqlens.ambiguity_detector")

AMBIGUOUS_KEYWORDS = {
    "best": "The definition of 'best' is ambiguous.",
    "top": "The ranking metric for 'top' is ambiguous.",
    "performance": "The performance metric is ambiguous.",
    "growth": "The time period or comparison metric for 'growth' is ambiguous.",
    "recent": "The date range for 'recent' is ambiguous.",
    "popular": "The popularity measure (e.g. quantity sold vs number of orders) is ambiguous.",
    "good": "The quality or threshold metric is ambiguous.",
    "successful": "The success metric is ambiguous.",
    "high value": "The value threshold is ambiguous."
}


class AmbiguityDetector:
    """
    Ambiguity Detection Engine combining deterministic schema inspection and LLM analysis
    to ensure SQLens asks for clarification only when questions are genuinely ambiguous,
    generating strictly schema-grounded clarification options.
    """

    @classmethod
    def detect_and_ground_ambiguity(
        cls,
        analysis: IntentAnalysis,
        question: str,
        actual_tables: List[Dict[str, Any]],
        clarification_round: int = 1
    ) -> IntentAnalysis:
        """
        Inspects question and analysis against actual_tables.
        If ambiguity is detected, generates schema-grounded options.
        """
        # If already unsupported, empty dataset, or resolved in refinement round (round > 1 and not needs_clarification)
        if analysis.unsupported_request or analysis.intent == "empty_dataset":
            analysis.needs_clarification = False
            analysis.status = "ready"
            return analysis

        if clarification_round > 1 and not analysis.needs_clarification:
            analysis.status = "ready"
            analysis.clarification = None
            return analysis

        q_lower = question.lower()
        matched_ambiguous_term = None
        ambiguity_reason = None

        for term, reason in AMBIGUOUS_KEYWORDS.items():
            # Match whole words to avoid partial word matches (e.g. 'stopped' matching 'top')
            if re.search(r'\b' + re.escape(term) + r'\b', q_lower):
                matched_ambiguous_term = term
                ambiguity_reason = reason
                break

        # Check if question is straightforward (e.g. explicit count, explicit revenue, explicit filter)
        is_straightforward = False
        if any(kw in q_lower for kw in ["how many", "count of", "revenue", "sales from", "from pune", "where "]):
            if not matched_ambiguous_term:
                is_straightforward = True

        # If LLM flagged clarification OR ambiguous keyword matched AND not straightforward
        should_clarify = (analysis.needs_clarification or matched_ambiguous_term) and not is_straightforward

        if not should_clarify:
            analysis.needs_clarification = False
            analysis.clarification = None
            analysis.status = "ready"
            return analysis


        # Build schema-grounded options
        relevant_table_names = set(analysis.relevant_tables)
        relevant_tables = [t for t in actual_tables if t["table_name"] in relevant_table_names]
        if not relevant_tables:
            relevant_tables = actual_tables

        numeric_columns: List[tuple] = [] # (table_name, col_name, display_name)
        date_columns: List[tuple] = []

        for t in relevant_tables:
            t_name = t["table_name"]
            for col in t.get("columns", []):
                col_name = col["name"]
                c_type = str(col.get("type", "")).lower()
                display = col.get("display_name", col_name)

                if any(k in c_type for k in ["int", "decimal", "numeric", "float", "double", "bigint"]):
                    # Ignore pure ID columns for metric ranking unless no other metric exists
                    if not (col_name.endswith("_id") or col_name == "id"):
                        numeric_columns.append((t_name, col_name, display))
                elif any(k in c_type for k in ["date", "time", "timestamp"]):
                    date_columns.append((t_name, col_name, display))

        grounded_options: List[ClarificationOption] = []

        if matched_ambiguous_term in ["best", "top", "performance", "popular", "high value"]:
            if numeric_columns:
                for idx, (t_name, c_name, display) in enumerate(numeric_columns[:4]):
                    opt_id = f"metric_{c_name}"
                    label_clean = display.replace("_", " ").title()
                    grounded_options.append(
                        ClarificationOption(
                            id=opt_id,
                            label=f"Highest {label_clean}",
                            description=f"Rank {t_name} by {display} ({c_name})"
                        )
                    )

            # Check if order count or item count can be offered
            if not grounded_options:
                grounded_options.append(
                    ClarificationOption(
                        id="most_records",
                        label="Most Frequent Records",
                        description="Rank by highest record count"
                    )
                )

        elif matched_ambiguous_term in ["recent", "growth"]:
            if date_columns:
                grounded_options = [
                    ClarificationOption(id="last_30_days", label="Last 30 Days", description="Filter records from the last 30 days"),
                    ClarificationOption(id="last_3_months", label="Last 3 Months", description="Filter records from the last 3 months"),
                    ClarificationOption(id="this_year", label="This Year", description="Filter records from current calendar year"),
                    ClarificationOption(id="all_time", label="All Time Comparison", description="Analyze overall trend across all available dates")
                ]
            else:
                grounded_options = [
                    ClarificationOption(id="monthly", label="Monthly Trend", description="Group data by month"),
                    ClarificationOption(id="yearly", label="Yearly Comparison", description="Group data by year")
                ]

        # Fallback options from LLM if present and grounded in schema
        if not grounded_options and analysis.clarification and analysis.clarification.options:
            grounded_options = analysis.clarification.options

        # Final default schema-grounded fallback
        if not grounded_options:
            grounded_options = [
                ClarificationOption(id="highest_value", label="Highest Value", description="Rank by primary numeric column"),
                ClarificationOption(id="record_count", label="Highest Count", description="Rank by total record count")
            ]

        clarification_q = f"How would you like to define '{matched_ambiguous_term or 'this query'}'?"
        if analysis.clarification and analysis.clarification.question:
            clarification_q = analysis.clarification.question

        analysis.needs_clarification = True
        analysis.status = "clarification_required"
        analysis.clarification = ClarificationDetails(
            question=clarification_q,
            reason=ambiguity_reason or "Question contains ambiguous terminology.",
            options=grounded_options,
            allow_custom_answer=True
        )

        return analysis
