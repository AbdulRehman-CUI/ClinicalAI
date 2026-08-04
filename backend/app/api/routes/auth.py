"""Authentication routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from app.schemas.auth import AuthUser, TokenRefreshRequest, TokenResponse, UserLoginRequest, UserRead, UserRegisterRequest
from app.schemas.common import ApiResponse
from app.services.auth import AuthService, get_auth_service, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[dict[str, Any]], status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[dict[str, Any]]:
    """Register a new user and return a token pair plus the user profile."""
    tokens = service.register(payload)
    user = service.user_repository.get_by_email(payload.email.lower())
    if user is None:
        raise RuntimeError("User registration failed")
    return ApiResponse(
        success=True,
        message="User registered successfully.",
        data={
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
        },
    )


@router.post("/login", response_model=ApiResponse[TokenResponse], status_code=status.HTTP_200_OK)
async def login(
    payload: UserLoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[TokenResponse]:
    """Authenticate a user and return JWTs."""
    tokens = service.login(payload)
    return ApiResponse(success=True, message="Login successful.", data=tokens)


@router.post("/refresh", response_model=ApiResponse[TokenResponse], status_code=status.HTTP_200_OK)
async def refresh(
    payload: TokenRefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[TokenResponse]:
    """Issue a fresh token pair from a refresh token."""
    tokens = service.refresh(payload)
    return ApiResponse(success=True, message="Tokens refreshed successfully.", data=tokens)


@router.post("/logout", response_model=ApiResponse[None], status_code=status.HTTP_200_OK)
async def logout() -> ApiResponse[None]:
    """Logout is handled client-side by discarding the token pair."""
    return ApiResponse(success=True, message="Logout successful.", data=None)


@router.get("/users/me", response_model=ApiResponse[UserRead], status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: AuthUser = Depends(get_current_user),
) -> ApiResponse[UserRead]:
    """Return the authenticated user's profile."""
    return ApiResponse(success=True, message="User profile retrieved successfully.", data=UserRead.model_validate(current_user))
