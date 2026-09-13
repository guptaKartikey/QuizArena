import pytest
from fastapi.testclient import TestClient
from backend.main import app
from database.database import SessionLocal
from database.repositories import create_quiz, add_questions_to_quiz

client = TestClient(app)

def test_api_admin_login():
    from database.models import Admin
    from backend.auth import hash_password
    db = SessionLocal()
    try:
        # Create a test admin
        test_email = "testadmin@example.com"
        test_password = "secure_test_pass"
        # Ensure admin exists for test without dropping the entire table
        Admin.__table__.create(db.get_bind(), checkfirst=True)
        admin_obj = db.query(Admin).filter(Admin.email == test_email).first()
        if not admin_obj:
            db.add(Admin(email=test_email, password_hash=hash_password(test_password)))
            db.commit()

        res = client.post("/api/admin/login", json={"email": test_email, "password": test_password})
        assert res.status_code == 200
        assert res.json()["success"] is True
    finally:
        db.close()

def test_api_join_quiz():
    db = SessionLocal()
    try:
        quiz = create_quiz(db, name="API Test Quiz", max_participants=5)
        add_questions_to_quiz(db, quiz.id, [{"question_text": "Sample", "options": ["A", "B"], "correct_answer": "A"}])

        res = client.post("/api/join", json={
            "join_code": quiz.join_code,
            "name": "TestPlayer"
        })

        assert res.status_code == 200
        data = res.json()["data"]
        assert data["name"] == "TestPlayer"
        assert data["quiz_id"] == quiz.id
    finally:
        db.close()

def test_api_qr_code():
    db = SessionLocal()
    try:
        quiz = create_quiz(db, name="QR Test Quiz")
        res = client.get(f"/api/qr/{quiz.id}")
        assert res.status_code == 200
        assert res.headers["content-type"] == "image/png"
    finally:
        db.close()
