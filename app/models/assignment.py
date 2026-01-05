import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class AssignmentType(str, enum.Enum):
    practice = "practice"
    homework = "homework"


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    class_group_id = Column(Integer, ForeignKey("class_groups.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)

    type = Column(Enum(AssignmentType, name="assignment_type"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    max_attempts = Column(Integer, nullable=False, default=1)
    published = Column(Boolean, default=True)
    questions = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class_group = relationship("ClassGroup", back_populates="assignments")
    subject = relationship("Subject", back_populates="assignments")
    topic = relationship("Topic", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    attempt_no = Column(Integer, nullable=False)
    answers = Column(JSON, nullable=False)
    score = Column(Integer, nullable=False)
    grade = Column(Integer, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", back_populates="submissions")
