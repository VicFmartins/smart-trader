from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import bearer_scheme, decode_access_token, extract_bearer_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginationParams
from app.services.auth import AuthService


def pagination_params(
    offset: Annotated[int, Query(ge=0, description="Zero-based record offset")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum records to return")] = 50,
) -> PaginationParams:
    return PaginationParams(offset=offset, limit=limit)


def optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def optional_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> User:
    token = extract_bearer_token(credentials)
    payload = decode_access_token(token)
    return AuthService(db).get_current_user_from_subject(payload["sub"])
