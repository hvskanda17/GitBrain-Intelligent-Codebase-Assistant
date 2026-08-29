from fastapi import APIRouter

from app.api.v1.deps import CurrentUser
from app.schemas.auth import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
