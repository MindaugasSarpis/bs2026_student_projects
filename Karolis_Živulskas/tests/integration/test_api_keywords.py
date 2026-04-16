"""Integration tests for keyword set/entry CRUD endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_create_keyword_set(client: TestClient):
    resp = client.post(
        "/api/v1/keywords/sets",
        json={"name": "Hate Terms EN", "language": "en"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Hate Terms EN"
    assert data["is_active"] is True


def test_duplicate_keyword_set_returns_409(client: TestClient):
    client.post("/api/v1/keywords/sets", json={"name": "Unique Set"})
    resp = client.post("/api/v1/keywords/sets", json={"name": "Unique Set"})
    assert resp.status_code == 409


def test_add_keyword_entry(client: TestClient):
    ks = client.post("/api/v1/keywords/sets", json={"name": "Test Set"}).json()
    set_id = ks["id"]

    resp = client.post(
        f"/api/v1/keywords/sets/{set_id}/entries",
        json={"pattern": "violent speech", "severity": 3, "added_by": "analyst"},
    )
    assert resp.status_code == 201
    entry = resp.json()
    assert entry["pattern"] == "violent speech"
    assert entry["severity"] == 3


def test_list_entries(client: TestClient):
    ks = client.post("/api/v1/keywords/sets", json={"name": "List Test"}).json()
    set_id = ks["id"]

    for i in range(3):
        client.post(
            f"/api/v1/keywords/sets/{set_id}/entries",
            json={"pattern": f"term{i}", "severity": 1},
        )

    resp = client.get(f"/api/v1/keywords/sets/{set_id}/entries")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_delete_entry(client: TestClient):
    ks = client.post("/api/v1/keywords/sets", json={"name": "Del Entry Test"}).json()
    set_id = ks["id"]

    entry = client.post(
        f"/api/v1/keywords/sets/{set_id}/entries",
        json={"pattern": "to_delete", "severity": 1},
    ).json()
    entry_id = entry["id"]

    resp = client.delete(f"/api/v1/keywords/entries/{entry_id}")
    assert resp.status_code == 204
