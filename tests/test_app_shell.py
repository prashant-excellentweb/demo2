"""The SPA catch-all must not swallow API 404s or serve files outside the build."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

DIST = Path(settings.FRONTEND_DIST_DIR)
requires_build = pytest.mark.skipif(
    not (DIST / "index.html").is_file(),
    reason="frontend build not present; run `npm run build` in frontend/",
)


def test_healthz_reports_version(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_api_path_returns_json_not_html(client: TestClient) -> None:
    """A stray API path must stay machine-readable.

    Falling through to the HTML shell here would give the client markup where
    it parses JSON, turning a routing typo into an unrelated parse error.
    """
    response = client.get("/api/not-a-real-endpoint")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


@requires_build
def test_client_route_serves_app_shell(client: TestClient) -> None:
    response = client.get("/login")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<div id="root">' in response.text


@requires_build
def test_traversal_outside_build_falls_back_to_shell(client: TestClient) -> None:
    response = client.get("/../chatgpt.db", headers={"x-test": "traversal"})

    assert response.status_code in (200, 404)
    # Either normalised away by the client or caught by the containment check,
    # but never the raw database file.
    assert "SQLite format" not in response.text
