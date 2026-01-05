from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class ClassGroup(Base):
    __tablename__ = "class_groups"
    __table_args__ = (UniqueConstraint("grade", "letter", name="uq_class_groups_grade_letter"),)

    id = Column(Integer, primary_key=True)
    grade = Column(Integer, nullable=False)
    letter = Column(String, nullable=False)
    name = Column(String, nullable=False, unique=True)

    students = relationship("User", back_populates="class_group")
    topics = relationship("Topic", back_populates="class_group", cascade="all, delete-orphan")
    theories = relationship("Theory", back_populates="class_group", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="class_group", cascade="all, delete-orphan")
    teacher_links = relationship("TeacherClass", back_populates="class_group", cascade="all, delete-orphan")
