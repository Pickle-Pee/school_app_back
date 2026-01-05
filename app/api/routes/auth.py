from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import get_settings
from app.core.security import verify_password, hash_password
from app.services.auth import build_access_token
from app.models import User, UserRole
from app.schemas.auth import LoginRequest, LoginResponse, LoginUser, SetPasswordRequest, SetPasswordResponse, MeResponse

router = APIRouter()
settings = get_settings()


@router.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.role == UserRole.teacher:
        if not request.teacher_code or request.teacher_code != user.teacher_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.password_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password not set")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = build_access_token(
        phone=user.phone,
        role=user.role.value,
        expires_minutes=settings.access_token_expire_minutes,
    )

    class_name = user.class_group.name if user.class_group else None
    subject_name = user.subject.name if user.subject else None

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role.value,
        user=LoginUser(
            id=user.id,
            full_name=user.full_name,
            phone=user.phone,
            class_name=class_name,
            subject=subject_name,
        ),
    )


@router.post("/auth/set-password", response_model=SetPasswordResponse)
def set_password(request: SetPasswordRequest, db: Session = Depends(get_db)) -> SetPasswordResponse:
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.teacher:
        if not request.teacher_code or request.teacher_code != user.teacher_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid teacher code")

    user.password_hash = hash_password(request.new_password)
    db.commit()

    return SetPasswordResponse(ok=True)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    if current_user.role == UserRole.teacher:
        profile = {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "subject": current_user.subject.name if current_user.subject else None,
            "email": current_user.email,
            "room": current_user.room,
            "note": current_user.note,
        }
    else:
        profile = {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "class_group": current_user.class_group,
        }

    return MeResponse(role=current_user.role.value, profile=profile)
