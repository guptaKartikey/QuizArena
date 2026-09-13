import pytest
from database.database import init_db, SessionLocal
from database.repositories import create_quiz, add_questions_to_quiz, get_quiz_by_id
from backend.game_engine import game_engine

init_db()

@pytest.mark.asyncio
async def test_game_engine_room_state():
    db = SessionLocal()
    try:
        quiz = create_quiz(db, name="State Test Quiz", description="Testing states", max_participants=10)
        questions_data = [
            {"question_text": "Q1 Text", "options": ["A. Opt1", "B. Opt2"], "correct_answer": "A"},
            {"question_text": "Q2 Text", "options": ["A. Opt1", "B. Opt2"], "correct_answer": "B"}
        ]
        add_questions_to_quiz(db, quiz.id, questions_data)

        room = game_engine.get_or_create_room(quiz.id)
        assert room.status == "WAITING"
        assert len(room.questions) == 2

        await game_engine.pause_quiz(quiz.id)
        assert room.status == "PAUSED"
        assert room.is_paused is True

        await game_engine.resume_quiz(quiz.id)
        assert room.is_paused is False

        await game_engine.finish_quiz(quiz.id)
        assert room.status == "FINISHED"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_eliminate_and_restore_participant():
    from database.repositories import create_participant, get_participant_by_token
    db = SessionLocal()
    try:
        quiz = create_quiz(db, name="Elimination Test Quiz", description="Testing elimination", max_participants=10)
        p = create_participant(db, quiz.id, name="CheaterPlayer")

        room = game_engine.get_or_create_room(quiz.id)
        assert p.is_eliminated is False

        # Eliminate
        res = await game_engine.eliminate_participant(quiz.id, p.id, reason="Anti-Cheat Violation")
        assert res.get("success") is True
        assert res.get("is_eliminated") is True
        
        db.refresh(p)
        assert p.is_eliminated is True
        assert p.is_alive is False

        # Live data should show eliminated
        live_data = game_engine.get_live_control_data(quiz.id)
        p_resp = next((item for item in live_data["participant_responses"] if item["id"] == p.id), None)
        assert p_resp is not None
        assert p_resp["is_eliminated"] is True
        assert p_resp["status"] == "Eliminated"

        # Restore
        res_rest = await game_engine.restore_participant(quiz.id, p.id)
        assert res_rest.get("success") is True
        assert res_rest.get("is_eliminated") is False

        db.refresh(p)
        assert p.is_eliminated is False
        assert p.is_alive is True
    finally:
        db.close()

