from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class TeacherClass(Base):
    __tablename__ = "teacher_classes"
    __table_args__ = (UniqueConstraint("teacher_id", "class_group_id", name="uq_teacher_class"),)

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_group_id = Column(Integer, ForeignKey("class_groups.id"), nullable=False)

    teacher = relationship("User", back_populates="teacher_classes")
    class_group = relationship("ClassGroup", back_populates="teacher_links")
