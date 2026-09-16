"""Every read and write must be scoped to the owning user."""

from fastapi.testclient import TestClient

from app.main import app


def _register(client: TestClient, username: str) -> None:
    response = client.post(
        "/api/auth/register", json={"username": username, "password": "sup3r-secret"}
    )
    assert response.status_code == 201


def test_users_cannot_reach_each_others_chats_or_projects() -> None:
    with TestClient(app) as owner, TestClient(app) as intruder:
        _register(owner, "owner-user")
        _register(intruder, "intruder-user")

        chat_id = owner.post("/api/chats", json={}).json()["id"]
        project_id = owner.post("/api/projects", json={"name": "Private"}).json()["id"]

        assert owner.get(f"/api/chats/{chat_id}").status_code == 200
        assert intruder.get("/api/chats").json() == []

        # Ownership is part of every query predicate, so a known id is useless.
        assert intruder.get(f"/api/chats/{chat_id}").status_code == 404
        assert intruder.delete(f"/api/chats/{chat_id}").status_code == 404
        renamed = intruder.patch(f"/api/chats/{chat_id}", json={"title": "Mine"})
        assert renamed.status_code == 404
        assert intruder.put(
            f"/api/projects/{project_id}", json={"name": "Stolen"}
        ).status_code == 404
        assert intruder.delete(f"/api/projects/{project_id}").status_code == 404

        # A chat cannot be filed into someone else's project either.
        intruder_chat = intruder.post("/api/chats", json={}).json()["id"]
        assert intruder.patch(
            f"/api/chats/{intruder_chat}", json={"project_id": project_id}
        ).status_code == 404

        assert owner.get(f"/api/chats/{chat_id}").status_code == 200


def test_deleting_a_project_keeps_its_chats() -> None:
    with TestClient(app) as client:
        _register(client, "project-owner")
        project_id = client.post("/api/projects", json={"name": "Temp"}).json()["id"]
        chat_id = client.post("/api/chats", json={"project_id": project_id}).json()["id"]

        assert client.delete(f"/api/projects/{project_id}").status_code == 204

        detail = client.get(f"/api/chats/{chat_id}")
        assert detail.status_code == 200
        assert detail.json()["project_id"] is None
