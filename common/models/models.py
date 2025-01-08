from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from config import Base

class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    auth_code = Column(String, nullable=False)

    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    # Связь с сессиями
    sessions = relationship("UserSession", back_populates="teacher", cascade="all, delete-orphan")

    # Связь с тестами
    tests = relationship("Test", back_populates="teacher", cascade="all, delete-orphan")
    # Связь с экзаменами
    exams = relationship("Exam", back_populates="teacher", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    # Связь с сессиями
    sessions = relationship("UserSession", back_populates="student", cascade="all, delete-orphan")

    # Связь со старой моделью StudentTestResult (если вы продолжаете её использовать)
    test_results = relationship("StudentTestResult", back_populates="student", cascade="all, delete-orphan")

    # ВАЖНО: Связь с новой моделью StudentResult
    #       чтобы работать с "student = relationship('Student', back_populates='results')"
    results = relationship("StudentResult", back_populates="student", cascade="all, delete-orphan")


class TeachersAuthCode(Base):
    __tablename__ = "teachers_auth_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    is_used = Column(Boolean, default=False)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_type = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)
    refresh_token = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)

    teacher = relationship("Teacher", back_populates="sessions")
    student = relationship("Student", back_populates="sessions")


class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'

    id = Column(Integer, primary_key=True, index=True)
    user_type = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)

    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    teacher = relationship("Teacher", back_populates="tests")

    grade = Column(Integer, nullable=True)
    subject = Column(String, nullable=True)

    # Вопросы теста
    questions = relationship("Question", back_populates="test", cascade="all, delete-orphan")

    # Связь со старой моделью StudentTestResult
    results = relationship("StudentTestResult", back_populates="test", cascade="all, delete-orphan")

    # ВАЖНО: Связь с новой моделью StudentResult
    #        т.к. в StudentResult: `test = relationship('Test', back_populates='student_results')`
    student_results = relationship("StudentResult", back_populates="test", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_type = Column(String, nullable=False)  # 'text_input','multiple_choice','single_choice'
    question_text = Column(String, nullable=False)

    options = Column(JSON, nullable=True)
    correct_answers = Column(JSON, nullable=True)
    text_answer = Column(String, nullable=True)

    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    test = relationship("Test", back_populates="questions")


class StudentTestResult(Base):
    __tablename__ = "student_test_results"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    student = relationship("Student", back_populates="test_results")

    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    test = relationship("Test", back_populates="results")

    submitted_at = Column(DateTime, default=datetime.utcnow)
    grade = Column(String, nullable=True)

    # Конкретные ответы на вопросы
    answers = relationship("StudentAnswer", back_populates="result", cascade="all, delete-orphan")


class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, index=True)

    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    question = relationship("Question")  # можно back_populates, если нужно

    result_id = Column(Integer, ForeignKey("student_test_results.id"), nullable=False)
    result = relationship("StudentTestResult", back_populates="answers")

    chosen_options = Column(JSON, nullable=True)
    text_input = Column(String, nullable=True)
    is_correct = Column(Boolean, nullable=True)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    teacher = relationship("Teacher")  # можно back_populates, если нужен


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)

    grade = Column(Integer, nullable=True)
    subject = Column(String, nullable=True)
    time_limit_minutes = Column(Integer, nullable=True)

    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    teacher = relationship("Teacher", back_populates="exams")

    questions = relationship("ExamQuestion", back_populates="exam", cascade="all, delete-orphan")

    # Связь с новой моделью StudentResult (exam_id)
    student_results = relationship("StudentResult", back_populates="exam", cascade="all, delete-orphan")


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    question_type = Column(String, nullable=False)
    question_text = Column(String, nullable=False)

    options = Column(JSON, nullable=True)
    correct_answers = Column(JSON, nullable=True)
    text_answer = Column(String, nullable=True)

    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    exam = relationship("Exam", back_populates="questions")


class StudentResult(Base):
    __tablename__ = "student_results"

    id = Column(Integer, primary_key=True, index=True)

    # Ссылка на студента
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    student = relationship("Student", back_populates="results")

    # Ссылка на test или exam:
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=True)
    test = relationship("Test", back_populates="student_results")

    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=True)
    exam = relationship("Exam", back_populates="student_results")

    # Авто-оценка (процент)
    score = Column(Float, nullable=False)
    final_grade = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # (Опционально) можно хранить grade/subject:
    grade = Column(Integer, nullable=True)
    subject = Column(String, nullable=True)
