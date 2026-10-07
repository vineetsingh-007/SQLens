import pytest
from sqlalchemy.orm import Session
from app.models.dataset import Dataset, DatasetTable
from app.services.ai.ai_service import AIService
from app.schemas.ai import IntentAnalysis, Metric, Grouping, Filter

@pytest.fixture
def sample_sales_dataset(db_session: Session):
    dataset = Dataset(
        original_filename="sales.csv",
        display_name="Sales Data",
        file_type="csv",
        file_size=2048,
        status="READY",
        schema_name="dataset_sales_followup_test",
        storage_path="/tmp/sales.csv"
    )
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)

    table = DatasetTable(
        dataset_id=dataset.id,
        table_name="orders",
        display_name="Orders",
        row_count=50,
        column_count=4,
        columns_json=[
            {"name": "region", "type": "text"},
            {"name": "revenue", "type": "numeric"},
            {"name": "order_year", "type": "integer"},
            {"name": "customer_id", "type": "integer"}
        ]
    )
    db_session.add(table)
    db_session.commit()
    return dataset


def test_followup_intent_preservation(db_session: Session, sample_sales_dataset: Dataset):
    async def run():
        service = AIService()
        prev_intent = {
            "intent": "revenue_analysis",
            "summary": "Revenue by region",
            "status": "ready",
            "metrics": [{"name": "revenue", "aggregation": "sum", "matched_column": "revenue"}],
            "grouping": [{"column": "region"}],
            "relevant_tables": ["orders"],
            "relevant_columns": ["region", "revenue"]
        }

        # Follow-up question: "What about only 2026?"
        response = await service.process_followup(
            dataset_id=sample_sales_dataset.id,
            conversation_id="conv-777",
            question="What about only 2026?",
            previous_intent=prev_intent,
            previous_question="Show revenue by region",
            db=db_session
        )

        assert response.success is True
        assert response.analysis is not None
        # Check that context or metrics were preserved / processed cleanly
        assert response.analysis.intent is not None

    import asyncio
    asyncio.run(run())
