from typing import Dict, Tuple

from app.models import Assignment


def grade_submission(assignment: Assignment, answers: Dict) -> Tuple[int, int]:
    total_points = 0
    earned_points = 0

    for index, question in enumerate(assignment.questions, start=1):
        points = int(question.get("points", 1))
        total_points += points
        key = f"q{index}"
        answer = answers.get(key)
        correct_answer = question.get("correct_answer")
        q_type = question.get("type")

        if correct_answer is None:
            continue

        if q_type == "select":
            if answer == correct_answer:
                earned_points += points
        elif q_type == "checkbox":
            if isinstance(answer, list) and set(answer) == set(correct_answer):
                earned_points += points
        elif q_type == "text":
            if isinstance(answer, str) and str(correct_answer).strip().lower() == answer.strip().lower():
                earned_points += points

    score = int((earned_points / total_points) * 100) if total_points else 0

    if score >= 90:
        grade = 5
    elif score >= 75:
        grade = 4
    elif score >= 60:
        grade = 3
    else:
        grade = 2

    return score, grade
