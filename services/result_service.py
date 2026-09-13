import io
import json
import pandas as pd
from sqlalchemy.orm import Session
from database.repositories import (
    get_quiz_by_id,
    get_quiz_participants,
    get_quiz_questions,
    get_quiz_leaderboard,
    get_team_leaderboard
)
from database.models import Answer, BuzzEvent

def get_quiz_analytics(db: Session, quiz_id: str) -> dict:
    quiz = get_quiz_by_id(db, quiz_id)
    if not quiz:
        return {}

    participants = get_quiz_participants(db, quiz_id)
    leaderboard = get_quiz_leaderboard(db, quiz_id)
    questions = get_quiz_questions(db, quiz_id)
    team_leaderboard = get_team_leaderboard(db, quiz_id) if quiz.mode == "TEAM_BATTLE" else []
    
    all_answers = db.query(Answer).filter(Answer.quiz_id == quiz_id).all()
    all_buzzes = db.query(BuzzEvent).filter(BuzzEvent.quiz_id == quiz_id).all()
    
    total_participants = len(participants)
    scores = [item["score"] for item in leaderboard] if leaderboard else [0]
    
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    highest_score = max(scores) if scores else 0.0
    lowest_score = min(scores) if scores else 0.0

    total_ans_count = len(all_answers)
    correct_count = sum(1 for a in all_answers if a.is_correct)
    wrong_count = total_ans_count - correct_count
    
    avg_accuracy = round((correct_count / total_ans_count * 100), 1) if total_ans_count > 0 else 0.0
    avg_response_time = round((sum(a.response_time for a in all_answers) / total_ans_count), 2) if total_ans_count > 0 else 0.0

    # Mode-Specific Analytics Details
    mode_analytics = {}
    if quiz.mode == "FIRST_TO_BUZZ":
        buzz_wins = [b for b in all_buzzes if b.position == 1]
        buzz_win_rate = round(len(buzz_wins) / len(all_buzzes) * 100, 1) if all_buzzes else 0.0
        mode_analytics["total_buzzes"] = len(all_buzzes)
        mode_analytics["buzz_win_rate"] = buzz_win_rate
        mode_analytics["second_chances_given"] = sum(1 for b in all_buzzes if b.is_second_chance)

    elif quiz.mode == "SURVIVAL":
        alive_players = [p for p in leaderboard if p.get("is_alive")]
        eliminated_players = [p for p in leaderboard if not p.get("is_alive")]
        mode_analytics["survivors_count"] = len(alive_players)
        mode_analytics["eliminated_count"] = len(eliminated_players)

    elif quiz.mode == "KNOCKOUT":
        rounds = quiz.mode_settings.get("rounds_count", 1)
        mode_analytics["total_rounds"] = rounds
        mode_analytics["eliminated_count"] = sum(1 for p in leaderboard if p.get("is_eliminated"))

    elif quiz.mode == "TEAM_BATTLE":
        mode_analytics["team_leaderboard"] = team_leaderboard

    # Question-wise performance
    question_stats = []
    for q in questions:
        q_ans = [a for a in all_answers if a.question_id == q.id]
        q_total = len(q_ans)
        q_correct = sum(1 for a in q_ans if a.is_correct)
        q_wrong = q_total - q_correct
        q_acc = round((q_correct / q_total * 100), 1) if q_total > 0 else 0.0
        q_avg_time = round((sum(a.response_time for a in q_ans) / q_total), 2) if q_total > 0 else 0.0
        
        question_stats.append({
            "question_id": q.id,
            "order_number": q.order_number,
            "question_text": q.question_text[:40] + "..." if len(q.question_text) > 40 else q.question_text,
            "total_responses": q_total,
            "correct": q_correct,
            "wrong": q_wrong,
            "accuracy": q_acc,
            "avg_time": q_avg_time
        })

    return {
        "quiz_id": quiz_id,
        "quiz_name": quiz.name,
        "mode": quiz.mode,
        "total_participants": total_participants,
        "total_questions": len(questions),
        "avg_score": avg_score,
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "avg_accuracy": avg_accuracy,
        "avg_response_time": avg_response_time,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "mode_analytics": mode_analytics,
        "question_stats": question_stats,
        "leaderboard": leaderboard,
        "team_leaderboard": team_leaderboard
    }

def export_results_csv(db: Session, quiz_id: str) -> str:
    leaderboard = get_quiz_leaderboard(db, quiz_id)
    df = pd.DataFrame(leaderboard)
    return df.to_csv(index=False)

def export_results_excel(db: Session, quiz_id: str) -> bytes:
    leaderboard = get_quiz_leaderboard(db, quiz_id)
    df_leaderboard = pd.DataFrame(leaderboard)
    
    analytics = get_quiz_analytics(db, quiz_id)
    df_questions = pd.DataFrame(analytics.get("question_stats", []))

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_leaderboard.to_excel(writer, sheet_name="Leaderboard", index=False)
        if not df_questions.empty:
            df_questions.to_excel(writer, sheet_name="Question Breakdown", index=False)
    
    return output.getvalue()

def export_results_json(db: Session, quiz_id: str) -> str:
    analytics = get_quiz_analytics(db, quiz_id)
    return json.dumps(analytics, indent=2)
