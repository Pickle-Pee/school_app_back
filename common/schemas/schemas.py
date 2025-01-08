from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, EmailStr


# -----------------------
# Регистрация и логин
# -----------------------
class StudentCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class TeacherCreate(StudentCreate):
    first_name: str
    last_name: str
    email: str
    password: str
    auth_code: str


class TeacherAuth(BaseModel):
    email: str
    password: str
    auth_code: Optional[str] = None


class UserProfile(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: str


class BaseUser(BaseModel):
    id: int
    email: str


class TeacherSch(BaseUser):
    auth_code: str


class StudentSch(BaseUser):
    pass


# -----------------------
# Сброс пароля
# -----------------------
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str
    auth_code: Optional[str] = None


# -----------------------
# Тесты
# -----------------------
class TestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    grade: Optional[int] = None
    subject: Optional[str] = None


class TestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class TestOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    grade: Optional[int] = None
    subject: Optional[str] = None

    class Config:
        orm_mode = True


# -----------------------
# Вопросы
# -----------------------
class QuestionBase(BaseModel):
    question_type: str  # 'text_input', 'multiple_choice', 'single_choice'
    question_text: str
    options: Optional[List[str]] = None
    correct_answers: Optional[List[str]] = None
    text_answer: Optional[str] = None


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    question_type: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answers: Optional[List[str]] = None
    text_answer: Optional[str] = None


class QuestionOut(QuestionBase):
    id: int

    class Config:
        orm_mode = True


class TestDetailOut(BaseModel):
    """Полный тест со списком вопросов"""
    id: int
    title: str
    description: Optional[str] = None
    questions: List[QuestionOut] = []

    class Config:
        orm_mode = True


# -----------------------
# Результаты прохождения теста (для учеников)
# -----------------------
class StudentAnswerCreate(BaseModel):
    """Ответ ученика на отдельный вопрос при отправке результатов"""
    question_id: int
    chosen_options: Optional[List[str]] = None  # для multiple/single_choice
    text_input: Optional[str] = None  # для text_input


class StudentTestSubmit(BaseModel):
    """Тело запроса, когда ученик отправляет результаты прохождения"""
    test_id: int
    answers: List[StudentAnswerCreate]


# -----------------------
# Результаты (для вывода) и оценка
# -----------------------
class StudentAnswerOut(BaseModel):
    question_id: int
    chosen_options: Optional[List[str]] = None
    text_input: Optional[str] = None
    is_correct: Optional[bool] = None

    class Config:
        orm_mode = True


class StudentTestResultOut(BaseModel):
    """Вывод информации о результате прохождения теста"""
    id: int
    student_id: int
    test_id: int
    submitted_at: Optional[str] = None
    grade: Optional[str] = None
    answers: List[StudentAnswerOut] = []

    class Config:
        orm_mode = True


class StudentOut(BaseModel):
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    class Config:
        orm_mode = True


class GradeUpdate(BaseModel):
    """Схема для выставления/обновления оценки учителем"""
    grade: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# Создание / обновление экзамена
class ExamCreate(BaseModel):
    title: str
    description: Optional[str] = None
    grade: Optional[int] = None
    subject: Optional[str] = None
    time_limit_minutes: Optional[int] = None


# Ответ при возврате экзамена (без списка вопросов)
class ExamOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    grade: Optional[int] = None
    subject: Optional[str] = None
    time_limit_minutes: Optional[int] = None

    class Config:
        orm_mode = True


# Для создания / обновления вопроса
class ExamQuestionCreate(BaseModel):
    question_type: str
    question_text: str
    options: Optional[List[str]] = None
    correct_answers: Optional[List[str]] = None
    text_answer: Optional[str] = None


# Ответ при возврате вопроса
class ExamQuestionOut(BaseModel):
    id: int
    question_type: str
    question_text: str
    options: Optional[List[str]] = None
    correct_answers: Optional[List[str]] = None
    text_answer: Optional[str] = None

    class Config:
        orm_mode = True


# Расширенный ответ при получении одного экзамена (вместе с вопросами)
class ExamDetailOut(ExamOut):
    questions: List[ExamQuestionOut] = []


class AnswerItem(BaseModel):
    question_id: int
    answer: Union[str, List[str], None] = None  # строка, массив строк, или null


class StudentTestSubmit(BaseModel):
    test_id: int
    answers: List[AnswerItem]


# Результат автопроверки
class SubmitResult(BaseModel):
    test_id: int
    total_questions: int
    correct_count: int
    score: float  # например, процент
    # Можно добавить grade (оценка), если хотите


class StudentResultCreate(BaseModel):
    student_id: int
    assessment_type: str  # 'test' or 'exam'
    assessment_id: int
    grade: Optional[int] = None
    subject: Optional[str] = None
    score: float
    final_grade: Optional[str] = None


class StudentResultOut(BaseModel):
    id: int
    student_id: int

    # test_id или exam_id (одно может быть None)
    test_id: Optional[int] = None
    exam_id: Optional[int] = None

    score: float  # 0..100
    final_grade: Optional[str] = None
    created_at: datetime

    # Можно включить поля grade, subject, если вы храните их в таблице
    grade: Optional[int] = None
    subject: Optional[str] = None

    class Config:
        orm_mode = True


class AnswerItem(BaseModel):
    question_id: int
    answer: Union[str, List[str], None] = None


class StudentTestSubmit(BaseModel):
    test_id: int
    answers: List[AnswerItem]


class StudentExamSubmit(BaseModel):
    exam_id: int
    answers: List[AnswerItem]


class SubmitResult(BaseModel):
    total_questions: int
    correct_count: int
    score: float
    final_grade: Optional[str] = None

    # Добавим поля, чтобы клиент знал, какой именно assessment
    test_id: Optional[int] = None
    exam_id: Optional[int] = None
