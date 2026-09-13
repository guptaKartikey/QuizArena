from sqlalchemy.orm import Session
from database.repositories import (
    create_quiz,
    add_questions_to_quiz,
    get_quiz_by_id,
    get_quiz_questions,
    get_all_quizzes
)

def create_full_quiz(db: Session, name: str, description: str, max_participants: int, settings: dict, questions: list):
    quiz = create_quiz(db, name, description, max_participants, settings)
    if questions:
        add_questions_to_quiz(db, quiz.id, questions)
    return quiz

def get_quiz_details(db: Session, quiz_id: str):
    quiz = get_quiz_by_id(db, quiz_id)
    if not quiz:
        return None
    questions = get_quiz_questions(db, quiz_id)
    return {
        "quiz": quiz,
        "questions": questions,
        "total_questions": len(questions)
    }
