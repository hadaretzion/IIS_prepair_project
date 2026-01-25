import csv

from sqlmodel import select

from backend.services import ingest
from backend.models import QuestionBank, QuestionType


def test_normalize_topics():
    assert ingest.normalize_topics('["Python", "SQL"]') == ["Python", "SQL"]
    assert ingest.normalize_topics("Python, SQL") == ["Python", "SQL"]
    assert ingest.normalize_topics("Docker") == ["Docker"]


def test_generate_question_id():
    row = {"question": "What is REST?"}
    question_id = ingest.generate_question_id("open", row, 1)
    assert question_id.startswith("open:")


def test_ingest_open_questions_with_topics(db_session, tmp_path):
    csv_path = tmp_path / "open.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "topics", "category"])
        writer.writeheader()
        writer.writerow({"question": "Tell me about yourself", "topics": "communication", "category": "behavioral"})

    count = ingest.ingest_open_questions_with_topics(db_session, csv_path)
    assert count == 1
    stored = db_session.exec(
        select(QuestionBank).where(QuestionBank.question_type == QuestionType.OPEN)
    ).first()
    assert stored is not None
