import os
import io
import pytest
from app.services.ingestion.normalizer import sanitize_identifier, normalize_column_names

def test_sanitize_identifier_rules():
    """Verify SQL identifier sanitization rules."""
    assert sanitize_identifier("Customer Name", is_table=False) == "customer_name"
    assert sanitize_identifier("Order Amount ($)", is_table=False) == "order_amount"
    assert sanitize_identifier("2025 Sales Data", is_table=True) == "table_2025_sales_data"
    assert sanitize_identifier("2025 Sales Data", is_table=False) == "col_2025_sales_data"
    assert sanitize_identifier("select", is_table=False) == "select_col"
    assert sanitize_identifier("group", is_table=True) == "group_tbl"

def test_column_deduplication():
    """Verify duplicate column names are suffixed cleanly."""
    cols = ["Name", "Name", "age", "Name"]
    normalized = normalize_column_names(cols)
    names = [c["name"] for c in normalized]
    assert names == ["name", "name_2", "age", "name_3"]

def test_unsupported_file_extension(client):
    """Verify uploading an unsupported file format returns HTTP 400."""
    file_bytes = io.BytesIO(b"%PDF-1.4 header contents")
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("report.pdf", file_bytes, "application/pdf")}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

def test_empty_csv_upload(client):
    """Verify uploading an empty CSV returns clean error."""
    file_bytes = io.BytesIO(b"")
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("empty.csv", file_bytes, "text/csv")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_csv_upload_success(client):
    """Verify uploading a valid CSV creates dataset and tables."""
    csv_data = "id,Customer Name,Score\n1,Alice,95.5\n2,Bob,88.0\n"
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))
    
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("test_customers.csv", file_bytes, "text/csv")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "READY"
    assert data["number_of_tables"] == 1
    assert "test_customers" in data["tables"]

def test_path_traversal_filename(client):
    """Verify path traversal filenames do not write outside upload directory."""
    csv_data = "id,val\n1,100\n"
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))
    
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("../../malicious.csv", file_bytes, "text/csv")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "malicious.csv"
