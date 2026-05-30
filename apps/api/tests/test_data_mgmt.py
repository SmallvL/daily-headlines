"""Tests for the data management module."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(test_db):  # noqa: F811 — uses conftest test_db
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def admin_token(client):
    """Login as admin and return token."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


@pytest.fixture()
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


class TestStorageStats:

    def test_get_stats(self, client, auth_headers):
        resp = client.get("/api/data-mgmt/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "db_size_mb" in data
        assert "tables" in data
        assert "total_records" in data
        assert isinstance(data["tables"], list)
        table_names = [t["table_name"] for t in data["tables"]]
        assert "users" in table_names

    def test_stats_requires_auth(self, client):
        resp = client.get("/api/data-mgmt/stats")
        assert resp.status_code in (401, 403)


class TestRetentionConfigs:

    def test_list_configs(self, client, auth_headers):
        resp = client.get("/api/data-mgmt/retention-configs", headers=auth_headers)
        assert resp.status_code == 200
        configs = resp.json()["data"]
        assert isinstance(configs, list)
        assert len(configs) >= 4

        feed_cfg = next((c for c in configs if c["table_name"] == "feed_items"), None)
        assert feed_cfg is not None
        assert feed_cfg["max_age_days"] == 90
        assert feed_cfg["keep_saved"] is True

    def test_update_config(self, client, auth_headers):
        resp = client.put(
            "/api/data-mgmt/retention-configs/feed_items",
            headers=auth_headers,
            json={"max_age_days": 60},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["max_age_days"] == 60
        assert data["table_name"] == "feed_items"

    def test_update_nonexistent_config(self, client, auth_headers):
        resp = client.put(
            "/api/data-mgmt/retention-configs/nonexistent_table",
            headers=auth_headers,
            json={"max_age_days": 30},
        )
        assert resp.status_code == 404


class TestPurge:

    def test_preview_purge(self, client, auth_headers):
        resp = client.post("/api/data-mgmt/purge/preview", headers=auth_headers)
        assert resp.status_code == 200
        previews = resp.json()["data"]
        assert isinstance(previews, list)
        assert len(previews) == 0

    def test_execute_purge_empty(self, client, auth_headers):
        resp = client.post("/api/data-mgmt/purge/execute", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_deleted"] == 0
        assert isinstance(data["results"], list)

    def test_preview_purge_specific_table(self, client, auth_headers):
        resp = client.post(
            "/api/data-mgmt/purge/preview?table_name=feed_items",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestExport:

    def test_export_json(self, client, auth_headers):
        resp = client.post(
            "/api/data-mgmt/export?fmt=json",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]

    def test_export_csv(self, client, auth_headers):
        resp = client.post(
            "/api/data-mgmt/export?fmt=csv",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_export_info(self, client, auth_headers):
        resp = client.get("/api/data-mgmt/export/info", headers=auth_headers)
        assert resp.status_code == 200
        info = resp.json()["data"]
        assert "filename" in info
        assert "tables_exported" in info


class TestVacuum:

    def test_run_vacuum(self, client, auth_headers):
        resp = client.post("/api/data-mgmt/vacuum", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["action"] == "vacuum"
        assert data["success"] is True
