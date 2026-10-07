import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.dataset import Dataset, DatasetTable
from app.services.ai.ai_service import AIService
from app.services.ai.text_to_sql_service import TextToSQLService
from app.services.ai.sql_validator import SQLValidationService
from app.services.query.query_execution_service import QueryExecutionService
from app.services.query.query_history_service import QueryHistoryService

client = TestClient(app)

@pytest.fixture
def e2e_dataset(db_session: Session):
    dataset = Dataset(
        original_filename="e2e_transactions.csv",
        display_name="E2E Transactions",
        file_type="csv",
        file_size=4096,
        status="READY",
        schema_name="dataset_e2e_test",
        storage_path="/tmp/e2e_transactions.csv"
    )
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)

    table = DatasetTable(
        dataset_id=dataset.id,
        table_name="transactions",
        display_name="Transactions",
        row_count=120,
        column_count=4,
        columns_json=[
            {"name": "category", "type": "text"},
            {"name": "amount", "type": "numeric"},
            {"name": "year", "type": "integer"},
            {"name": "customer_id", "type": "integer"}
        ]
    )
    db_session.add(table)
    db_session.commit()

    # Create physical SQLite table for test execution
    from sqlalchemy import text
    db_session.execute(text("CREATE TABLE IF NOT EXISTS dataset_e2e_test__transactions (category TEXT, amount REAL, year INT, customer_id INT)"))
    db_session.execute(text("INSERT INTO dataset_e2e_test__transactions VALUES ('Electronics', 1500.0, 2026, 101), ('Clothing', 350.0, 2026, 102)"))
    db_session.commit()
    return dataset


def test_full_end_to_end_pipeline(db_session: Session, e2e_dataset: Dataset):
    """
    Phase 10 Comprehensive End-to-End Integration Test covering:
    Ingestion -> Schema -> Intent -> Text-to-SQL -> Phase 7 Validation -> Execution -> History -> Follow-up -> Safe Re-Run.
    """
    async def run():
        ai_service = AIService()
        text_to_sql = TextToSQLService()
        validator = SQLValidationService()
        executor = QueryExecutionService(validator=validator)

        conv_id = "e2e_conv_1"

        # 1. Turn 1 Question: "Show total amount by category"
        q1 = "Show total amount by category"
        res1 = await ai_service.analyze_question(dataset_id=e2e_dataset.id, question=q1, db=db_session)
        assert res1.success is True
        assert res1.analysis is not None

        sql1_res = await text_to_sql.generate_sql(dataset_id=e2e_dataset.id, question=q1, intent=res1.analysis, db=db_session)
        assert sql1_res.success is True
        sql1 = sql1_res.sql_result.sql
        assert "SELECT" in sql1.upper()

        val1 = validator.validate_sql(dataset_id=e2e_dataset.id, sql=sql1, db=db_session)
        assert val1.valid is True
        assert val1.status == "approved"

        exec1 = executor.execute_query(dataset_id=e2e_dataset.id, sql=sql1, db=db_session)
        assert exec1.success is True

        h1 = QueryHistoryService.create_history_item(
            db=db_session,
            dataset_id=e2e_dataset.id,
            conversation_id=conv_id,
            user_question=q1,
            intent_json=res1.analysis.model_dump(),
            generated_sql=sql1,
            execution_status=exec1.status,
            row_count=exec1.row_count
        )
        assert h1.id is not None

        # 2. Turn 2 Follow-up: "Only for 2026"
        q2 = "Only for 2026"
        res2 = await ai_service.process_followup(
            dataset_id=e2e_dataset.id,
            conversation_id=conv_id,
            question=q2,
            previous_intent=res1.analysis.model_dump(),
            previous_question=q1,
            db=db_session
        )
        assert res2.success is True
        assert res2.analysis is not None

        sql2_res = await text_to_sql.generate_sql(dataset_id=e2e_dataset.id, question=q2, intent=res2.analysis, db=db_session)
        assert sql2_res.success is True

        val2 = validator.validate_sql(dataset_id=e2e_dataset.id, sql=sql2_res.sql_result.sql, db=db_session)
        assert val2.valid is True

        # 3. Query History & Re-Run Isolation Check
        hist = QueryHistoryService.get_history_by_dataset(db=db_session, dataset_id=e2e_dataset.id)
        assert hist.total == 1

        # Re-run stored query with mandatory Phase 7 re-check
        rerun_item = QueryHistoryService.get_history_item(db=db_session, dataset_id=e2e_dataset.id, query_id=h1.id)
        assert rerun_item is not None
        val_rerun = validator.validate_sql(dataset_id=e2e_dataset.id, sql=rerun_item.generated_sql, db=db_session)
        assert val_rerun.valid is True

        exec_rerun = executor.execute_query(dataset_id=e2e_dataset.id, sql=rerun_item.generated_sql, db=db_session)
        assert exec_rerun.success is True

    import asyncio
    asyncio.run(run())
