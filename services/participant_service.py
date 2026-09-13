from sqlalchemy.orm import Session
from database.repositories import (
    get_quiz_by_code,
    get_quiz_participants,
    create_participant,
    get_participant_by_token,
    get_participant_by_id
)
import random

def join_quiz_room(db: Session, join_code: str, player_name: str, team_name: str = None) -> tuple[dict, str]:
    quiz = get_quiz_by_code(db, join_code)
    if not quiz:
        return None, "Invalid quiz join code."

    if quiz.status == "FINISHED":
        return None, "This quiz has already ended."

    if not quiz.allow_late_joining and quiz.status not in ["WAITING", "STARTING"]:
        return None, "Quiz has already started. Late joining is disabled."

    participants = get_quiz_participants(db, quiz.id)
    if len(participants) >= quiz.max_participants:
        return None, "Quiz room is full."

    # Check existing name in room to prevent confusion
    existing_name = any(p.name.strip().lower() == player_name.strip().lower() for p in participants)
    if existing_name:
        player_name = f"{player_name} ({random.randint(10,99)})"

    participant = create_participant(db, quiz.id, player_name)
    
    return {
        "participant_id": participant.id,
        "session_token": participant.session_token,
        "name": participant.name,
        "quiz_id": quiz.id,
        "quiz_name": quiz.name,
        "join_code": quiz.join_code,
        "quiz_status": quiz.status
    }, None

def generate_demo_participants(db: Session, quiz_id: str, count: int = 15):
    demo_names = [
        "Kartik", "Rahul", "Aman", "Priya", "Rohan", "Neha", "Sneha", "Vikram",
        "Ananya", "Dev", "Isha", "Karan", "Meera", "Nikhil", "Pooja", "Raj",
        "Simran", "Tanvi", "Varun", "Yash"
    ]
    created = []
    for i in range(min(count, len(demo_names))):
        name = demo_names[i]
        p = create_participant(db, quiz_id, name)
        created.append(p)
    return created
