import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.orm import Session

from app.schemas.ai import (
    QueryResultColumn,
    IntentAnalysis
)
from app.services.query.query_execution_service import QueryExecutionService, MAX_RESULT_ROWS
from app.services.query.chart_engine import ChartRecommendationEngine
from app.services.ai.insight_service import InsightService


@pytest.fixture
def mock_db_and_schema(monkeypatch):
    db_mock = MagicMock(spec=Session)

    mock_schema = {
        "dataset": MagicMock(schema_name="ds_test123"),
        "tables": [
            MagicMock(
                table_name="products",
                columns_json=[
                    {"column_name": "product_name", "data_type": "TEXT"},
                    {"column_name": "revenue", "data_type": "NUMERIC"}
                ]
            )
        ]
    }
    monkeypatch.setattr("app.services.schema.SchemaService.get_full_schema", lambda d_id, db: mock_schema)
    return db_mock


def test_security_bypass_attempt_rejection(mock_db_and_schema):
    """
    Verify that unvalidated/dangerous SQL passed directly to execute_query is rejected by Phase 7 security guard.
    """
    service = QueryExecutionService()
    dangerous_sql = "DELETE FROM products WHERE product_id = 1;"

    res = service.execute_query(
        dataset_id="test-dataset-id",
        sql=dangerous_sql,
        db=mock_db_and_schema
    )

    assert res.success is False
    assert res.status == "validation_failed"
    assert "Security Violation" in res.error
    assert res.row_count == 0


def test_value_normalization():
    service = QueryExecutionService()

    assert service._normalize_value(Decimal("123.45")) == 123.45
    assert service._normalize_value(Decimal("100.00")) == 100
    assert service._normalize_value(date(2026, 9, 19)) == "2026-09-19"
    assert service._normalize_value(datetime(2026, 9, 19, 12, 0, 0)) == "2026-09-19T12:00:00"
    assert service._normalize_value(None) is None


def test_chart_recommendation_bar_chart():
    cols = [
        QueryResultColumn(name="product_name", type="text"),
        QueryResultColumn(name="revenue", type="numeric")
    ]
    rows = [
        {"product_name": "Laptop", "revenue": 1000},
        {"product_name": "Phone", "revenue": 500}
    ]

    rec = ChartRecommendationEngine.recommend_chart(cols, rows)
    assert rec.chart_type == "bar"
    assert rec.x_axis == "product_name"
    assert rec.y_axis == "revenue"


def test_chart_recommendation_line_chart():
    cols = [
        QueryResultColumn(name="order_date", type="date"),
        QueryResultColumn(name="sales", type="numeric")
    ]
    rows = [
        {"order_date": "2026-01-01", "sales": 100},
        {"order_date": "2026-02-01", "sales": 200}
    ]

    rec = ChartRecommendationEngine.recommend_chart(cols, rows)
    assert rec.chart_type == "line"
    assert rec.x_axis == "order_date"
    assert rec.y_axis == "sales"


def test_chart_recommendation_kpi():
    cols = [QueryResultColumn(name="total_revenue", type="numeric")]
    rows = [{"total_revenue": 50000}]

    rec = ChartRecommendationEngine.recommend_chart(cols, rows)
    assert rec.chart_type == "kpi"
    assert rec.y_axis == "total_revenue"


@pytest.mark.anyio
async def test_insight_service_empty_rows():
    service = InsightService()
    res = await service.generate_result_insights(
        question="Show sales",
        columns=[QueryResultColumn(name="sales", type="numeric")],
        rows=[]
    )
    assert "no matching data" in res.summary_insight.lower()
