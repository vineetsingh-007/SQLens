def test_health_check_endpoint(client):
    """Test GET /api/health returns 200 and expected status JSON."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert data["service"] == "SQLens backend"
    assert "database" in data
