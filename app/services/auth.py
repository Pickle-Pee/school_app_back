from datetime import timedelta

from app.core.security import create_access_token


def build_access_token(phone: str, role: str, expires_minutes: int) -> str:
    return create_access_token(subject=phone, role=role, expires_delta=timedelta(minutes=expires_minutes))
