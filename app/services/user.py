from datetime import UTC

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.security import hash_password, verify_password
from app.db.base import utcnow
from app.models import User
from app.repositories.usage import UsageRepository
from app.schemas.user import UserUpdateRequest


class UserService:
    def __init__(self, session: Session):
        self.session = session
        self.usage = UsageRepository(session)

    def update_profile(self, user: User, payload: UserUpdateRequest) -> User:
        if payload.display_name is not None:
            user.display_name = payload.display_name

        if payload.new_password:
            # A leaked session cookie should not be enough to seize the account,
            # so rotating the password requires proving the current one.
            if not payload.current_password or not verify_password(
                payload.current_password, user.hashed_password
            ):
                raise ValidationError("Your current password is incorrect.")
            user.hashed_password = hash_password(payload.new_password)

        self.session.commit()
        self.session.refresh(user)
        return user

    def daily_usage(self, user: User) -> tuple[int, int]:
        today = utcnow().astimezone(UTC).date()
        return self.usage.tokens_used_on(user.id, today), settings.DAILY_TOKEN_BUDGET
