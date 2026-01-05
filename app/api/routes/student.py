from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_student
from app.models import User, Subject, Topic, Theory, Assignment, Submission, AssignmentType
from app.schemas.student import (
    StudentProfileOut,
    SubjectOut,
    TopicOut,
    TheoryOut,
    AssignmentOut,
    AssignmentDetailOut,
    GradesResponse,
)
from app.schemas.assignment import AssignmentSubmitRequest, AssignmentSubmitResponse
from app.services.attempts import get_attempts_used
from app.services.grading import grade_submission

router = APIRouter()


def get_subject(db: Session, name: str) -> Subject:
    subject = db.query(Subject).filter(Subject.name == name).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router.get("/profile", response_model=StudentProfileOut)
def student_profile(current_student: User = Depends(get_current_student)) -> StudentProfileOut:
    if not current_student.class_group:
        raise HTTPException(status_code=400, detail="Student class not set")
    return StudentProfileOut(
        id=current_student.id,
        full_name=current_student.full_name,
        phone=current_student.phone,
        class_group=current_student.class_group,
    )


@router.get("/subjects", response_model=list[SubjectOut])
def student_subjects(
    db: Session = Depends(get_db),
    current_student: User = Depends(get_current_student),
):
    subjects = db.query(Subject).all()
    return subjects


@router.get("/topics", response_model=list[TopicOut])
def student_topics(
    subject: str = Query(...),
    db: Session = Depends(get_db),
    current_student: User = Depends(get_current_student),
):
    if not current_student.class_group_id:
        raise HTTPException(status_code=400, detail="Student class not set")
    subject_obj = get_subject(db, subject)
    return (
        db.query(Topic)
        .filter(Topic.subject_id == subject_obj.id, Topic.class_group_id == current_student.class_group_id)
        .all()
    )


@router.get("/theory", response_model=list[TheoryOut])
def student_theory(
    subject: str = Query(...),
    topic_id: int = Query(...),
    db: Session = Depends(get_db),
    current_student: User = Depends(get_current_student),
):
    subject_obj = get_subject(db, subject)
    theories = (
        db.query(Theory)
        .filter(Theory.subject_id == subject_obj.id, Theory.topic_id == topic_id)
        .all()
    )
    result = []
    for theory in theories:
        result.append(
            TheoryOut(
                id=theory.id,
                kind=theory.kind.value,
                text=theory.text,
                file_url=f"/files/{theory.id}" if theory.file_path else None,
                updated_at=theory.updated_at.isoformat() if theory.updated_at else "",
            )
        )
    return result


@router.get("/assignments", response_model=list[AssignmentOut])
def student_assignments(
    subject: str = Query(...),
    type: AssignmentType = Query(...),
    topic_id: int = Query(...),
    db: Session = Depends(get_db),
    current_student: User = Depends(get_current_student),
):
    subject_obj = get_subject(db, subject)
    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.subject_id == subject_obj.id,
            Assignment.topic_id == topic_id,
            Assignment.type == type,
            Assignment.published.is_(True),
        )
        .all()
    )

    output = []
    for assignment in assignments:
        attempts_used = get_attempts_used(db, current_student.id, assignment.id)
        last_submission = (
            db.query(Submission)
            .filter(Submission.student_id == current_student.id, Submission.assignment_id == assignment.id)
            .order_by(Submission.attempt_no.desc())
            .first()
        )
        output.append(
            AssignmentOut(
                id=assignment.id,
                title=assignment.title,
                type=assignment.type.value,
                max_attempts=assignment.max_attempts,
                attempts_used=attempts_used,
                attempts_left=max(assignment.max_attempts - attempts_used, 0),
                last_grade=last_submission.grade if last_submission else None,
            )
        )
    return output


@router.get("/assignments/{assignment_id}", response_model=AssignmentDetailOut)
def student_assignment_detail(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_student: User = Depends(get_current_student),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    attempts_used = get_attempts_used(db, current_student.id, assignment.id)
    return AssignmentDetailOut(
        id=assignment.id,
        title=assignment.title,
        type=assignment.type.value,
        topic_id=assignment.topic_id,
        max_attempts=assignment.max_attempts,
        attempts_used=attempts_used,
        attempts_left=max(assignment.max_attempts - attempts_used, 0),
        questions=assignment.questions,
    )


@router.post("/assignments/{assignment_id}/submit", response_model=AssignmentSubmitResponse)
def submit_assignment(
    assignment_id: int,
    payload: AssignmentSubmitRequest,
    db: Session = Depends(get_db),
    current_student: User = Depends(get_current_student),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    attempts_used = get_attempts_used(db, current_student.id, assignment.id)
    if attempts_used >= assignment.max_attempts:
        raise HTTPException(status_code=400, detail="No attempts left")

    score, grade = grade_submission(assignment, payload.answers)
    submission = Submission(
        assignment_id=assignment.id,
        student_id=current_student.id,
        attempt_no=attempts_used + 1,
        answers=payload.answers,
        score=score,
        grade=grade,
    )
    db.add(submission)
    db.commit()

    attempts_left = max(assignment.max_attempts - (attempts_used + 1), 0)
    return AssignmentSubmitResponse(
        ok=True,
        attempt_no=attempts_used + 1,
        score=score,
        grade=grade,
        attempts_left=attempts_left,
    )


@router.get("/grades", response_model=GradesResponse)
def student_grades(
    subject: str = Query(...),
    db: Session = Depends(get_db),
    current_student: User = Depends(get_current_student),
):
    subject_obj = get_subject(db, subject)
    submissions = (
        db.query(Submission, Assignment, Topic)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(Topic, Assignment.topic_id == Topic.id)
        .filter(
            Submission.student_id == current_student.id,
            Assignment.subject_id == subject_obj.id,
        )
        .order_by(Submission.submitted_at.desc())
        .all()
    )

    items = []
    grades = []
    for submission, assignment, topic in submissions:
        grades.append(submission.grade)
        items.append(
            {
                "topic_id": topic.id,
                "topic_title": topic.title,
                "assignment_title": assignment.title,
                "type": assignment.type.value,
                "grade": submission.grade,
                "submitted_at": submission.submitted_at.isoformat(),
            }
        )

    avg_grade = sum(grades) / len(grades) if grades else 0.0
    return GradesResponse(avg_grade=round(avg_grade, 2), items=items)
