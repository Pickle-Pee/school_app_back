from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    topics = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    theories = relationship("Theory", back_populates="subject", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="subject", cascade="all, delete-orphan")
    teachers = relationship("User", back_populates="subject")
