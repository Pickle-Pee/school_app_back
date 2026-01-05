import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.api.deps import get_db
from app.core.security import hash_password
from app.models import User, UserRole, ClassGroup, Subject


@pytest.fixture(scope="session")
def db_engine(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    get_settings.cache_clear()
    settings = get_settings()
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine):
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_data(db_session):
    class_group = ClassGroup(grade=7, letter="а", name="7а")
    subject = Subject(name="Математика")
    db_session.add_all([class_group, subject])
    db_session.flush()

    teacher = User(
        full_name="Иванов Иван",
        phone="+79990000001",
        password_hash=hash_password("teacher123"),
        role=UserRole.teacher,
        teacher_code="TCH-001",
        subject_id=subject.id,
    )
    student = User(
        full_name="Петров Пётр",
        phone="+79990000002",
        password_hash=hash_password("student123"),
        role=UserRole.student,
        class_group_id=class_group.id,
    )
    db_session.add_all([teacher, student])
    db_session.commit()
    return {"teacher": teacher, "student": student}
