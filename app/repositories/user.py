from sqlalchemy import select

from app.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def get_by_id(self, user_id: str) -> User | None:
        return self.session.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def username_exists(self, username: str) -> bool:
        return (
            self.session.scalar(select(User.id).where(User.username == username)) is not None
        )

    def create(self, username: str, display_name: str, hashed_password: str) -> User:
        user = User(
            username=username,
            display_name=display_name,
            hashed_password=hashed_password,
        )
        self.add(user)
        self.flush()
        return user
