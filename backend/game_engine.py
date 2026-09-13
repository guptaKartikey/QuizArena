import asyncio
import time
import logging
from typing import Dict, Optional, Any, List
from database.database import SessionLocal
from database.repositories import (
    get_quiz_by_id,
    get_quiz_questions,
    get_quiz_participants,
    get_quiz_leaderboard,
    get_team_leaderboard,
    update_quiz_status,
    record_answer,
    record_buzz
)
from database.models import Participant, Answer, BuzzEvent, Team, Question
from backend.scoring import calculate_score
from backend.buzzer import buzzer_manager
from backend.websocket_manager import manager

logger = logging.getLogger("quizarena.engine")

class QuizRoomState:
    def __init__(self, quiz_id: str):
        self.quiz_id = quiz_id
        self.status = "WAITING"
        self.current_question_index = 0
        self.current_round = 1
        self.questions = []
        self.timer_seconds = 30
        self.remaining_seconds = 30
        self.timer_task: Optional[asyncio.Task] = None
        self.is_paused = False
        self.pre_pause_status = "WAITING"
        self.buzzer_winner_id: Optional[str] = None
        self.buzzer_winner_name: Optional[str] = None
        self.question_start_time: float = 0.0
        self.mode = "CLASSIC"
        self.mode_settings = {}
        self.team_votes: Dict[int, Dict[int, Dict[str, str]]] = {}

class GameEngine:
    def __init__(self):
        self.rooms: Dict[str, QuizRoomState] = {}

    def get_or_create_room(self, quiz_id: str) -> QuizRoomState:
        if quiz_id not in self.rooms:
            self.rooms[quiz_id] = QuizRoomState(quiz_id)
            db = SessionLocal()
            try:
                quiz = get_quiz_by_id(db, quiz_id)
                if quiz:
                    self.rooms[quiz_id].timer_seconds = quiz.question_timer
                    self.rooms[quiz_id].remaining_seconds = quiz.question_timer
                    self.rooms[quiz_id].status = quiz.status
                    self.rooms[quiz_id].mode = quiz.mode
                    self.rooms[quiz_id].mode_settings = quiz.mode_settings
                    self.rooms[quiz_id].current_round = quiz.current_round
                    self.rooms[quiz_id].questions = get_quiz_questions(db, quiz_id)
            finally:
                db.close()
        return self.rooms[quiz_id]

    async def start_quiz(self, quiz_id: str):
        room = self.get_or_create_room(quiz_id)
        
        db = SessionLocal()
        try:
            quiz = get_quiz_by_id(db, quiz_id)
            if quiz:
                room.timer_seconds = quiz.question_timer
                room.remaining_seconds = quiz.question_timer
                room.mode = quiz.mode
                room.mode_settings = quiz.mode_settings
            
            room.questions = get_quiz_questions(db, quiz_id)
            update_quiz_status(db, quiz_id, "STARTING")
        finally:
            db.close()

        room.is_paused = False
        room.status = "STARTING"
        room.current_question_index = 0
        room.current_round = 1

        if not room.questions:
            logger.error(f"Cannot start quiz {quiz_id}: No questions found in database!")
            return {"error": "No questions found for this quiz."}

        await manager.broadcast_to_quiz(quiz_id, {
            "type": "QUIZ_STARTED",
            "quiz_id": quiz_id,
            "mode": room.mode,
            "total_questions": len(room.questions)
        })

        await asyncio.sleep(1)
        await self.next_question(quiz_id)

    async def next_question(self, quiz_id: str):
        room = self.get_or_create_room(quiz_id)
        
        if room.current_question_index >= len(room.questions):
            if room.mode == "KNOCKOUT" and room.current_round < room.mode_settings.get("rounds_count", 1):
                await self.handle_knockout_round_end(quiz_id)
                return
            else:
                await self.finish_quiz(quiz_id)
                return

        db = SessionLocal()
        try:
            quiz = get_quiz_by_id(db, quiz_id)
            current_q = room.questions[room.current_question_index]
            room.remaining_seconds = quiz.question_timer
            room.buzzer_winner_id = None
            room.buzzer_winner_name = None
            room.question_start_time = time.time()

            if quiz.mode == "FIRST_TO_BUZZ" or quiz.enable_buzzer:
                room.status = "BUZZER_ACTIVE"
            else:
                room.status = "QUESTION_ACTIVE"

            update_quiz_status(db, quiz_id, room.status)
            await buzzer_manager.reset_buzzer(quiz_id, current_q.id)

            safe_question = {
                "id": current_q.id,
                "order_number": current_q.order_number,
                "round_number": current_q.round_number,
                "question_text": current_q.question_text,
                "options": current_q.options,
                "timer_seconds": quiz.question_timer
            }

            await manager.broadcast_to_quiz(quiz_id, {
                "type": "QUESTION_ACTIVE",
                "quiz_id": quiz_id,
                "current_index": room.current_question_index + 1,
                "total_questions": len(room.questions),
                "question": safe_question,
                "status": room.status,
                "timer": room.remaining_seconds,
                "mode": quiz.mode,
                "current_round": room.current_round,
                "allow_answer_change": getattr(quiz, "allow_answer_change", True)
            })

            if room.timer_task and not room.timer_task.done():
                room.timer_task.cancel()

            room.timer_task = asyncio.create_task(self._run_timer(quiz_id))
        finally:
            db.close()

    async def _run_timer(self, quiz_id: str):
        room = self.get_or_create_room(quiz_id)
        while room.remaining_seconds > 0 and not room.is_paused:
            await asyncio.sleep(1)
            if room.is_paused:
                break
            room.remaining_seconds -= 1
            await manager.broadcast_to_quiz(quiz_id, {
                "type": "TIMER_TICK",
                "remaining": room.remaining_seconds
            })

        if room.remaining_seconds <= 0 and not room.is_paused:
            await self.show_question_result(quiz_id)

    async def extend_timer(self, quiz_id: str, extra_seconds: int = 10):
        room = self.get_or_create_room(quiz_id)
        room.remaining_seconds += extra_seconds
        await manager.broadcast_to_quiz(quiz_id, {
            "type": "TIMER_EXTENDED",
            "remaining": room.remaining_seconds,
            "added": extra_seconds
        })

    async def restart_question(self, quiz_id: str):
        room = self.get_or_create_room(quiz_id)
        db = SessionLocal()
        try:
            quiz = get_quiz_by_id(db, quiz_id)
            if quiz:
                room.remaining_seconds = quiz.question_timer
                room.question_start_time = time.time()
                await manager.broadcast_to_quiz(quiz_id, {
                    "type": "QUESTION_RESTARTED",
                    "remaining": room.remaining_seconds
                })
        finally:
            db.close()

    async def broadcast_announcement(self, quiz_id: str, message_text: str):
        await manager.broadcast_to_quiz(quiz_id, {
            "type": "ANNOUNCEMENT",
            "message": message_text
        })

    async def broadcast_music_toggle(self, quiz_id: str, enabled: bool):
        await manager.broadcast_to_quiz(quiz_id, {
            "type": "MUSIC_TOGGLE",
            "enabled": enabled
        })

    async def eliminate_participant(self, quiz_id: str, participant_id: str, reason: str = None) -> dict:
        db = SessionLocal()
        try:
            participant = db.query(Participant).filter(Participant.id == participant_id).first()
            if not participant:
                return {"error": "Participant not found."}

            room = self.get_or_create_room(quiz_id)
            participant.is_eliminated = True
            participant.is_alive = False
            participant.eliminated_in_round = room.current_question_index + 1
            db.commit()

            elim_reason = reason or "Eliminated by Admin for suspected cheating / rules violation."
            
            await manager.broadcast_to_quiz(quiz_id, {
                "type": "PLAYER_ELIMINATED",
                "participant_id": participant_id,
                "name": participant.name,
                "reason": elim_reason
            })

            quiz = get_quiz_by_id(db, quiz_id)
            if quiz and quiz.mode == "SURVIVAL":
                alive_count = db.query(Participant).filter(
                    Participant.quiz_id == quiz_id,
                    Participant.is_alive == True
                ).count()
                if alive_count <= 1:
                    await self.finish_quiz(quiz_id)

            return {
                "success": True,
                "participant_id": participant.id,
                "name": participant.name,
                "is_eliminated": True,
                "reason": elim_reason
            }
        finally:
            db.close()

    async def restore_participant(self, quiz_id: str, participant_id: str) -> dict:
        db = SessionLocal()
        try:
            participant = db.query(Participant).filter(Participant.id == participant_id).first()
            if not participant:
                return {"error": "Participant not found."}

            participant.is_eliminated = False
            participant.is_alive = True
            participant.eliminated_in_round = None
            if participant.lives == 0:
                participant.lives = 1
            db.commit()

            await manager.broadcast_to_quiz(quiz_id, {
                "type": "PLAYER_RESTORED",
                "participant_id": participant_id,
                "name": participant.name
            })

            return {
                "success": True,
                "participant_id": participant.id,
                "name": participant.name,
                "is_eliminated": False
            }
        finally:
            db.close()

    async def submit_answer(self, quiz_id: str, participant_id: str, selected_option: str) -> dict:
        room = self.get_or_create_room(quiz_id)
        if room.status not in ["QUESTION_ACTIVE", "ANSWERING"]:
            return {"error": "Question is not currently accepting answers."}

        current_q = room.questions[room.current_question_index]
        
        db = SessionLocal()
        try:
            quiz = get_quiz_by_id(db, quiz_id)
            participant = db.query(Participant).filter(Participant.id == participant_id).first()

            if not participant or participant.is_eliminated:
                return {"error": "Participant is eliminated or invalid."}

            if (quiz.mode == "FIRST_TO_BUZZ" or quiz.enable_buzzer) and room.buzzer_winner_id:
                if participant_id != room.buzzer_winner_id:
                    return {"error": "Only the current buzzer winner can answer."}

            response_time = max(0.1, round(time.time() - room.question_start_time, 2))
            is_correct = (selected_option.upper().strip() == current_q.correct_answer.upper().strip())

            speed_tiers = quiz.mode_settings.get("speed_tiers", []) if quiz.mode == "SPEED_QUIZ" else None

            points, speed_bonus = calculate_score(
                is_correct=is_correct,
                response_time=response_time,
                total_time=quiz.question_timer,
                correct_points=quiz.correct_points,
                wrong_points=quiz.wrong_points,
                no_answer_points=quiz.no_answer_points,
                enable_negative_marking=quiz.enable_negative_marking,
                enable_speed_bonus=quiz.enable_speed_bonus,
                mode=quiz.mode,
                speed_tiers=speed_tiers
            )

            record_answer(
                db=db,
                quiz_id=quiz_id,
                question_id=current_q.id,
                participant_id=participant_id,
                selected_answer=selected_option.upper().strip(),
                is_correct=is_correct,
                response_time=response_time,
                points=points,
                speed_bonus=speed_bonus,
                allow_change=getattr(quiz, "allow_answer_change", True)
            )

            # SURVIVAL MODE LOGIC
            if quiz.mode == "SURVIVAL" and not is_correct:
                participant.lives = max(0, participant.lives - 1)
                if participant.lives == 0:
                    participant.is_alive = False
                    participant.is_eliminated = True
                    participant.eliminated_in_round = room.current_question_index + 1
                    
                    await manager.broadcast_to_quiz(quiz_id, {
                        "type": "PLAYER_ELIMINATED",
                        "participant_id": participant_id,
                        "name": participant.name
                    })

                db.commit()

                alive_count = db.query(Participant).filter(
                    Participant.quiz_id == quiz_id,
                    Participant.is_alive == True
                ).count()

                if alive_count <= 1:
                    await self.finish_quiz(quiz_id)
                    return {"success": True, "is_correct": is_correct, "points": points, "game_over": True}

            # FIRST_TO_BUZZ SECOND CHANCE LOGIC
            if (quiz.mode == "FIRST_TO_BUZZ" or quiz.enable_buzzer) and not is_correct:
                allow_second_chance = quiz.mode_settings.get("allow_second_chance", False)
                if allow_second_chance:
                    next_buzzer = await buzzer_manager.pass_to_next_fastest(quiz_id, current_q.id)
                    if next_buzzer:
                        room.status = "ANSWERING"
                        room.buzzer_winner_id = next_buzzer["winner_id"]
                        room.buzzer_winner_name = next_buzzer["winner_name"]
                        
                        await manager.broadcast_to_quiz(quiz_id, {
                            "type": "SECOND_CHANCE",
                            "winner_id": next_buzzer["winner_id"],
                            "winner_name": next_buzzer["winner_name"],
                            "message": f"Wrong answer! Question passed to {next_buzzer['winner_name']}!"
                        })
                        return {"success": True, "is_correct": False, "passed": True}

            # Broadcast answer stats & live response update to admin clients
            connected_p_count = len(get_quiz_participants(db, quiz_id))
            answers = db.query(Answer).filter(
                Answer.quiz_id == quiz_id,
                Answer.question_id == current_q.id
            ).all()

            # Answer distribution
            ans_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
            for a in answers:
                if a.selected_answer in ans_dist:
                    ans_dist[a.selected_answer] += 1

            await manager.broadcast_to_admin(quiz_id, {
                "type": "ANSWER_SUBMITTED",
                "participant_id": participant_id,
                "participant_name": participant.name,
                "selected_option": selected_option,
                "is_correct": is_correct,
                "response_time": response_time,
                "points": points,
                "answered_count": len(answers),
                "total_participants": connected_p_count,
                "answer_distribution": ans_dist
            })

            if quiz.mode == "FIRST_TO_BUZZ" or quiz.enable_buzzer:
                if room.timer_task and not room.timer_task.done():
                    room.timer_task.cancel()
                await asyncio.sleep(1)
                await self.show_question_result(quiz_id)

            return {
                "success": True,
                "is_correct": is_correct,
                "points": points,
                "lives": participant.lives if quiz.mode == "SURVIVAL" else None,
                "selected_option": selected_option
            }
        finally:
            db.close()

    async def handle_buzz(self, quiz_id: str, participant_id: str, participant_name: str) -> dict:
        room = self.get_or_create_room(quiz_id)
        if room.status not in ["BUZZER_ACTIVE", "ANSWERING"]:
            return {"error": "Buzzer is not active."}

        current_q = room.questions[room.current_question_index]
        buzz_res = await buzzer_manager.register_buzz(quiz_id, current_q.id, participant_id, participant_name)

        db = SessionLocal()
        try:
            quiz = get_quiz_by_id(db, quiz_id)
            buzz_penalty = quiz.mode_settings.get("wrong_buzz_penalty", 0.0) if quiz else 0.0

            record_buzz(
                db=db,
                quiz_id=quiz_id,
                question_id=current_q.id,
                participant_id=participant_id,
                timestamp_ns=buzz_res["timestamp_ns"],
                position=buzz_res["position"],
                result="WON" if buzz_res["is_winner"] else "LOST",
                penalty=0.0
            )

            if buzz_res["is_winner"]:
                room.status = "ANSWERING"
                room.buzzer_winner_id = participant_id
                room.buzzer_winner_name = participant_name

                await manager.broadcast_to_quiz(quiz_id, {
                    "type": "BUZZ_LOCKED",
                    "winner_id": participant_id,
                    "winner_name": participant_name,
                    "question_id": current_q.id
                })
        finally:
            db.close()

        return buzz_res

    async def handle_knockout_round_end(self, quiz_id: str):
        room = self.get_or_create_room(quiz_id)
        room.status = "ROUND_END"

        db = SessionLocal()
        try:
            update_quiz_status(db, quiz_id, "ROUND_END")
            leaderboard = get_quiz_leaderboard(db, quiz_id)

            knockout_rounds = room.mode_settings.get("knockout_rounds", [])
            current_r_config = next((r for r in knockout_rounds if r.get("round") == room.current_round), None)
            eliminate_count = current_r_config.get("eliminate_count", 2) if current_r_config else 2

            active_players = [p for p in leaderboard if not p.get("is_eliminated")]
            to_eliminate = active_players[-eliminate_count:] if len(active_players) > eliminate_count else []

            for p_dict in to_eliminate:
                p_obj = db.query(Participant).filter(Participant.id == p_dict["participant_id"]).first()
                if p_obj:
                    p_obj.is_eliminated = True
                    p_obj.is_alive = False
                    p_obj.eliminated_in_round = room.current_round

            db.commit()

            await manager.broadcast_to_quiz(quiz_id, {
                "type": "KNOCKOUT_ROUND_END",
                "round": room.current_round,
                "eliminated_players": to_eliminate,
                "leaderboard": leaderboard
            })

            room.current_round += 1
            update_quiz_status(db, quiz_id, f"ROUND_{room.current_round}")
        finally:
            db.close()

    async def show_question_result(self, quiz_id: str):
        room = self.get_or_create_room(quiz_id)
        room.status = "QUESTION_RESULT"

        db = SessionLocal()
        try:
            update_quiz_status(db, quiz_id, "QUESTION_RESULT")
            current_q = room.questions[room.current_question_index]

            answers = db.query(Answer).filter(
                Answer.quiz_id == quiz_id,
                Answer.question_id == current_q.id
            ).all()

            correct_count = sum(1 for a in answers if a.is_correct)
            wrong_count = sum(1 for a in answers if not a.is_correct)
            total_participants = len(get_quiz_participants(db, quiz_id))
            no_answer_count = max(0, total_participants - len(answers))

            fastest_ans = min(answers, key=lambda a: a.response_time) if answers else None
            fastest_name = fastest_ans.participant.name if fastest_ans else "N/A"
            fastest_time = fastest_ans.response_time if fastest_ans else 0.0

            result_data = {
                "type": "QUESTION_RESULT",
                "question_id": current_q.id,
                "correct_answer": current_q.correct_answer,
                "explanation": current_q.explanation or "",
                "stats": {
                    "correct": correct_count,
                    "wrong": wrong_count,
                    "no_answer": no_answer_count,
                    "fastest": f"{fastest_name} ({fastest_time}s)" if fastest_ans else "None"
                }
            }

            await manager.broadcast_to_quiz(quiz_id, result_data)

            quiz = get_quiz_by_id(db, quiz_id)
            if quiz and quiz.automatic_next_question:
                await asyncio.sleep(5)
                await self.show_leaderboard(quiz_id)
        finally:
            db.close()

    async def show_leaderboard(self, quiz_id: str):
        room = self.get_or_create_room(quiz_id)
        room.status = "LEADERBOARD"

        db = SessionLocal()
        try:
            update_quiz_status(db, quiz_id, "LEADERBOARD")
            leaderboard = get_quiz_leaderboard(db, quiz_id)
            team_lb = get_team_leaderboard(db, quiz_id) if room.mode == "TEAM_BATTLE" else []

            await manager.broadcast_to_quiz(quiz_id, {
                "type": "LEADERBOARD_UPDATE",
                "leaderboard": leaderboard[:10],
                "team_leaderboard": team_lb,
                "current_index": room.current_question_index + 1,
                "total_questions": len(room.questions)
            })

            quiz = get_quiz_by_id(db, quiz_id)
            if quiz and quiz.automatic_next_question:
                await asyncio.sleep(5)
                room.current_question_index += 1
                await self.next_question(quiz_id)
        finally:
            db.close()

    async def pause_quiz(self, quiz_id: str):
        room = self.get_or_create_room(quiz_id)
        room.is_paused = True
        if room.status != "PAUSED":
            room.pre_pause_status = room.status
        room.status = "PAUSED"
        
        db = SessionLocal()
        try:
            update_quiz_status(db, quiz_id, "PAUSED")
        finally:
            db.close()

        await manager.broadcast_to_quiz(quiz_id, {
            "type": "QUIZ_PAUSED",
            "message": "⏸️ Quiz is paused. Waiting for host to resume..."
        })

    async def resume_quiz(self, quiz_id: str):
        room = self.get_or_create_room(quiz_id)
        if room.status == "WAITING":
            await self.start_quiz(quiz_id)
            return

        room.is_paused = False
        target_status = room.pre_pause_status if (room.pre_pause_status and room.pre_pause_status != "PAUSED") else "QUESTION_ACTIVE"
        room.status = target_status
        
        db = SessionLocal()
        try:
            update_quiz_status(db, quiz_id, room.status)
        finally:
            db.close()

        await manager.broadcast_to_quiz(quiz_id, {
            "type": "QUIZ_RESUMED",
            "status": room.status,
            "remaining": room.remaining_seconds
        })
        
        if room.timer_task and not room.timer_task.done():
            room.timer_task.cancel()
        room.timer_task = asyncio.create_task(self._run_timer(quiz_id))

    async def finish_quiz(self, quiz_id: str):
        room = self.get_or_create_room(quiz_id)
        room.status = "FINISHED"

        db = SessionLocal()
        try:
            update_quiz_status(db, quiz_id, "FINISHED")
            leaderboard = get_quiz_leaderboard(db, quiz_id)
            team_lb = get_team_leaderboard(db, quiz_id) if room.mode == "TEAM_BATTLE" else []
            winner = leaderboard[0] if leaderboard else None

            await manager.broadcast_to_quiz(quiz_id, {
                "type": "QUIZ_FINISHED",
                "winner": winner,
                "leaderboard": leaderboard,
                "team_leaderboard": team_lb
            })
        finally:
            db.close()

    def get_live_control_data(self, quiz_id: str) -> dict:
        room = self.get_or_create_room(quiz_id)
        db = SessionLocal()
        try:
            quiz = get_quiz_by_id(db, quiz_id)
            participants = get_quiz_participants(db, quiz_id)
            leaderboard = get_quiz_leaderboard(db, quiz_id)
            team_lb = get_team_leaderboard(db, quiz_id) if quiz and quiz.mode == "TEAM_BATTLE" else []
            
            questions = get_quiz_questions(db, quiz_id)
            room.questions = questions
            current_q = questions[room.current_question_index] if (questions and room.current_question_index < len(questions)) else None

            # Current question responses
            answers = []
            ans_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
            if current_q:
                answers = db.query(Answer).filter(
                    Answer.quiz_id == quiz_id,
                    Answer.question_id == current_q.id
                ).all()
                for a in answers:
                    if a.selected_answer in ans_dist:
                        ans_dist[a.selected_answer] += 1

            # Participant responses table
            connected_ws_ids = set(manager.get_connected_player_ids(quiz_id))
            participant_responses = []
            for p in participants:
                p_ans = next((a for a in answers if a.participant_id == p.id), None)
                status_label = "Waiting"
                if p.is_eliminated:
                    status_label = "Eliminated"
                elif p_ans:
                    status_label = "Correct" if p_ans.is_correct else "Wrong"

                participant_responses.append({
                    "id": p.id,
                    "name": p.name,
                    "team_name": p.team.name if p.team else None,
                    "answer": p_ans.selected_answer if p_ans else "—",
                    "status": status_label,
                    "time": f"{p_ans.response_time}s" if p_ans else "—",
                    "points": f"+{p_ans.points}" if p_ans and p_ans.points > 0 else (f"{p_ans.points}" if p_ans else "0"),
                    "connected": p.id in connected_ws_ids or p.connected,
                    "lives": p.lives,
                    "is_eliminated": p.is_eliminated
                })

            current_leader = leaderboard[0] if leaderboard else None

            answered_count = len(answers)
            total_participants_count = len(participants)
            not_answered_count = max(0, total_participants_count - answered_count)
            correct_count = sum(1 for a in answers if a.is_correct)
            wrong_count = sum(1 for a in answers if not a.is_correct)
            avg_response_time = round(sum(a.response_time for a in answers) / len(answers), 2) if answers else 0.0

            return {
                "quiz_id": quiz_id,
                "quiz_name": quiz.name if quiz else "",
                "status": room.status,
                "mode": quiz.mode if quiz else "CLASSIC",
                "mode_settings": quiz.mode_settings if quiz else {},
                "current_index": room.current_question_index + 1 if questions else 0,
                "total_questions": len(questions),
                "remaining_seconds": room.remaining_seconds,
                "timer_seconds": quiz.question_timer if quiz else 30,
                "current_question": {
                    "id": current_q.id,
                    "question_text": current_q.question_text,
                    "options": current_q.options,
                    "correct_answer": current_q.correct_answer,
                    "explanation": current_q.explanation
                } if current_q else None,
                "connected_count": len(connected_ws_ids),
                "total_participants_count": total_participants_count,
                "max_participants": quiz.max_participants if quiz else 50,
                "answered_count": answered_count,
                "not_answered_count": not_answered_count,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "avg_response_time": avg_response_time,
                "current_leader": current_leader,
                "buzzer_winner_name": room.buzzer_winner_name,
                "answer_distribution": ans_dist,
                "participant_responses": participant_responses,
                "leaderboard": leaderboard,
                "team_leaderboard": team_lb
            }
        finally:
            db.close()

    def get_participant_history(self, quiz_id: str, participant_id: str) -> dict:
        db = SessionLocal()
        try:
            p = db.query(Participant).filter(Participant.id == participant_id).first()
            if not p:
                return {}

            answers = db.query(Answer).filter(Answer.participant_id == participant_id).all()
            leaderboard = get_quiz_leaderboard(db, quiz_id)
            p_rank = next((item["rank"] for item in leaderboard if item["participant_id"] == participant_id), "N/A")

            history = []
            for a in answers:
                q = db.query(Question).filter(Question.id == a.question_id).first()
                history.append({
                    "question_order": q.order_number if q else 1,
                    "question_text": q.question_text[:40] if q else "Question",
                    "selected_answer": a.selected_answer,
                    "correct_answer": q.correct_answer if q else "",
                    "is_correct": a.is_correct,
                    "points": a.points,
                    "response_time": a.response_time
                })

            total_score = sum(a.points for a in answers)
            correct_count = sum(1 for a in answers if a.is_correct)
            wrong_count = sum(1 for a in answers if not a.is_correct)
            accuracy = round((correct_count / len(answers) * 100), 1) if answers else 0.0
            avg_time = round((sum(a.response_time for a in answers) / len(answers)), 2) if answers else 0.0

            return {
                "participant_id": p.id,
                "name": p.name,
                "team_name": p.team.name if p.team else None,
                "rank": p_rank,
                "total_score": round(total_score, 1),
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "accuracy": accuracy,
                "avg_response_time": avg_time,
                "lives": p.lives,
                "is_eliminated": p.is_eliminated,
                "history": history
            }
        finally:
            db.close()

game_engine = GameEngine()
