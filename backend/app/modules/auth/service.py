from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.db.enums import UserStatus
from app.db.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.security import (
    InvalidTokenError,
    IssuedTokenPair,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    issue_token_pair,
    parse_token,
    verify_password,
)


class InvalidCredentialsError(ValueError):
    """Raised when username/password verification fails."""


class InactiveUserError(ValueError):
    """Raised when the target account is not active."""


@dataclass
class AuthService:
    repository: AuthRepository
    settings: Settings

    def login(self, username: str, password: str) -> tuple[User, IssuedTokenPair]:
        user = self.repository.get_user_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid username or password.")
        if user.status is not UserStatus.ACTIVE:
            raise InactiveUserError("User is disabled.")

        return user, self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> tuple[User, IssuedTokenPair]:
        try:
            claims = parse_token(
                refresh_token,
                expected_type=TOKEN_TYPE_REFRESH,
                settings=self.settings,
            )
        except InvalidTokenError as exc:
            raise InvalidCredentialsError("Invalid refresh token.") from exc
        user = self.repository.get_user_by_id(claims.user_id)
        if user is None:
            raise InvalidCredentialsError("Invalid refresh token.")
        if user.status is not UserStatus.ACTIVE:
            raise InactiveUserError("User is disabled.")

        return user, self._issue_tokens(user)

    def get_current_user(self, access_token: str) -> User:
        try:
            claims = parse_token(
                access_token,
                expected_type=TOKEN_TYPE_ACCESS,
                settings=self.settings,
            )
        except InvalidTokenError as exc:
            raise InvalidCredentialsError("Invalid access token.") from exc
        user = self.repository.get_user_by_id(claims.user_id)
        if user is None:
            raise InvalidCredentialsError("Invalid access token.")
        if user.status is not UserStatus.ACTIVE:
            raise InactiveUserError("User is disabled.")
        return user

    def _issue_tokens(self, user: User) -> IssuedTokenPair:
        return issue_token_pair(
            user_id=user.id,
            username=user.username,
            role=user.role,
            settings=self.settings,
        )
