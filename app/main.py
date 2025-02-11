import os
import shutil
from datetime import datetime, timedelta
from typing import Union, List

from fastapi import Depends, HTTPException, status, UploadFile, Form, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from common.models import models
from common.models.models import UserSession, Teacher, Student, Material, Exam, ExamQuestion, Test, StudentResult
from common.schemas import schemas
from common.schemas.schemas import (
    StudentCreate, TeacherCreate, TeacherAuth, BaseUser, PasswordReset,
    PasswordResetRequest, TeacherSch, StudentSch,
    StudentTestSubmit, StudentTestResultOut, GradeUpdate, UserProfile, RefreshTokenRequest, LogoutRequest, StudentOut,
    TestCreate, ExamCreate, ExamOut, ExamDetailOut, TestOut, ExamQuestionOut, ExamQuestionCreate, SubmitResult,
    StudentExamSubmit, StudentResultOut
)
from common.utils import utils  # Наш файл utils.py
from common.utils.utils import get_db, get_current_user, get_current_teacher, get_current_student, \
    calculate_grade_from_score, do_autograde_exam, do_autograde_test
from config import (
    Base, SessionLocal, app, SECRET_KEY,
    ALGORITHM, REFRESH_TOKEN_EXPIRE_DAYS, logger
)

Base.metadata.create_all(bind=SessionLocal.kw['bind'])


# -----------------------
# Регистрация
# -----------------------
@app.post("/register/student", response_model=StudentSch)
def register_student(student: StudentCreate, db: Session = Depends(utils.get_db)):
    db_student = utils.get_student_by_email(db, email=student.email)
    if db_student:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    new_student = utils.create_student(db=db, student=student)
    logger.info(f"Новый ученик зарегистрирован: {new_student.email}")
    return new_student


@app.post("/register/teacher", response_model=TeacherSch)
def register_teacher(teacher: TeacherCreate, db: Session = Depends(utils.get_db)):
    code_entry = utils.get_unused_auth_code(db, code=teacher.auth_code)
    if not code_entry:
        raise HTTPException(status_code=400, detail="Неверный или использованный код авторизации")
    new_teacher = utils.create_teacher(db=db, teacher=teacher, code_entry=code_entry)
    logger.info(f"Новый учитель зарегистрирован: {new_teacher.email}")
    return new_teacher


# -----------------------
# Логин, рефреш
# -----------------------
@app.post("/login")
def login(auth: TeacherAuth, db: Session = Depends(utils.get_db)):
    # Определяем, кто логинится: учитель (если есть auth_code) или студент
    if auth.auth_code:
        db_user = utils.get_teacher_by_email(db, email=auth.email)
        if not db_user or db_user.auth_code != auth.auth_code:
            logger.warning(f"Неудачная попытка входа для учителя: {auth.email}")
            raise HTTPException(status_code=401, detail="Неверные учетные данные или код авторизации")
        user_type = "teacher"
    else:
        db_user = utils.get_student_by_email(db, email=auth.email)
        if not db_user:
            logger.warning(f"Неудачная попытка входа для ученика: {auth.email}")
            raise HTTPException(status_code=401, detail="Неверные учетные данные")
        user_type = "student"

    if not utils.verify_password(auth.password, db_user.password):
        logger.warning(f"Неверный пароль для пользователя: {auth.email}")
        raise HTTPException(status_code=401, detail="Неверные учетные данные")

    # Генерация токенов
    access_token_expires = timedelta(minutes=15)
    access_token = utils.create_access_token(
        data={
            "sub": db_user.email,
            "user_type": user_type
        },
        expires_delta=access_token_expires
    )
    refresh_token = utils.create_refresh_token(
        data={
            "sub": db_user.email,
            "user_type": user_type
        }
    )

    # Сохранение сессии
    session = UserSession(
        user_type=user_type,
        user_id=db_user.id,
        refresh_token=refresh_token,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    db.commit()

    logger.info(f"Пользователь вошёл в систему: {db_user.email}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@app.get("/me", response_model=UserProfile)
def get_me(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    if isinstance(current_user, TeacherSch):
        teacher = db.query(Teacher).filter(Teacher.id == current_user.id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher not found")
        return UserProfile(
            email=teacher.email,
            first_name=teacher.first_name or "",
            last_name=teacher.last_name or "",
            role="teacher"
        )
    else:
        student = db.query(Student).filter(Student.id == current_user.id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        return UserProfile(
            email=student.email,
            first_name=student.first_name or "",
            last_name=student.last_name or "",
            role="student"
        )


@app.post("/refresh")
def refresh_token(
        body: RefreshTokenRequest,
        db: Session = Depends(get_db)
):
    refresh_token = body.refresh_token

    session = db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_type = session.user_type
    user_id = session.user_id

    access_token = utils.create_access_token(
        data={
            "sub": user_id,
            "user_type": user_type
        }
    )
    new_refresh_token = utils.create_refresh_token(
        data={
            "sub": user_id,
            "user_type": user_type
        }
    )

    session.refresh_token = new_refresh_token
    session.expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@app.post("/logout")
def logout(
        request: LogoutRequest,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)  # <-- при желании, если требуем access_token
):
    """
    Эндпоинт для 'разлогина'.
    Получаем refresh_token, удаляем соответствующую запись в БД.
    """
    # Ищем запись в таблице `user_sessions` по refresh_token
    session = db.query(UserSession).filter(
        UserSession.refresh_token == request.refresh_token
    ).first()

    if not session:
        # Можем просто вернуть 200,
        # но для наглядности выкинем 404, если токен не найден
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")

    # Удаляем сессию из БД
    db.delete(session)
    db.commit()

    return {"message": "Вы успешно разлогинились"}


# -----------------------
# Пример защищённого эндпоинта
# -----------------------
@app.get("/protected")
def protected_route(current_user: BaseUser = Depends(utils.get_current_user)):
    return {"message": f"Hello, {current_user.email}!"}


# -----------------------
# Сброс пароля
# -----------------------
@app.post("/reset-password-request")
def reset_password_request(request: PasswordResetRequest, db: Session = Depends(utils.get_db)):
    # Проверка, существует ли пользователь
    user = utils.get_teacher_by_email(db, email=request.email)
    user_type = 'teacher'
    if not user:
        user = utils.get_student_by_email(db, email=request.email)
        user_type = 'student'
    if not user:
        # Чтобы предотвратить перебор пользователей, возвращаем общий ответ
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Если такой email существует, ссылка для сброса пароля была отправлена."
        )

    # Создание токена сброса пароля
    token = utils.create_password_reset_token(db, user_type=user_type, user_id=user.id)

    return {
        "message": "Ссылка для сброса пароля отправлена на ваш email.",
        "reset_token": token
    }


@app.post("/reset-password")
def reset_password(request: PasswordReset, db: Session = Depends(utils.get_db)):
    # Получение токена сброса пароля
    reset_token = utils.get_password_reset_token(db, token=request.token)
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный токен сброса пароля."
        )
    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Срок действия токена сброса пароля истек."
        )

    # Получение пользователя по токену
    if reset_token.user_type == 'teacher':
        user = db.query(Teacher).filter(Teacher.id == reset_token.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь не найден."
            )
        # Проверка кода авторизации
        if not request.auth_code or request.auth_code != user.auth_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный код авторизации."
            )
    elif reset_token.user_type == 'student':
        user = db.query(Student).filter(Student.id == reset_token.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь не найден."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный тип пользователя."
        )

    # Хэширование нового пароля
    hashed_password = utils.hash_password(request.new_password)
    user.password = hashed_password
    db.commit()

    # Удаление токена сброса пароля
    utils.delete_password_reset_token(db, token=request.token)

    return {"message": "Пароль успешно сброшен."}


# ------------------------------------
# READ: список тестов (для всех - учитель и ученик)
# ------------------------------------
@app.get("/tests", response_model=List[schemas.TestOut])
def get_tests(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Возвращаем список тестов.
    Если user_type == 'teacher', показываем только тесты, принадлежащие учителю.
    Если student, показываем все тесты (или по другой логике, например grade).
    """
    if hasattr(current_user, 'auth_code'):
        # Это учитель
        teacher_id = current_user.id
        tests = db.query(models.Test).filter(models.Test.teacher_id == teacher_id).all()
        return tests
    else:
        # Это студент
        # Например, вернём все тесты
        tests = db.query(models.Test).all()
        return tests

# ------------------------------------
# READ: детали теста (для всех - учитель и ученик)
# ------------------------------------
@app.get("/tests/{test_id}", response_model=schemas.TestDetailOut)
def get_test_detail(
    test_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Возвращаем детали одного теста + вопросы.
    Учитель - проверяем, что тест принадлежит ему.
    Ученик - просто отдаём, если тест есть (или проверяем, доступен ли).
    """
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")

    if hasattr(current_user, 'auth_code'):
        # Учитель
        if test.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Тест не принадлежит вам")
        return test
    else:
        # Ученик
        # Просто возвращаем
        return test

# ------------------------------------
# CREATE: создать тест (только учитель)
# ------------------------------------
@app.post("/tests", response_model=schemas.TestOut)
def create_new_test(
    test_data: schemas.TestCreate,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(get_current_teacher)  # <-- только учитель
):
    """
    Создаёт новый тест. Доступно только учителю.
    """
    test = models.Test(
        title=test_data.title,
        description=test_data.description,
        grade=test_data.grade,
        subject=test_data.subject,
        teacher_id=current_teacher.id
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test

# ------------------------------------
# UPDATE: обновить тест (только учитель)
# ------------------------------------
@app.put("/tests/{test_id}", response_model=schemas.TestOut)
def update_my_test(
    test_id: int,
    update_data: schemas.TestUpdate,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(get_current_teacher)
):
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test or test.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Тест не найден или не принадлежит вам")

    if update_data.title is not None:
        test.title = update_data.title
    if update_data.description is not None:
        test.description = update_data.description
    if update_data.grade is not None:
        test.grade = update_data.grade
    if update_data.subject is not None:
        test.subject = update_data.subject

    db.commit()
    db.refresh(test)
    return test

# ------------------------------------
# DELETE: удалить тест (только учитель)
# ------------------------------------
@app.delete("/tests/{test_id}")
def delete_my_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(get_current_teacher)
):
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test or test.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Тест не найден")
    db.delete(test)
    db.commit()
    return {"message": "Тест удалён"}

# ------------------------------------
# Работа с вопросами
# ------------------------------------
@app.post("/tests/{test_id}/questions", response_model=schemas.QuestionOut)
def add_question_to_test(
    test_id: int,
    question_data: schemas.QuestionCreate,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(get_current_teacher)  # Только учитель
):
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test or test.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Тест не найден")
    question = models.Question(
        question_type=question_data.question_type,
        question_text=question_data.question_text,
        options=question_data.options,
        correct_answers=question_data.correct_answers,
        text_answer=question_data.text_answer,
        test_id=test_id
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question

@app.put("/tests/{test_id}/questions/{question_id}", response_model=schemas.QuestionOut)
def update_question_in_test(
    test_id: int,
    question_id: int,
    question_update: schemas.QuestionUpdate,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(get_current_teacher)
):
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test or test.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Тест не найден")

    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question or question.test_id != test.id:
        raise HTTPException(status_code=404, detail="Вопрос не найден в данном тесте")

    if question_update.question_type is not None:
        question.question_type = question_update.question_type
    if question_update.question_text is not None:
        question.question_text = question_update.question_text
    if question_update.options is not None:
        question.options = question_update.options
    if question_update.correct_answers is not None:
        question.correct_answers = question_update.correct_answers
    if question_update.text_answer is not None:
        question.text_answer = question_update.text_answer

    db.commit()
    db.refresh(question)
    return question

@app.delete("/tests/{test_id}/questions/{question_id}")
def delete_question_in_test(
    test_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(get_current_teacher)
):
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test or test.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Тест не найден")

    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question or question.test_id != test.id:
        raise HTTPException(status_code=404, detail="Вопрос не найден в данном тесте")

    db.delete(question)
    db.commit()
    return {"message": "Вопрос удалён"}

# ------------------------------------
# Прохождение теста (ученик) и результаты
# ------------------------------------
@app.post("/student/submit-test", response_model=schemas.StudentTestResultOut)
def submit_test_result(
    data: schemas.StudentTestSubmit,
    db: Session = Depends(get_db),
    current_student: models.Student = Depends(get_current_student)
):
    """
    Ученик отправляет результат прохождения теста.
    """
    test = db.query(models.Test).filter(models.Test.id == data.test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")

    # Логика сохранения результатов
    result = utils.create_student_test_result(
        db,
        student_id=current_student.id,
        test_id=test.id,
        answers_data=data.answers
    )
    return result

@app.get("/teacher/tests/{test_id}/results", response_model=List[schemas.StudentTestResultOut])
def get_test_results(
    test_id: int,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(get_current_teacher)
):
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test or test.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Тест не найден или не принадлежит вам")

    results = utils.get_test_results_for_test(db, test_id=test_id)
    return results

@app.get("/teacher/tests/{test_id}/results/{result_id}", response_model=schemas.StudentTestResultOut)
def get_test_result_detail(
    test_id: int,
    result_id: int,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(get_current_teacher)
):
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test or test.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Тест не найден или не принадлежит вам")

    result = utils.get_student_test_result_by_id(db, result_id)
    if not result or result.test_id != test_id:
        raise HTTPException(status_code=404, detail="Результат не найден")

    return result

@app.put("/teacher/tests/{test_id}/results/{result_id}/grade", response_model=schemas.StudentTestResultOut)
def set_grade_for_result(
    test_id: int,
    result_id: int,
    grade_data: schemas.GradeUpdate,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(get_current_teacher)
):
    """
    Учитель выставляет/обновляет оценку за результат теста.
    """
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test or test.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Тест не найден или не принадлежит вам")

    result = utils.get_student_test_result_by_id(db, result_id)
    if not result or result.test_id != test_id:
        raise HTTPException(status_code=404, detail="Результат не найден")

    updated_result = utils.update_grade(db, result, grade_data.grade)
    return updated_result

@app.post("/materials/upload")
def upload_material(
        title: str = Form(...),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_teacher: Teacher = Depends(get_current_teacher),
):
    """
    Учитель загружает PDF.
    """
    # Проверяем расширение файла, например ".pdf"
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Только PDF-файлы допустимы.")

    # Папка, куда сохраняем файлы
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)  # Создаём, если не существует

    save_path = os.path.join(upload_dir, file.filename)

    # Сохраняем файл на диск
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Создаём запись в БД
    material = Material(
        title=title,
        file_path=save_path,
        teacher_id=current_teacher.id,
        uploaded_at=datetime.utcnow()
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    return {
        "id": material.id,
        "title": material.title,
        "file_path": material.file_path
    }


@app.get("/materials")
def list_materials(db: Session = Depends(get_db)):
    """
    Возвращает список всех материалов
    """
    materials = db.query(Material).all()
    result = []
    for m in materials:
        result.append({
            "id": m.id,
            "title": m.title,
            "file_path": m.file_path,
            "uploaded_at": m.uploaded_at,
        })
    return result


@app.get("/materials/{material_id}")
def get_material(material_id: int, db: Session = Depends(get_db)):
    """
    Возвращает информацию о материале (без самих байтов)
    """
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return {
        "id": material.id,
        "title": material.title,
        "file_path": material.file_path,
        "uploaded_at": material.uploaded_at,
    }


@app.get("/materials/{material_id}/content")
def get_material_content(material_id: int, db: Session = Depends(get_db)):
    """
    Возвращает байты PDF, чтобы клиент мог открыть внутри приложения
    """
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Читаем файл
    try:
        with open(material.file_path, "rb") as f:
            pdf_bytes = f.read()
    except OSError:
        raise HTTPException(status_code=404, detail="File not found on disk")

    return Response(content=pdf_bytes, media_type="application/pdf")


@app.get("/teacher/students", response_model=List[StudentOut])
def get_all_students(
        db: Session = Depends(get_db),
        current_teacher: Teacher = Depends(get_current_teacher)
):
    """
    Возвращает список всех учеников (доступно только для учителя).
    """
    students = db.query(Student).all()
    return students


# ------------------------------
# GET (список экзаменов): учитель видит только свои, ученик — все
# ------------------------------
@app.get("/exams", response_model=List[ExamOut])
def get_exams(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Возвращает список экзаменов.
    - Если user_type == teacher -> вернуть только экзамены учителя
    - Если user_type == student -> вернуть все (или по логике)
    """
    if hasattr(current_user, 'auth_code'):
        # Значит это Teacher
        exams = db.query(Exam).filter(Exam.teacher_id == current_user.id).all()
        return exams
    else:
        # Student
        # Вернуть все экзамены, или какую-то фильтрацию (например, по grade/subject)
        # Для простоты: все
        exams = db.query(Exam).all()
        return exams

# ------------------------------
# GET (детали экзамена): учитель проверяем принадлежность, ученик - просто отдаём
# ------------------------------
@app.get("/exams/{exam_id}", response_model=ExamDetailOut)
def get_exam_detail(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Экзамен не найден")

    if hasattr(current_user, 'auth_code'):
        # Teacher
        if exam.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Экзамен не принадлежит вам")
        return exam
    else:
        # Student
        # Просто возвращаем, если экзамен есть
        return exam


# ------------------------------
# CREATE (добавить экзамен) - только учитель
# ------------------------------
@app.post("/exams", response_model=ExamOut)
def create_exam(
    exam_data: ExamCreate,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    exam = Exam(
        title=exam_data.title,
        description=exam_data.description,
        grade=exam_data.grade,
        subject=exam_data.subject,
        time_limit_minutes=exam_data.time_limit_minutes,
        teacher_id=current_teacher.id
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


# ------------------------------
# UPDATE (обновить экзамен) - только учитель
# ------------------------------
@app.put("/exams/{exam_id}", response_model=ExamOut)
def update_exam(
    exam_id: int,
    update_data: ExamCreate,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam or exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Экзамен не найден или не принадлежит вам")

    exam.title = update_data.title
    exam.description = update_data.description
    exam.grade = update_data.grade
    exam.subject = update_data.subject
    exam.time_limit_minutes = update_data.time_limit_minutes

    db.commit()
    db.refresh(exam)
    return exam


# ------------------------------
# DELETE (удалить экзамен) - только учитель
# ------------------------------
@app.delete("/exams/{exam_id}")
def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam or exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Экзамен не найден")
    db.delete(exam)
    db.commit()
    return {"message": "Экзамен удалён"}


# --------------------------------------
# Работа с вопросами (ExamQuestion) - только учитель
# --------------------------------------
@app.post("/exams/{exam_id}/questions", response_model=ExamQuestionOut)
def add_question_to_exam(
    exam_id: int,
    question_data: ExamQuestionCreate,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam or exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Экзамен не найден")

    question = ExamQuestion(
        question_type=question_data.question_type,
        question_text=question_data.question_text,
        options=question_data.options,
        correct_answers=question_data.correct_answers,
        text_answer=question_data.text_answer,
        exam_id=exam_id
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@app.put("/exams/{exam_id}/questions/{question_id}", response_model=ExamQuestionOut)
def update_question_in_exam(
    exam_id: int,
    question_id: int,
    question_data: ExamQuestionCreate,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam or exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Экзамен не найден")

    question = db.query(ExamQuestion).filter(ExamQuestion.id == question_id).first()
    if not question or question.exam_id != exam_id:
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    question.question_type = question_data.question_type
    question.question_text = question_data.question_text
    question.options = question_data.options
    question.correct_answers = question_data.correct_answers
    question.text_answer = question_data.text_answer
    db.commit()
    db.refresh(question)
    return question


@app.delete("/exams/{exam_id}/questions/{question_id}")
def delete_question_in_exam(
    exam_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam or exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=404, detail="Экзамен не найден")

    question = db.query(ExamQuestion).filter(ExamQuestion.id == question_id).first()
    if not question or question.exam_id != exam_id:
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    db.delete(question)
    db.commit()
    return {"message": "Вопрос удалён"}


@app.post("/student/tests/submit", response_model=SubmitResult)
def submit_test_result(
    data: StudentTestSubmit,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    test = db.query(Test).filter(Test.id == data.test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")

    (correct_count, total_questions, score) = do_autograde_test(test, data.answers)

    final_grade = calculate_grade_from_score(score)

    new_result = StudentResult(
        student_id=current_student.id,
        assessment_type='test',
        assessment_id=test.id,
        score=score,
        final_grade=final_grade,
        grade=test.grade,
        subject=test.subject,
    )
    db.add(new_result)
    db.commit()
    db.refresh(new_result)

    return SubmitResult(
        total_questions=total_questions,
        correct_count=correct_count,
        score=score,
        final_grade=final_grade
    )

@app.post("/student/exams/submit", response_model=SubmitResult)
def submit_exam_result(
    data: StudentExamSubmit,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    exam = db.query(Exam).filter(Exam.id == data.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Экзамен не найден")

    (correct_count, total_questions, score) = do_autograde_exam(exam, data.answers)

    final_grade = calculate_grade_from_score(score)

    new_result = StudentResult(
        student_id=current_student.id,
        assessment_type='exam',
        assessment_id=exam.id,
        score=score,
        final_grade=final_grade,
        grade=exam.grade,
        subject=exam.subject,
    )
    db.add(new_result)
    db.commit()
    db.refresh(new_result)

    return SubmitResult(
        total_questions=total_questions,
        correct_count=correct_count,
        score=score,
        final_grade=final_grade
    )


@app.get("/student/my-results", response_model=List[StudentResultOut])
def get_my_results(
        db: Session = Depends(get_db),
        current_student: Student = Depends(get_current_student)
):
    """
    Возвращает все результаты (тесты и экзамены) для текущего ученика.
    Объединяем данные из таблиц StudentTestResult и StudentResult,
    приводя их к единому формату, требуемому схемой StudentResultOut.
    """
    # Результаты тестов
    test_results = db.query(models.StudentTestResult) \
        .filter(models.StudentTestResult.student_id == current_student.id) \
        .all()
    # Результаты экзаменов
    exam_results = db.query(models.StudentResult) \
        .filter(models.StudentResult.student_id == current_student.id) \
        .all()

    combined_results = []

    for r in test_results:
        combined_results.append({
            "id": r.id,
            "student_id": r.student_id,
            "test_id": r.test_id,
            "exam_id": None,
            "score": getattr(r, "score", 0.0),
            "final_grade": r.grade,
            "created_at": r.submitted_at,
            "grade": None,
            "subject": None,
        })

    for r in exam_results:
        combined_results.append({
            "id": r.id,
            "student_id": r.student_id,
            "test_id": None,
            "exam_id": r.assessment_id,
            "score": r.score,
            "final_grade": r.final_grade,
            "created_at": r.created_at,
            "grade": r.grade,
            "subject": r.subject,
        })

    # Сортируем результаты по дате (от новых к старым)
    combined_results.sort(key=lambda x: x["created_at"], reverse=True)

    return combined_results


@app.get("/teacher/student/{student_id}/results", response_model=List[StudentResultOut])
def get_results_for_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    """
    Возвращает результаты ученика с ID = student_id.
    Можно добавить проверку, действительно ли этот ученик 'принадлежит' учителю, если есть такая логика.
    """
    # Если нужна проверка, что student_id в "классе" учителя, можно тут сделать:
    # student = db.query(Student).filter(Student.id == student_id).first()
    # if student.class_id != current_teacher.class_id:  # пример
    #     raise HTTPException(403, "Ученик не относится к вам")

    results = db.query(StudentResult).filter(StudentResult.student_id == student_id).all()
    return results