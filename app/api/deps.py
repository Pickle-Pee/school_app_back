from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        phone = payload.get("sub")
        role = payload.get("role")
        if not phone or not role:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise credentials_exception
    return user


def get_current_teacher(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.teacher:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher role required")
    return current_user


def get_current_student(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student role required")
    return current_user
