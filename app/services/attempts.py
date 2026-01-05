from sqlalchemy.orm import Session

from app.models import Submission


def get_attempts_used(db: Session, student_id: int, assignment_id: int) -> int:
    return db.query(Submission).filter(
        Submission.student_id == student_id,
        Submission.assignment_id == assignment_id,
    ).count()


def reset_attempts_for_student(db: Session, student_id: int, assignment_id: int) -> None:
    db.query(Submission).filter(
        Submission.student_id == student_id,
        Submission.assignment_id == assignment_id,
    ).delete(synchronize_session=False)
    db.commit()
