"""Tests for the plugins system."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.modules.auth.service import seed_admin_user
from app.plugins.base.registry import get_plugin_registry, auto_discover_plugins


@pytest.fixture
def client():
    """Create test client with in-memory database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    seed_admin_user(db)
    db.close()

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Get auth headers with valid token."""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_plugins(client, auth_headers):
    """Test listing all available plugins."""
    response = client.get("/api/plugins", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 4  # bilibili, weibo, xiaohongshu, toutiao

    plugin_ids = [p["id"] for p in data]
    assert "bilibili" in plugin_ids
    assert "weibo" in plugin_ids
    assert "xiaohongshu" in plugin_ids
    assert "toutiao" in plugin_ids


def test_get_plugin_detail(client, auth_headers):
    """Test getting plugin details."""
    response = client.get("/api/plugins/bilibili", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == "bilibili"
    assert data["name"] == "哔哩哔哩"
    assert "qrcode" in data["auth_methods"]
    assert "cookie" in data["auth_methods"]
    assert "auth_schema" in data
    assert "subscription_types" in data
    assert len(data["subscription_types"]) >= 1


def test_get_plugin_not_found(client, auth_headers):
    """Test getting non-existent plugin."""
    response = client.get("/api/plugins/nonexistent", headers=auth_headers)
    assert response.status_code == 404


def test_plugin_registry():
    """Test plugin registry discovery."""
    auto_discover_plugins()
    registry = get_plugin_registry()
    plugins = registry.list_plugins()
    assert len(plugins) >= 4

    # Test get by ID
    bilibili = registry.get("bilibili")
    assert bilibili is not None
    assert bilibili.plugin_id == "bilibili"
    assert bilibili.display_name == "哔哩哔哩"

    # Test nonexistent
    assert registry.get("nonexistent") is None


def test_plugin_auth_methods():
    """Test that all plugins have valid auth methods."""
    auto_discover_plugins()
    registry = get_plugin_registry()

    for plugin_info in registry.list_plugins():
        plugin = registry.get(plugin_info["id"])
        assert plugin is not None
        assert len(plugin.supported_auth_methods) > 0
        assert plugin.plugin_id
        assert plugin.display_name
        assert plugin.description


def test_plugin_auth_config_schema():
    """Test that all plugins return valid auth config schemas."""
    import asyncio
    auto_discover_plugins()
    registry = get_plugin_registry()

    for plugin_info in registry.list_plugins():
        plugin = registry.get(plugin_info["id"])
        schema = asyncio.run(plugin.get_auth_config_schema())
        assert "type" in schema
        assert "properties" in schema


def test_plugin_subscription_types():
    """Test that all plugins return subscription types."""
    import asyncio
    auto_discover_plugins()
    registry = get_plugin_registry()

    for plugin_info in registry.list_plugins():
        plugin = registry.get(plugin_info["id"])
        types = asyncio.run(plugin.get_subscription_types())
        assert len(types) > 0
        for t in types:
            assert "id" in t
            assert "name" in t


def test_init_auth_invalid_method(client, auth_headers):
    """Test initializing auth with invalid method."""
    response = client.post(
        "/api/plugins/bilibili/auth/init?method=invalid",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 400


def test_validate_credentials_invalid(client, auth_headers):
    """Test validating invalid credentials."""
    response = client.post(
        "/api/plugins/bilibili/auth/validate",
        headers=auth_headers,
        json={"cookies": "invalid_cookie"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid"] is False


def test_unauthenticated_access(client):
    """Test that plugin endpoints require authentication."""
    response = client.get("/api/plugins")
    assert response.status_code in [401, 403]

    response = client.get("/api/plugins/bilibili")
    assert response.status_code in [401, 403]
