import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.ai import (
    IntentAnalysis,
    Entity,
    Metric,
    Filter,
    ClarificationDetails,
    ClarificationOption
)
from app.services.ai.ai_service import AIService
from app.services.ai.schema_selector import SchemaSelector
from app.services.ai.intent_validator import IntentValidator
from app.services.ai.base_provider import BaseAIProvider


client = TestClient(app)


class MockAIProvider(BaseAIProvider):
    def __init__(self, mock_response: IntentAnalysis = None, fail_with: Exception = None):
        self.mock_response = mock_response or IntentAnalysis(
            intent="customer_count",
            summary="Count the total number of customers.",
            entities=[Entity(name="customers", matched_table="customers")],
            metrics=[Metric(name="count", aggregation="count", matched_column="customer_id")],
            relevant_tables=["customers"],
            relevant_columns=["customer_id"],
            needs_clarification=False
        )
        self.fail_with = fail_with

    async def test_connection(self):
        if self.fail_with:
            return {"success": False, "configured": False, "status": "error", "message": str(self.fail_with)}
        return {"success": True, "configured": True, "status": "connected", "provider": "Mock", "model": "test-model", "message": "OK"}

    async def analyze_intent(self, question, schema_text, clarification_context=None, previous_turns=None):
        if self.fail_with:
            raise self.fail_with
        if clarification_context:
            return IntentAnalysis(
                intent="customer_spending_analysis",
                summary=f"Analysis for best customers filtered by: {clarification_context}",
                entities=[Entity(name="customers", matched_table="customers")],
                metrics=[Metric(name="spending", aggregation="sum", matched_column="amount")],
                relevant_tables=["customers", "orders"],
                needs_clarification=False
            )
        return self.mock_response

    async def refine_intent_with_clarification(self, original_question, clarification_answer, schema_text, previous_turns=None):
        if self.fail_with:
            raise self.fail_with
        return IntentAnalysis(
            intent="customer_spending_analysis",
            summary=f"Analysis for best customers filtered by: {clarification_answer}",
            entities=[Entity(name="customers", matched_table="customers")],
            metrics=[Metric(name="spending", aggregation="sum", matched_column="amount")],
            relevant_tables=["customers", "orders"],
            needs_clarification=False
        )



@pytest.fixture
def sample_tables():
    return [
        {
            "table_name": "customers",
            "display_name": "Customers",
            "columns": [
                {"name": "customer_id", "type": "INTEGER", "is_primary_key": True},
                {"name": "name", "type": "TEXT"},
                {"name": "city", "type": "TEXT"}
            ],
            "primary_keys": ["customer_id"],
            "foreign_keys": []
        },
        {
            "table_name": "orders",
            "display_name": "Orders",
            "columns": [
                {"name": "order_id", "type": "INTEGER", "is_primary_key": True},
                {"name": "customer_id", "type": "INTEGER", "is_foreign_key": True, "referenced_table": "customers"},
                {"name": "amount", "type": "NUMERIC"}
            ],
            "primary_keys": ["order_id"],
            "foreign_keys": [{"column_name": "customer_id", "referenced_table": "customers", "referenced_column": "customer_id"}]
        }
    ]


@pytest.fixture
def sample_relationships():
    return [
        {
            "from_table": "orders",
            "from_column": "customer_id",
            "to_table": "customers",
            "to_column": "customer_id",
            "is_confirmed": True
        }
    ]


def test_ai_health_endpoint():
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    json_data = response.json()
    assert "status" in json_data
    assert "configured" in json_data


def test_schema_selector(sample_tables, sample_relationships):
    res = SchemaSelector.select_relevant_schema(sample_tables, sample_relationships, "Which customers spent the most?")
    assert "customers" in res["relevant_table_names"]
    assert "orders" in res["relevant_table_names"]
    assert "TABLE: customers" in res["schema_text"]
    assert "TABLE: orders" in res["schema_text"]


import asyncio

def test_hallucinated_schema_detection(sample_tables):
    mock_ai = MockAIProvider(
        mock_response=IntentAnalysis(
            intent="fake_intent",
            summary="Testing hallucination filter",
            entities=[Entity(name="fake", matched_table="non_existent_table")],
            metrics=[Metric(name="fake_metric", matched_column="non_existent_column")],
            relevant_tables=["customers", "non_existent_table"],
            relevant_columns=["customers.customer_id", "customers.fake_col"],
            needs_clarification=False
        )
    )
    sanitized, val_res = IntentValidator.validate_intent(mock_ai.mock_response, sample_tables)

    assert "non_existent_table" not in sanitized.relevant_tables
    assert "customers" in sanitized.relevant_tables
    assert sanitized.entities[0].matched_table is None
    assert sanitized.metrics[0].matched_column is None
    assert "customers.fake_col" not in sanitized.relevant_columns
    assert val_res.valid is False



def test_ambiguity_and_clarification(sample_tables):
    async def run():
        ambiguous_response = IntentAnalysis(
            intent="ambiguous_customers",
            summary="Question is ambiguous",
            needs_clarification=True,
            clarification=ClarificationDetails(
                question="What do you mean by best customers?",
                options=[
                    ClarificationOption(id="spending", label="Highest spending"),
                    ClarificationOption(id="orders", label="Most orders")
                ]
            )
        )
        mock_ai = MockAIProvider(mock_response=ambiguous_response)
        service = AIService(provider=mock_ai)

        res1 = await service.provider.analyze_intent("Show me best customers", "SCHEMA")
        assert res1.needs_clarification is True
        assert len(res1.clarification.options) == 2

        res2 = await service.provider.analyze_intent(
            question="Show me best customers",
            schema_text="SCHEMA",
            clarification_context="Highest spending"
        )
        assert res2.needs_clarification is False
        assert "Highest spending" in res2.summary

    asyncio.run(run())


def test_unsupported_request_handling():
    async def run():
        unsupported = IntentAnalysis(
            intent="weather_request",
            summary="Request is unrelated to dataset",
            unsupported_request=True,
            unsupported_reason="No weather data available in database."
        )
        mock_ai = MockAIProvider(mock_response=unsupported)
        res = await mock_ai.analyze_intent("What is the weather today?", "SCHEMA")
        assert res.unsupported_request is True
        assert res.unsupported_reason is not None

    asyncio.run(run())



def test_invalid_question_validation():
    response = client.post("/api/ai/analyze", json={
        "dataset_id": "00000000-0000-0000-0000-000000000000",
        "question": ""
    })
    assert response.status_code == 422
