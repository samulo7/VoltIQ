from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.models import User
from app.modules.auth.deps import get_auth_service, get_current_user
from app.modules.auth.schemas import (
    AuthUserResponse,
    LoginRequest,
    LoginResponse,
    TokenPairResponse,
    TokenRefreshRequest,
)
from app.modules.auth.service import AuthService, InactiveUserError, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/health")
def auth_health() -> dict[str, str]:
    return {"module": "auth", "status": "ok"}


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    try:
        user, token_pair = service.login(payload.username.strip(), payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled.",
        ) from exc

    return LoginResponse(
        user=AuthUserResponse.model_validate(user),
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        access_expires_in_seconds=token_pair.access_expires_in_seconds,
        refresh_expires_in_seconds=token_pair.refresh_expires_in_seconds,
    )


@router.post("/refresh", response_model=TokenPairResponse)
def refresh_token(
    payload: TokenRefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPairResponse:
    try:
        _, token_pair = service.refresh(payload.refresh_token)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled.",
        ) from exc

    return TokenPairResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        access_expires_in_seconds=token_pair.access_expires_in_seconds,
        refresh_expires_in_seconds=token_pair.refresh_expires_in_seconds,
    )


@router.get("/me", response_model=AuthUserResponse)
def current_user(user: User = Depends(get_current_user)) -> AuthUserResponse:
    return AuthUserResponse.model_validate(user)

