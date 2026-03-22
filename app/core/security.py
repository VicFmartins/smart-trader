from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    payload = {"sub": subject, "exp": expires_at}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict[str, str]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired access token.") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthenticationError("Token payload is missing the required subject.")

    return {"sub": subject}


def extract_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AuthenticationError("Bearer authentication is required.")
    return credentials.credentials
