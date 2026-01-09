from datetime import datetime
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_teacher
from app.core.config import get_settings
from app.models import User, UserRole, ClassGroup, Subject, Topic, Theory, TheoryKind, Assignment, Submission, AssignmentType
from app.models.teacher_class import TeacherClass
from app.schemas.class_group import ClassGroupOut
from app.schemas.teacher import (
    TeacherProfileOut,
    TopicOut,
    GradeSummaryResponse,
    GradeByTopicResponse,
    ResetAttemptsRequest,
    ResetAttemptsResponse,
)
from app.schemas.theory import TheoryOut, TheoryCreate, TheoryUpdate
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentOut,
    AssignmentDetailOut,
    SubmissionList,
)
from app.services.attempts import reset_attempts_for_student

router = APIRouter()
settings = get_settings()


def get_subject(db: Session, name: str) -> Subject:
    subject = db.query(Subject).filter(Subject.name == name).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router.get("/profile", response_model=TeacherProfileOut)
def teacher_profile(current_teacher: User = Depends(get_current_teacher)) -> TeacherProfileOut:
    return TeacherProfileOut(
        id=current_teacher.id,
        full_name=current_teacher.full_name,
        phone=current_teacher.phone,
        subject=current_teacher.subject.name if current_teacher.subject else None,
        email=current_teacher.email,
        room=current_teacher.room,
        note=current_teacher.note,
    )


@router.get("/classes", response_model=list[ClassGroupOut])
def teacher_classes(
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    links = db.query(TeacherClass).filter(TeacherClass.teacher_id == current_teacher.id).all()
    return [link.class_group for link in links]


@router.get("/topics", response_model=list[TopicOut])
def teacher_topics(
    class_id: int = Query(...),
    subject: str = Query(...),
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    subject_obj = get_subject(db, subject)
    topics = (
        db.query(Topic)
        .filter(Topic.class_group_id == class_id, Topic.subject_id == subject_obj.id)
        .all()
    )
    return topics


@router.get("/grades/summary", response_model=GradeSummaryResponse)
def grades_summary(
    class_id: int = Query(...),
    subject: str = Query(...),
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    subject_obj = get_subject(db, subject)
    class_group = db.query(ClassGroup).filter(ClassGroup.id == class_id).first()
    if not class_group:
        raise HTTPException(status_code=404, detail="Class not found")

    students = (
        db.query(User)
        .filter(User.role == UserRole.student, User.class_group_id == class_id)
        .all()
    )

    data = []
    for student in students:
        submissions = (
            db.query(Submission)
            .join(Assignment, Submission.assignment_id == Assignment.id)
            .filter(
                Submission.student_id == student.id,
                Assignment.subject_id == subject_obj.id,
                Assignment.class_group_id == class_id,
            )
            .all()
        )
        if submissions:
            avg_grade = sum(s.grade for s in submissions) / len(submissions)
        else:
            avg_grade = 0.0
        data.append({"id": student.id, "full_name": student.full_name, "avg_grade": round(avg_grade, 2)})

    return GradeSummaryResponse(
        class_group=ClassGroupOut.model_validate(class_group), students=data)


@router.get("/grades/by-topic", response_model=GradeByTopicResponse)
def grades_by_topic(
    class_id: int = Query(...),
    topic_id: int = Query(...),
    type: AssignmentType = Query(...),
    subject: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    subject_obj = get_subject(db, subject)
    base_query = (
        db.query(Submission, Assignment, User)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(User, Submission.student_id == User.id)
        .filter(
            Assignment.class_group_id == class_id,
            Assignment.topic_id == topic_id,
            Assignment.type == type,
            Assignment.subject_id == subject_obj.id,
        )
        .order_by(Submission.submitted_at.desc())
    )

    total = base_query.count()
    rows = base_query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for submission, assignment, student in rows:
        items.append(
            {
                "student_id": student.id,
                "student_name": student.full_name,
                "assignment_id": assignment.id,
                "assignment_title": assignment.title,
                "attempt_no": submission.attempt_no,
                "score": submission.score,
                "grade": submission.grade,
                "submitted_at": submission.submitted_at.isoformat(),
            }
        )

    return GradeByTopicResponse(items=items, page=page, page_size=page_size, total=total)


@router.post("/attempts/reset", response_model=ResetAttemptsResponse)
def reset_attempts(
    request: ResetAttemptsRequest,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
) -> ResetAttemptsResponse:
    reset_attempts_for_student(db, request.student_id, request.assignment_id)
    return ResetAttemptsResponse(ok=True)


@router.get("/theory", response_model=list[TheoryOut])
def list_theory(
    class_id: int = Query(...),
    subject: str = Query(...),
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    subject_obj = get_subject(db, subject)
    theories = (
        db.query(Theory)
        .filter(Theory.class_group_id == class_id, Theory.subject_id == subject_obj.id)
        .all()
    )
    result = []
    for theory in theories:
        result.append(
            TheoryOut(
                id=theory.id,
                topic_id=theory.topic_id,
                topic_title=theory.topic.title,
                kind=theory.kind.value,
                text=theory.text,
                file_url=f"/files/{theory.id}" if theory.file_path else None,
                updated_at=theory.updated_at.isoformat() if theory.updated_at else "",
            )
        )
    return result


@router.post("/theory", response_model=TheoryOut)
async def create_theory(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        class_id = int(form.get("class_id"))
        subject = form.get("subject")
        topic_id = int(form.get("topic_id"))
        kind = form.get("kind")
        upload = form.get("file")
        if kind != "file" or upload is None:
            raise HTTPException(status_code=400, detail="File upload required for file kind")
        subject_obj = get_subject(db, subject)
        os.makedirs(settings.files_dir, exist_ok=True)
        file_path = f"{settings.files_dir}/{datetime.utcnow().timestamp()}_{upload.filename}"
        with open(file_path, "wb") as output:
            output.write(await upload.read())
        theory = Theory(
            class_group_id=class_id,
            subject_id=subject_obj.id,
            topic_id=topic_id,
            kind=TheoryKind.file,
            file_path=file_path,
        )
    else:
        payload = await request.json()
        data = TheoryCreate(**payload)
        subject_obj = get_subject(db, data.subject)
        theory = Theory(
            class_group_id=data.class_id,
            subject_id=subject_obj.id,
            topic_id=data.topic_id,
            kind=TheoryKind.text,
            text=data.text,
        )

    db.add(theory)
    db.commit()
    db.refresh(theory)

    return TheoryOut(
        id=theory.id,
        topic_id=theory.topic_id,
        topic_title=theory.topic.title,
        kind=theory.kind.value,
        text=theory.text,
        file_url=f"/files/{theory.id}" if theory.file_path else None,
        updated_at=theory.updated_at.isoformat() if theory.updated_at else "",
    )


@router.patch("/theory/{theory_id}", response_model=TheoryOut)
def update_theory(
    theory_id: int,
    payload: TheoryUpdate,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    theory = db.query(Theory).filter(Theory.id == theory_id).first()
    if not theory:
        raise HTTPException(status_code=404, detail="Theory not found")

    if payload.class_id is not None:
        theory.class_group_id = payload.class_id
    if payload.topic_id is not None:
        theory.topic_id = payload.topic_id
    if payload.subject is not None:
        subject_obj = get_subject(db, payload.subject)
        theory.subject_id = subject_obj.id
    if payload.kind is not None:
        theory.kind = TheoryKind(payload.kind)
    if payload.text is not None:
        theory.text = payload.text

    db.commit()
    db.refresh(theory)

    return TheoryOut(
        id=theory.id,
        topic_id=theory.topic_id,
        topic_title=theory.topic.title,
        kind=theory.kind.value,
        text=theory.text,
        file_url=f"/files/{theory.id}" if theory.file_path else None,
        updated_at=theory.updated_at.isoformat() if theory.updated_at else "",
    )


@router.delete("/theory/{theory_id}")
def delete_theory(
    theory_id: int,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    theory = db.query(Theory).filter(Theory.id == theory_id).first()
    if not theory:
        raise HTTPException(status_code=404, detail="Theory not found")
    db.delete(theory)
    db.commit()
    return {"ok": True}


@router.get("/assignments", response_model=list[AssignmentOut])
def list_assignments(
    class_id: int = Query(...),
    subject: str = Query(...),
    type: AssignmentType = Query(...),
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    subject_obj = get_subject(db, subject)
    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.class_group_id == class_id,
            Assignment.subject_id == subject_obj.id,
            Assignment.type == type,
        )
        .all()
    )
    return assignments


@router.post("/assignments", response_model=dict)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    subject_obj = get_subject(db, payload.subject)
    assignment = Assignment(
        class_group_id=payload.class_id,
        subject_id=subject_obj.id,
        topic_id=payload.topic_id,
        type=payload.type,
        title=payload.title,
        description=payload.description,
        max_attempts=payload.max_attempts,
        published=payload.published,
        questions=[q.dict() for q in payload.questions],
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {"id": assignment.id}


@router.get("/assignments/{assignment_id}", response_model=AssignmentDetailOut)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return AssignmentDetailOut(
        id=assignment.id,
        title=assignment.title,
        type=assignment.type.value,
        topic_id=assignment.topic_id,
        max_attempts=assignment.max_attempts,
        questions=assignment.questions,
    )


@router.patch("/assignments/{assignment_id}", response_model=AssignmentDetailOut)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if payload.class_id is not None:
        assignment.class_group_id = payload.class_id
    if payload.subject is not None:
        assignment.subject_id = get_subject(db, payload.subject).id
    if payload.topic_id is not None:
        assignment.topic_id = payload.topic_id
    if payload.type is not None:
        assignment.type = payload.type
    if payload.title is not None:
        assignment.title = payload.title
    if payload.description is not None:
        assignment.description = payload.description
    if payload.max_attempts is not None:
        assignment.max_attempts = payload.max_attempts
    if payload.published is not None:
        assignment.published = payload.published
    if payload.questions is not None:
        assignment.questions = [q.dict() for q in payload.questions]

    db.commit()
    db.refresh(assignment)

    return AssignmentDetailOut(
        id=assignment.id,
        title=assignment.title,
        type=assignment.type.value,
        topic_id=assignment.topic_id,
        max_attempts=assignment.max_attempts,
        questions=assignment.questions,
    )


@router.delete("/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
    return {"ok": True}


@router.get("/submissions", response_model=SubmissionList)
def list_submissions(
    assignment_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher),
):
    base_query = (
        db.query(Submission, User)
        .join(User, Submission.student_id == User.id)
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.submitted_at.desc())
    )
    total = base_query.count()
    rows = base_query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for submission, student in rows:
        items.append(
            {
                "id": submission.id,
                "student_id": student.id,
                "student_name": student.full_name,
                "attempt_no": submission.attempt_no,
                "answers": submission.answers,
                "score": submission.score,
                "grade": submission.grade,
                "submitted_at": submission.submitted_at.isoformat(),
            }
        )

    return SubmissionList(items=items, page=page, page_size=page_size, total=total)
