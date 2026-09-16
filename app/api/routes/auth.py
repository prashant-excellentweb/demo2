from fastapi import APIRouter, Response, status

from app.api.cookies import clear_session_cookie, set_session_cookie
from app.api.deps import AuthServiceDep, CurrentUser
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, auth: AuthServiceDep) -> UserRead:
    user = auth.register(payload)
    set_session_cookie(response, auth.issue_token(user))
    return UserRead.model_validate(user)


@router.post("/login", response_model=UserRead)
def login(payload: LoginRequest, response: Response, auth: AuthServiceDep) -> UserRead:
    user = auth.authenticate(payload)
    set_session_cookie(response, auth.issue_token(user))
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/me", response_model=UserRead)
def read_current_user(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
