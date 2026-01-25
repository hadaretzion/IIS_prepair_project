from backend.services.selection import build_interview_plan
from tests.backend.fixtures.sample_data import create_job_spec, create_question_bank, create_user
from backend.models import QuestionType


def test_build_interview_plan_basic(db_session):
    user = create_user(db_session, user_id="user-select")
    job_spec = create_job_spec(db_session, job_spec_id="job-select")
    create_question_bank(
        db_session,
        question_type=QuestionType.OPEN,
        question_text="Describe a tough bug you fixed.",
        question_id="open:select1",
        topics=["python"],
    )
    create_question_bank(
        db_session,
        question_type=QuestionType.CODE,
        question_text="Reverse a linked list.",
        question_id="code:select1",
        topics=["linked list"],
        difficulty="Easy",
    )

    plan = build_interview_plan(
        user_id=user.id,
        job_spec_id=job_spec.id,
        cv_version_id=None,
        mode="direct",
        settings={"num_open": 1, "num_code": 1, "duration_minutes": 10},
        session=db_session,
    )

    assert plan["total"] == 2
    assert len(plan["items"]) == 2
    assert all("selected_question_id" in item for item in plan["items"])
