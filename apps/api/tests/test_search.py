from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.modules.auth.service import seed_admin_user


def test_saved_search_crud() -> None:
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

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    token = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    ).json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/search/saved-searches",
        headers=headers,
        json={
            "name": "RSS with image",
            "query": {
                "q": "AI",
                "source_type": "rss",
                "has_image": True,
                "saved": True,
                "read": False,
                "include_hidden": True,
            },
        },
    )
    assert create_response.status_code == 200
    search_id = create_response.json()["data"]["id"]

    list_response = client.get(
        "/api/search/saved-searches", headers=headers
    )
    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["query"]["source_type"] == "rss"
    assert list_response.json()["data"][0]["query"]["saved"] is True
    assert list_response.json()["data"][0]["query"]["read"] is False
    assert (
        list_response.json()["data"][0]["query"]["include_hidden"] is True
    )

    delete_response = client.delete(
        f"/api/search/saved-searches/{search_id}", headers=headers
    )
    assert delete_response.status_code == 200

    empty_response = client.get(
        "/api/search/saved-searches", headers=headers
    )
    assert empty_response.json()["data"] == []

    app.dependency_overrides.clear()
