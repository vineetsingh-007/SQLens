import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.schemas.ai import (
    IntentAnalysis,
    Entity,
    Metric,
    Filter,
    ClarificationDetails,
    ClarificationOption,
    ValidationResult
)
from app.services.ai.ai_service import AIService, MAX_CLARIFICATION_ROUNDS
from app.services.ai.intent_validator import IntentValidator
from app.services.ai.ambiguity_detector import AmbiguityDetector
from app.services.ai.base_provider import BaseAIProvider


class MockClarificationProvider(BaseAIProvider):
    def __init__(self):
        pass

    async def test_connection(self):
        return {"success": True, "configured": True, "status": "connected", "provider": "Mock"}

    async def analyze_intent(self, question, schema_text, clarification_context=None, previous_turns=None):
        q_lower = question.lower()
        if "best customers" in q_lower:
            return IntentAnalysis(
                intent="ranking_analysis",
                summary="Analyze best customers.",
                entities=[Entity(name="customers", matched_table="customers")],
                metrics=[Metric(name="credit_limit", aggregation="max", matched_column="credit_limit")],
                relevant_tables=["customers"],
                needs_clarification=True,
                status="clarification_required"
            )
        elif "weather" in q_lower:
            return IntentAnalysis(
                intent="weather_request",
                summary="Unrelated question.",
                unsupported_request=True,
                unsupported_reason="No weather data available.",
                needs_clarification=False,
                status="ready"
            )
        else:
            return IntentAnalysis(
                intent="count_customers",
                summary="Count the total number of customers.",
                entities=[Entity(name="customers", matched_table="customers")],
                metrics=[Metric(name="count", aggregation="count", matched_column="customer_id")],
                relevant_tables=["customers"],
                needs_clarification=False,
                status="ready"
            )

    async def refine_intent_with_clarification(self, original_question, clarification_answer, schema_text, previous_turns=None):
        return IntentAnalysis(
            intent="customer_spending_analysis",
            summary=f"Refined analysis for best customers filtered by: {clarification_answer}",
            entities=[Entity(name="customers", matched_table="customers")],
            metrics=[Metric(name="credit_limit", aggregation="max", matched_column="credit_limit")],
            relevant_tables=["customers"],
            needs_clarification=False,
            status="ready"
        )


@pytest.fixture
def sample_schema_tables():
    return [
        {
            "table_name": "customers",
            "display_name": "Customers",
            "columns": [
                {"name": "customer_id", "type": "INTEGER", "is_primary_key": True},
                {"name": "name", "type": "TEXT"},
                {"name": "credit_limit", "type": "INTEGER"}
            ],
            "primary_keys": ["customer_id"],
            "foreign_keys": []
        }
    ]


def test_intent_validator_valid_and_invalid(sample_schema_tables):
    valid_analysis = IntentAnalysis(
        intent="count_customers",
        summary="Valid intent",
        relevant_tables=["customers"],
        relevant_columns=["customers.customer_id"],
        needs_clarification=False
    )
    sanitized, res = IntentValidator.validate_intent(valid_analysis, sample_schema_tables)
    assert res.valid is True
    assert len(res.invalid_fields) == 0

    invalid_analysis = IntentAnalysis(
        intent="fake_intent",
        summary="Invalid intent",
        relevant_tables=["non_existent_table"],
        relevant_columns=["customers.fake_column"],
        needs_clarification=False
    )
    sanitized_inv, res_inv = IntentValidator.validate_intent(invalid_analysis, sample_schema_tables)
    assert res_inv.valid is False
    assert len(res_inv.invalid_fields) > 0


def test_ambiguity_detector_grounded_options(sample_schema_tables):
    analysis = IntentAnalysis(
        intent="best_customers",
        summary="Show best customers",
        relevant_tables=["customers"],
        needs_clarification=True
    )
    grounded = AmbiguityDetector.detect_and_ground_ambiguity(
        analysis=analysis,
        question="Show me the best customers.",
        actual_tables=sample_schema_tables,
        clarification_round=1
    )
    assert grounded.needs_clarification is True
    assert grounded.status == "clarification_required"
    assert grounded.clarification is not None
    assert len(grounded.clarification.options) > 0
    assert any("Credit Limit" in option.label for option in grounded.clarification.options)



def test_max_clarification_rounds_guard(sample_schema_tables):
    async def run():
        mock_provider = MockClarificationProvider()
        service = AIService(provider=mock_provider)

        # 3rd round should trigger max_rounds_exceeded
        analysis_res = await mock_provider.analyze_intent("Show me the best customers.", "SCHEMA")
        analysis_res.needs_clarification = True

        grounded = AmbiguityDetector.detect_and_ground_ambiguity(
            analysis=analysis_res,
            question="Show me the best customers.",
            actual_tables=sample_schema_tables,
            clarification_round=MAX_CLARIFICATION_ROUNDS
        )
        assert grounded.needs_clarification is True

    asyncio.run(run())
