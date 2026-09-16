import struct
import zlib

from fastapi.testclient import TestClient

from app.main import app


def _png_bytes() -> bytes:
    """Smallest valid 1x1 PNG, so the magic-number check passes."""

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixel = zlib.compress(b"\x00\xff\x00\x00")
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", pixel)
        + chunk(b"IEND", b"")
    )


def test_text_upload_returns_metadata_without_contents(
    client: TestClient, account: dict
) -> None:
    response = client.post(
        "/api/attachments",
        files={"file": ("notes.txt", b"Some notes about indexing.", "text/plain")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["is_image"] is False
    # The old endpoint echoed the whole payload back to the browser.
    assert "content" not in body


def test_attachment_is_bound_to_the_message_it_was_sent_with(
    client: TestClient, account: dict
) -> None:
    attachment = client.post(
        "/api/attachments",
        files={"file": ("data.csv", b"col_a,col_b\n1,2\n", "text/csv")},
    ).json()
    chat_id = client.post("/api/chats", json={}).json()["id"]

    sent = client.post(
        f"/api/chats/{chat_id}/messages",
        json={"content": "Summarise this", "attachment_ids": [attachment["id"]]},
    )
    assert sent.status_code == 200

    message = client.get(f"/api/chats/{chat_id}").json()["messages"][0]
    assert [a["filename"] for a in message["attachments"]] == ["data.csv"]


def test_an_attachment_cannot_be_reused_on_a_second_message(
    client: TestClient, account: dict
) -> None:
    attachment = client.post(
        "/api/attachments", files={"file": ("a.txt", b"one", "text/plain")}
    ).json()
    chat_id = client.post("/api/chats", json={}).json()["id"]

    first = client.post(
        f"/api/chats/{chat_id}/messages",
        json={"content": "First", "attachment_ids": [attachment["id"]]},
    )
    assert first.status_code == 200

    replay = client.post(
        f"/api/chats/{chat_id}/messages",
        json={"content": "Second", "attachment_ids": [attachment["id"]]},
    )
    assert replay.status_code == 404


def test_image_upload_is_served_back_as_a_file(client: TestClient, account: dict) -> None:
    payload = _png_bytes()
    attachment = client.post(
        "/api/attachments", files={"file": ("pixel.png", payload, "image/png")}
    ).json()
    assert attachment["is_image"] is True
    assert attachment["size_bytes"] == len(payload)

    content = client.get(f"/api/attachments/{attachment['id']}/content")
    assert content.status_code == 200
    assert content.headers["content-type"].startswith("image/png")
    assert content.headers["x-content-type-options"] == "nosniff"
    assert content.content == payload


def test_a_disguised_non_image_is_rejected(client: TestClient, account: dict) -> None:
    response = client.post(
        "/api/attachments",
        files={"file": ("payload.png", b"<script>alert(1)</script>", "image/png")},
    )
    assert response.status_code == 415


def test_executable_upload_is_rejected(client: TestClient, account: dict) -> None:
    response = client.post(
        "/api/attachments",
        files={"file": ("tool.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_oversized_upload_is_rejected(client: TestClient, account: dict) -> None:
    from app.core.config import settings

    too_big = b"a" * (settings.MAX_UPLOAD_BYTES + 1024)
    response = client.post(
        "/api/attachments", files={"file": ("big.txt", too_big, "text/plain")}
    )
    assert response.status_code == 413


def test_attachments_are_private_to_their_owner(client: TestClient, account: dict) -> None:
    attachment = client.post(
        "/api/attachments", files={"file": ("secret.txt", b"classified", "text/plain")}
    ).json()

    with TestClient(app) as other:
        other.post(
            "/api/auth/register",
            json={"username": "nosy-user", "password": "sup3r-secret"},
        )
        assert other.get(
            f"/api/attachments/{attachment['id']}/content"
        ).status_code == 404
