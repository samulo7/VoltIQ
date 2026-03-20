from __future__ import annotations

import base64
import binascii
import datetime as dt
import hashlib
import hmac
import json
import os
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.db.enums import UserRole

JWT_ALGORITHM = "HS256"
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
PBKDF2_PREFIX = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 390_000


class InvalidTokenError(ValueError):
    """Raised when a JWT token cannot be validated."""


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    username: str
    role: UserRole
    token_type: str
    issued_at: dt.datetime
    expires_at: dt.datetime


@dataclass(frozen=True)
class IssuedTokenPair:
    access_token: str
    refresh_token: str
    access_expires_in_seconds: int
    refresh_expires_in_seconds: int


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{PBKDF2_PREFIX}${PBKDF2_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    parts = stored_hash.split("$")
    if len(parts) == 4 and parts[0] == PBKDF2_PREFIX:
        try:
            iterations = int(parts[1])
            salt = base64.urlsafe_b64decode(parts[2].encode("ascii"))
            expected = base64.urlsafe_b64decode(parts[3].encode("ascii"))
        except (ValueError, binascii.Error):
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual, expected)

    if stored_hash.startswith("plain$"):
        return hmac.compare_digest(password, stored_hash.removeprefix("plain$"))

    # Backward compatibility for previously seeded plain-text passwords in local dev.
    return hmac.compare_digest(password, stored_hash)


def issue_token_pair(
    *,
    user_id: uuid.UUID,
    username: str,
    role: UserRole,
    settings: Settings,
) -> IssuedTokenPair:
    access_expires = int(settings.jwt_access_token_expires_minutes * 60)
    refresh_expires = int(settings.jwt_refresh_token_expires_minutes * 60)
    now = _utcnow()

    access_token = _encode_token(
        user_id=user_id,
        username=username,
        role=role,
        token_type=TOKEN_TYPE_ACCESS,
        expires_in_seconds=access_expires,
        issued_at=now,
        settings=settings,
    )
    refresh_token = _encode_token(
        user_id=user_id,
        username=username,
        role=role,
        token_type=TOKEN_TYPE_REFRESH,
        expires_in_seconds=refresh_expires,
        issued_at=now,
        settings=settings,
    )
    return IssuedTokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_in_seconds=access_expires,
        refresh_expires_in_seconds=refresh_expires,
    )


def parse_token(token: str, *, expected_type: str, settings: Settings) -> TokenClaims:
    payload = _decode_token(token, settings.jwt_secret_key)
    _validate_claim(payload, "iss", settings.jwt_issuer)
    _validate_claim(payload, "typ", expected_type)

    try:
        user_id = uuid.UUID(str(payload["sub"]))
        username = str(payload["username"])
        role = UserRole(str(payload["role"]))
        issued_at = _from_timestamp(payload["iat"])
        expires_at = _from_timestamp(payload["exp"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError("Invalid token payload.") from exc

    if expires_at <= _utcnow():
        raise InvalidTokenError("Token expired.")

    return TokenClaims(
        user_id=user_id,
        username=username,
        role=role,
        token_type=expected_type,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def _encode_token(
    *,
    user_id: uuid.UUID,
    username: str,
    role: UserRole,
    token_type: str,
    expires_in_seconds: int,
    issued_at: dt.datetime,
    settings: Settings,
) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    iat = int(issued_at.timestamp())
    exp = iat + expires_in_seconds
    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "sub": str(user_id),
        "username": username,
        "role": role.value,
        "typ": token_type,
        "iat": iat,
        "exp": exp,
        "jti": str(uuid.uuid4()),
    }

    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    signature_segment = _b64url_encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _decode_token(token: str, secret: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise InvalidTokenError("Malformed token.") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    signature = _b64url_decode(signature_segment)
    if not hmac.compare_digest(signature, expected_signature):
        raise InvalidTokenError("Invalid token signature.")

    try:
        header = json.loads(_b64url_decode(header_segment).decode("utf-8"))
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, binascii.Error) as exc:
        raise InvalidTokenError("Malformed token payload.") from exc

    if header.get("alg") != JWT_ALGORITHM:
        raise InvalidTokenError("Unsupported token algorithm.")

    if not isinstance(payload, dict):
        raise InvalidTokenError("Malformed token payload.")

    return payload


def _validate_claim(payload: dict[str, Any], key: str, expected: str) -> None:
    actual = payload.get(key)
    if actual != expected:
        raise InvalidTokenError(f"Invalid token claim: {key}.")


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _from_timestamp(raw_value: Any) -> dt.datetime:
    timestamp = int(raw_value)
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)
