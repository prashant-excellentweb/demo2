from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.core.security import SESSION_COOKIE_NAME
from app.db.session import get_db
from app.models import User
from app.services.attachment import AttachmentService
from app.services.auth import AuthService
from app.services.chat import ChatService
from app.services.project import ProjectService
from app.services.search import WebSearchService
from app.services.user import UserService

DbSession = Annotated[Session, Depends(get_db)]


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(session)


def get_current_user(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Resolve the signed session cookie into a live user row.

    The token is httpOnly so page scripts cannot read it, and the user is
    re-read on every request so a disabled account loses access immediately
    rather than when its JWT eventually expires.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = auth_service.resolve_user(token)
    if user is None:
        raise AuthenticationError("Please sign in to continue.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_chat_service(session: DbSession) -> ChatService:
    return ChatService(session, search_service=WebSearchService())


def get_project_service(session: DbSession) -> ProjectService:
    return ProjectService(session)


def get_user_service(session: DbSession) -> UserService:
    return UserService(session)


def get_attachment_service(session: DbSession) -> AttachmentService:
    return AttachmentService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]
