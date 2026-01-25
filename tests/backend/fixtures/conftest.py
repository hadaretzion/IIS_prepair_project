from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from backend.db import get_session
from backend.main import app
from backend.models import QuestionType
from tests.backend.fixtures.sample_data import (
    create_cv_version,
    create_job_spec,
    create_question_bank,
    create_user,
)


@pytest.fixture()
def db_engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture()
def client(db_engine):
    def override_get_session():
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_user(db_session):
    return create_user(db_session, user_id="user-123")


@pytest.fixture()
def sample_job_spec(db_session):
    return create_job_spec(db_session, job_spec_id="job-123")


@pytest.fixture()
def sample_cv_version(db_session, sample_user):
    return create_cv_version(db_session, user_id=sample_user.id)


@pytest.fixture()
def sample_questions(db_session):
    open_q = create_question_bank(
        db_session,
        question_type=QuestionType.OPEN,
        question_text="Tell me about a challenge you solved.",
        question_id="open:1",
        topics=["communication", "ownership"],
    )
    code_q = create_question_bank(
        db_session,
        question_type=QuestionType.CODE,
        question_text="Implement two-sum.",
        question_id="code:1",
        topics=["arrays", "hashmap"],
        difficulty="Easy",
    )
    return [open_q, code_q]
