import io

def test_schema_discovery_and_statistics(client):
    """Test full Phase 3 pipeline: schema discovery, relationships, statistics, pagination, refresh."""
    # 1. Upload sample CSV with relationships candidate columns
    csv_data = "customer_id,customer_name,city,age\n101,Alice,New York,30\n102,Bob,San Francisco,25\n103,Charlie,,40\n"
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))
    
    upload_res = client.post(
        "/api/datasets/upload",
        files={"file": ("customers.csv", file_bytes, "text/csv")},
        headers={"X-Session-ID": "test_schema_session"}
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]
    table_name = upload_res.json()["tables"][0]

    # 2. Get full schema
    schema_res = client.get(f"/api/datasets/{dataset_id}/schema", headers={"X-Session-ID": "test_schema_session"})
    assert schema_res.status_code == 200
    schema_data = schema_res.json()
    assert schema_data["dataset_id"] == dataset_id
    assert schema_data["number_of_tables"] == 1
    assert len(schema_data["tables"]) == 1
    
    cols = schema_data["tables"][0]["columns_json"]
    col_names = [c["name"] for c in cols]
    assert "customer_id" in col_names
    assert "customer_name" in col_names

    # 3. Get table statistics
    stats_res = client.get(
        f"/api/datasets/{dataset_id}/tables/{table_name}/statistics",
        headers={"X-Session-ID": "test_schema_session"}
    )
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_rows"] == 3
    assert stats["total_columns"] == 4
    # City column has 1 missing value (Charlie's city)
    assert stats["total_missing_values"] >= 1

    col_stats = {c["column_name"]: c for c in stats["columns_stats"]}
    assert col_stats["age"]["min_value"] == 25
    assert col_stats["age"]["max_value"] == 40
    assert col_stats["age"]["avg_value"] == 31.67

    # 4. Test paginated preview
    preview_res = client.get(
        f"/api/datasets/{dataset_id}/preview/{table_name}?page=1&page_size=2",
        headers={"X-Session-ID": "test_schema_session"}
    )
    assert preview_res.status_code == 200
    preview = preview_res.json()
    assert preview["page"] == 1
    assert preview["page_size"] == 2
    assert preview["total_rows"] == 3
    assert preview["total_pages"] == 2
    assert len(preview["rows"]) == 2

    # 5. Test schema refresh
    refresh_res = client.post(
        f"/api/datasets/{dataset_id}/schema/refresh",
        headers={"X-Session-ID": "test_schema_session"}
    )
    assert refresh_res.status_code == 200
    assert refresh_res.json()["number_of_tables"] == 1

    # 6. Test isolated table access failure for invalid table
    invalid_tbl_res = client.get(
        f"/api/datasets/{dataset_id}/tables/non_existent_table",
        headers={"X-Session-ID": "test_schema_session"}
    )
    assert invalid_tbl_res.status_code == 404
