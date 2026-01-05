import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class TheoryKind(str, enum.Enum):
    text = "text"
    file = "file"


class Theory(Base):
    __tablename__ = "theories"

    id = Column(Integer, primary_key=True)
    class_group_id = Column(Integer, ForeignKey("class_groups.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)

    kind = Column(Enum(TheoryKind, name="theory_kind"), nullable=False)
    text = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class_group = relationship("ClassGroup", back_populates="theories")
    subject = relationship("Subject", back_populates="theories")
    topic = relationship("Topic", back_populates="theories")
