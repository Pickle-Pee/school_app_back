import enum
from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    role = Column(Enum(UserRole, name="user_role"), nullable=False)

    teacher_code = Column(String, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    class_group_id = Column(Integer, ForeignKey("class_groups.id"), nullable=True)

    room = Column(String, nullable=True)
    note = Column(String, nullable=True)

    class_group = relationship("ClassGroup", back_populates="students")
    subject = relationship("Subject", back_populates="teachers")

    submissions = relationship("Submission", back_populates="student", cascade="all, delete-orphan")
    teacher_classes = relationship("TeacherClass", back_populates="teacher", cascade="all, delete-orphan")
