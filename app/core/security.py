from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import settings

SESSION_COOKIE_NAME = "session_token"

# bcrypt hashes at most 72 bytes and silently ignores the rest. Truncating
# explicitly keeps behaviour identical to the hashes passlib wrote previously,
# so existing passwords still verify.
_BCRYPT_MAX_BYTES = 72


def _encode_password(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode_password(password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            _encode_password(plain_password), hashed_password.encode("ascii")
        )
    except (ValueError, TypeError):
        # Malformed or non-bcrypt hash in the database; treat as a failed login
        # rather than a 500.
        return False


def create_access_token(subject: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Return the token subject, or None when it is missing/invalid/expired."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except InvalidTokenError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) and subject else None
