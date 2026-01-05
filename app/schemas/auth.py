from typing import Optional, Literal, Union
from pydantic import BaseModel

from app.schemas.class_group import ClassGroupOut


class LoginRequest(BaseModel):
    phone: str
    password: str
    teacher_code: Optional[str] = None


class LoginUser(BaseModel):
    id: int
    full_name: str
    phone: str
    class_name: Optional[str] = None
    subject: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: Literal["student", "teacher"]
    user: LoginUser


class SetPasswordRequest(BaseModel):
    phone: str
    new_password: str
    teacher_code: Optional[str] = None


class SetPasswordResponse(BaseModel):
    ok: bool


class TeacherProfile(BaseModel):
    id: int
    full_name: str
    phone: str
    subject: Optional[str] = None
    email: Optional[str] = None
    room: Optional[str] = None
    note: Optional[str] = None


class StudentProfile(BaseModel):
    id: int
    full_name: str
    phone: str
    class_group: Optional[ClassGroupOut]

    class Config:
        orm_mode = True


class MeResponse(BaseModel):
    role: Literal["student", "teacher"]
    profile: Union[TeacherProfile, StudentProfile]
