import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from app.services.ai.sql_validator import SQLValidationService, MAX_SQL_LENGTH


@pytest.fixture
def mock_db_and_schema(monkeypatch):
    db_mock = MagicMock(spec=Session)

    mock_schema = {
        "dataset": MagicMock(schema_name="dataset_123"),
        "tables": [
            MagicMock(
                table_name="orders",
                display_name="Orders",
                columns_json=[
                    {"column_name": "order_id", "data_type": "INTEGER"},
                    {"column_name": "customer_id", "data_type": "INTEGER"},
                    {"column_name": "amount", "data_type": "NUMERIC"}
                ]
            ),
            MagicMock(
                table_name="customers",
                display_name="Customers",
                columns_json=[
                    {"column_name": "customer_id", "data_type": "INTEGER"},
                    {"column_name": "name", "data_type": "TEXT"}
                ]
            )
        ]
    }
    monkeypatch.setattr("app.services.schema.SchemaService.get_full_schema", lambda d_id, db: mock_schema)
    return db_mock


def test_valid_select_query_validation(mock_db_and_schema):
    service = SQLValidationService()
    valid_sql = """
    SELECT c.customer_id, c.name, SUM(o.amount) AS total_spending
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.name
    ORDER BY total_spending DESC
    LIMIT 10;
    """

    res = service.validate_sql(
        dataset_id="test-dataset-id",
        sql=valid_sql,
        db=mock_db_and_schema
    )

    assert res.valid is True
    assert res.status == "approved"
    assert res.dialect == "postgresql"
    assert res.statement_type == "SELECT"
    assert set(res.tables_used) == {"customers", "orders"}
    assert len(res.errors) == 0


def test_multi_statement_rejection(mock_db_and_schema):
    service = SQLValidationService()
    multi_sql = "SELECT * FROM customers; DROP TABLE orders;"

    res = service.validate_sql(
        dataset_id="test-dataset-id",
        sql=multi_sql,
        db=mock_db_and_schema
    )

    assert res.valid is False
    assert res.status == "rejected"
    assert any(e.code == "MULTIPLE_STATEMENTS" for e in res.errors)


def test_non_read_only_query_rejection(mock_db_and_schema):
    service = SQLValidationService()
    delete_sql = "DELETE FROM customers WHERE customer_id = 1;"

    res = service.validate_sql(
        dataset_id="test-dataset-id",
        sql=delete_sql,
        db=mock_db_and_schema
    )

    assert res.valid is False
    assert res.status == "rejected"
    assert any(e.code == "NON_READ_ONLY_QUERY" for e in res.errors)


def test_malicious_cte_rejection(mock_db_and_schema):
    service = SQLValidationService()
    cte_sql = "WITH bad_cte AS (DELETE FROM orders RETURNING *) SELECT * FROM bad_cte;"

    res = service.validate_sql(
        dataset_id="test-dataset-id",
        sql=cte_sql,
        db=mock_db_and_schema
    )

    assert res.valid is False
    assert res.status == "rejected"
    assert any(e.code == "NON_READ_ONLY_QUERY" for e in res.errors)


def test_system_schema_access_rejection(mock_db_and_schema):
    service = SQLValidationService()
    sys_sql = "SELECT * FROM information_schema.tables;"

    res = service.validate_sql(
        dataset_id="test-dataset-id",
        sql=sys_sql,
        db=mock_db_and_schema
    )

    assert res.valid is False
    assert res.status == "rejected"
    assert any(e.code == "SYSTEM_SCHEMA_ACCESS" for e in res.errors)


def test_invalid_table_rejection(mock_db_and_schema):
    service = SQLValidationService()
    invalid_tbl_sql = "SELECT * FROM non_existent_table;"

    res = service.validate_sql(
        dataset_id="test-dataset-id",
        sql=invalid_tbl_sql,
        db=mock_db_and_schema
    )

    assert res.valid is False
    assert res.status == "rejected"
    assert any(e.code == "INVALID_TABLE" for e in res.errors)


def test_cartesian_join_warning(mock_db_and_schema):
    service = SQLValidationService()
    cross_sql = "SELECT * FROM customers CROSS JOIN orders;"

    res = service.validate_sql(
        dataset_id="test-dataset-id",
        sql=cross_sql,
        db=mock_db_and_schema
    )

    assert res.valid is True
    assert res.status == "approved"
    assert any("Cartesian" in w for w in res.warnings)


def test_sql_length_limit(mock_db_and_schema):
    service = SQLValidationService()
    long_sql = "SELECT * FROM customers WHERE name = '" + "A" * (MAX_SQL_LENGTH + 10) + "';"

    res = service.validate_sql(
        dataset_id="test-dataset-id",
        sql=long_sql,
        db=mock_db_and_schema
    )

    assert res.valid is False
    assert res.status == "rejected"
    assert any(e.code == "SQL_TOO_LONG" for e in res.errors)
