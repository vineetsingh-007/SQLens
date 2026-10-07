import io

def test_full_dataset_lifecycle(client):
    """Test full workflow: upload -> list -> detail -> preview -> delete."""
    # 1. Upload
    csv_content = "user_id,username,email\n1,alice,alice@example.com\n2,bob,bob@example.com\n"
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))
    
    upload_res = client.post(
        "/api/datasets/upload",
        files={"file": ("users.csv", file_bytes, "text/csv")},
        headers={"X-Session-ID": "test_session_123"}
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]
    table_name = upload_res.json()["tables"][0]

    # 2. List datasets
    list_res = client.get("/api/datasets", headers={"X-Session-ID": "test_session_123"})
    assert list_res.status_code == 200
    datasets = list_res.json()
    assert len(datasets) >= 1
    assert any(d["id"] == dataset_id for d in datasets)

    # 3. Get dataset detail
    detail_res = client.get(f"/api/datasets/{dataset_id}", headers={"X-Session-ID": "test_session_123"})
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["status"] == "READY"
    assert detail["number_of_tables"] == 1
    assert detail["total_rows"] == 2

    # 4. Preview table
    preview_res = client.get(
        f"/api/datasets/{dataset_id}/preview/{table_name}?limit=10",
        headers={"X-Session-ID": "test_session_123"}
    )
    assert preview_res.status_code == 200
    preview = preview_res.json()
    assert len(preview["rows"]) == 2
    assert preview["rows"][0]["username"] == "alice"

    # 5. Delete dataset
    del_res = client.delete(f"/api/datasets/{dataset_id}", headers={"X-Session-ID": "test_session_123"})
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 6. Verify detail returns 404 after deletion
    detail_res_after = client.get(f"/api/datasets/{dataset_id}")
    assert detail_res_after.status_code == 404
