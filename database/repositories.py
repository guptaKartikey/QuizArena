from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models import Admin, Quiz, Question, Participant, Team, Answer, BuzzEvent
import uuid
import random
import string
import json

def get_admin_by_username(db: Session, username: str):
    return db.query(Admin).filter(Admin.username == username).first()

def create_admin(db: Session, username: str, password_hash: str):
    admin = Admin(username=username, password_hash=password_hash)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin

def generate_join_code(db: Session, length=5):
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        existing = db.query(Quiz).filter(Quiz.join_code == code).first()
        if not existing:
            return code

def generate_quiz_id(db: Session):
    while True:
        quiz_id = f"QA-{random.randint(1000,99999)}"
        existing = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not existing:
            return quiz_id

def create_quiz(db: Session, name: str, description: str = "", max_participants: int = 50, settings: dict = None, mode: str = "CLASSIC", mode_settings: dict = None):
    settings = settings or {}
    mode_settings = mode_settings or {}
    quiz_id = generate_quiz_id(db)
    join_code = generate_join_code(db)

    # Initial lives setting for Survival mode
    initial_lives = mode_settings.get("initial_lives", 3) if mode == "SURVIVAL" else 3

    quiz = Quiz(
        id=quiz_id,
        name=name,
        description=description,
        join_code=join_code,
        max_participants=max_participants,
        mode=mode,
        mode_settings_json=json.dumps(mode_settings),
        question_timer=settings.get("question_timer", 30),
        correct_points=settings.get("correct_points", 10.0),
        wrong_points=settings.get("wrong_points", -5.0),
        no_answer_points=settings.get("no_answer_points", 0.0),
        enable_negative_marking=settings.get("enable_negative_marking", True),
        enable_speed_bonus=settings.get("enable_speed_bonus", True),
        enable_buzzer=settings.get("enable_buzzer", False) or (mode == "FIRST_TO_BUZZ"),
        enable_random_questions=settings.get("enable_random_questions", False),
        enable_random_options=settings.get("enable_random_options", False),
        allow_late_joining=settings.get("allow_late_joining", True),
        show_answer_after=settings.get("show_answer_after", True),
        show_leaderboard_after=settings.get("show_leaderboard_after", True),
        automatic_next_question=settings.get("automatic_next_question", False),
        enable_powerups=settings.get("enable_powerups", False),
        enable_team_buzzer=settings.get("enable_team_buzzer", False),
        show_explanation=settings.get("show_explanation", True),
        allow_answer_change=settings.get("allow_answer_change", True),
        total_rounds=mode_settings.get("total_rounds", 1) if mode in ["KNOCKOUT", "CHAMPIONSHIP"] else 1
    )

    db.add(quiz)
    db.commit()

    # Pre-create Teams if Team Battle
    if mode == "TEAM_BATTLE":
        num_teams = mode_settings.get("num_teams", 2)
        team_names = mode_settings.get("team_names", ["Red Dragons", "Blue Eagles", "Green Lions", "Gold Tigers"])
        for i in range(num_teams):
            t_name = team_names[i] if i < len(team_names) else f"Team {chr(65+i)}"
            t = Team(quiz_id=quiz.id, name=t_name)
            db.add(t)
        db.commit()

    db.refresh(quiz)
    return quiz

def get_quiz_by_id(db: Session, quiz_id: str):
    return db.query(Quiz).filter(Quiz.id == quiz_id).first()

def get_quiz_by_code(db: Session, join_code: str):
    return db.query(Quiz).filter(Quiz.join_code == join_code.upper()).first()

def get_all_quizzes(db: Session):
    return db.query(Quiz).order_by(Quiz.created_at.desc()).all()

def update_quiz_status(db: Session, quiz_id: str, status: str):
    quiz = get_quiz_by_id(db, quiz_id)
    if quiz:
        quiz.status = status
        db.commit()
        db.refresh(quiz)
    return quiz

def add_questions_to_quiz(db: Session, quiz_id: str, questions_data: list):
    created = []
    for idx, q in enumerate(questions_data, start=1):
        question = Question(
            quiz_id=quiz_id,
            question_text=q["question_text"],
            options_json=json.dumps(q["options"]),
            correct_answer=q["correct_answer"],
            explanation=q.get("explanation", ""),
            order_number=idx,
            round_number=q.get("round_number", 1)
        )
        db.add(question)
        created.append(question)
    db.commit()
    for q in created:
        db.refresh(q)
    return created

def get_quiz_questions(db: Session, quiz_id: str, round_number: int = None):
    query = db.query(Question).filter(Question.quiz_id == quiz_id)
    if round_number:
        query = query.filter(Question.round_number == round_number)
    return query.order_by(Question.order_number.asc()).all()

def create_participant(db: Session, quiz_id: str, name: str, team_id: int = None):
    quiz = get_quiz_by_id(db, quiz_id)
    initial_lives = quiz.mode_settings.get("initial_lives", 3) if quiz and quiz.mode == "SURVIVAL" else 3

    # Auto team assignment if Team Battle and no team specified
    if quiz and quiz.mode == "TEAM_BATTLE" and not team_id:
        teams = db.query(Team).filter(Team.quiz_id == quiz_id).all()
        if teams:
            # Pick team with fewest members
            teams_sorted = sorted(teams, key=lambda t: len(t.members))
            team_id = teams_sorted[0].id

    p_id = str(uuid.uuid4())[:8]
    session_token = str(uuid.uuid4())
    participant = Participant(
        id=p_id,
        quiz_id=quiz_id,
        team_id=team_id,
        name=name,
        session_token=session_token,
        connected=True,
        is_alive=True,
        lives=initial_lives,
        is_eliminated=False
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant

def get_participant_by_token(db: Session, session_token: str):
    return db.query(Participant).filter(Participant.session_token == session_token).first()

def get_participant_by_id(db: Session, participant_id: str):
    return db.query(Participant).filter(Participant.id == participant_id).first()

def get_quiz_participants(db: Session, quiz_id: str):
    return db.query(Participant).filter(Participant.quiz_id == quiz_id).all()

def record_answer(db: Session, quiz_id: str, question_id: int, participant_id: str, selected_answer: str, is_correct: bool, response_time: float, points: float, speed_bonus: float = 0.0, allow_change: bool = False):
    existing = db.query(Answer).filter(
        Answer.quiz_id == quiz_id,
        Answer.question_id == question_id,
        Answer.participant_id == participant_id
    ).first()

    if existing:
        if allow_change:
            existing.selected_answer = selected_answer
            existing.is_correct = is_correct
            existing.response_time = response_time
            existing.points = points
            existing.speed_bonus = speed_bonus
            db.commit()
            db.refresh(existing)
            return existing
        return existing

    answer = Answer(
        quiz_id=quiz_id,
        question_id=question_id,
        participant_id=participant_id,
        selected_answer=selected_answer,
        is_correct=is_correct,
        response_time=response_time,
        points=points,
        speed_bonus=speed_bonus
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer

def record_buzz(db: Session, quiz_id: str, question_id: int, participant_id: str, timestamp_ns: int, position: int, result: str = "PENDING", penalty: float = 0.0, is_second_chance: bool = False):
    buzz = BuzzEvent(
        quiz_id=quiz_id,
        question_id=question_id,
        participant_id=participant_id,
        timestamp_ns=timestamp_ns,
        position=position,
        result=result,
        penalty_applied=penalty,
        is_second_chance=is_second_chance
    )
    db.add(buzz)
    db.commit()
    db.refresh(buzz)
    return buzz

def get_quiz_leaderboard(db: Session, quiz_id: str):
    participants = get_quiz_participants(db, quiz_id)
    leaderboard = []
    
    for p in participants:
        answers = db.query(Answer).filter(Answer.participant_id == p.id).all()
        buzz_penalties = db.query(func.sum(BuzzEvent.penalty_applied)).filter(BuzzEvent.participant_id == p.id).scalar() or 0.0
        
        total_score = sum(a.points for a in answers) - buzz_penalties
        correct_count = sum(1 for a in answers if a.is_correct)
        wrong_count = sum(1 for a in answers if not a.is_correct)
        avg_time = (sum(a.response_time for a in answers) / len(answers)) if answers else 0.0
        
        buzz_wins = db.query(BuzzEvent).filter(
            BuzzEvent.participant_id == p.id,
            BuzzEvent.position == 1
        ).count()

        leaderboard.append({
            "participant_id": p.id,
            "name": p.name,
            "team_id": p.team_id,
            "team_name": p.team.name if p.team else None,
            "score": round(total_score, 1),
            "correct": correct_count,
            "wrong": wrong_count,
            "total_answered": len(answers),
            "avg_time": round(avg_time, 2),
            "buzz_wins": buzz_wins,
            "lives": p.lives,
            "is_alive": p.is_alive,
            "is_eliminated": p.is_eliminated,
            "eliminated_in_round": p.eliminated_in_round
        })
        
    leaderboard.sort(key=lambda x: x["score"], reverse=True)
    for idx, item in enumerate(leaderboard, start=1):
        item["rank"] = idx
        
    return leaderboard

def get_team_leaderboard(db: Session, quiz_id: str):
    teams = db.query(Team).filter(Team.quiz_id == quiz_id).all()
    team_scores = []
    
    ind_leaderboard = get_quiz_leaderboard(db, quiz_id)
    score_map = {item["participant_id"]: item["score"] for item in ind_leaderboard}

    for t in teams:
        t_score = sum(score_map.get(m.id, 0.0) for m in t.members)
        team_scores.append({
            "team_id": t.id,
            "name": t.name,
            "member_count": len(t.members),
            "score": round(t_score, 1)
        })

    team_scores.sort(key=lambda x: x["score"], reverse=True)
    for idx, item in enumerate(team_scores, start=1):
        item["rank"] = idx
        
    return team_scores
