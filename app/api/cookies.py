from fastapi import Response

from app.core.config import settings
from app.core.security import SESSION_COOKIE_NAME


def set_session_cookie(response: Response, token: str) -> None:
    """Install the session cookie.

    `httponly` keeps it out of reach of JavaScript, and `samesite=lax` means the
    browser withholds it on cross-site POST requests, which is what stands in
    for CSRF tokens on this JSON-only API. `secure` follows the environment so
    local HTTP development still works.
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.ACCESS_TOKEN_EXPIRE_DAYS * 86_400,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )
