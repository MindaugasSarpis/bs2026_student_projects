"""Integration tests for the /api/v1/targets endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_create_and_list_target(client: TestClient):
    payload = {
        "facebook_id": "testpage123",
        "name": "Test Page",
        "target_type": "page",
        "scan_interval_minutes": 30,
        "priority": 2,
    }
    resp = client.post("/api/v1/targets/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["facebook_id"] == "testpage123"
    assert data["name"] == "Test Page"
    assert data["is_active"] is True

    # List
    resp = client.get("/api/v1/targets/")
    assert resp.status_code == 200
    items = resp.json()
    assert any(t["facebook_id"] == "testpage123" for t in items)


def test_duplicate_facebook_id_returns_409(client: TestClient):
    payload = {"facebook_id": "dup123", "name": "Dup", "target_type": "page"}
    client.post("/api/v1/targets/", json=payload)
    resp = client.post("/api/v1/targets/", json=payload)
    assert resp.status_code == 409


def test_get_nonexistent_target_returns_404(client: TestClient):
    resp = client.get("/api/v1/targets/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_deactivate_target(client: TestClient):
    payload = {"facebook_id": "deact123", "name": "To Deactivate", "target_type": "group"}
    created = client.post("/api/v1/targets/", json=payload).json()
    target_id = created["id"]

    resp = client.patch(f"/api/v1/targets/{target_id}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_delete_target(client: TestClient):
    payload = {"facebook_id": "del123", "name": "To Delete", "target_type": "page"}
    created = client.post("/api/v1/targets/", json=payload).json()
    target_id = created["id"]

    resp = client.delete(f"/api/v1/targets/{target_id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/targets/{target_id}")
    assert resp.status_code == 404
