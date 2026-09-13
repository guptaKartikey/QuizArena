import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
from database.database import SessionLocal
from database.repositories import get_all_quizzes, get_quiz_by_id, get_quiz_participants, get_quiz_leaderboard
from qr.generator import generate_qr_code_base64, generate_qr_code_bytes
from services.participant_service import generate_demo_participants
from services.network_utils import get_local_ip, normalize_cloud_url
import os

API_BASE_URL = normalize_cloud_url(os.getenv("API_BASE_URL", "http://localhost:8000"))

def render_active_quiz():
    st.title("Active Quiz Live Control Dashboard")

    db = SessionLocal()
    try:
        quizzes = get_all_quizzes(db)
        if not quizzes:
            st.info("No quizzes found. Please create a quiz first.")
            return

        quiz_dict = {f"{q.name} [{q.mode}] [{q.join_code}] ({q.status})": q.id for q in quizzes}
        
        default_index = 0
        if "active_quiz_id" in st.session_state and st.session_state["active_quiz_id"]:
            for idx, q_id in enumerate(quiz_dict.values()):
                if q_id == st.session_state["active_quiz_id"]:
                    default_index = idx
                    break

        selected_label = st.selectbox("Select Active Quiz Room", list(quiz_dict.keys()), index=default_index)
        quiz_id = quiz_dict[selected_label]
        quiz = get_quiz_by_id(db, quiz_id)

        detected_ip_base = get_local_ip()
        if "custom_base_url" not in st.session_state or not st.session_state["custom_base_url"] or ("10." in st.session_state.get("custom_base_url", "") and detected_ip_base.startswith("https://")):
            st.session_state["custom_base_url"] = detected_ip_base

        base_url = st.text_input("Server Network Address (For QR Code & Mobile Access)", value=st.session_state["custom_base_url"])
        st.session_state["custom_base_url"] = base_url.rstrip("/")

        participants = get_quiz_participants(db, quiz_id)
        join_url = f"{st.session_state['custom_base_url']}/join/{quiz.join_code}"
        qr_base64 = generate_qr_code_base64(join_url)

        # Top QR Code / Join Code bar
        with st.expander("📱 Show Room QR Code & Join Information", expanded=False):
            c_qr1, c_qr2 = st.columns([1, 2])
            with c_qr1:
                st.image(qr_base64, width=180)
            with c_qr2:
                st.markdown(f"### Join Code: **`{quiz.join_code}`**")
                st.markdown(f"Join Link: `{join_url}`")
                st.caption("Participants scan this QR code on their phones to join the room instantly.")

        st.markdown("---")

        # RENDER DEDICATED REAL-TIME 3-COLUMN LIVE CONTROL DASHBOARD COMPONENT
        live_control_dashboard_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg-dark: #0B132B;
                    --bg-card: #1C2541;
                    --bg-card-hover: #263359;
                    --primary-blue: #3B82F6;
                    --accent-green: #10B981;
                    --accent-red: #EF4444;
                    --accent-gold: #F59E0B;
                    --text-white: #F8FAFC;
                    --text-muted: #94A3B8;
                    --border: rgba(255, 255, 255, 0.1);
                    --font-heading: 'Outfit', sans-serif;
                    --font-body: 'Inter', sans-serif;
                }}
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{ background: var(--bg-dark); color: var(--text-white); font-family: var(--font-body); padding: 12px; }}

                /* Header */
                .dashboard-header {{
                    background: #0F172A;
                    border: 1px solid var(--border);
                    border-radius: 14px;
                    padding: 16px 20px;
                    margin-bottom: 16px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 12px;
                }}
                .logo-section {{ display: flex; align-items: center; gap: 12px; }}
                .logo-icon {{ font-size: 2rem; }}
                .brand-title {{ font-family: var(--font-heading); font-size: 1.4rem; font-weight: 800; letter-spacing: 1px; }}
                .badge-live {{ background: rgba(16, 185, 129, 0.2); border: 1px solid var(--accent-green); color: var(--accent-green); font-weight: 800; padding: 4px 12px; border-radius: 12px; font-size: 0.85rem; }}
                .header-metrics {{ display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }}
                .metric-pill {{ background: rgba(255,255,255,0.05); border: 1px solid var(--border); padding: 8px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 700; }}
                .metric-pill strong {{ color: var(--primary-blue); }}

                /* 3-Column Layout */
                .dashboard-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1.3fr 1fr;
                    gap: 16px;
                    margin-bottom: 16px;
                }}
                @media (max-width: 1024px) {{ .dashboard-grid {{ grid-template-columns: 1fr; }} }}

                .panel-card {{
                    background: var(--bg-card);
                    border: 1px solid var(--border);
                    border-radius: 14px;
                    padding: 18px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.4);
                }}
                .panel-title {{ font-family: var(--font-heading); font-size: 1.1rem; margin-bottom: 14px; color: var(--text-white); display: flex; align-items: center; justify-content: space-between; }}

                /* Left Panel: Question Card */
                .q-box {{ background: #0F172A; border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 14px; }}
                .q-text {{ font-size: 1.15rem; font-weight: 700; line-height: 1.4; margin-bottom: 12px; }}
                .q-options {{ display: flex; flex-direction: column; gap: 8px; }}
                .q-opt {{ background: rgba(255,255,255,0.05); border: 1px solid var(--border); padding: 10px 14px; border-radius: 8px; font-size: 0.9rem; font-weight: 600; display: flex; justify-content: space-between; }}
                .q-opt.correct-opt {{ border-color: var(--accent-green); background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }}

                /* Timer Progress Bar */
                .progress-bar-bg {{ background: rgba(255,255,255,0.1); height: 10px; border-radius: 6px; overflow: hidden; margin: 12px 0; }}
                .progress-bar-fill {{ background: var(--accent-gold); height: 100%; width: 100%; transition: width 1s linear; }}

                /* Host Control Buttons Grid */
                .controls-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 14px; }}
                .btn-ctrl {{ padding: 10px 12px; border-radius: 8px; border: none; font-weight: 700; font-family: var(--font-heading); font-size: 0.85rem; cursor: pointer; transition: all 0.2s; }}
                .btn-primary-ctrl {{ background: var(--primary-blue); color: #FFF; }}
                .btn-primary-ctrl:hover {{ background: #2563EB; }}
                .btn-warning-ctrl {{ background: var(--accent-gold); color: #000; }}
                .btn-danger-ctrl {{ background: var(--accent-red); color: #FFF; }}

                /* Middle Panel: Participant Responses Table */
                .filter-bar {{ display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }}
                .filter-btn {{ background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text-muted); padding: 6px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }}
                .filter-btn.active {{ background: var(--primary-blue); color: #FFF; border-color: var(--primary-blue); }}
                
                .response-table-wrapper {{ max-height: 380px; overflow-y: auto; }}
                .resp-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
                .resp-table th {{ background: #0F172A; text-align: left; padding: 10px; color: var(--text-muted); position: sticky; top: 0; }}
                .resp-table td {{ padding: 10px; border-bottom: 1px solid var(--border); cursor: pointer; }}
                .resp-table tr:hover {{ background: var(--bg-card-hover); }}

                .status-badge {{ padding: 3px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 800; display: inline-block; }}
                .status-correct {{ background: rgba(16,185,129,0.2); color: var(--accent-green); }}
                .status-wrong {{ background: rgba(239,68,68,0.2); color: var(--accent-red); }}
                .status-waiting {{ background: rgba(255,255,255,0.1); color: var(--text-muted); }}
                .status-eliminated {{ background: rgba(239,68,68,0.25); color: #FFAAAA; border: 1px solid var(--accent-red); }}

                .btn-eliminate-inline {{ background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.5); color: #FFAAAA; padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; cursor: pointer; transition: all 0.2s; }}
                .btn-eliminate-inline:hover {{ background: var(--accent-red); color: #FFFFFF; }}
                .btn-restore-inline {{ background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.5); color: #A7F3D0; padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; cursor: pointer; transition: all 0.2s; }}
                .btn-restore-inline:hover {{ background: var(--accent-green); color: #FFFFFF; }}

                /* Right Panel: Leaderboard & Mode Monitor */
                .lb-list {{ list-style: none; display: flex; flex-direction: column; gap: 8px; max-height: 360px; overflow-y: auto; }}
                .lb-row {{ background: rgba(255,255,255,0.05); border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; }}
                .lb-rank {{ font-weight: 800; width: 30px; }}
                .lb-score {{ font-family: var(--font-heading); font-weight: 800; color: var(--primary-blue); }}

                /* Mode Monitor Container */
                .mode-monitor {{ background: #0F172A; border: 1px solid var(--border); border-radius: 10px; padding: 12px; margin-top: 14px; font-size: 0.85rem; }}

                /* Bottom Panel */
                .stats-summary-row {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; margin-bottom: 16px; }}
                @media (max-width: 768px) {{ .stats-summary-row {{ grid-template-columns: repeat(2, 1fr); }} }}
                .stat-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 12px; text-align: center; }}
                .stat-card-val {{ font-family: var(--font-heading); font-size: 1.3rem; font-weight: 800; margin-top: 4px; }}

                /* Bottom Distribution, Announcement & Audio */
                .bottom-grid {{ display: grid; grid-template-columns: 1fr 1fr 1.25fr; gap: 16px; }}
                @media (max-width: 1024px) {{ .bottom-grid {{ grid-template-columns: 1fr; }} }}

                .dist-bars {{ display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }}
                .dist-bar-item {{ display: flex; align-items: center; gap: 10px; font-size: 0.85rem; }}
                .dist-bar-bg {{ flex: 1; background: rgba(255,255,255,0.1); height: 16px; border-radius: 8px; overflow: hidden; }}
                .dist-bar-fill {{ background: var(--primary-blue); height: 100%; transition: width 0.5s; }}

                /* Drawer Modal */
                .drawer-overlay {{ position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: none; justify-content: flex-end; z-index: 1000; }}
                .drawer-overlay.active {{ display: flex; }}
                .drawer-card {{ background: var(--bg-card); width: 380px; max-width: 90%; height: 100%; padding: 24px; overflow-y: auto; border-left: 2px solid var(--primary-blue); animation: slideIn 0.3s ease; }}
                @keyframes slideIn {{ from {{ transform: translateX(100%); }} to {{ transform: translateX(0); }} }}

                .announcement-box {{ display: flex; gap: 8px; margin-top: 10px; }}
                .announcement-input {{ flex: 1; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border); background: #0F172A; color: #FFF; outline: none; }}
            </style>
        </head>
        <body>
            <!-- TOP HEADER -->
            <div class="dashboard-header">
                <div class="logo-section">
                    <span class="logo-icon">🏆</span>
                    <div>
                        <span class="brand-title">QUIZARENA</span>
                        <span class="badge-live" id="header-status">🟢 LIVE</span>
                    </div>
                </div>
                <div class="header-metrics">
                    <div class="metric-pill">Quiz: <strong id="hdr-quiz-name">{quiz.name}</strong></div>
                    <div class="metric-pill">Mode: <strong id="hdr-quiz-mode">{quiz.mode}</strong></div>
                    <div class="metric-pill">Question: <strong id="hdr-q-count">1 / 10</strong></div>
                    <div class="metric-pill">Participants: <strong id="hdr-p-count">0 / {quiz.max_participants}</strong></div>
                    <div class="metric-pill">Remaining: <strong id="hdr-timer">⏱️ 00:30</strong></div>
                    <div class="metric-pill">Leader: <strong id="hdr-leader">🥇 N/A</strong></div>
                </div>
            </div>

            <!-- 3-COLUMN LIVE GRID -->
            <div class="dashboard-grid">
                
                <!-- LEFT PANEL: CURRENT QUESTION & CONTROLS -->
                <div class="panel-card">
                    <div class="panel-title">
                        <span>❓ CURRENT QUESTION</span>
                        <span class="badge-live" id="lbl-q-status">🟢 ACTIVE</span>
                    </div>

                    <div class="q-box">
                        <div class="q-text" id="lbl-q-text">Waiting for question to start...</div>
                        <div class="q-options" id="lbl-q-options"></div>
                    </div>

                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" id="timer-progress"></div>
                    </div>

                    <div style="font-size:0.85rem; color:var(--text-muted); display:flex; justify-content:space-between; margin-bottom:10px;">
                        <span>Answered: <strong style="color:#FFF;" id="lbl-answered-ratio">0 / 0</strong></span>
                        <span>Waiting: <strong style="color:#FFF;" id="lbl-waiting-count">0</strong></span>
                    </div>

                    <!-- Buzzer winner box -->
                    <div id="buzzer-winner-box" style="display:none;" class="mode-monitor">
                        <strong>🔴 BUZZER WINNER:</strong> <span id="lbl-buzzer-winner" style="color:var(--accent-gold); font-weight:800;">None</span>
                    </div>

                    <!-- Primary Host Control Buttons -->
                    <div class="controls-grid">
                        <button class="btn-ctrl btn-primary-ctrl" style="background:#10B981;" onclick="sendControl('start')">🚀 START QUIZ</button>
                        <button class="btn-ctrl btn-warning-ctrl" onclick="sendControl('pause')">⏸️ PAUSE</button>
                        <button class="btn-ctrl btn-primary-ctrl" onclick="sendControl('resume')">▶️ RESUME</button>
                        <button class="btn-ctrl btn-primary-ctrl" onclick="sendControl('show_answer')">👁️ SHOW ANSWER</button>
                        <button class="btn-ctrl btn-primary-ctrl" style="background:#8B5CF6;" onclick="sendControl('show_leaderboard')">🏆 SHOW LEADERBOARD</button>
                        <button class="btn-ctrl btn-primary-ctrl" onclick="sendControl('next_question')">⏩ NEXT QUESTION</button>
                        <button class="btn-ctrl btn-warning-ctrl" onclick="sendControl('restart_question')">🔄 RESTART Q</button>
                        <button class="btn-ctrl btn-danger-ctrl" onclick="sendControl('end')">🛑 END QUIZ</button>
                    </div>
                </div>

                <!-- MIDDLE PANEL: LIVE PARTICIPANT RESPONSES -->
                <div class="panel-card">
                    <div class="panel-title">
                        <span>👥 LIVE RESPONSES</span>
                        <span style="font-size:0.8rem; color:var(--text-muted);">Click player for details</span>
                    </div>

                    <div class="filter-bar">
                        <button class="filter-btn active" onclick="setFilter('ALL', this)">All</button>
                        <button class="filter-btn" onclick="setFilter('CORRECT', this)">Correct</button>
                        <button class="filter-btn" onclick="setFilter('WRONG', this)">Wrong</button>
                        <button class="filter-btn" onclick="setFilter('WAITING', this)">Waiting</button>
                        <button class="filter-btn" onclick="setFilter('ELIMINATED', this)">Eliminated</button>
                    </div>

                    <div class="response-table-wrapper">
                        <table class="resp-table">
                            <thead>
                                <tr>
                                    <th>Player</th>
                                    <th>Ans</th>
                                    <th>Status</th>
                                    <th>Time</th>
                                    <th>Pts</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody id="resp-table-body">
                                <tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No participants responses yet.</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- RIGHT PANEL: LEADERBOARD & MODE MONITORS -->
                <div class="panel-card">
                    <div class="panel-title">
                        <span>🏆 LIVE LEADERBOARD</span>
                    </div>

                    <ul class="lb-list" id="live-lb-list">
                        <li style="color:var(--text-muted); text-align:center;">Waiting for scores...</li>
                    </ul>

                    <!-- Mode Specific Monitor -->
                    <div class="mode-monitor" id="mode-monitor-panel">
                        <strong>📊 Mode Monitor ({quiz.mode})</strong>
                        <div id="mode-monitor-content" style="margin-top:6px; color:var(--text-muted);">
                            Active game mode features ready.
                        </div>
                    </div>
                </div>

            </div>

            <!-- BOTTOM STATS SUMMARY -->
            <div class="stats-summary-row">
                <div class="stat-card">
                    <div style="font-size:0.75rem; color:var(--text-muted);">PARTICIPANTS</div>
                    <div class="stat-card-val" id="stat-total-p">0</div>
                </div>
                <div class="stat-card">
                    <div style="font-size:0.75rem; color:var(--text-muted);">ANSWERED</div>
                    <div class="stat-card-val" style="color:var(--primary-blue);" id="stat-answered">0</div>
                </div>
                <div class="stat-card">
                    <div style="font-size:0.75rem; color:var(--text-muted);">CORRECT</div>
                    <div class="stat-card-val" style="color:var(--accent-green);" id="stat-correct">0</div>
                </div>
                <div class="stat-card">
                    <div style="font-size:0.75rem; color:var(--text-muted);">WRONG</div>
                    <div class="stat-card-val" style="color:var(--accent-red);" id="stat-wrong">0</div>
                </div>
                <div class="stat-card">
                    <div style="font-size:0.75rem; color:var(--text-muted);">NOT ANSWERED</div>
                    <div class="stat-card-val" style="color:var(--text-muted);" id="stat-not-ans">0</div>
                </div>
                <div class="stat-card">
                    <div style="font-size:0.75rem; color:var(--text-muted);">AVG TIME</div>
                    <div class="stat-card-val" style="color:var(--accent-gold);" id="stat-avg-time">0.0s</div>
                </div>
            </div>

            <!-- BOTTOM DISTRIBUTION & ANNOUNCEMENTS -->
            <div class="bottom-grid">
                <div class="panel-card">
                    <div class="panel-title"><span>📊 LIVE ANSWER DISTRIBUTION</span></div>
                    <div class="dist-bars" id="dist-bars-container">
                        <div class="dist-bar-item"><span>A</span><div class="dist-bar-bg"><div class="dist-bar-fill" style="width:0%;"></div></div><span>0</span></div>
                        <div class="dist-bar-item"><span>B</span><div class="dist-bar-bg"><div class="dist-bar-fill" style="width:0%;"></div></div><span>0</span></div>
                        <div class="dist-bar-item"><span>C</span><div class="dist-bar-bg"><div class="dist-bar-fill" style="width:0%;"></div></div><span>0</span></div>
                        <div class="dist-bar-item"><span>D</span><div class="dist-bar-bg"><div class="dist-bar-fill" style="width:0%;"></div></div><span>0</span></div>
                    </div>
                </div>

                <div class="panel-card">
                    <div class="panel-title"><span>📢 ADMIN ANNOUNCEMENT</span></div>
                    <p style="font-size:0.8rem; color:var(--text-muted);">Broadcast instant popup notifications to player phones.</p>
                    <div class="announcement-box">
                        <input type="text" class="announcement-input" id="input-announce" placeholder="e.g. 10 seconds remaining!">
                        <button class="btn-ctrl btn-primary-ctrl" onclick="sendAnnouncement()">SEND</button>
                    </div>

                    <div style="margin-top:14px; display:flex; gap:8px;">
                        <button class="btn-ctrl btn-warning-ctrl" onclick="extendTimer(10)">⏱️ +10 SEC</button>
                        <button class="btn-ctrl btn-warning-ctrl" onclick="extendTimer(30)">⏱️ +30 SEC</button>
                    </div>
                </div>

                <!-- LIVE MUSIC & AUDIO CONTROLS -->
                <div class="panel-card">
                    <div class="panel-title"><span>🎵 LIVE MUSIC & SOUND CONTROLS</span></div>
                    <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:8px;">Broadcast music to players & control host audio.</p>
                    
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <div style="display:flex; gap:8px;">
                            <button id="btn-global-music" class="btn-ctrl btn-primary-ctrl" style="background:#8B5CF6; flex:1; font-size:0.75rem;" onclick="toggleGlobalMusic()">
                                🔊 MUTE FOR ALL
                            </button>
                            <button id="btn-host-audio" class="btn-ctrl btn-warning-ctrl" style="flex:1; font-size:0.75rem;" onclick="toggleHostAudio()">
                                🔊 HOST AUDIO: ON
                            </button>
                        </div>

                        <div style="display:flex; align-items:center; gap:8px; font-size:0.75rem; color:var(--text-muted);">
                            <span>Host Vol:</span>
                            <input type="range" id="host-volume-slider" min="0" max="100" value="60" style="flex:1; cursor:pointer;" oninput="adjustHostVolume(this.value)">
                            <span id="host-vol-pct" style="width:30px; text-align:right;">60%</span>
                        </div>

                        <div style="display:flex; gap:4px; flex-wrap:wrap; margin-top:2px;">
                            <button class="btn-ctrl" style="background:rgba(255,255,255,0.08); font-size:0.7rem; padding:3px 6px;" onclick="adminSoundEngine.playCorrect()">🔔 Ding</button>
                            <button class="btn-ctrl" style="background:rgba(255,255,255,0.08); font-size:0.7rem; padding:3px 6px;" onclick="adminSoundEngine.playWrong()">🚨 Buzz</button>
                            <button class="btn-ctrl" style="background:rgba(255,255,255,0.08); font-size:0.7rem; padding:3px 6px;" onclick="adminSoundEngine.playTick()">⏰ Tick</button>
                            <button class="btn-ctrl" style="background:rgba(255,255,255,0.08); font-size:0.7rem; padding:3px 6px;" onclick="adminSoundEngine.playFanfare()">🏆 Fanfare</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- PARTICIPANT DETAILS DRAWER -->
            <div class="drawer-overlay" id="drawer-overlay" onclick="closeDrawer(event)">
                <div class="drawer-card" onclick="event.stopPropagation()">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                        <h3 style="font-family:var(--font-heading);" id="drw-name">Participant Details</h3>
                        <button style="background:none; border:none; color:var(--text-muted); font-size:1.5rem; cursor:pointer;" onclick="closeDrawerForce()">×</button>
                    </div>
                    
                    <div style="background:#0F172A; padding:12px; border-radius:10px; margin-bottom:14px; font-size:0.85rem;">
                        <p>Rank: <strong id="drw-rank">#1</strong></p>
                        <p>Status: <strong id="drw-status" style="color:var(--accent-green);">Active</strong></p>
                        <p>Total Score: <strong style="color:var(--primary-blue);" id="drw-score">0 pts</strong></p>
                        <p>Accuracy: <strong id="drw-acc">0%</strong></p>
                        <p>Avg Time: <strong id="drw-time">0s</strong></p>
                    </div>

                    <div style="display:flex; gap:8px; margin-bottom:16px;" id="drw-actions-container">
                        <button id="drw-btn-eliminate" class="btn-ctrl btn-danger-ctrl" style="flex:1; padding:8px; font-size:0.8rem;" onclick="eliminateDrawerParticipant()">🚫 ELIMINATE PLAYER</button>
                        <button id="drw-btn-restore" class="btn-ctrl btn-primary-ctrl" style="flex:1; padding:8px; font-size:0.8rem; background:#10B981; display:none;" onclick="restoreDrawerParticipant()">🔄 RESTORE PLAYER</button>
                    </div>

                    <h4>Answer History</h4>
                    <ul id="drw-history-list" style="list-style:none; margin-top:10px; font-size:0.8rem; display:flex; flex-direction:column; gap:8px;">
                        <li style="color:var(--text-muted);">No answer history yet.</li>
                    </ul>
                </div>
            </div>

            <!-- REAL-TIME WEBSOCKET DASHBOARD SCRIPT WITH EMBEDDED SOUND ENGINE -->
            <script>
                const quizId = "{quiz_id}";
                const apiBase = "{API_BASE_URL}";
                let ws = null;
                let activeFilter = "ALL";
                let currentResponses = [];
                let isGlobalMusicMuted = false;
                let lastStatus = "";
                let lastRemainingSeconds = -1;

                // ── SYNTHESIS WEB AUDIO ENGINE ──
                class QuizSoundEngine {{
                    constructor() {{
                        this.ctx = null;
                        this.masterGain = null;
                        this.bgGain = null;
                        this.sfxGain = null;
                        this.isMuted = false;
                        this.volume = 0.6;
                        this.bgPlaying = false;
                        this.bgStep = 0;
                        this.bgTimer = null;
                        this.unlocked = false;
                    }}

                    init() {{
                        if (!this.ctx) {{
                            const AudioCtx = window.AudioContext || window.webkitAudioContext;
                            if (!AudioCtx) return;
                            this.ctx = new AudioCtx();

                            this.masterGain = this.ctx.createGain();
                            this.masterGain.gain.setValueAtTime(this.isMuted ? 0.0 : this.volume, this.ctx.currentTime);
                            this.masterGain.connect(this.ctx.destination);

                            this.bgGain = this.ctx.createGain();
                            this.bgGain.gain.setValueAtTime(0.22, this.ctx.currentTime);
                            this.bgGain.connect(this.masterGain);

                            this.sfxGain = this.ctx.createGain();
                            this.sfxGain.gain.setValueAtTime(0.65, this.ctx.currentTime);
                            this.sfxGain.connect(this.masterGain);
                        }}

                        if (this.ctx && this.ctx.state === 'suspended') {{
                            this.ctx.resume();
                        }}
                        this.unlocked = true;
                    }}

                    ensureContext() {{
                        if (!this.ctx || !this.unlocked) {{
                            this.init();
                        }}
                        if (this.ctx && this.ctx.state === 'suspended') {{
                            this.ctx.resume();
                        }}
                    }}

                    setVolume(val) {{
                        this.volume = Math.max(0, Math.min(1, val));
                        if (this.masterGain && this.ctx && !this.isMuted) {{
                            this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);
                        }}
                    }}

                    toggleMute() {{
                        this.isMuted = !this.isMuted;
                        this.applyMuteState();
                        return this.isMuted;
                    }}

                    applyMuteState() {{
                        if (!this.masterGain || !this.ctx) return;
                        const target = this.isMuted ? 0.0001 : this.volume;
                        this.masterGain.gain.setValueAtTime(this.masterGain.gain.value, this.ctx.currentTime);
                        this.masterGain.gain.exponentialRampToValueAtTime(target, this.ctx.currentTime + 0.05);
                    }}

                    startBgMusic() {{
                        this.ensureContext();
                        if (this.bgPlaying) return;
                        this.bgPlaying = true;
                        this.bgStep = 0;

                        const stepTime = 115;
                        const chordRoots = [130.81, 130.81, 130.81, 130.81, 98.00, 98.00, 98.00, 98.00, 110.00, 110.00, 110.00, 110.00, 87.31, 87.31, 87.31, 87.31];
                        const melodyPitches = [
                            523.25, 659.25, 783.99, 1046.50,
                            392.00, 493.88, 587.33, 783.99,
                            440.00, 523.25, 659.25, 880.00,
                            349.23, 440.00, 523.25, 698.46
                        ];

                        this.bgTimer = setInterval(() => {{
                            if (!this.bgPlaying || !this.ctx) return;
                            const now = this.ctx.currentTime;
                            const idx = this.bgStep % 16;

                            if (idx % 2 === 0) {{
                                const root = chordRoots[idx];
                                const oscBass = this.ctx.createOscillator();
                                const gainBass = this.ctx.createGain();
                                oscBass.type = 'triangle';
                                oscBass.frequency.setValueAtTime(root, now);

                                gainBass.gain.setValueAtTime(0.35, now);
                                gainBass.gain.exponentialRampToValueAtTime(0.001, now + 0.18);

                                oscBass.connect(gainBass);
                                gainBass.connect(this.bgGain);
                                oscBass.start(now);
                                oscBass.stop(now + 0.2);
                            }}

                            const pitch = melodyPitches[idx];
                            const oscMelody = this.ctx.createOscillator();
                            const gainMelody = this.ctx.createGain();
                            oscMelody.type = (idx % 4 === 0) ? 'sine' : 'triangle';
                            oscMelody.frequency.setValueAtTime(pitch, now);

                            gainMelody.gain.setValueAtTime(0.18, now);
                            gainMelody.gain.exponentialRampToValueAtTime(0.001, now + 0.1);

                            oscMelody.connect(gainMelody);
                            gainMelody.connect(this.bgGain);
                            oscMelody.start(now);
                            oscMelody.stop(now + 0.11);

                            if (idx % 2 === 1) {{
                                const oscHat = this.ctx.createOscillator();
                                const gainHat = this.ctx.createGain();
                                oscHat.type = 'square';
                                oscHat.frequency.setValueAtTime(1400 + (Math.random() * 400), now);
                                gainHat.gain.setValueAtTime(0.04, now);
                                gainHat.gain.exponentialRampToValueAtTime(0.0001, now + 0.03);
                                oscHat.connect(gainHat);
                                gainHat.connect(this.bgGain);
                                oscHat.start(now);
                                oscHat.stop(now + 0.04);
                            }}

                            this.bgStep++;
                        }}, stepTime);
                    }}

                    stopBgMusic() {{
                        this.bgPlaying = false;
                        if (this.bgTimer) {{
                            clearInterval(this.bgTimer);
                            this.bgTimer = null;
                        }}
                    }}

                    playTick(isLow = false) {{
                        this.ensureContext();
                        if (!this.ctx) return;
                        const now = this.ctx.currentTime;

                        const osc = this.ctx.createOscillator();
                        const gain = this.ctx.createGain();
                        
                        const freq = isLow ? 750 : 1100;
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(freq, now);
                        osc.frequency.exponentialRampToValueAtTime(150, now + 0.04);

                        gain.gain.setValueAtTime(0.45, now);
                        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.045);

                        osc.connect(gain);
                        gain.connect(this.sfxGain);
                        osc.start(now);
                        osc.stop(now + 0.05);
                    }}

                    playCorrect() {{
                        this.ensureContext();
                        if (!this.ctx) return;
                        const now = this.ctx.currentTime;

                        const notes = [
                            {{ f: 783.99, t: 0.00, dur: 0.25 }},
                            {{ f: 1046.50, t: 0.08, dur: 0.35 }},
                            {{ f: 1318.51, t: 0.16, dur: 0.60 }}
                        ];

                        notes.forEach(n => {{
                            const osc = this.ctx.createOscillator();
                            const gain = this.ctx.createGain();
                            osc.type = 'sine';
                            osc.frequency.setValueAtTime(n.f, now + n.t);

                            gain.gain.setValueAtTime(0.001, now + n.t);
                            gain.gain.linearRampToValueAtTime(0.5, now + n.t + 0.02);
                            gain.gain.exponentialRampToValueAtTime(0.001, now + n.t + n.dur);

                            osc.connect(gain);
                            gain.connect(this.sfxGain);
                            osc.start(now + n.t);
                            osc.stop(now + n.t + n.dur + 0.05);
                        }});
                    }}

                    playWrong() {{
                        this.ensureContext();
                        if (!this.ctx) return;
                        const now = this.ctx.currentTime;

                        [140, 133].forEach(freq => {{
                            const osc = this.ctx.createOscillator();
                            const gain = this.ctx.createGain();
                            osc.type = 'sawtooth';
                            osc.frequency.setValueAtTime(freq, now);

                            gain.gain.setValueAtTime(0.4, now);
                            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);

                            osc.connect(gain);
                            gain.connect(this.sfxGain);
                            osc.start(now);
                            osc.stop(now + 0.3);
                        }});
                    }}

                    playFanfare() {{
                        this.ensureContext();
                        if (!this.ctx) return;
                        this.stopBgMusic();

                        const now = this.ctx.currentTime;

                        const melody = [
                            {{ f: 392.00, t: 0.00, dur: 0.15 }},
                            {{ f: 523.25, t: 0.16, dur: 0.15 }},
                            {{ f: 659.25, t: 0.32, dur: 0.15 }},
                            {{ f: 783.99, t: 0.48, dur: 0.35 }},
                            {{ f: 659.25, t: 0.88, dur: 0.15 }},
                            {{ f: 783.99, t: 1.04, dur: 0.70 }}
                        ];

                        melody.forEach(m => {{
                            const osc = this.ctx.createOscillator();
                            const gain = this.ctx.createGain();
                            osc.type = 'triangle';
                            osc.frequency.setValueAtTime(m.f, now + m.t);

                            gain.gain.setValueAtTime(0.001, now + m.t);
                            gain.gain.linearRampToValueAtTime(0.55, now + m.t + 0.03);
                            gain.gain.exponentialRampToValueAtTime(0.001, now + m.t + m.dur);

                            osc.connect(gain);
                            gain.connect(this.sfxGain);
                            osc.start(now + m.t);
                            osc.stop(now + m.t + m.dur + 0.05);
                        }});

                        const chordTime = now + 1.1;
                        [523.25, 659.25, 783.99, 1046.50].forEach(f => {{
                            const osc = this.ctx.createOscillator();
                            const gain = this.ctx.createGain();
                            osc.type = 'sine';
                            osc.frequency.setValueAtTime(f, chordTime);

                            gain.gain.setValueAtTime(0.001, chordTime);
                            gain.gain.linearRampToValueAtTime(0.4, chordTime + 0.04);
                            gain.gain.exponentialRampToValueAtTime(0.001, chordTime + 1.6);

                            osc.connect(gain);
                            gain.connect(this.sfxGain);
                            osc.start(chordTime);
                            osc.stop(chordTime + 1.7);
                        }});
                    }}
                }}

                const adminSoundEngine = new QuizSoundEngine();

                // Unlock audio context on any user click
                document.addEventListener('click', () => {{
                    if (adminSoundEngine) adminSoundEngine.ensureContext();
                }}, {{ once: false, passive: true }});

                async function toggleGlobalMusic() {{
                    isGlobalMusicMuted = !isGlobalMusicMuted;
                    const btn = document.getElementById('btn-global-music');
                    const enabled = !isGlobalMusicMuted;
                    
                    if (btn) {{
                        btn.innerText = isGlobalMusicMuted ? '🔇 UNMUTE FOR ALL' : '🔊 MUTE FOR ALL';
                        btn.style.background = isGlobalMusicMuted ? '#6B7280' : '#8B5CF6';
                    }}

                    try {{
                        await fetch(`${{apiBase}}/api/admin/quiz/${{quizId}}/toggle_music`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ enabled: enabled }})
                        }});
                    }} catch (e) {{
                        console.error("Error broadcasting music toggle:", e);
                    }}
                }}

                function toggleHostAudio() {{
                    const isMuted = adminSoundEngine.toggleMute();
                    const btn = document.getElementById('btn-host-audio');
                    if (btn) {{
                        btn.innerText = isMuted ? '🔇 HOST AUDIO: OFF' : '🔊 HOST AUDIO: ON';
                        btn.style.background = isMuted ? '#6B7280' : 'var(--accent-gold)';
                    }}
                }}

                function adjustHostVolume(val) {{
                    adminSoundEngine.setVolume(val / 100);
                    const pctElem = document.getElementById('host-vol-pct');
                    if (pctElem) pctElem.innerText = `${{val}}%`;
                }}

                function initAdminWS() {{
                    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const apiHost = apiBase.replace(/^https?:\\/\\//, '');
                    const wsUrl = `${{wsProtocol}}//${{apiHost}}/ws/admin/${{quizId}}`;
                    console.log("Connecting Admin WebSocket to:", wsUrl);
                    
                    try {{
                        ws = new WebSocket(wsUrl);

                        ws.onopen = () => {{
                            console.log("Admin WebSocket connected successfully.");
                            fetchLiveData();
                        }};

                        ws.onmessage = (event) => {{
                            const data = JSON.parse(event.data);
                            handleAdminEvent(data);
                        }};

                        ws.onclose = () => {{
                            setTimeout(initAdminWS, 3000);
                        }};

                        ws.onerror = (err) => {{
                            console.error("WebSocket error:", err);
                        }};
                    }} catch (e) {{
                        console.error("Error creating WebSocket:", e);
                    }}
                }}

                async function fetchLiveData() {{
                    try {{
                        const res = await fetch(`${{apiBase}}/api/admin/quiz/${{quizId}}/live_data`);
                        if (res.ok) {{
                            const data = await res.json();
                            updateDashboardData(data);
                        }}
                    }} catch (e) {{
                        console.error("Error fetching live data:", e);
                    }}
                }}

                function handleAdminEvent(data) {{
                    if (data.type === "QUESTION_ACTIVE") {{
                        adminSoundEngine.startBgMusic();
                    }}
                    else if (data.type === "TIMER_TICK") {{
                        if (data.remaining <= 5 && data.remaining > 0) {{
                            adminSoundEngine.playTick(data.remaining % 2 === 0);
                        }}
                    }}
                    else if (data.type === "QUESTION_RESULT") {{
                        adminSoundEngine.stopBgMusic();
                        adminSoundEngine.playCorrect();
                    }}
                    else if (data.type === "QUIZ_FINISHED") {{
                        adminSoundEngine.stopBgMusic();
                        adminSoundEngine.playFanfare();
                    }}
                    else if (data.type === "QUIZ_PAUSED") {{
                        adminSoundEngine.stopBgMusic();
                    }}
                    else if (data.type === "QUIZ_RESUMED") {{
                        if (data.status === "QUESTION_ACTIVE" || data.status === "BUZZER_ACTIVE") {{
                            adminSoundEngine.startBgMusic();
                        }}
                    }}

                    fetchLiveData();
                }}

                function updateDashboardData(data) {{
                    if (!data) return;

                    // Sound automation based on polling state
                    if (data.status === "QUESTION_ACTIVE" || data.status === "BUZZER_ACTIVE") {{
                        if (lastStatus !== data.status) {{
                            adminSoundEngine.startBgMusic();
                        }}
                        if (data.remaining_seconds <= 5 && data.remaining_seconds > 0 && data.remaining_seconds !== lastRemainingSeconds) {{
                            adminSoundEngine.playTick(data.remaining_seconds % 2 === 0);
                        }}
                    }} else if (data.status === "FINISHED") {{
                        if (lastStatus !== "FINISHED") {{
                            adminSoundEngine.stopBgMusic();
                            adminSoundEngine.playFanfare();
                        }}
                    }} else if (data.status === "WAITING" || data.status === "PAUSED") {{
                        adminSoundEngine.stopBgMusic();
                    }}

                    lastStatus = data.status;
                    lastRemainingSeconds = data.remaining_seconds;

                    const statusPill = document.getElementById('header-status');
                    if (statusPill) statusPill.innerText = `🟢 ${{data.status}}`;

                    const qStatusPill = document.getElementById('lbl-q-status');
                    if (qStatusPill) qStatusPill.innerText = `🟢 ${{data.status}}`;

                    document.getElementById('hdr-q-count').innerText = `${{data.current_index}} / ${{data.total_questions}}`;
                    document.getElementById('hdr-p-count').innerText = `${{data.total_participants_count || data.connected_count}} / ${{data.max_participants}}`;
                    document.getElementById('hdr-timer').innerText = `⏱️ 00:${{data.remaining_seconds < 10 ? '0' : ''}}${{data.remaining_seconds}}`;
                    
                    if (data.current_leader) {{
                        document.getElementById('hdr-leader').innerText = `🥇 ${{data.current_leader.name}} (${{data.current_leader.score}} pts)`;
                    }} else {{
                        document.getElementById('hdr-leader').innerText = `🥇 N/A`;
                    }}

                    // Question Box
                    if (data.current_question) {{
                        document.getElementById('lbl-q-text').innerText = `${{data.current_index}}. ${{data.current_question.question_text}}`;
                        const optsContainer = document.getElementById('lbl-q-options');
                        optsContainer.innerHTML = '';
                        data.current_question.options.forEach(opt => {{
                            const div = document.createElement('div');
                            div.className = 'q-opt';
                            if (opt.startsWith(data.current_question.correct_answer + ".") || opt.toUpperCase().startsWith(data.current_question.correct_answer)) {{
                                div.classList.add('correct-opt');
                            }}
                            div.innerText = opt;
                            optsContainer.appendChild(div);
                        }});
                    }}

                    // Timer bar
                    const timerSec = data.timer_seconds || 30;
                    const pct = Math.max(0, Math.min(100, (data.remaining_seconds / timerSec) * 100));
                    document.getElementById('timer-progress').style.width = `${{pct}}%`;

                    const totalP = data.total_participants_count || data.connected_count || 0;
                    document.getElementById('lbl-answered-ratio').innerText = `${{data.answered_count}} / ${{totalP}}`;
                    document.getElementById('lbl-waiting-count').innerText = data.not_answered_count;

                    // Buzzer winner box
                    const buzzBox = document.getElementById('buzzer-winner-box');
                    if (data.buzzer_winner_name) {{
                        buzzBox.style.display = 'block';
                        document.getElementById('lbl-buzzer-winner').innerText = data.buzzer_winner_name;
                    }} else {{
                        buzzBox.style.display = 'none';
                    }}

                    // Participant Responses Table
                    currentResponses = data.participant_responses || [];
                    renderResponsesTable();

                    // Leaderboard
                    const lbList = document.getElementById('live-lb-list');
                    lbList.innerHTML = '';
                    if (data.leaderboard && data.leaderboard.length > 0) {{
                        (data.leaderboard || []).slice(0, 8).forEach(item => {{
                            const li = document.createElement('li');
                            li.className = 'lb-row';
                            li.innerHTML = `
                                <span class="lb-rank">#${{item.rank}}</span>
                                <span style="flex:1; padding-left:10px;">${{item.name}}</span>
                                <span class="lb-score">${{item.score}} pts</span>
                            `;
                            lbList.appendChild(li);
                        }});
                    }} else {{
                        lbList.innerHTML = '<li style="color:var(--text-muted); text-align:center;">Waiting for scores...</li>';
                    }}

                    // Bottom Stats
                    document.getElementById('stat-total-p').innerText = `${{totalP}} / ${{data.max_participants}}`;
                    document.getElementById('stat-answered').innerText = data.answered_count;
                    document.getElementById('stat-correct').innerText = data.correct_count;
                    document.getElementById('stat-wrong').innerText = data.wrong_count;
                    document.getElementById('stat-not-ans').innerText = data.not_answered_count;
                    document.getElementById('stat-avg-time').innerText = `${{data.avg_response_time}}s`;

                    // Distribution bars
                    const dist = data.answer_distribution || {{}};
                    const totalAns = data.answered_count > 0 ? data.answered_count : 1;
                    const container = document.getElementById('dist-bars-container');
                    container.innerHTML = '';
                    ['A', 'B', 'C', 'D'].forEach(opt => {{
                        const count = dist[opt] || 0;
                        const pctBar = data.answered_count > 0 ? (count / totalAns) * 100 : 0;
                        const item = document.createElement('div');
                        item.className = 'dist-bar-item';
                        item.innerHTML = `
                            <span style="font-weight:700; width:15px;">${{opt}}</span>
                            <div class="dist-bar-bg"><div class="dist-bar-fill" style="width:${{pctBar}}%;"></div></div>
                            <span style="width:25px; text-align:right;">${{count}}</span>
                        `;
                        container.appendChild(item);
                    }});
                }}

                let currentDrawerParticipantId = null;
                let currentDrawerParticipantName = "";

                function renderResponsesTable() {{
                    const tbody = document.getElementById('resp-table-body');
                    tbody.innerHTML = '';

                    const filtered = currentResponses.filter(p => {{
                        if (activeFilter === 'ALL') return true;
                        if (activeFilter === 'CORRECT') return p.status === 'Correct';
                        if (activeFilter === 'WRONG') return p.status === 'Wrong';
                        if (activeFilter === 'WAITING') return p.status === 'Waiting';
                        if (activeFilter === 'ELIMINATED') return p.is_eliminated || p.status === 'Eliminated';
                        return true;
                    }});

                    if (filtered.length === 0) {{
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No responses match filter.</td></tr>';
                        return;
                    }}

                    filtered.forEach(p => {{
                        const tr = document.createElement('tr');
                        tr.onclick = () => openParticipantDrawer(p.id);
                        
                        let badgeClass = 'status-waiting';
                        let statusText = p.status;
                        if (p.is_eliminated || p.status === 'Eliminated') {{
                            badgeClass = 'status-eliminated';
                            statusText = '💀 Eliminated';
                        }} else if (p.status === 'Correct') {{
                            badgeClass = 'status-correct';
                        }} else if (p.status === 'Wrong') {{
                            badgeClass = 'status-wrong';
                        }}

                        let actionBtn = '';
                        if (p.is_eliminated || p.status === 'Eliminated') {{
                            actionBtn = `<button class="btn-restore-inline" onclick="restoreParticipant('${{p.id}}', '${{p.name}}', event)">🔄 Restore</button>`;
                        }} else {{
                            actionBtn = `<button class="btn-eliminate-inline" onclick="eliminateParticipant('${{p.id}}', '${{p.name}}', event)">🚫 Eliminate</button>`;
                        }}

                        tr.innerHTML = `
                            <td><strong>${{p.name}}</strong></td>
                            <td>${{p.answer}}</td>
                            <td><span class="status-badge ${{badgeClass}}">${{statusText}}</span></td>
                            <td>${{p.time}}</td>
                            <td style="font-weight:700; color:var(--primary-blue);">${{p.points}}</td>
                            <td style="text-align:center;" onclick="event.stopPropagation()">${{actionBtn}}</td>
                        `;
                        tbody.appendChild(tr);
                    }});
                }}

                function setFilter(filterType, btn) {{
                    activeFilter = filterType;
                    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    renderResponsesTable();
                }}

                async function eliminateParticipant(pId, pName, event) {{
                    if (event) event.stopPropagation();
                    const reason = prompt(`Reason for eliminating ${{pName}} (e.g. Tab Switching / Suspicious Behavior):`, "Anti-Cheat: Suspicious activity detected");
                    if (reason === null) return;

                    try {{
                        const res = await fetch(`${{apiBase}}/api/admin/quiz/${{quizId}}/participant/${{pId}}/eliminate`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ reason: reason }})
                        }});
                        if (res.ok) {{
                            fetchLiveData();
                            if (currentDrawerParticipantId === pId) {{
                                openParticipantDrawer(pId);
                            }}
                        }} else {{
                            alert("Failed to eliminate participant.");
                        }}
                    }} catch (e) {{
                        console.error(e);
                        alert("Error eliminating participant: " + e.message);
                    }}
                }}

                async function restoreParticipant(pId, pName, event) {{
                    if (event) event.stopPropagation();
                    if (!confirm(`Restore ${{pName}} back to active quiz participation?`)) return;

                    try {{
                        const res = await fetch(`${{apiBase}}/api/admin/quiz/${{quizId}}/participant/${{pId}}/restore`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }}
                        }});
                        if (res.ok) {{
                            fetchLiveData();
                            if (currentDrawerParticipantId === pId) {{
                                openParticipantDrawer(pId);
                            }}
                        }} else {{
                            alert("Failed to restore participant.");
                        }}
                    }} catch (e) {{
                        console.error(e);
                        alert("Error restoring participant: " + e.message);
                    }}
                }}

                function eliminateDrawerParticipant() {{
                    if (currentDrawerParticipantId) {{
                        eliminateParticipant(currentDrawerParticipantId, currentDrawerParticipantName);
                    }}
                }}

                function restoreDrawerParticipant() {{
                    if (currentDrawerParticipantId) {{
                        restoreParticipant(currentDrawerParticipantId, currentDrawerParticipantName);
                    }}
                }}

                async function sendControl(action) {{
                    try {{
                        await fetch(`${{apiBase}}/api/admin/quiz/${{quizId}}/control`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ action: action }})
                        }});
                        fetchLiveData();
                    }} catch (e) {{ console.error(e); }}
                }}

                async function extendTimer(seconds) {{
                    try {{
                        await fetch(`${{apiBase}}/api/admin/quiz/${{quizId}}/extend_timer`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ seconds: seconds }})
                        }});
                        fetchLiveData();
                    }} catch (e) {{ console.error(e); }}
                }}

                async function sendAnnouncement() {{
                    const input = document.getElementById('input-announce');
                    const msg = input.value.trim();
                    if (!msg) return;

                    try {{
                        await fetch(`${{apiBase}}/api/admin/quiz/${{quizId}}/announce`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ message: msg }})
                        }});
                        input.value = '';
                    }} catch (e) {{ console.error(e); }}
                }}

                async function openParticipantDrawer(pId) {{
                    try {{
                        const res = await fetch(`${{apiBase}}/api/admin/quiz/${{quizId}}/participant/${{pId}}/history`);
                        const data = await res.json();
                        
                        currentDrawerParticipantId = pId;
                        currentDrawerParticipantName = data.name || "Participant";

                        document.getElementById('drw-name').innerText = data.name;
                        document.getElementById('drw-rank').innerText = `#${{data.rank}}`;
                        document.getElementById('drw-score').innerText = `${{data.total_score}} pts`;
                        document.getElementById('drw-acc').innerText = `${{data.accuracy}}%`;
                        document.getElementById('drw-time').innerText = `${{data.avg_response_time}}s`;

                        const statusEl = document.getElementById('drw-status');
                        const elimBtn = document.getElementById('drw-btn-eliminate');
                        const restBtn = document.getElementById('drw-btn-restore');

                        if (data.is_eliminated) {{
                            statusEl.innerHTML = '<span style="color:var(--accent-red);">💀 Eliminated</span>';
                            if (elimBtn) elimBtn.style.display = 'none';
                            if (restBtn) restBtn.style.display = 'block';
                        }} else {{
                            statusEl.innerHTML = '<span style="color:var(--accent-green);">Active</span>';
                            if (elimBtn) elimBtn.style.display = 'block';
                            if (restBtn) restBtn.style.display = 'none';
                        }}

                        const list = document.getElementById('drw-history-list');
                        list.innerHTML = '';
                        (data.history || []).forEach(h => {{
                            const li = document.createElement('li');
                            li.style.background = 'rgba(255,255,255,0.05)';
                            li.style.padding = '8px 12px';
                            li.style.borderRadius = '6px';
                            li.innerHTML = `
                                <div><strong>Q${{h.question_order}}.</strong> ${{h.question_text}}</div>
                                <div style="color: ${{h.is_correct ? 'var(--accent-green)' : 'var(--accent-red)'}};">
                                    Ans: ${{h.selected_answer}} (${{h.is_correct ? 'Correct' : 'Wrong'}}) | ${{h.points}} pts
                                </div>
                            `;
                            list.appendChild(li);
                        }});

                        document.getElementById('drawer-overlay').classList.add('active');
                    }} catch(e) {{ console.error(e); }}
                }}

                function closeDrawer(e) {{
                    document.getElementById('drawer-overlay').classList.remove('active');
                }}

                function closeDrawerForce() {{
                    document.getElementById('drawer-overlay').classList.remove('active');
                }}

                // Immediate load on script init & auto-poll timer
                fetchLiveData();
                initAdminWS();
                setInterval(fetchLiveData, 2000);
            </script>
        </body>
        </html>
        """

        components.html(live_control_dashboard_html, height=1200, scrolling=True)

        st.markdown("---")
        st.subheader("🏆 Quick Actions & Leaderboard Broadcast")
        c_lb1, c_lb2, c_lb3 = st.columns(3)
        with c_lb1:
            if st.button("🏆 Broadcast Live Leaderboard", type="primary", use_container_width=True):
                try:
                    res = requests.post(f"{API_BASE_URL}/api/admin/quiz/{quiz_id}/control", json={"action": "show_leaderboard"})
                    if res.status_code == 200:
                        st.success("🎉 Leaderboard broadcasted to all player screens!")
                    else:
                        st.error(f"Failed to broadcast leaderboard: {res.text}")
                except Exception as e:
                    st.error(f"Error connecting to server: {e}")
        with c_lb2:
            if st.button("👁️ Show Answer to Players", use_container_width=True):
                try:
                    res = requests.post(f"{API_BASE_URL}/api/admin/quiz/{quiz_id}/control", json={"action": "show_answer"})
                    if res.status_code == 200:
                        st.success("✓ Answer revealed on all player screens!")
                    else:
                        st.error(f"Failed to reveal answer: {res.text}")
                except Exception as e:
                    st.error(f"Error connecting to server: {e}")
        with c_lb3:
            if st.button("⏩ Advance to Next Question", use_container_width=True):
                try:
                    res = requests.post(f"{API_BASE_URL}/api/admin/quiz/{quiz_id}/control", json={"action": "next_question"})
                    if res.status_code == 200:
                        st.success("⏩ Advanced to next question!")
                    else:
                        st.error(f"Failed to advance question: {res.text}")
                except Exception as e:
                    st.error(f"Error connecting to server: {e}")

    finally:
        db.close()
