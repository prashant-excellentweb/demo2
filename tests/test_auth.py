from fastapi.testclient import TestClient


def test_register_sets_session_and_returns_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "sup3r-secret", "display_name": "Alice"},
    )
    assert response.status_code == 201
    assert response.json()["username"] == "alice"
    assert "session_token" in response.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"] == "Alice"


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_duplicate_username_is_rejected(client: TestClient, account: dict) -> None:
    response = client.post(
        "/api/auth/register",
        json={"username": account["username"], "password": "another-secret"},
    )
    assert response.status_code == 409
    assert "taken" in response.json()["detail"]


def test_short_password_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register", json={"username": "shorty", "password": "abc"}
    )
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_login_with_wrong_password_fails(client: TestClient, account: dict) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": account["username"], "password": "not-the-password"},
    )
    assert response.status_code == 401


def test_login_then_logout_clears_access(client: TestClient, account: dict) -> None:
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    login = client.post(
        "/api/auth/login",
        json={"username": account["username"], "password": "sup3r-secret"},
    )
    assert login.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_password_change_requires_current_password(
    client: TestClient, account: dict
) -> None:
    """A stolen session cookie must not be enough to take over the account."""
    without_current = client.patch(
        "/api/users/me", json={"new_password": "brand-new-secret"}
    )
    assert without_current.status_code == 422

    with_current = client.patch(
        "/api/users/me",
        json={"current_password": "sup3r-secret", "new_password": "brand-new-secret"},
    )
    assert with_current.status_code == 200
