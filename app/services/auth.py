import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest

logger = logging.getLogger(__name__)

# Verified against when the username is unknown, so a missing account costs the
# same time as a wrong password and cannot be probed by response latency.
_DUMMY_HASH = hash_password("timing-equalisation-placeholder")


class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)

    def register(self, payload: RegisterRequest) -> User:
        if self.users.username_exists(payload.username):
            raise ConflictError("That username is already taken.")

        try:
            user = self.users.create(
                username=payload.username,
                display_name=payload.display_name or payload.username,
                hashed_password=hash_password(payload.password),
            )
            self.session.commit()
        except IntegrityError as exc:
            # Two simultaneous signups for the same name; the unique index wins.
            self.session.rollback()
            raise ConflictError("That username is already taken.") from exc

        self.session.refresh(user)
        return user

    def authenticate(self, payload: LoginRequest) -> User:
        user = self.users.get_by_username(payload.username)
        if user is None:
            verify_password(payload.password, _DUMMY_HASH)
            raise AuthenticationError("Incorrect username or password.")

        if not verify_password(payload.password, user.hashed_password):
            raise AuthenticationError("Incorrect username or password.")

        if not user.is_active:
            raise AuthenticationError("This account has been disabled.")

        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(user.username)

    def resolve_user(self, token: str | None) -> User | None:
        if not token:
            return None
        username = decode_access_token(token)
        if not username:
            return None
        user = self.users.get_by_username(username)
        if user is None or not user.is_active:
            return None
        return user
