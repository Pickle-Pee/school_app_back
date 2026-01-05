from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import ClassGroup, Subject, Topic, User, UserRole, Theory, TheoryKind, Assignment, AssignmentType
from app.models.teacher_class import TeacherClass


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.query(User).first():
            return

        class_7a = ClassGroup(grade=7, letter="а", name="7а")
        class_7b = ClassGroup(grade=7, letter="б", name="7б")
        db.add_all([class_7a, class_7b])

        math = Subject(name="Математика")
        info = Subject(name="Информатика")
        db.add_all([math, info])
        db.flush()

        teacher_math = User(
            full_name="Иванов Иван",
            phone="+79990000001",
            email="ivanov@example.com",
            password_hash=hash_password("teacher123"),
            role=UserRole.teacher,
            teacher_code="TCH-001",
            subject_id=math.id,
            room="101",
        )
        teacher_info = User(
            full_name="Сидорова Анна",
            phone="+79990000002",
            email="sidorova@example.com",
            password_hash=hash_password("teacher123"),
            role=UserRole.teacher,
            teacher_code="TCH-002",
            subject_id=info.id,
            room="102",
        )
        student_1 = User(
            full_name="Петров Пётр",
            phone="+79990001001",
            password_hash=hash_password("student123"),
            role=UserRole.student,
            class_group=class_7a,
        )
        student_2 = User(
            full_name="Иванова Мария",
            phone="+79990001002",
            password_hash=hash_password("student123"),
            role=UserRole.student,
            class_group=class_7a,
        )

        db.add_all([teacher_math, teacher_info, student_1, student_2])
        db.flush()

        db.add_all([
            TeacherClass(teacher_id=teacher_math.id, class_group_id=class_7a.id),
            TeacherClass(teacher_id=teacher_info.id, class_group_id=class_7b.id),
        ])

        topic_1 = Topic(title="Алгебраические выражения", subject_id=math.id, class_group_id=class_7a.id)
        topic_2 = Topic(title="Программирование", subject_id=info.id, class_group_id=class_7b.id)
        db.add_all([topic_1, topic_2])
        db.flush()

        theory = Theory(
            class_group_id=class_7a.id,
            subject_id=math.id,
            topic_id=topic_1.id,
            kind=TheoryKind.text,
            text="Введение в алгебраические выражения",
        )
        db.add(theory)

        assignment = Assignment(
            class_group_id=class_7a.id,
            subject_id=math.id,
            topic_id=topic_1.id,
            type=AssignmentType.practice,
            title="ПР №1",
            description="Базовые выражения",
            max_attempts=3,
            published=True,
            questions=[
                {
                    "type": "select",
                    "prompt": "2+2= ?",
                    "options": ["3", "4"],
                    "required": True,
                    "points": 1,
                    "correct_answer": "4",
                }
            ],
        )
        db.add(assignment)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
