from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    class_group_id = Column(Integer, ForeignKey("class_groups.id"), nullable=False)

    subject = relationship("Subject", back_populates="topics")
    class_group = relationship("ClassGroup", back_populates="topics")
    theories = relationship("Theory", back_populates="topic", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="topic", cascade="all, delete-orphan")
