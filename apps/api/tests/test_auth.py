from fastapi.testclient import TestClient

from app.main import app


def test_login_and_me(test_db) -> None:  # noqa: F811
    client = TestClient(app)
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["data"]["access_token"]

    me_response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert me_response.status_code == 200
    assert me_response.json()["data"]["roles"] == ["admin"]
