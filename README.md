# Цифровой класс (Backend)

Backend на FastAPI для приложения «Цифровой класс».

## Возможности
- JWT авторизация (учитель/ученик).
- Работа с классами, предметами, темами.
- Теория (текст/файл) и практика/ДЗ (assignments).
- Сдачи учеников, попытки, оценки.

## Требования
- Python 3.11+
- PostgreSQL (или SQLite для тестов)

## Настройка окружения
Создайте файл `.env` в корне проекта:

```
DATABASE_URL=postgresql://admin:admin@localhost:6000/new_school
SECRET_KEY=change-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
FILES_DIR=uploads
FILES_BASE_URL=
```

## Установка

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Миграции (Alembic)

```
alembic upgrade head
```

## Запуск

```
uvicorn app.main:app --reload
```

## Сиды (демо-данные)

```
python -m app.db.init_db
```

### Демо пользователи
- Учитель: `+79990000001` / `teacher123` / `TCH-001`
- Учитель: `+79990000002` / `teacher123` / `TCH-002`
- Ученик: `+79990001001` / `student123`
- Ученик: `+79990001002` / `student123`

## Тесты

```
pytest
```

## Основные эндпоинты
- `POST /auth/login`
- `POST /auth/set-password`
- `GET /me`
- `GET /teacher/profile`
- `GET /teacher/classes`
- `GET /teacher/grades/summary`
- `GET /teacher/grades/by-topic`
- `POST /teacher/attempts/reset`
- `GET /student/profile`
- `GET /student/subjects`
- `GET /student/topics`
- `GET /student/theory`
- `GET /student/assignments`
- `POST /student/assignments/{id}/submit`
