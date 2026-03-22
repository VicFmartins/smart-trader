from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.schemas.common import APIResponse
from app.services.auth import AuthService


router = APIRouter(prefix="/auth")


@router.post("/login", response_model=APIResponse[TokenResponse])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> APIResponse[TokenResponse]:
    token = AuthService(db).authenticate_and_issue_token(email=payload.email, password=payload.password)
    return APIResponse(data=token)


@router.get("/me", response_model=APIResponse[UserRead])
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> APIResponse[UserRead]:
    return APIResponse(data=UserRead.model_validate(current_user))
