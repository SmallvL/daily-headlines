from fastapi.testclient import TestClient

from app.main import app


def login_admin() -> str:
    response = TestClient(app).post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def test_get_preference_includes_login_background_url(test_db):
    client = TestClient(app)
    token = login_admin()
    response = client.get(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "login_background_url" in data
    assert data["login_background_url"] is None


def test_update_login_background_url(test_db):
    client = TestClient(app)
    token = login_admin()
    response = client.patch(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"login_background_url": "/uploads/login-bg-test.jpg"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["login_background_url"] == "/uploads/login-bg-test.jpg"

    response = client.get(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.json()["data"]["login_background_url"] == "/uploads/login-bg-test.jpg"


def test_clear_login_background_url(test_db):
    client = TestClient(app)
    token = login_admin()
    client.patch(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"login_background_url": "/uploads/login-bg-test.jpg"},
    )
    response = client.patch(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"login_background_url": None},
    )
    assert response.status_code == 200
    assert response.json()["data"]["login_background_url"] is None


def test_public_login_background_endpoint(test_db):
    client = TestClient(app)
    token = login_admin()
    client.patch(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"login_background_url": "/uploads/login-bg-public.jpg"},
    )

    response = client.get("/api/preferences/login-background")
    assert response.status_code == 200
    assert response.json()["data"] == "/uploads/login-bg-public.jpg"
