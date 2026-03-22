from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ApplicationError, AuthenticationError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.auth import TokenResponse, UserRead


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    def get_user_by_email(self, email: str) -> User | None:
        normalized_email = self.normalize_email(email)
        return self.users.get_by_email(normalized_email)

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.users.get_by_id(user_id)

    def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
        is_admin: bool = False,
        is_active: bool = True,
    ) -> User:
        normalized_email = self.normalize_email(email)
        if self.users.get_by_email(normalized_email):
            raise ApplicationError("A user with this email already exists.", error_code="user_conflict")

        user = User(
            email=normalized_email,
            full_name=full_name.strip() if full_name else None,
            password_hash=hash_password(password),
            is_admin=is_admin,
            is_active=is_active,
        )
        return self.users.save(user)

    def create_or_update_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
        is_admin: bool = False,
        is_active: bool = True,
    ) -> tuple[User, bool]:
        existing = self.get_user_by_email(email)
        if existing:
            existing.full_name = full_name.strip() if full_name else existing.full_name
            existing.password_hash = hash_password(password)
            existing.is_admin = is_admin
            existing.is_active = is_active
            return self.users.save(existing), False

        return (
            self.create_user(
                email=email,
                password=password,
                full_name=full_name,
                is_admin=is_admin,
                is_active=is_active,
            ),
            True,
        )

    def authenticate_user(self, *, email: str, password: str) -> User:
        user = self.get_user_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("This user is inactive.")
        return user

    def issue_token(self, user: User) -> TokenResponse:
        access_token, expires_at = create_access_token(str(user.id))
        return TokenResponse(
            access_token=access_token,
            expires_at=expires_at,
            user=UserRead.model_validate(user),
        )

    def authenticate_and_issue_token(self, *, email: str, password: str) -> TokenResponse:
        user = self.authenticate_user(email=email, password=password)
        return self.issue_token(user)

    def get_current_user_from_subject(self, subject: str) -> User:
        try:
            user_id = int(subject)
        except ValueError as exc:
            raise AuthenticationError("Token subject is invalid.") from exc

        user = self.get_user_by_id(user_id)
        if user is None:
            raise AuthenticationError("Authenticated user is no longer available.")
        if not user.is_active:
            raise AuthenticationError("This user is inactive.")
        return user
