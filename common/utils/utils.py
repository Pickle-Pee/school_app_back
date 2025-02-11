import secrets
from datetime import timedelta, datetime
from typing import Union, Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from common.models import models
from common.models.models import (
    Student, TeachersAuthCode, Teacher,
    PasswordResetToken, StudentTestResult, StudentAnswer, Test
)
from common.schemas import schemas
from common.schemas.schemas import (
    StudentCreate, TeacherCreate, TeacherSch, StudentSch,
    StudentAnswerCreate, AnswerItem
)
from config import (
    ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS, SessionLocal
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------------
# Студенты / Учителя / Авторизация
# ----------------------------
def get_student_by_email(db: Session, email: str) -> Optional[Student]:
    return db.query(Student).filter(Student.email == email).first()


def create_student(db: Session, student: StudentCreate):
    hashed_password = hash_password(student.password)
    db_student = Student(
        email=student.email,
        password=hashed_password,
        first_name=student.first_name,
        last_name=student.last_name
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


def get_unused_auth_code(db: Session, code: str) -> Optional[TeachersAuthCode]:
    try:
        return db.query(TeachersAuthCode).filter(
            TeachersAuthCode.code == code,
            TeachersAuthCode.is_used == False
        ).one()
    except NoResultFound:
        return None


def create_teacher(db: Session, teacher: TeacherCreate, code_entry: TeachersAuthCode):
    hashed_password = hash_password(teacher.password)
    db_teacher = Teacher(
        email=teacher.email,
        password=hashed_password,
        auth_code=teacher.auth_code,
        first_name=teacher.first_name,
        last_name=teacher.last_name
    )
    db.add(db_teacher)
    code_entry.is_used = True
    db.commit()
    db.refresh(db_teacher)
    return db_teacher


def get_teacher_by_email(db: Session, email: str) -> Optional[Teacher]:
    return db.query(Teacher).filter(Teacher.email == email).first()


# ----------------------------
# Пароли
# ----------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ----------------------------
# Токены (access/refresh)
# ----------------------------
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ----------------------------
# Сброс пароля
# ----------------------------
def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def create_password_reset_token(
        db: Session,
        user_type: str,
        user_id: int,
        expires_delta: timedelta = timedelta(hours=1)
) -> str:
    token = generate_reset_token()
    expires_at = datetime.utcnow() + expires_delta
    reset_token = PasswordResetToken(
        user_type=user_type,
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return token


def get_password_reset_token(db: Session, token: str) -> Optional[PasswordResetToken]:
    return db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()


def delete_password_reset_token(db: Session, token: str) -> None:
    reset_token = get_password_reset_token(db, token)
    if reset_token:
        db.delete(reset_token)
        db.commit()


# ----------------------------
# get_current_user / get_current_teacher / get_current_student
# ----------------------------
def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> Union[TeacherSch, StudentSch]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_type: str = payload.get("user_type")
        if not email or not user_type:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if user_type == "teacher":
        teacher = get_teacher_by_email(db, email)
        if teacher:
            return TeacherSch(id=teacher.id, email=teacher.email, auth_code=teacher.auth_code)
        else:
            raise credentials_exception
    elif user_type == "student":
        student = get_student_by_email(db, email)
        if student:
            return StudentSch(id=student.id, email=student.email)
        else:
            raise credentials_exception
    else:
        raise credentials_exception


def get_current_teacher(
        current_user: Union[TeacherSch, StudentSch] = Depends(get_current_user),
        db: Session = Depends(get_db)
) -> Teacher:
    if isinstance(current_user, TeacherSch):
        teacher_in_db = db.query(Teacher).filter(Teacher.id == current_user.id).first()
        if not teacher_in_db:
            raise HTTPException(status_code=404, detail="Учитель не найден")
        return teacher_in_db
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль учителя",
        )


def get_current_student(
        current_user: Union[TeacherSch, StudentSch] = Depends(get_current_user),
        db: Session = Depends(get_db)
) -> Student:
    if isinstance(current_user, StudentSch):
        student_in_db = db.query(Student).filter(Student.id == current_user.id).first()
        if not student_in_db:
            raise HTTPException(status_code=404, detail="Ученик не найден")
        return student_in_db
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль ученика",
        )


# ----------------------------
# Тесты, Вопросы
# ----------------------------
def create_test(db: Session, teacher_id: int, data: schemas.TestCreate) -> models.Test:
    test = models.Test(
        title=data.title,
        description=data.description,
        teacher_id=teacher_id
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


def get_test_by_id(db: Session, test_id: int) -> Optional[models.Test]:
    return db.query(models.Test).filter(models.Test.id == test_id).first()


def get_tests_by_teacher(db: Session, teacher_id: int) -> List[models.Test]:
    return db.query(models.Test).filter(models.Test.teacher_id == teacher_id).all()


def update_test(db: Session, test: models.Test, data: schemas.TestUpdate) -> models.Test:
    if data.title is not None:
        test.title = data.title
    if data.description is not None:
        test.description = data.description
    db.commit()
    db.refresh(test)
    return test


def delete_test(db: Session, test: models.Test) -> None:
    db.delete(test)
    db.commit()


def create_question(db: Session, test_id: int, data: schemas.QuestionCreate) -> models.Question:
    question = models.Question(
        question_type=data.question_type,
        question_text=data.question_text,
        options=data.options,
        correct_answers=data.correct_answers,
        text_answer=data.text_answer,
        test_id=test_id
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_question_by_id(db: Session, question_id: int) -> Optional[models.Question]:
    return db.query(models.Question).filter(models.Question.id == question_id).first()


def update_question(db: Session, question: models.Question, data: schemas.QuestionUpdate) -> models.Question:
    if data.question_type is not None:
        question.question_type = data.question_type
    if data.question_text is not None:
        question.question_text = data.question_text
    if data.options is not None:
        question.options = data.options
    if data.correct_answers is not None:
        question.correct_answers = data.correct_answers
    if data.text_answer is not None:
        question.text_answer = data.text_answer
    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, question: models.Question) -> None:
    db.delete(question)
    db.commit()


# ----------------------------
# Результаты теста (StudentTestResult), ответы (StudentAnswer)
# ----------------------------
def create_student_test_result(
        db: Session,
        student_id: int,
        test_id: int,
        answers_data: List[AnswerItem]
) -> models.StudentTestResult:
    # Создаём запись о прохождении теста с пустым грейдом
    result = models.StudentTestResult(
        student_id=student_id,
        test_id=test_id,
        submitted_at=datetime.utcnow(),
        grade=None  # Изначально грейд не задан
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    # Обрабатываем каждый ответ
    for ans in answers_data:
        question = db.query(models.Question).filter(models.Question.id == ans.question_id).first()
        if not question:
            # Если вопрос не найден, пропускаем его
            continue

        is_correct = None
        text_input = None
        chosen_options = None

        if question.question_type == "text_input":
            # Для текстового вопроса ожидаем, что ans.answer – строка
            if question.text_answer and isinstance(ans.answer, str):
                text_input = ans.answer
                is_correct = (question.text_answer.strip().lower() == text_input.strip().lower())
        elif question.question_type in ["single_choice", "multiple_choice"]:
            # Для вариантов выбора ожидаем, что ans.answer – список строк или строка
            if question.correct_answers and ans.answer is not None:
                if isinstance(ans.answer, list):
                    chosen_options = ans.answer
                elif isinstance(ans.answer, str):
                    chosen_options = [ans.answer]
                if chosen_options is not None:
                    set_submitted = set(chosen_options)
                    set_correct = set(question.correct_answers)
                    is_correct = (set_submitted == set_correct)

        student_answer = models.StudentAnswer(
            question_id=question.id,
            result_id=result.id,
            chosen_options=chosen_options,
            text_input=text_input,
            is_correct=is_correct
        )
        db.add(student_answer)

    db.commit()

    # Выполняем автопроверку для теста:
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден для автопроверки")
    correct_count, total_questions, score = do_autograde_test(test, answers_data)
    final_grade = calculate_grade_from_score(score)

    # Обновляем результат теста с вычисленным грейдом
    result.grade = final_grade
    db.commit()
    db.refresh(result)
    return result


def get_student_test_result_by_id(db: Session, result_id: int) -> Optional[models.StudentTestResult]:
    return db.query(models.StudentTestResult).filter(models.StudentTestResult.id == result_id).first()


def get_test_results_for_test(db: Session, test_id: int) -> List[models.StudentTestResult]:
    return db.query(models.StudentTestResult).filter(models.StudentTestResult.test_id == test_id).all()


def update_grade(db: Session, result: models.StudentTestResult, grade: str) -> models.StudentTestResult:
    result.grade = grade
    db.commit()
    db.refresh(result)
    return result


def get_current_student(
        current_user: Union[TeacherSch, StudentSch] = Depends(get_current_user),
        db: Session = Depends(get_db)
) -> Student:
    """
    Гарантируем, что current_user — студент.
    Возвращаем модель Student из БД, или кидаем 403, если нет.
    """
    # Проверяем, является ли current_user именно StudentSch
    if not isinstance(current_user, StudentSch):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль ученика",
        )

    # Получаем саму модель Student
    student_in_db = db.query(Student).filter(Student.id == current_user.id).first()
    if not student_in_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ученик не найден",
        )
    return student_in_db


def do_autograde_test(test, answers_list):
    question_map = {q.id: q for q in test.questions}
    total = len(test.questions)
    correct = 0

    for ans_item in answers_list:
        qid = ans_item.question_id
        user_answer = ans_item.answer
        question = question_map.get(qid)
        if not question:
            continue

        if question.question_type in ["multiple_choice", "single_choice"]:
            correct_this = False
            if question.question_type == "multiple_choice":
                if isinstance(user_answer, list) and question.correct_answers:
                    if set(user_answer) == set(question.correct_answers):
                        correct_this = True
            else:
                if isinstance(user_answer, str) and question.correct_answers:
                    if user_answer in question.correct_answers:
                        correct_this = True
            if correct_this:
                correct += 1

        elif question.question_type == "text_input":
            if question.text_answer and isinstance(user_answer, str):
                if user_answer.strip().lower() == question.text_answer.strip().lower():
                    correct += 1

    score = 0.0
    if total > 0:
        score = (correct / total) * 100.0
    return (correct, total, score)


def do_autograde_exam(exam, answers_list):
    question_map = {q.id: q for q in exam.questions}
    total = len(exam.questions)
    correct = 0

    for ans_item in answers_list:
        qid = ans_item.question_id
        user_answer = ans_item.answer
        question = question_map.get(qid)
        if not question:
            continue

        if question.question_type in ["multiple_choice", "single_choice"]:
            correct_this = False
            if question.question_type == "multiple_choice":
                if isinstance(user_answer, list) and question.correct_answers:
                    if set(user_answer) == set(question.correct_answers):
                        correct_this = True
            else:
                if isinstance(user_answer, str) and question.correct_answers:
                    if user_answer in question.correct_answers:
                        correct_this = True
            if correct_this:
                correct += 1

        elif question.question_type == "text_input":
            if question.text_answer and isinstance(user_answer, str):
                if user_answer.strip().lower() == question.text_answer.strip().lower():
                    correct += 1

    score = 0.0
    if total > 0:
        score = (correct / total) * 100.0
    return (correct, total, score)


def calculate_grade_from_score(score: float) -> str:
    """
    Пример простейшей шкалы:
    90+ = 5
    75+ = 4
    60+ = 3
    иначе = 2
    """
    if score >= 90:
        return "5"
    elif score >= 75:
        return "4"
    elif score >= 60:
        return "3"
    else:
        return "2"
