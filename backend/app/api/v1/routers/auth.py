from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_user_repo
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RefreshRequest, TokenPair, UserLogin, UserRead, UserRegister
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> UserRead:
    user = await AuthService(user_repo).register(data)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    data: UserLogin,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> TokenPair:
    _, tokens = await AuthService(user_repo).login(data.email, data.password)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    data: RefreshRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> TokenPair:
    return await AuthService(user_repo).refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> None:
    await AuthService(user_repo).logout(data.refresh_token)
