from typing import List, Optional, Literal, Any
from pydantic import BaseModel


QuestionType = Literal["select", "checkbox", "text"]
AssignmentType = Literal["practice", "homework"]


class AssignmentQuestion(BaseModel):
    type: QuestionType
    prompt: str
    options: Optional[List[str]] = None
    required: bool = True
    points: int
    correct_answer: Optional[Any] = None


class AssignmentCreate(BaseModel):
    class_id: int
    subject: str
    topic_id: int
    type: AssignmentType
    title: str
    description: Optional[str] = None
    max_attempts: int
    published: bool = True
    questions: List[AssignmentQuestion]


class AssignmentUpdate(BaseModel):
    class_id: Optional[int] = None
    subject: Optional[str] = None
    topic_id: Optional[int] = None
    type: Optional[AssignmentType] = None
    title: Optional[str] = None
    description: Optional[str] = None
    max_attempts: Optional[int] = None
    published: Optional[bool] = None
    questions: Optional[List[AssignmentQuestion]] = None


class AssignmentOut(BaseModel):
    id: int
    topic_id: int
    title: str
    type: AssignmentType
    max_attempts: int
    published: bool

    class Config:
        orm_mode = True


class AssignmentDetailOut(BaseModel):
    id: int
    title: str
    type: AssignmentType
    topic_id: int
    max_attempts: int
    questions: List[AssignmentQuestion]

    class Config:
        orm_mode = True


class StudentAssignmentOut(BaseModel):
    id: int
    title: str
    type: AssignmentType
    max_attempts: int
    attempts_used: int
    attempts_left: int
    last_grade: Optional[int] = None


class SubmissionOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    attempt_no: int
    answers: dict
    score: int
    grade: int
    submitted_at: str


class SubmissionList(BaseModel):
    items: List[SubmissionOut]
    page: int
    page_size: int
    total: int


class AssignmentSubmitRequest(BaseModel):
    answers: dict


class AssignmentSubmitResponse(BaseModel):
    ok: bool
    attempt_no: int
    score: int
    grade: int
    attempts_left: int
