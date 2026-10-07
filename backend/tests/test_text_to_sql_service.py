import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.orm import Session

from app.schemas.ai import (
    IntentAnalysis,
    Entity,
    Metric,
    Filter,
    Grouping,
    Sorting,
    SQLGenerationResult,
    SQLGenerationResponse,
    SQLGenerationRequest
)
from app.services.ai.text_to_sql_service import TextToSQLService


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.generate_sql = AsyncMock()
    return provider


@pytest.fixture
def sample_valid_intent():
    return IntentAnalysis(
        intent="ranking_analysis",
        summary="Top 10 customers by total order spending",
        status="ready",
        entities=[Entity(name="customers", matched_table="customers")],
        metrics=[Metric(name="spending", aggregation="SUM", matched_column="amount")],
        grouping=[Grouping(column="customer_id")],
        sorting=Sorting(column="total_spending", direction="desc"),
        limit=10,
        relevant_tables=["customers", "orders"],
        relevant_columns=["customer_id", "amount"],
        needs_clarification=False,
        confidence=0.95
    )


@pytest.fixture
def sample_unresolved_intent():
    return IntentAnalysis(
        intent="ambiguous_query",
        summary="User question is ambiguous",
        status="clarification_required",
        needs_clarification=True,
        confidence=0.5
    )


@pytest.mark.anyio
async def test_unresolved_clarification_guard(mock_provider, sample_unresolved_intent):
    db_mock = MagicMock(spec=Session)
    service = TextToSQLService(provider=mock_provider)

    res = await service.generate_sql(
        dataset_id="test-dataset-id",
        question="Show best customers",
        intent=sample_unresolved_intent,
        db=db_mock
    )

    assert res.success is False
    assert res.status == "generation_rejected"
    assert "clarification is still required" in res.error
    mock_provider.generate_sql.assert_not_called()


@pytest.mark.anyio
async def test_destructive_sql_rejection(mock_provider, sample_valid_intent, monkeypatch):
    db_mock = MagicMock(spec=Session)
    service = TextToSQLService(provider=mock_provider)

    # Mock SchemaService to return usable schema
    mock_schema = {
        "tables": [
            MagicMock(
                table_name="customers",
                display_name="Customers",
                row_count=100,
                column_count=2,
                columns_json=[{"column_name": "customer_id", "data_type": "INTEGER"}],
                primary_keys_json=["customer_id"],
                foreign_keys_json=[]
            )
        ],
        "relationships": []
    }
    monkeypatch.setattr("app.services.schema.SchemaService.get_full_schema", lambda d_id, db: mock_schema)

    # Mock Gemini returning destructive DELETE query
    mock_provider.generate_sql.return_value = SQLGenerationResult(
        sql="DELETE FROM customers WHERE customer_id = 10;",
        dialect="postgresql",
        tables_used=["customers"],
        columns_used=["customer_id"],
        explanation="Deletes customer records.",
        confidence=0.9
    )

    res = await service.generate_sql(
        dataset_id="test-dataset-id",
        question="Delete customer 10",
        intent=sample_valid_intent,
        db=db_mock
    )

    assert res.success is False
    assert res.status == "generation_rejected"
    assert "Only read-only SELECT queries are allowed" in res.error or "DELETE" in res.error


@pytest.mark.anyio
async def test_valid_select_sql_generation(mock_provider, sample_valid_intent, monkeypatch):
    db_mock = MagicMock(spec=Session)
    service = TextToSQLService(provider=mock_provider)

    mock_schema = {
        "tables": [
            MagicMock(
                table_name="orders",
                display_name="Orders",
                row_count=500,
                column_count=3,
                columns_json=[
                    {"column_name": "order_id", "data_type": "INTEGER"},
                    {"column_name": "customer_id", "data_type": "INTEGER"},
                    {"column_name": "amount", "data_type": "NUMERIC"}
                ],
                primary_keys_json=["order_id"],
                foreign_keys_json=[]
            ),
            MagicMock(
                table_name="customers",
                display_name="Customers",
                row_count=100,
                column_count=2,
                columns_json=[
                    {"column_name": "customer_id", "data_type": "INTEGER"},
                    {"column_name": "name", "data_type": "TEXT"}
                ],
                primary_keys_json=["customer_id"],
                foreign_keys_json=[]
            )
        ],
        "relationships": [
            MagicMock(
                source_table="orders",
                source_column="customer_id",
                target_table="customers",
                target_column="customer_id",
                is_confirmed=True
            )
        ]
    }
    monkeypatch.setattr("app.services.schema.SchemaService.get_full_schema", lambda d_id, db: mock_schema)

    expected_sql = """
SELECT c.customer_id, c.name, SUM(o.amount) AS total_spending
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spending DESC
LIMIT 10;
""".strip()

    mock_provider.generate_sql.return_value = SQLGenerationResult(
        sql=expected_sql,
        dialect="postgresql",
        tables_used=["customers", "orders"],
        columns_used=["customers.customer_id", "customers.name", "orders.amount"],
        explanation="Calculates top 10 spending customers using JOIN and SUM aggregation.",
        confidence=0.98
    )

    res = await service.generate_sql(
        dataset_id="test-dataset-id",
        question="Show the top 10 customers by total spending",
        intent=sample_valid_intent,
        db=db_mock
    )

    assert res.success is True
    assert res.status == "generated"
    assert res.sql_result is not None
    assert "SELECT" in res.sql_result.sql
    assert "JOIN orders" in res.sql_result.sql
    assert res.sql_result.dialect == "postgresql"
    assert res.sql_result.tables_used == ["customers", "orders"]
    assert res.sql_result.confidence == 0.98
