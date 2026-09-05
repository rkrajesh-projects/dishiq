from fastapi.testclient import TestClient


def test_health_check_returns_200_and_valid_json(client: TestClient):
    """
    Test GET /api/health endpoint returns 200 OK and expected JSON status.
    """
    response = client.get("/api/health")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    data = response.json()
    assert data["status"] == "ok"
    assert data["application"] == "DishIQ"
    assert data["version"] == "1.0.0"


def test_health_check_does_not_require_db(client: TestClient):
    """
    Verify health check executes independently without requiring PostgreSQL.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
