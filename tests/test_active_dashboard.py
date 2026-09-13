import pytest
from fastapi.testclient import TestClient
from backend.main import app
from database.database import init_db, SessionLocal
from database.repositories import create_quiz, add_questions_to_quiz, create_participant, record_answer

client = TestClient(app)

def test_active_live_data_endpoint():
    db = SessionLocal()
    try:
        quiz = create_quiz(db, name="Live Dashboard Test Quiz")
        q_list = add_questions_to_quiz(db, quiz.id, [{"question_text": "Capital of France?", "options": ["A. Madrid", "B. Paris"], "correct_answer": "B"}])
        q_id = q_list[0].id
        p = create_participant(db, quiz.id, name="TestLivePlayer")
        record_answer(db, quiz.id, q_id, p.id, "B", True, 2.31, 10.0)

        res = client.get(f"/api/admin/quiz/{quiz.id}/live_data")
        assert res.status_code == 200
        data = res.json()
        assert data["quiz_name"] == "Live Dashboard Test Quiz"
        assert data["answered_count"] >= 1
        assert data["correct_count"] >= 1
        assert len(data["participant_responses"]) >= 1
        assert data["answer_distribution"]["B"] >= 1
    finally:
        db.close()

def test_admin_announcement_endpoint():
    db = SessionLocal()
    try:
        quiz = create_quiz(db, name="Announce Test Quiz")
        res = client.post(f"/api/admin/quiz/{quiz.id}/announce", json={"message": "10 seconds remaining!"})
        assert res.status_code == 200
        assert res.json()["success"] is True
    finally:
        db.close()

def test_extend_timer_endpoint():
    db = SessionLocal()
    try:
        quiz = create_quiz(db, name="Timer Extend Quiz")
        res = client.post(f"/api/admin/quiz/{quiz.id}/extend_timer", json={"seconds": 10})
        assert res.status_code == 200
        assert res.json()["added"] == 10
    finally:
        db.close()

def test_participant_history_endpoint():
    db = SessionLocal()
    try:
        quiz = create_quiz(db, name="History Test Quiz")
        q_list = add_questions_to_quiz(db, quiz.id, [{"question_text": "Sample Q", "options": ["A", "B"], "correct_answer": "A"}])
        q_id = q_list[0].id
        p = create_participant(db, quiz.id, name="HistoryPlayer")
        record_answer(db, quiz.id, q_id, p.id, "A", True, 1.5, 10.0)

        res = client.get(f"/api/admin/quiz/{quiz.id}/participant/{p.id}/history")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "HistoryPlayer"
        assert len(data["history"]) >= 1
        assert data["history"][0]["selected_answer"] == "A"
    finally:
        db.close()
