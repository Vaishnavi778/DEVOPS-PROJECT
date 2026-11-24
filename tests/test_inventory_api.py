import json
from decimal import Decimal

from fastapi.testclient import TestClient

from inventory_api.main import app


def test_create_and_list_items(client):
    response = client.post(
        "/items",
        json={"sku": "CHAIR-001", "name": "Desk chair", "quantity": 12, "unit_price": "89.99"},
    )

    assert response.status_code == 201
    assert response.json()["sku"] == "CHAIR-001"
    assert Decimal(response.json()["unit_price"]) == Decimal("89.99")
    assert client.get("/items").json()[0]["name"] == "Desk chair"


def test_duplicate_sku_returns_conflict(client):
    item = {"sku": "PEN-001", "name": "Pen", "quantity": 5, "unit_price": "1.25"}
    assert client.post("/items", json=item).status_code == 201

    response = client.post("/items", json=item)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_rejects_negative_quantity(client):
    response = client.post(
        "/items",
        json={"sku": "BOX-001", "name": "Box", "quantity": -1, "unit_price": "2.00"},
    )

    assert response.status_code == 422


def test_update_and_delete_item(client):
    created = client.post(
        "/items",
        json={"sku": "BOOK-001", "name": "Notebook", "quantity": 4, "unit_price": "3.50"},
    ).json()
    replacement = {
        "sku": "BOOK-001",
        "name": "Notebook",
        "quantity": 8,
        "unit_price": "3.50",
    }

    assert client.put(f"/items/{created['id']}", json=replacement).json()["quantity"] == 8
    assert client.delete(f"/items/{created['id']}").status_code == 204
    assert client.get(f"/items/{created['id']}").status_code == 404


def test_health_and_metrics_endpoints(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}
    assert client.get("/metrics").status_code == 200


def test_inventory_routes_require_a_valid_api_key(client):
    with TestClient(app) as unauthenticated_client:
        missing_key_response = unauthenticated_client.get("/items")
        invalid_key_response = unauthenticated_client.get(
            "/items",
            headers={"X-API-Key": "not-the-test-key"},
        )

    assert missing_key_response.status_code == 401
    assert invalid_key_response.status_code == 401
    assert client.get("/items").status_code == 200


def test_readiness_fails_when_api_key_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("API_KEY")

    response = client.get("/health/ready")

    assert response.status_code == 503


def test_request_logs_are_structured_and_do_not_include_payload(client, caplog):
    with caplog.at_level("INFO", logger="inventory_api.requests"):
        client.post(
            "/items",
            json={
                "sku": "LOG-001",
                "name": "Private sample",
                "quantity": 1,
                "unit_price": "1.00",
            },
        )

    record = next(record for record in caplog.records if record.name == "inventory_api.requests")
    log_data = json.loads(record.message)
    assert log_data["method"] == "POST"
    assert log_data["status_code"] == 201
    assert "Private sample" not in record.message
