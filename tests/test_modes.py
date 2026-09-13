import pytest
from database.database import init_db, SessionLocal
from database.repositories import (
    create_quiz,
    add_questions_to_quiz,
    create_participant,
    get_quiz_leaderboard,
    get_team_leaderboard,
    record_answer
)
from backend.scoring import calculate_score, calculate_speed_tier_points
from backend.game_engine import game_engine

init_db()

def test_classic_quiz_mode():
    db = SessionLocal()
    try:
        quiz = create_quiz(db, name="Classic Quiz Test", mode="CLASSIC")
        add_questions_to_quiz(db, quiz.id, [{"question_text": "Q1", "options": ["A", "B"], "correct_answer": "A"}])
        
        p = create_participant(db, quiz.id, name="PlayerClassic")
        pts, bonus = calculate_score(is_correct=True, response_time=2.0, total_time=30.0, correct_points=10.0)
        
        record_answer(db, quiz.id, 1, p.id, "A", True, 2.0, pts, bonus)
        lb = get_quiz_leaderboard(db, quiz.id)
        assert len(lb) == 1
        assert lb[0]["score"] > 10.0
    finally:
        db.close()

def test_speed_quiz_tiers():
    speed_tiers = [
        {"min_s": 0, "max_s": 5, "pts": 10},
        {"min_s": 5, "max_s": 10, "pts": 8},
        {"min_s": 10, "max_s": 15, "pts": 6}
    ]
    
    tier_pts_fast = calculate_speed_tier_points(2.5, speed_tiers)
    assert tier_pts_fast == 10

    tier_pts_mid = calculate_speed_tier_points(7.0, speed_tiers)
    assert tier_pts_mid == 8

    pts, bonus = calculate_score(is_correct=True, response_time=2.5, total_time=30.0, correct_points=10.0, mode="SPEED_QUIZ", speed_tiers=speed_tiers)
    assert bonus == 10.0
    assert pts == 20.0

def test_team_battle_mode():
    db = SessionLocal()
    try:
        mode_settings = {"num_teams": 2, "team_names": ["Red Dragons", "Blue Eagles"]}
        quiz = create_quiz(db, name="Team Battle Test", mode="TEAM_BATTLE", mode_settings=mode_settings)
        
        p1 = create_participant(db, quiz.id, name="Alpha")
        p2 = create_participant(db, quiz.id, name="Beta")

        record_answer(db, quiz.id, 1, p1.id, "A", True, 3.0, 10.0)
        record_answer(db, quiz.id, 1, p2.id, "A", True, 4.0, 10.0)

        team_lb = get_team_leaderboard(db, quiz.id)
        assert len(team_lb) == 2
        assert team_lb[0]["score"] > 0
    finally:
        db.close()

def test_survival_mode_lives():
    db = SessionLocal()
    try:
        mode_settings = {"initial_lives": 3}
        quiz = create_quiz(db, name="Survival Test", mode="SURVIVAL", mode_settings=mode_settings)
        p = create_participant(db, quiz.id, name="Survivor")
        assert p.lives == 3
        assert p.is_alive is True
    finally:
        db.close()

@pytest.mark.asyncio
async def test_first_to_buzz_second_chance():
    db = SessionLocal()
    try:
        mode_settings = {"allow_second_chance": True}
        quiz = create_quiz(db, name="Buzz Test Quiz", mode="FIRST_TO_BUZZ", mode_settings=mode_settings)
        add_questions_to_quiz(db, quiz.id, [{"question_text": "Who discovered gravity?", "options": ["A. Newton", "B. Einstein"], "correct_answer": "A"}])
        
        p1 = create_participant(db, quiz.id, name="Player1")
        p2 = create_participant(db, quiz.id, name="Player2")

        room = game_engine.get_or_create_room(quiz.id)
        room.status = "BUZZER_ACTIVE"

        # Simulate 2 buzzes
        res1 = await game_engine.handle_buzz(quiz.id, p1.id, "Player1")
        res2 = await game_engine.handle_buzz(quiz.id, p2.id, "Player2")

        assert res1["is_winner"] is True
        assert res2["is_winner"] is False

        # Simulate player 1 giving incorrect answer
        ans_res = await game_engine.submit_answer(quiz.id, p1.id, "B")
        assert ans_res.get("passed") is True
        assert room.buzzer_winner_id == p2.id
    finally:
        db.close()
