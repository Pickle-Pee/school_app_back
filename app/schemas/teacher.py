from typing import List, Optional
from pydantic import BaseModel

from app.schemas.class_group import ClassGroupOut


class TeacherProfileOut(BaseModel):
    id: int
    full_name: str
    phone: str
    subject: Optional[str] = None
    email: Optional[str] = None
    room: Optional[str] = None
    note: Optional[str] = None


class TopicOut(BaseModel):
    id: int
    title: str


class GradeSummaryStudent(BaseModel):
    id: int
    full_name: str
    avg_grade: float


class GradeSummaryResponse(BaseModel):
    class_group: ClassGroupOut
    students: List[GradeSummaryStudent]


class GradeByTopicItem(BaseModel):
    student_id: int
    student_name: str
    assignment_id: int
    assignment_title: str
    attempt_no: int
    score: int
    grade: int
    submitted_at: str


class GradeByTopicResponse(BaseModel):
    items: List[GradeByTopicItem]
    page: int
    page_size: int
    total: int


class ResetAttemptsRequest(BaseModel):
    student_id: int
    assignment_id: int


class ResetAttemptsResponse(BaseModel):
    ok: bool
