from fastapi import APIRouter

from app.api.deps import CurrentUser, UserServiceDep
from app.schemas.user import DailyUsageRead, UserRead, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserUpdateRequest, user: CurrentUser, service: UserServiceDep
) -> UserRead:
    return UserRead.model_validate(service.update_profile(user, payload))


@router.get("/me/usage", response_model=DailyUsageRead)
def read_usage(user: CurrentUser, service: UserServiceDep) -> DailyUsageRead:
    tokens_used, budget = service.daily_usage(user)
    return DailyUsageRead(tokens_used=tokens_used, daily_budget=budget)
