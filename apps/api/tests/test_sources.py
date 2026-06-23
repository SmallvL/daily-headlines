import asyncio
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.modules.auth.service import seed_admin_user
from app.modules.feed.schemas import FeedItemCreate
from app.modules.sources import service as api_source_service_module
from app.modules.sources import service as source_service_module
from app.modules.sources.models import Source


def test_create_fetch_and_list_feed(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed admin user
    db = testing_session()
    seed_admin_user(db)
    db.close()

    def override_db() -> Iterator[Session]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    async def fake_fetch(source_id: str, endpoint: str, limit: int = 20, extra_headers: dict[str, str] | None = None):
        return (
            "Fixture Feed",
            [
                FeedItemCreate(
                    source_id=source_id,
                    external_id="fixture-1",
                    title="Fixture item",
                    summary="Fixture summary",
                    url="https://example.com/item-1",
                )
            ],
        )

    monkeypatch.setattr(source_service_module.rss_connector, "fetch", fake_fetch)
    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/sources",
        headers=headers,
        json={
            "name": "Fixture",
            "type": "rss",
            "endpoint": "https://example.com/rss.xml",
            "schedule_enabled": True,
            "schedule_interval_minutes": 30,
        },
    )
    assert create_response.status_code in (200, 201)
    source_id = create_response.json()["data"]["id"]
    assert create_response.json()["data"]["schedule_enabled"] is True
    assert create_response.json()["data"]["schedule_interval_minutes"] == 30
    assert create_response.json()["data"]["next_fetch_at"] is not None

    schedule_response = client.patch(
        f"/api/sources/{source_id}/schedule",
        headers=headers,
        json={"schedule_enabled": False, "schedule_interval_minutes": None},
    )
    assert schedule_response.status_code == 200
    assert schedule_response.json()["data"]["schedule_enabled"] is False
    assert schedule_response.json()["data"]["next_fetch_at"] is None

    first_fetch = client.post(
        f"/api/sources/{source_id}/fetch-now", headers=headers
    )
    assert first_fetch.status_code == 200
    assert first_fetch.json()["data"]["inserted"] == 1
    assert first_fetch.json()["data"]["log_id"].startswith("fetchlog_")

    logs_response = client.get(
        f"/api/sources/{source_id}/fetch-logs", headers=headers
    )
    assert logs_response.status_code == 200
    assert logs_response.json()["data"][0]["status"] == "success"
    assert logs_response.json()["data"][0]["inserted_count"] == 1
    assert logs_response.json()["data"][0]["skipped_count"] == 0

    second_fetch = client.post(
        f"/api/sources/{source_id}/fetch-now", headers=headers
    )
    assert second_fetch.status_code == 200
    assert second_fetch.json()["data"]["skipped"] == 1

    with testing_session() as db:
        source = db.get(Source, source_id)
        assert source is not None
        source.schedule_enabled = True
        source.schedule_interval_minutes = 30
        source.next_fetch_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
        completed = asyncio.run(
            source_service_module.source_service.run_due_scheduled_sources(db)
        )
        assert completed == 1

    schedule_logs_response = client.get(
        f"/api/sources/{source_id}/fetch-logs", headers=headers
    )
    assert schedule_logs_response.status_code == 200
    assert schedule_logs_response.json()["data"][0]["trigger"] == "schedule"
    assert schedule_logs_response.json()["data"][0]["status"] == "success"

    feed_response = client.get("/api/feed/items", headers=headers)
    assert feed_response.status_code == 200
    assert feed_response.json()["data"]["items"][0]["title"] == "Fixture item"
    item_id = feed_response.json()["data"]["items"][0]["id"]

    save_response = client.post(
        f"/api/feed/items/{item_id}/save", headers=headers
    )
    assert save_response.status_code == 200
    assert save_response.json()["data"]["is_saved"] is True

    saved_response = client.get(
        "/api/feed/items?saved=true", headers=headers
    )
    assert saved_response.status_code == 200
    assert len(saved_response.json()["data"]["items"]) == 1

    unsave_response = client.delete(
        f"/api/feed/items/{item_id}/save", headers=headers
    )
    assert unsave_response.status_code == 200
    assert unsave_response.json()["data"]["is_saved"] is False

    empty_saved_response = client.get(
        "/api/feed/items?saved=true", headers=headers
    )
    assert empty_saved_response.status_code == 200
    assert empty_saved_response.json()["data"]["items"] == []

    search_response = client.get(
        "/api/feed/items?q=Fixture&source_type=rss", headers=headers
    )
    assert search_response.status_code == 200
    assert len(search_response.json()["data"]["items"]) == 1

    empty_search_response = client.get(
        "/api/feed/items?q=NoMatch", headers=headers
    )
    assert empty_search_response.status_code == 200
    assert empty_search_response.json()["data"]["items"] == []

    unread_response = client.get(
        "/api/feed/items?read=false", headers=headers
    )
    assert unread_response.status_code == 200
    assert len(unread_response.json()["data"]["items"]) == 1

    read_response = client.post(
        f"/api/feed/items/{item_id}/read", headers=headers
    )
    assert read_response.status_code == 200
    assert read_response.json()["data"]["is_read"] is True

    read_filtered_response = client.get(
        "/api/feed/items?read=true", headers=headers
    )
    assert read_filtered_response.status_code == 200
    assert len(read_filtered_response.json()["data"]["items"]) == 1

    empty_unread_response = client.get(
        "/api/feed/items?read=false", headers=headers
    )
    assert empty_unread_response.status_code == 200
    assert empty_unread_response.json()["data"]["items"] == []

    hide_response = client.post(
        f"/api/feed/items/{item_id}/hide", headers=headers
    )
    assert hide_response.status_code == 200
    assert hide_response.json()["data"]["is_hidden"] is True

    hidden_filtered_response = client.get(
        "/api/feed/items", headers=headers
    )
    assert hidden_filtered_response.status_code == 200
    assert hidden_filtered_response.json()["data"]["items"] == []

    include_hidden_response = client.get(
        "/api/feed/items?include_hidden=true", headers=headers
    )
    assert include_hidden_response.status_code == 200
    assert len(include_hidden_response.json()["data"]["items"]) == 1

    delete_response = client.delete(
        f"/api/sources/{source_id}", headers=headers
    )
    assert delete_response.status_code in (200, 204)

    sources_response = client.get("/api/sources", headers=headers)
    assert sources_response.json()["data"] == []

    app.dependency_overrides.clear()


def test_create_api_source_with_mapping(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed admin user
    db = testing_session()
    seed_admin_user(db)
    db.close()

    def override_db() -> Iterator[Session]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    async def fake_fetch(
        source_id: str, endpoint: str, config: dict, limit: int = 20,
        extra_headers: dict[str, str] | None = None,
    ):
        assert config["items_path"] == "data.items"
        return (
            "Fixture API",
            [
                FeedItemCreate(
                    source_id=source_id,
                    external_id="api-1",
                    title="API item",
                    summary="API summary",
                    url="https://example.com/api-1",
                )
            ],
        )

    monkeypatch.setattr(
        api_source_service_module.api_connector, "fetch", fake_fetch
    )
    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    token = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    ).json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Fixture API",
        "type": "api",
        "endpoint": "https://example.com/api/news",
        "config": {
            "items_path": "data.items",
            "mappings": {
                "id": "id",
                "title": "title",
                "url": "url",
                "summary": "summary",
            },
        },
    }
    source_id = client.post(
        "/api/sources", headers=headers, json=payload
    ).json()["data"]["id"]

    fetch_response = client.post(
        f"/api/sources/{source_id}/fetch-now", headers=headers
    )
    assert fetch_response.status_code == 200
    assert fetch_response.json()["data"]["inserted"] == 1

    feed_response = client.get("/api/feed/items", headers=headers)
    assert feed_response.json()["data"]["items"][0]["title"] == "API item"

    app.dependency_overrides.clear()
