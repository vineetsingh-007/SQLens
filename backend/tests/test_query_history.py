import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.dataset import Dataset, DatasetTable
from app.services.query.query_history_service import QueryHistoryService

client = TestClient(app)

@pytest.fixture
def sample_dataset(db_session: Session):
    dataset = Dataset(
        original_filename="sales_history.csv",
        display_name="Sales History",
        file_type="csv",
        file_size=1024,
        status="READY",
        schema_name="dataset_sales_history_test",
        storage_path="/tmp/test_sales_history.csv"
    )
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)

    table = DatasetTable(
        dataset_id=dataset.id,
        table_name="sales",
        display_name="Sales",
        row_count=100,
        column_count=3,
        columns_json=[
            {"name": "region", "type": "text"},
            {"name": "revenue", "type": "numeric"},
            {"name": "year", "type": "integer"}
        ]
    )
    db_session.add(table)
    db_session.commit()
    return dataset


def test_query_history_crud_and_isolation(db_session: Session, sample_dataset: Dataset):
    # 1. Create history item
    item1 = QueryHistoryService.create_history_item(
        db=db_session,
        dataset_id=sample_dataset.id,
        conversation_id="conv-123",
        user_question="Show revenue by region",
        intent_json={"metric": "revenue", "grouping": ["region"]},
        generated_sql="SELECT region, SUM(revenue) FROM sales GROUP BY region;",
        execution_status="success",
        row_count=5,
        chart_type="bar",
        insight_summary="North generated highest revenue"
    )
    assert item1.id is not None
    assert item1.dataset_id == sample_dataset.id

    # 2. Get history by dataset
    hist = QueryHistoryService.get_history_by_dataset(db=db_session, dataset_id=sample_dataset.id, page=1, page_size=10)
    assert hist.total == 1
    assert hist.items[0].id == item1.id
    assert hist.items[0].user_question == "Show revenue by region"

    # 3. Dataset isolation check with dummy dataset id
    hist_empty = QueryHistoryService.get_history_by_dataset(db=db_session, dataset_id="other-dataset-id", page=1, page_size=10)
    assert hist_empty.total == 0

    # 4. Get single history item
    fetched = QueryHistoryService.get_history_item(db=db_session, dataset_id=sample_dataset.id, query_id=item1.id)
    assert fetched is not None
    assert fetched.user_question == "Show revenue by region"

    # 5. Single item isolation check
    fetched_wrong = QueryHistoryService.get_history_item(db=db_session, dataset_id="other-dataset-id", query_id=item1.id)
    assert fetched_wrong is None

    # 6. API endpoint list history
    resp = client.get(f"/api/query/history/{sample_dataset.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == item1.id

    # 7. Delete history item via API
    del_resp = client.delete(f"/api/query/history/{sample_dataset.id}/{item1.id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Confirm deletion
    hist_after = QueryHistoryService.get_history_by_dataset(db=db_session, dataset_id=sample_dataset.id)
    assert hist_after.total == 0
