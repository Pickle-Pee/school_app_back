from typing import Optional
from pydantic import BaseModel


class TheoryOut(BaseModel):
    id: int
    topic_id: int
    topic_title: str
    kind: str
    text: Optional[str] = None
    file_url: Optional[str] = None
    updated_at: str


class TheoryCreate(BaseModel):
    class_id: int
    subject: str
    topic_id: int
    kind: str
    text: Optional[str] = None


class TheoryUpdate(BaseModel):
    topic_id: Optional[int] = None
    kind: Optional[str] = None
    text: Optional[str] = None
    subject: Optional[str] = None
    class_id: Optional[int] = None
