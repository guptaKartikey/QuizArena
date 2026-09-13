import os
import json
import logging
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

from database.database import init_db, get_db
from backend.api_routes import router as api_router
from backend.websocket_manager import manager
from backend.game_engine import game_engine
from database.repositories import get_quiz_by_code, get_participant_by_id, get_participant_by_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quizarena.main")

# Initialize database tables
init_db()

app = FastAPI(title="QuizArena - Real-Time QR Multiplayer Quiz Platform", version="1.0.0")

# CORS middleware for mobile and desktop access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Robust absolute paths — works on Render, Windows, Linux
_BASE_DIR = Path(__file__).resolve().parent.parent   # repo root
player_static_dir = str(_BASE_DIR / "player" / "static")
_PLAYER_HTML = str(_BASE_DIR / "player" / "templates" / "player.html")

logger.info(f"Static dir: {player_static_dir}")
logger.info(f"Player HTML: {_PLAYER_HTML}")
logger.info(f"player.html exists: {Path(_PLAYER_HTML).exists()}")

os.makedirs(player_static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=player_static_dir), name="static")

# Register REST routes
app.include_router(api_router)

@app.get("/", response_class=HTMLResponse)
def index_page():
    return FileResponse(_PLAYER_HTML, media_type="text/html")

@app.get("/join/{join_code}", response_class=HTMLResponse)
def join_page(join_code: str):
    # join_code is pre-filled by JavaScript reading window.location.pathname
    return FileResponse(_PLAYER_HTML, media_type="text/html")

# Real-Time WebSocket endpoint for Players
@app.websocket("/ws/play/{quiz_id}/{participant_id}")
async def websocket_player_endpoint(websocket: WebSocket, quiz_id: str, participant_id: str):
    await manager.connect_player(quiz_id, participant_id, websocket)
    
    # Send initial room state
    room = game_engine.get_or_create_room(quiz_id)
    await websocket.send_json({
        "type": "INIT_STATE",
        "quiz_id": quiz_id,
        "status": room.status,
        "mode": room.mode,
        "current_index": room.current_question_index + 1 if room.questions else 0,
        "total_questions": len(room.questions)
    })

    # If quiz is currently active, push the active question payload immediately to the connecting player!
    if room.status in ["QUESTION_ACTIVE", "BUZZER_ACTIVE"] and room.questions and room.current_question_index < len(room.questions):
        current_q = room.questions[room.current_question_index]
        db = SessionLocal()
        try:
            quiz = get_quiz_by_code(db, room.quiz_id) if not room.quiz_id.startswith("QA-") else get_participant_by_id(db, participant_id)
            timer_sec = room.remaining_seconds
        finally:
            db.close()

        safe_question = {
            "id": current_q.id,
            "order_number": current_q.order_number,
            "round_number": current_q.round_number,
            "question_text": current_q.question_text,
            "options": current_q.options,
            "timer_seconds": timer_sec
        }
        await websocket.send_json({
            "type": "QUESTION_ACTIVE",
            "quiz_id": quiz_id,
            "current_index": room.current_question_index + 1,
            "total_questions": len(room.questions),
            "question": safe_question,
            "status": room.status,
            "timer": timer_sec,
            "mode": room.mode
        })

    try:
        while True:
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            msg_type = data.get("type", "").upper()

            if msg_type == "PING":
                await websocket.send_json({"type": "PONG"})

            elif msg_type == "BUZZ":
                participant_name = data.get("participant_name", "Player")
                buzz_res = await game_engine.handle_buzz(quiz_id, participant_id, participant_name)
                await websocket.send_json({
                    "type": "BUZZ_RESPONSE",
                    "data": buzz_res
                })

            elif msg_type == "SUBMIT_ANSWER":
                selected_option = data.get("selected_option", "")
                ans_res = await game_engine.submit_answer(quiz_id, participant_id, selected_option)
                await websocket.send_json({
                    "type": "ANSWER_RESPONSE",
                    "data": ans_res
                })

    except WebSocketDisconnect:
        manager.disconnect_player(quiz_id, participant_id)
        logger.info(f"Player {participant_id} disconnected from WebSocket.")
    except Exception as e:
        logger.error(f"WebSocket error for player {participant_id}: {e}")
        manager.disconnect_player(quiz_id, participant_id)

# Real-Time WebSocket endpoint for Admin Observers
@app.websocket("/ws/admin/{quiz_id}")
async def websocket_admin_endpoint(websocket: WebSocket, quiz_id: str):
    await manager.connect_admin(quiz_id, websocket)
    room = game_engine.get_or_create_room(quiz_id)
    await websocket.send_json({
        "type": "ADMIN_INIT",
        "quiz_id": quiz_id,
        "status": room.status,
        "current_index": room.current_question_index + 1 if room.questions else 0,
        "total_questions": len(room.questions)
    })
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_admin(quiz_id, websocket)
