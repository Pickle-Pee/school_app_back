"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = sa.Enum("student", "teacher", name="user_role")
theory_kind_enum = sa.Enum("text", "file", name="theory_kind")
assignment_type_enum = sa.Enum("practice", "homework", name="assignment_type")


def upgrade() -> None:
    user_role_enum.create(op.get_bind(), checkfirst=True)
    theory_kind_enum.create(op.get_bind(), checkfirst=True)
    assignment_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "class_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("letter", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.UniqueConstraint("grade", "letter", name="uq_class_groups_grade_letter"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False, unique=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("teacher_code", sa.String(), nullable=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=True),
        sa.Column("class_group_id", sa.Integer(), sa.ForeignKey("class_groups.id"), nullable=True),
        sa.Column("room", sa.String(), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
    )

    op.create_table(
        "teacher_classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("class_group_id", sa.Integer(), sa.ForeignKey("class_groups.id"), nullable=False),
        sa.UniqueConstraint("teacher_id", "class_group_id", name="uq_teacher_class"),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("class_group_id", sa.Integer(), sa.ForeignKey("class_groups.id"), nullable=False),
    )

    op.create_table(
        "theories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_group_id", sa.Integer(), sa.ForeignKey("class_groups.id"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("kind", theory_kind_enum, nullable=False),
        sa.Column("text", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_group_id", sa.Integer(), sa.ForeignKey("class_groups.id"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("type", assignment_type_enum, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("submissions")
    op.drop_table("assignments")
    op.drop_table("theories")
    op.drop_table("topics")
    op.drop_table("teacher_classes")
    op.drop_table("users")
    op.drop_table("subjects")
    op.drop_table("class_groups")

    assignment_type_enum.drop(op.get_bind(), checkfirst=True)
    theory_kind_enum.drop(op.get_bind(), checkfirst=True)
    user_role_enum.drop(op.get_bind(), checkfirst=True)
