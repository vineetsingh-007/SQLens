import logging
from typing import Dict, Any, Optional, List
from app.schemas.ai import AIInsightResult, IntentAnalysis, QueryResultColumn
from app.services.ai.base_provider import BaseAIProvider
from app.services.ai.gemini_provider import GeminiProvider

logger = logging.getLogger("sqlens.insight_service")

MAX_INSIGHT_ROWS = 50


class InsightService:
    """
    Phase 8 — Insight Service.
    Generates natural-language executive summaries and highlights based ONLY on returned query rows.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self.provider = provider or GeminiProvider()

    async def generate_result_insights(
        self,
        question: str,
        columns: List[QueryResultColumn],
        rows: List[Dict[str, Any]],
        intent: Optional[IntentAnalysis] = None
    ) -> AIInsightResult:
        """
        Extracts sample result rows and invokes Gemini to generate data insights.
        """
        if not rows:
            return AIInsightResult(
                summary_insight="The query executed successfully, but returned no matching data rows to analyze.",
                key_highlights=[]
            )

        col_names = [c.name for c in columns]
        intent_summary = intent.summary if intent else f"Query for question: {question}"

        # Slice sample rows to MAX_INSIGHT_ROWS (50) to keep LLM context light
        sample_rows = rows[:MAX_INSIGHT_ROWS]

        try:
            insight_res = await self.provider.generate_insights(
                question=question,
                intent_summary=intent_summary,
                columns=col_names,
                sample_rows=sample_rows
            )
            return insight_res
        except Exception as e:
            logger.error(f"Insight generation fallback triggered due to error: {e}")
            return AIInsightResult(
                summary_insight="Query executed successfully.",
                key_highlights=[]
            )
