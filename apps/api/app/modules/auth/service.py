import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.auth.schemas import CurrentUser, LoginRequest, TokenPair
from app.modules.users.models import User

_HASH_ITERATIONS = 260_000  # OWASP recommendation for PBKDF2-SHA256


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _HASH_ITERATIONS)
    return f"pbkdf2:sha256:{_HASH_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    """Verify password against stored hash. Format: pbkdf2:sha256:iterations$salt$hash"""
    try:
        prefix, salt_hex, hash_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, _HASH_ITERATIONS)
        return hmac.compare_digest(dk, expected)
    except (ValueError, AttributeError):
        return False


def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        hours=settings.jwt_expire_hours
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> str:
    """Decode JWT and return user_id. Raises 401 on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return user_id
    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from err


def seed_admin_user(db: Session) -> None:
    """Create or update the dev admin user in the database."""
    username = settings.dev_admin_username
    existing = db.scalar(select(User).where(User.username == username))
    if existing:
        changed = False
        if existing.role != "admin":
            existing.role = "admin"
            changed = True
        if existing.status != "active":
            existing.status = "active"
            changed = True
        if changed:
            db.commit()
        return

    admin = User(
        id=f"user_{uuid4().hex}",
        username=username,
        password_hash=hash_password(settings.dev_admin_password),
        display_name="管理员",
        role="admin",
        status="active",
    )
    db.add(admin)
    db.commit()


class AuthService:
    def login(self, db: Session, payload: LoginRequest) -> TokenPair:
        user = db.scalar(
            select(User).where(User.username == payload.username)
        )
        if not user or not verify_password(
            payload.password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )
        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号已被禁用",
            )
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        return TokenPair(access_token=create_token(user.id))

    def get_current_user(
        self, db: Session, token: str
    ) -> CurrentUser:
        user_id = decode_token(token)
        user = db.get(User, user_id)
        if not user or user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号已被禁用",
            )
        return CurrentUser(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            roles=[user.role] if user.role else ["user"],
        )


auth_service = AuthService()
