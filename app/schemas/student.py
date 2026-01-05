from typing import List, Optional
from pydantic import BaseModel

from app.schemas.class_group import ClassGroupOut


class StudentProfileOut(BaseModel):
    id: int
    full_name: str
    phone: str
    class_group: ClassGroupOut

    class Config:
        orm_mode = True


class SubjectOut(BaseModel):
    name: str


class TopicOut(BaseModel):
    id: int
    title: str


class TheoryOut(BaseModel):
    id: int
    kind: str
    text: Optional[str] = None
    file_url: Optional[str] = None
    updated_at: str


class AssignmentOut(BaseModel):
    id: int
    title: str
    type: str
    max_attempts: int
    attempts_used: int
    attempts_left: int
    last_grade: Optional[int] = None


class AssignmentDetailOut(BaseModel):
    id: int
    title: str
    type: str
    topic_id: int
    max_attempts: int
    attempts_used: int
    attempts_left: int
    questions: list


class GradeItem(BaseModel):
    topic_id: int
    topic_title: str
    assignment_title: str
    type: str
    grade: int
    submitted_at: str


class GradesResponse(BaseModel):
    avg_grade: float
    items: List[GradeItem]
