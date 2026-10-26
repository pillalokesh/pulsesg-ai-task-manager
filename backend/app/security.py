from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


def jwt_algorithm(secret: str) -> str:
    key_length = len(secret.encode())
    if key_length < 32:
        raise ValueError("JWT_SECRET must contain at least 32 UTF-8 bytes")
    if key_length >= 64:
        return "HS512"
    if key_length >= 48:
        return "HS384"
    return "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ValueError, TypeError):
        return False


def create_token(email: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": email, "iat": now, "exp": now + timedelta(hours=24)},
        settings.jwt_secret,
        algorithm=jwt_algorithm(settings.jwt_secret),
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        algorithm = jwt_algorithm(settings.jwt_secret)
        claims = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[algorithm])
        email = claims.get("sub")
        if not isinstance(email, str):
            raise unauthorized
    except jwt.PyJWTError as error:
        raise unauthorized from error
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None:
        raise unauthorized
    return user
