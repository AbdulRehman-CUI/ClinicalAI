"""Authentication and authorization service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.repositories.user import UserRepository
from app.schemas.auth import AuthUser, Role, TokenRefreshRequest, TokenResponse, UserLoginRequest, UserRead, UserRegisterRequest
from app.services.exceptions import ResourceNotFoundError, ValidationError

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


class AuthService:
    """Coordinate registration, login, refresh, and authorization checks."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def register(self, payload: UserRegisterRequest) -> TokenResponse:
        """Register a new user and issue initial tokens."""
        if self.user_repository.get_by_email(payload.email.lower()) is not None:
            raise ValidationError("Email already registered.")

        hashed_password = self._hash_password(payload.password)
        user = self.user_repository.create(
            {
                "full_name": payload.full_name,
                "email": payload.email.lower(),
                "hashed_password": hashed_password,
                "role": payload.role.value,
                "is_active": True,
            }
        )
        return self._issue_tokens(user)

    def login(self, payload: UserLoginRequest) -> TokenResponse:
        """Authenticate a user and issue tokens."""
        user = self.user_repository.get_by_email(payload.email.lower())
        if user is None or not self._verify_password(payload.password, user.hashed_password):
            raise ValidationError("Invalid email or password.")
        if not user.is_active:
            raise ValidationError("User account is disabled.")
        return self._issue_tokens(user)

    def refresh(self, payload: TokenRefreshRequest) -> TokenResponse:
        """Refresh access and refresh tokens using a valid refresh token."""
        try:
            claims = jwt.decode(
                payload.refresh_token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"require": ["sub", "type", "exp"]},
            )
        except jwt.PyJWTError as exc:
            raise ValidationError("Invalid refresh token.") from exc

        if claims.get("type") != "refresh":
            raise ValidationError("Invalid refresh token type.")

        user = self.user_repository.get(int(claims["sub"]))
        if user is None or not user.is_active:
            raise ValidationError("User account is disabled.")
        return self._issue_tokens(user)

    def get_current_user(self, token: str) -> AuthUser:
        """Decode a JWT and return the authenticated user context."""
        try:
            claims = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"require": ["sub", "type", "exp"]},
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

        if claims.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        user = self.user_repository.get(int(claims["sub"]))
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active")
        return AuthUser.model_validate(user)

    def require_role(self, *allowed_roles: Role) -> Any:
        """Build a dependency that ensures the current user has one of the allowed roles."""

        def dependency(current_user: AuthUser = Depends(get_current_user_dependency)) -> AuthUser:
            if current_user.role not in {role.value for role in allowed_roles}:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
            return current_user

        return dependency

    def get_current_user_payload(self, user: User) -> UserRead:
        """Return a safe user representation."""
        return UserRead.model_validate(user)

    def _issue_tokens(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for a user."""
        now = datetime.now(timezone.utc)
        access_payload = {
            "sub": str(user.id),
            "type": "access",
            "role": user.role,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
            "iat": now,
        }
        refresh_payload = {
            "sub": str(user.id),
            "type": "refresh",
            "role": user.role,
            "exp": now + timedelta(days=settings.refresh_token_expire_days),
            "iat": now,
        }
        access_token = jwt.encode(access_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        refresh_token = jwt.encode(refresh_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    def _hash_password(self, password: str) -> str:
        """Hash a plaintext password using bcrypt."""
        salt = bcrypt.gensalt(rounds=settings.password_hash_rounds)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against a stored bcrypt hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Create an auth service bound to the current database session."""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("Creating AuthService dependency")
    return AuthService(UserRepository(db))


def get_current_user_dependency(
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> AuthUser:
    return service.get_current_user(token)


def get_current_user(
    current_user: AuthUser = Depends(get_current_user_dependency),
) -> AuthUser:
    """Convenience dependency for routes that need the signed-in user."""
    return current_user


def get_optional_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    service: AuthService = Depends(get_auth_service),
) -> AuthUser | None:
    """Return the signed-in user when present, otherwise allow anonymous access."""
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication scheme")
    token = authorization.removeprefix("Bearer ").strip()
    return service.get_current_user(token)
