from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    SetPasswordRequest,
    SetPasswordResponse,
    MeResponse,
)
from app.schemas.class_group import ClassGroupOut
from app.schemas.teacher import (
    TeacherProfileOut,
    TopicOut as TeacherTopicOut,
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
    StudentAssignmentOut,
    SubmissionList,
    AssignmentSubmitRequest,
    AssignmentSubmitResponse,
)
from app.schemas.student import (
    StudentProfileOut,
    SubjectOut,
    TopicOut as StudentTopicOut,
    TheoryOut as StudentTheoryOut,
    AssignmentOut as StudentAssignmentListOut,
    AssignmentDetailOut as StudentAssignmentDetailOut,
    GradesResponse,
)

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "SetPasswordRequest",
    "SetPasswordResponse",
    "MeResponse",
    "ClassGroupOut",
    "TeacherProfileOut",
    "TeacherTopicOut",
    "GradeSummaryResponse",
    "GradeByTopicResponse",
    "ResetAttemptsRequest",
    "ResetAttemptsResponse",
    "TheoryOut",
    "TheoryCreate",
    "TheoryUpdate",
    "AssignmentCreate",
    "AssignmentUpdate",
    "AssignmentOut",
    "AssignmentDetailOut",
    "StudentAssignmentOut",
    "SubmissionList",
    "AssignmentSubmitRequest",
    "AssignmentSubmitResponse",
    "StudentProfileOut",
    "SubjectOut",
    "StudentTopicOut",
    "StudentTheoryOut",
    "StudentAssignmentListOut",
    "StudentAssignmentDetailOut",
    "GradesResponse",
]
