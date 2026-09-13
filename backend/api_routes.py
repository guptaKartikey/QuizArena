from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
import json
import io
import pandas as pd

from database.database import get_db, init_db
from database.repositories import (
    get_quiz_by_code,
    get_quiz_by_id,
    get_all_quizzes,
    get_quiz_participants,
    get_quiz_leaderboard,
    create_quiz,
    add_questions_to_quiz
)
from services.participant_service import join_quiz_room, generate_demo_participants
from services.quiz_service import create_full_quiz, get_quiz_details
from services.result_service import (
    get_quiz_analytics,
    export_results_csv,
    export_results_excel,
    export_results_json
)
from pdf_processor.parser import (
    extract_text_from_pdf,
    parse_txt_content,
    parse_csv_file,
    parse_excel_file
)
from pdf_processor.question_extractor import parse_questions_from_text
from qr.generator import generate_qr_code_bytes, generate_qr_code_base64
from backend.auth import authenticate_admin
from backend.game_engine import game_engine

router = APIRouter()

@router.post("/api/admin/login")
def admin_login(data: dict):
    email = data.get("email", "")
    password = data.get("password", "")
    if authenticate_admin(email, password):
        return {"success": True, "token": "admin_authenticated_session"}
    return JSONResponse(status_code=401, content={"success": False, "message": "Invalid admin credentials"})

@router.post("/api/admin/signup")
def admin_signup(data: dict):
    from database.database import SessionLocal
    from database.models import Admin
    from backend.auth import hash_password, ADMIN_INVITE_CODE

    email = data.get("email", "").strip()
    password = data.get("password", "")
    invite_code = data.get("invite_code", "")

    if not email or not password:
        return JSONResponse(status_code=400, content={"success": False, "message": "Email and password are required."})

    if len(password) < 6:
        return JSONResponse(status_code=400, content={"success": False, "message": "Password must be at least 6 characters."})

    if invite_code.strip().upper() != ADMIN_INVITE_CODE.strip().upper():
        return JSONResponse(status_code=403, content={"success": False, "message": "Invalid invite code."})

    db = SessionLocal()
    try:
        existing = db.query(Admin).filter(Admin.email == email).first()
        if existing:
            return JSONResponse(status_code=409, content={"success": False, "message": "An account with this email already exists."})

        hashed = hash_password(password)
        new_admin = Admin(email=email, password_hash=hashed)
        db.add(new_admin)
        db.commit()
        return {"success": True, "message": "Account created successfully! You can now login."}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": "Something went wrong. Please try again."})
    finally:
        db.close()

@router.post("/api/join")
def api_join_quiz(data: dict, db: Session = Depends(get_db)):
    join_code = data.get("join_code", "")
    player_name = data.get("name", "")
    team_name = data.get("team_name", None)

    if not join_code or not player_name:
        raise HTTPException(status_code=400, detail="Join code and player name are required.")

    res, err = join_quiz_room(db, join_code, player_name, team_name)
    if err:
        return JSONResponse(status_code=400, content={"success": False, "message": err})
    
    return {"success": True, "data": res}

@router.post("/api/player/submit_answer")
async def api_player_submit_answer(data: dict):
    quiz_id = data.get("quiz_id", "")
    participant_id = data.get("participant_id", "")
    selected_option = data.get("selected_option", "")
    if not quiz_id or not participant_id or not selected_option:
        raise HTTPException(status_code=400, detail="Missing required parameters.")
    
    res = await game_engine.submit_answer(quiz_id, participant_id, selected_option)
    return {"success": True, "data": res}

@router.post("/api/player/buzz")
async def api_player_buzz(data: dict):
    quiz_id = data.get("quiz_id", "")
    participant_id = data.get("participant_id", "")
    participant_name = data.get("participant_name", "Player")
    if not quiz_id or not participant_id:
        raise HTTPException(status_code=400, detail="Missing required parameters.")
    
    res = await game_engine.handle_buzz(quiz_id, participant_id, participant_name)
    return {"success": True, "data": res}

@router.get("/api/player/state")
def api_get_player_state(quiz_id: str, participant_id: str, db: Session = Depends(get_db)):
    room = game_engine.get_or_create_room(quiz_id)
    p = get_participant_by_id(db, participant_id)
    
    current_q = None
    if room.questions and room.current_question_index < len(room.questions):
        q_obj = room.questions[room.current_question_index]
        current_q = {
            "id": q_obj.id,
            "order_number": q_obj.order_number,
            "round_number": q_obj.round_number,
            "question_text": q_obj.question_text,
            "options": q_obj.options,
            "timer_seconds": room.remaining_seconds
        }

    return {
        "type": "QUESTION_ACTIVE" if room.status in ["QUESTION_ACTIVE", "BUZZER_ACTIVE"] else "INIT_STATE",
        "quiz_id": quiz_id,
        "status": room.status,
        "mode": room.mode,
        "current_index": room.current_question_index + 1 if room.questions else 0,
        "total_questions": len(room.questions),
        "timer": room.remaining_seconds,
        "question": current_q,
        "participant": {
            "id": p.id if p else participant_id,
            "name": p.name if p else "Player",
            "lives": p.lives if p else 3,
            "is_eliminated": p.is_eliminated if p else False
        } if p else None
    }

@router.post("/api/parse-file")
async def parse_uploaded_file(file: UploadFile = File(...)):
    filename = file.filename.lower()
    content = await file.read()
    
    questions = []
    if filename.endswith(".pdf"):
        text = extract_text_from_pdf(content)
        questions = parse_questions_from_text(text)
    elif filename.endswith(".txt"):
        text = content.decode("utf-8", errors="ignore")
        questions = parse_questions_from_text(text)
    elif filename.endswith(".csv"):
        import io
        questions = parse_csv_file(io.BytesIO(content))
    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
        import io
        questions = parse_excel_file(io.BytesIO(content))
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF, TXT, CSV, or XLSX.")

    return {"filename": file.filename, "extracted_count": len(questions), "questions": questions}

@router.post("/api/admin/quiz/create")
def api_create_quiz(data: dict, db: Session = Depends(get_db)):
    name = data.get("name", "Untitled Quiz")
    description = data.get("description", "")
    max_participants = int(data.get("max_participants", 50))
    settings = data.get("settings", {})
    questions = data.get("questions", [])

    quiz = create_full_quiz(db, name, description, max_participants, settings, questions)
    
    return {
        "success": True,
        "quiz_id": quiz.id,
        "join_code": quiz.join_code,
        "total_questions": len(questions)
    }

@router.get("/api/quiz/{quiz_id}")
def api_get_quiz(quiz_id: str, db: Session = Depends(get_db)):
    details = get_quiz_details(db, quiz_id)
    if not details:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz = details["quiz"]
    return {
        "id": quiz.id,
        "name": quiz.name,
        "description": quiz.description,
        "join_code": quiz.join_code,
        "status": quiz.status,
        "mode": quiz.mode,
        "max_participants": quiz.max_participants,
        "total_questions": details["total_questions"]
    }

@router.get("/api/qr/{quiz_id}")
def get_qr_image(quiz_id: str, db: Session = Depends(get_db)):
    quiz = get_quiz_by_id(db, quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    join_url = f"http://localhost:8000/join/{quiz.join_code}"
    qr_bytes = generate_qr_code_bytes(join_url)
    return Response(content=qr_bytes, media_type="image/png")

@router.post("/api/admin/quiz/{quiz_id}/control")
async def admin_quiz_control(quiz_id: str, data: dict, db: Session = Depends(get_db)):
    action = data.get("action", "").lower()
    
    if action == "start":
        await game_engine.start_quiz(quiz_id)
    elif action == "pause":
        await game_engine.pause_quiz(quiz_id)
    elif action == "resume":
        await game_engine.resume_quiz(quiz_id)
    elif action == "next_question":
        room = game_engine.get_or_create_room(quiz_id)
        room.current_question_index += 1
        await game_engine.next_question(quiz_id)
    elif action == "show_answer":
        await game_engine.show_question_result(quiz_id)
    elif action == "show_leaderboard":
        await game_engine.show_leaderboard(quiz_id)
    elif action == "end":
        await game_engine.finish_quiz(quiz_id)
    elif action == "restart_question":
        await game_engine.restart_question(quiz_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    return {"success": True, "action": action}

@router.post("/api/admin/quiz/{quiz_id}/announce")
async def api_admin_announce(quiz_id: str, data: dict):
    message = data.get("message", "")
    if message:
        await game_engine.broadcast_announcement(quiz_id, message)
        return {"success": True, "message": message}
    raise HTTPException(status_code=400, detail="Announcement message is required.")

@router.post("/api/admin/quiz/{quiz_id}/extend_timer")
async def api_admin_extend_timer(quiz_id: str, data: dict):
    extra = int(data.get("seconds", 10))
    await game_engine.extend_timer(quiz_id, extra)
    return {"success": True, "added": extra, "extended": extra}

@router.post("/api/admin/quiz/{quiz_id}/toggle_music")
async def api_admin_toggle_music(quiz_id: str, data: dict):
    enabled = bool(data.get("enabled", True))
    await game_engine.broadcast_music_toggle(quiz_id, enabled)
    return {"success": True, "enabled": enabled}

@router.get("/api/admin/quiz/{quiz_id}/live_data")
def api_get_live_data(quiz_id: str):
    data = game_engine.get_live_control_data(quiz_id)
    return data

@router.get("/api/admin/quiz/{quiz_id}/participant/{participant_id}/history")
def api_get_participant_history(quiz_id: str, participant_id: str):
    history = game_engine.get_participant_history(quiz_id, participant_id)
    return history

@router.post("/api/admin/quiz/{quiz_id}/participant/{participant_id}/eliminate")
async def api_admin_eliminate_participant(quiz_id: str, participant_id: str, data: dict = None):
    reason = (data or {}).get("reason", "Eliminated by Admin (Suspected Cheating / Rules Violation)")
    result = await game_engine.eliminate_participant(quiz_id, participant_id, reason)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/api/admin/quiz/{quiz_id}/participant/{participant_id}/restore")
async def api_admin_restore_participant(quiz_id: str, participant_id: str):
    result = await game_engine.restore_participant(quiz_id, participant_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/api/admin/quiz/{quiz_id}/demo_players")
def api_add_demo_players(quiz_id: str, data: dict, db: Session = Depends(get_db)):
    count = int(data.get("count", 15))
    created = generate_demo_participants(db, quiz_id, count)
    return {"success": True, "added_count": len(created)}

@router.get("/api/admin/quiz/{quiz_id}/analytics")
def api_quiz_analytics(quiz_id: str, db: Session = Depends(get_db)):
    return get_quiz_analytics(db, quiz_id)

@router.get("/api/admin/quiz/{quiz_id}/export/{fmt}")
def api_export_quiz_results(quiz_id: str, fmt: str, db: Session = Depends(get_db)):
    fmt = fmt.lower()
    if fmt == "csv":
        csv_data = export_results_csv(db, quiz_id)
        return StreamingResponse(
            io.StringIO(csv_data),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=results_{quiz_id}.csv"}
        )
    elif fmt in ["excel", "xlsx"]:
        excel_data = export_results_excel(db, quiz_id)
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=results_{quiz_id}.xlsx"}
        )
    elif fmt == "json":
        json_str = export_results_json(db, quiz_id)
        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=results_{quiz_id}.json"}
        )
    else:
        raise HTTPException(status_code=400, detail="Supported export formats: csv, excel, json")
