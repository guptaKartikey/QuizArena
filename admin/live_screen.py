import streamlit as st
import streamlit.components.v1 as components
import requests
from database.database import SessionLocal
from database.repositories import get_all_quizzes, get_quiz_by_id
from services.network_utils import get_local_ip, normalize_cloud_url
import os

API_BASE_URL = normalize_cloud_url(os.getenv("API_BASE_URL", "http://localhost:8000"))

def render_live_screen():
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

        c_sel1, c_sel2 = st.columns([3, 1])
        with c_sel1:
            selected_label = st.selectbox("Select Quiz Room for Big Screen Display", list(quiz_dict.keys()), index=default_index)
        with c_sel2:
            st.write("")
            st.write("")
            if st.button("🔄 Refresh Screen", use_container_width=True):
                st.rerun()

        quiz_id = quiz_dict[selected_label]
        quiz = get_quiz_by_id(db, quiz_id)

        detected_ip_base = get_local_ip()
        if "custom_base_url" not in st.session_state or not st.session_state["custom_base_url"] or ("10." in st.session_state.get("custom_base_url", "") and detected_ip_base.startswith("https://")):
            st.session_state["custom_base_url"] = detected_ip_base

        join_url = f"{st.session_state['custom_base_url']}/join/{quiz.join_code}"

        live_screen_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg-dark: #070D1E;
                    --bg-card: #0F172A;
                    --primary-blue: #2563EB;
                    --accent-cyan: #38BDF8;
                    --accent-green: #10B981;
                    --accent-red: #EF4444;
                    --accent-gold: #F59E0B;
                    --text-white: #FFFFFF;
                    --text-muted: #94A3B8;
                    --border: rgba(255, 255, 255, 0.12);
                    --font-heading: 'Outfit', sans-serif;
                    --font-body: 'Inter', sans-serif;
                }}
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{ background: var(--bg-dark); color: var(--text-white); font-family: var(--font-body); padding: 16px; min-height: 100vh; }}

                .screen-header {{
                    background: var(--bg-card);
                    border: 1px solid var(--border);
                    border-radius: 18px;
                    padding: 16px 28px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 16px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                }}
                .header-brand {{ display: flex; align-items: center; gap: 14px; }}
                .header-brand-icon {{ font-size: 2.4rem; }}
                .header-brand-title {{ font-family: var(--font-heading); font-size: 1.8rem; font-weight: 900; letter-spacing: 1px; color: #FFF; }}
                .header-brand-tag {{ font-size: 0.75rem; font-weight: 700; color: var(--accent-cyan); letter-spacing: 1.5px; }}

                .header-badges {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
                .badge-pill {{
                    background: rgba(255,255,255,0.06);
                    border: 1px solid var(--border);
                    padding: 8px 16px;
                    border-radius: 12px;
                    font-size: 0.95rem;
                    font-weight: 700;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}
                .badge-timer {{
                    background: rgba(245, 158, 11, 0.15);
                    border-color: var(--accent-gold);
                    color: var(--accent-gold);
                    font-size: 1.2rem;
                    font-weight: 800;
                }}
                .badge-timer.urgent {{
                    background: rgba(239, 68, 68, 0.25);
                    border-color: var(--accent-red);
                    color: #FFAAAA;
                    animation: pulseAlert 0.8s infinite alternate;
                }}
                @keyframes pulseAlert {{ from {{ transform: scale(1); }} to {{ transform: scale(1.06); }} }}

                .main-layout {{
                    margin-top: 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }}

                .big-question-card {{
                    background: linear-gradient(145deg, #131E3A, #0F172A);
                    border: 2px solid rgba(59, 130, 246, 0.4);
                    border-radius: 20px;
                    padding: 30px 34px;
                    box-shadow: 0 12px 36px rgba(0,0,0,0.6);
                    position: relative;
                }}
                .q-meta-bar {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 14px;
                    font-size: 0.95rem;
                    font-weight: 700;
                    color: var(--accent-cyan);
                }}
                .big-question-text {{
                    font-family: var(--font-heading);
                    font-size: 1.9rem;
                    font-weight: 800;
                    line-height: 1.35;
                    color: #FFFFFF;
                }}

                .timer-bar-track {{
                    background: rgba(255,255,255,0.08);
                    height: 10px;
                    border-radius: 5px;
                    margin-top: 20px;
                    overflow: hidden;
                }}
                .timer-bar-fill {{
                    background: linear-gradient(90deg, var(--accent-cyan), var(--primary-blue));
                    height: 100%;
                    width: 100%;
                    transition: width 0.8s linear;
                }}

                .options-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 16px;
                }}
                @media (max-width: 768px) {{ .options-grid {{ grid-template-columns: 1fr; }} }}

                .big-opt-card {{
                    background: var(--bg-card);
                    border: 2px solid var(--border);
                    border-radius: 16px;
                    padding: 20px 24px;
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    font-size: 1.2rem;
                    font-weight: 600;
                    transition: all 0.3s ease;
                }}
                .opt-letter {{
                    background: rgba(255,255,255,0.1);
                    width: 44px;
                    height: 44px;
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-family: var(--font-heading);
                    font-weight: 900;
                    font-size: 1.3rem;
                    flex-shrink: 0;
                }}
                .big-opt-card.is-correct {{
                    background: rgba(16, 185, 129, 0.25) !important;
                    border-color: var(--accent-green) !important;
                    box-shadow: 0 0 24px rgba(16, 185, 129, 0.4) !important;
                    transform: scale(1.02);
                }}
                .big-opt-card.is-correct .opt-letter {{
                    background: var(--accent-green) !important;
                    color: #FFFFFF !important;
                }}

                .submissions-bar {{
                    background: var(--bg-card);
                    border: 1px solid var(--border);
                    border-radius: 16px;
                    padding: 16px 24px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 14px;
                }}
                .submissions-count {{ font-size: 1.1rem; font-weight: 700; color: #FFF; }}
                .submissions-count strong {{ color: var(--accent-cyan); font-size: 1.4rem; }}

                .results-breakdown-section {{
                    background: var(--bg-card);
                    border: 1px solid var(--border);
                    border-radius: 20px;
                    padding: 24px 28px;
                    display: none;
                    animation: fadeIn 0.4s ease;
                }}
                @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}

                .results-header-banner {{
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .correct-ans-callout {{
                    display: inline-block;
                    background: rgba(16, 185, 129, 0.2);
                    border: 2px solid var(--accent-green);
                    color: #A7F3D0;
                    font-family: var(--font-heading);
                    font-size: 1.4rem;
                    font-weight: 800;
                    padding: 12px 28px;
                    border-radius: 14px;
                    box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3);
                }}
                .explanation-box {{
                    margin-top: 14px;
                    background: rgba(255,255,255,0.04);
                    border-left: 4px solid var(--accent-cyan);
                    padding: 12px 18px;
                    border-radius: 0 10px 10px 0;
                    font-size: 0.95rem;
                    color: #CBD5E1;
                    text-align: left;
                }}

                .players-columns-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-top: 18px;
                }}
                @media (max-width: 768px) {{ .players-columns-grid {{ grid-template-columns: 1fr; }} }}

                .player-column-card {{
                    background: #0B132B;
                    border: 1px solid var(--border);
                    border-radius: 16px;
                    padding: 18px;
                }}
                .player-column-title {{
                    font-family: var(--font-heading);
                    font-size: 1.15rem;
                    font-weight: 800;
                    margin-bottom: 14px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .col-correct {{ color: var(--accent-green); }}
                .col-wrong {{ color: var(--accent-red); }}

                .player-pill-list {{
                    list-style: none;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    max-height: 280px;
                    overflow-y: auto;
                }}
                .player-pill-item {{
                    background: rgba(255,255,255,0.05);
                    border-radius: 10px;
                    padding: 10px 14px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 0.95rem;
                }}
                .player-pill-item.is-correct {{ border-left: 4px solid var(--accent-green); }}
                .player-pill-item.is-wrong {{ border-left: 4px solid var(--accent-red); }}

                .host-toolbar {{
                    background: #0F172A;
                    border: 1px solid var(--border);
                    border-radius: 16px;
                    padding: 14px 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 12px;
                    margin-top: 10px;
                }}
                .btn-action {{
                    border: none;
                    border-radius: 10px;
                    font-family: var(--font-heading);
                    font-weight: 700;
                    font-size: 0.9rem;
                    padding: 10px 18px;
                    cursor: pointer;
                    transition: transform 0.1s ease;
                }}
                .btn-action:hover {{ transform: translateY(-2px); }}
                .btn-next {{ background: linear-gradient(135deg, #2563EB, #1D4ED8); color: #FFF; }}
                .btn-show {{ background: linear-gradient(135deg, #10B981, #059669); color: #FFF; }}
                .btn-leaderboard {{ background: linear-gradient(135deg, #8B5CF6, #7C3AED); color: #FFF; }}
                .btn-sound {{ background: rgba(255,255,255,0.1); color: #FFF; border: 1px solid var(--border); }}
            </style>
        </head>
        <body>

            <div class="screen-header">
                <div class="header-brand">
                    <span class="header-brand-icon">🏆</span>
                    <div>
                        <div class="header-brand-title">QUIZARENA</div>
                        <div class="header-brand-tag">BIG SCREEN • LIVE STAGE DISPLAY</div>
                    </div>
                </div>

                <div class="header-badges">
                    <div class="badge-pill">
                        <span>📱 Join:</span>
                        <strong style="color:var(--accent-cyan); font-size:1.15rem;">{quiz.join_code}</strong>
                    </div>
                    <div class="badge-pill">
                        <span>Question:</span>
                        <strong id="hdr-q-idx">1 / {len(quiz.questions) if quiz.questions else 0}</strong>
                    </div>
                    <div class="badge-pill badge-timer" id="hdr-timer-pill">
                        ⏱️ <span id="hdr-timer-sec">30s</span>
                    </div>
                    <div class="badge-pill" id="hdr-status-pill">
                        🟢 <span id="hdr-status-text">WAITING</span>
                    </div>
                </div>
            </div>

            <div class="main-layout">
                <div class="big-question-card">
                    <div class="q-meta-bar">
                        <span id="lbl-q-round">ROUND 1</span>
                        <span id="lbl-q-pts">🎯 LIVE QUESTION</span>
                    </div>
                    <div class="big-question-text" id="lbl-q-text">
                        Waiting for host to start the round...
                    </div>
                    <div class="timer-bar-track">
                        <div class="timer-bar-fill" id="timer-bar-fill"></div>
                    </div>
                </div>

                <div class="options-grid" id="options-container">
                    <div class="big-opt-card"><span class="opt-letter">A</span><span>Option A</span></div>
                    <div class="big-opt-card"><span class="opt-letter">B</span><span>Option B</span></div>
                    <div class="big-opt-card"><span class="opt-letter">C</span><span>Option C</span></div>
                    <div class="big-opt-card"><span class="opt-letter">D</span><span>Option D</span></div>
                </div>

                <div class="submissions-bar">
                    <div class="submissions-count">
                        👥 Players Answered: <strong id="lbl-answered-count">0</strong> / <span id="lbl-total-count">0</span>
                    </div>
                    <div style="color:var(--text-muted); font-size:0.95rem;">
                        ⏳ Waiting for: <strong style="color:#FFF;" id="lbl-waiting-count">0</strong> players
                    </div>
                </div>

                <div class="results-breakdown-section" id="results-breakdown-section">
                    <div class="results-header-banner">
                        <div class="correct-ans-callout" id="correct-ans-callout">
                            ✓ CORRECT ANSWER: <span id="correct-ans-letter">B</span>
                        </div>
                        <div class="explanation-box hidden" id="explanation-box">
                            <strong>💡 Explanation:</strong> <span id="explanation-text"></span>
                        </div>
                    </div>

                    <div class="players-columns-grid">
                        <div class="player-column-card">
                            <div class="player-column-title col-correct">
                                <span>✅ CORRECT PLAYERS</span>
                                <span id="lbl-correct-badge" style="background:rgba(16,185,129,0.2); padding:2px 10px; border-radius:10px;">0</span>
                            </div>
                            <ul class="player-pill-list" id="list-correct-players">
                                <li style="color:var(--text-muted); text-align:center; padding:12px;">No players answered correctly.</li>
                            </ul>
                        </div>

                        <div class="player-column-card">
                            <div class="player-column-title col-wrong">
                                <span>❌ INCORRECT / TIMED OUT</span>
                                <span id="lbl-wrong-badge" style="background:rgba(239,68,68,0.2); padding:2px 10px; border-radius:10px;">0</span>
                            </div>
                            <ul class="player-pill-list" id="list-wrong-players">
                                <li style="color:var(--text-muted); text-align:center; padding:12px;">No wrong answers.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            <div class="host-toolbar">
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <button class="btn-action btn-show" onclick="sendControl('show_answer')">👁️ REVEAL ANSWER</button>
                    <button class="btn-action btn-next" onclick="sendControl('next_question')">⏩ NEXT QUESTION</button>
                    <button class="btn-action btn-leaderboard" onclick="sendControl('show_leaderboard')">🏆 SHOW LEADERBOARD</button>
                </div>
                <div style="display:flex; gap:8px;">
                    <button class="btn-action btn-sound" id="btn-sound-mute" onclick="toggleStageSound()">🔊 SOUND: ON</button>
                </div>
            </div>

            <script>
                const quizId = "{quiz_id}";
                const apiBase = "{API_BASE_URL}";
                let ws = null;
                let lastStatus = "";
                let lastRemainingSeconds = -1;

                class QuizSoundEngine {{
                    constructor() {{
                        this.ctx = null;
                        this.masterGain = null;
                        this.bgGain = null;
                        this.sfxGain = null;
                        this.isMuted = false;
                        this.volume = 0.65;
                        this.bgPlaying = false;
                        this.bgStep = 0;
                        this.bgTimer = null;
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
                        if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
                    }}
                    ensureContext() {{
                        this.init();
                        if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
                    }}
                    toggleMute() {{
                        this.isMuted = !this.isMuted;
                        if (this.masterGain && this.ctx) {{
                            this.masterGain.gain.setValueAtTime(this.isMuted ? 0.0001 : this.volume, this.ctx.currentTime);
                        }}
                        return this.isMuted;
                    }}
                    startBgMusic() {{
                        this.ensureContext();
                        if (this.bgPlaying) return;
                        this.bgPlaying = true;
                        this.bgStep = 0;
                        const chordRoots = [130.81, 130.81, 130.81, 130.81, 98.00, 98.00, 98.00, 98.00, 110.00, 110.00, 110.00, 110.00, 87.31, 87.31, 87.31, 87.31];
                        const melodyPitches = [523.25, 659.25, 783.99, 1046.50, 392.00, 493.88, 587.33, 783.99, 440.00, 523.25, 659.25, 880.00, 349.23, 440.00, 523.25, 698.46];

                        this.bgTimer = setInterval(() => {{
                            if (!this.bgPlaying || !this.ctx) return;
                            const now = this.ctx.currentTime;
                            const idx = this.bgStep % 16;
                            if (idx % 2 === 0) {{
                                const oscBass = this.ctx.createOscillator();
                                const gainBass = this.ctx.createGain();
                                oscBass.type = 'triangle';
                                oscBass.frequency.setValueAtTime(chordRoots[idx], now);
                                gainBass.gain.setValueAtTime(0.35, now);
                                gainBass.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
                                oscBass.connect(gainBass);
                                gainBass.connect(this.bgGain);
                                oscBass.start(now);
                                oscBass.stop(now + 0.2);
                            }}
                            const oscMelody = this.ctx.createOscillator();
                            const gainMelody = this.ctx.createGain();
                            oscMelody.type = (idx % 4 === 0) ? 'sine' : 'triangle';
                            oscMelody.frequency.setValueAtTime(melodyPitches[idx], now);
                            gainMelody.gain.setValueAtTime(0.18, now);
                            gainMelody.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
                            oscMelody.connect(gainMelody);
                            gainMelody.connect(this.bgGain);
                            oscMelody.start(now);
                            oscMelody.stop(now + 0.11);
                            this.bgStep++;
                        }}, 115);
                    }}
                    stopBgMusic() {{
                        this.bgPlaying = false;
                        if (this.bgTimer) {{ clearInterval(this.bgTimer); this.bgTimer = null; }}
                    }}
                    playTick(isLow = false) {{
                        this.ensureContext();
                        if (!this.ctx) return;
                        const now = this.ctx.currentTime;
                        const osc = this.ctx.createOscillator();
                        const gain = this.ctx.createGain();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(isLow ? 750 : 1100, now);
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
                        [ {{ f: 783.99, t: 0.00, dur: 0.25 }}, {{ f: 1046.50, t: 0.08, dur: 0.35 }}, {{ f: 1318.51, t: 0.16, dur: 0.60 }} ].forEach(n => {{
                            const osc = this.ctx.createOscillator();
                            const gain = this.ctx.createGain();
                            osc.type = 'sine';
                            osc.frequency.setValueAtTime(n.f, now + n.t);
                            gain.gain.setValueAtTime(0.001, now + n.t);
                            gain.linearRampToValueAtTime(0.5, now + n.t + 0.02);
                            gain.gain.exponentialRampToValueAtTime(0.001, now + n.t + n.dur);
                            osc.connect(gain);
                            gain.connect(this.sfxGain);
                            osc.start(now + n.t);
                            osc.stop(now + n.t + n.dur + 0.05);
                        }});
                    }}
                    playFanfare() {{
                        this.ensureContext();
                        if (!this.ctx) return;
                        this.stopBgMusic();
                        const now = this.ctx.currentTime;
                        [ {{ f: 392.00, t: 0.00, dur: 0.15 }}, {{ f: 523.25, t: 0.16, dur: 0.15 }}, {{ f: 659.25, t: 0.32, dur: 0.15 }}, {{ f: 783.99, t: 0.48, dur: 0.35 }}, {{ f: 659.25, t: 0.88, dur: 0.15 }}, {{ f: 783.99, t: 1.04, dur: 0.70 }} ].forEach(m => {{
                            const osc = this.ctx.createOscillator();
                            const gain = this.ctx.createGain();
                            osc.type = 'triangle';
                            osc.frequency.setValueAtTime(m.f, now + m.t);
                            gain.gain.setValueAtTime(0.001, now + m.t);
                            gain.linearRampToValueAtTime(0.55, now + m.t + 0.03);
                            gain.gain.exponentialRampToValueAtTime(0.001, now + m.t + m.dur);
                            osc.connect(gain);
                            gain.connect(this.sfxGain);
                            osc.start(now + m.t);
                            osc.stop(now + m.t + m.dur + 0.05);
                        }});
                    }}
                }}

                const sound = new QuizSoundEngine();
                document.addEventListener('click', () => sound.ensureContext(), {{ once: false, passive: true }});

                function toggleStageSound() {{
                    const isMuted = sound.toggleMute();
                    const btn = document.getElementById('btn-sound-mute');
                    if (btn) {{
                        btn.innerText = isMuted ? '🔇 SOUND: OFF' : '🔊 SOUND: ON';
                        btn.style.background = isMuted ? '#6B7280' : 'rgba(255,255,255,0.1)';
                    }}
                }}

                function initStageWS() {{
                    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const apiHost = apiBase.replace(/^https?:\\/\\//, '');
                    const wsUrl = `${{wsProtocol}}//${{apiHost}}/ws/admin/${{quizId}}`;
                    try {{
                        ws = new WebSocket(wsUrl);
                        ws.onopen = () => fetchStageData();
                        ws.onmessage = (event) => {{
                            const data = JSON.parse(event.data);
                            fetchStageData();
                        }};
                        ws.onclose = () => setTimeout(initStageWS, 3000);
                    }} catch(e) {{ console.error(e); }}
                }}

                async function fetchStageData() {{
                    try {{
                        const res = await fetch(`${{apiBase}}/api/admin/quiz/${{quizId}}/live_data`);
                        if (res.ok) {{
                            const data = await res.json();
                            updateStageView(data);
                        }}
                    }} catch(e) {{ console.error(e); }}
                }}

                function updateStageView(data) {{
                    if (!data) return;

                    if (data.status === "QUESTION_ACTIVE" || data.status === "BUZZER_ACTIVE") {{
                        if (lastStatus !== data.status) sound.startBgMusic();
                        if (data.remaining_seconds <= 5 && data.remaining_seconds > 0 && data.remaining_seconds !== lastRemainingSeconds) {{
                            sound.playTick(data.remaining_seconds % 2 === 0);
                        }}
                    }} else if (data.status === "FINISHED") {{
                        if (lastStatus !== "FINISHED") {{
                            sound.stopBgMusic();
                            sound.playFanfare();
                        }}
                    }} else if (data.status === "WAITING" || data.status === "PAUSED") {{
                        sound.stopBgMusic();
                    }}

                    lastStatus = data.status;
                    lastRemainingSeconds = data.remaining_seconds;

                    document.getElementById('hdr-q-idx').innerText = `${{data.current_index}} / ${{data.total_questions}}`;
                    document.getElementById('hdr-timer-sec').innerText = `${{data.remaining_seconds}}s`;
                    document.getElementById('hdr-status-text').innerText = data.status;

                    const timerPill = document.getElementById('hdr-timer-pill');
                    if (data.remaining_seconds <= 5 && data.remaining_seconds > 0) {{
                        timerPill.classList.add('urgent');
                    }} else {{
                        timerPill.classList.remove('urgent');
                    }}

                    if (data.current_question) {{
                        document.getElementById('lbl-q-text').innerText = data.current_question.question_text;
                        const optsContainer = document.getElementById('options-container');
                        optsContainer.innerHTML = '';

                        const isRevealed = (data.status === 'QUESTION_RESULT' || data.status === 'FINISHED' || (data.total_participants_count > 0 && data.answered_count >= data.total_participants_count));
                        
                        let opts = data.current_question.options || [];
                        if (typeof opts === 'string') {{
                            try {{ opts = JSON.parse(opts); }} catch(e) {{ opts = []; }}
                        }}

                        opts.forEach(opt => {{
                            const letter = opt.trim()[0];
                            const text = opt.substring(opt.indexOf('.') + 1).trim() || opt;
                            const isCorrectOpt = isRevealed && (letter === data.current_question.correct_answer);

                            const div = document.createElement('div');
                            div.className = 'big-opt-card' + (isCorrectOpt ? ' is-correct' : '');
                            div.innerHTML = `
                                <span class="opt-letter">${{letter}}</span>
                                <span>${{text}}</span>
                                ${{isCorrectOpt ? '<span style="margin-left:auto; font-size:1.4rem;">✓</span>' : ''}}
                            `;
                            optsContainer.appendChild(div);
                        }});
                    }}

                    const timerSec = data.timer_seconds || 30;
                    const pct = Math.max(0, Math.min(100, (data.remaining_seconds / timerSec) * 100));
                    document.getElementById('timer-bar-fill').style.width = `${{pct}}%`;

                    const totalP = data.total_participants_count || data.connected_count || 0;
                    document.getElementById('lbl-answered-count').innerText = data.answered_count;
                    document.getElementById('lbl-total-count').innerText = totalP;
                    document.getElementById('lbl-waiting-count').innerText = data.not_answered_count;

                    const resultsSection = document.getElementById('results-breakdown-section');
                    const isRoundDone = (data.status === 'QUESTION_RESULT' || data.status === 'FINISHED' || (totalP > 0 && data.answered_count >= totalP));

                    if (isRoundDone && data.current_question) {{
                        resultsSection.style.display = 'block';
                        document.getElementById('correct-ans-letter').innerText = `${{data.current_question.correct_answer}}`;

                        const expBox = document.getElementById('explanation-box');
                        if (data.current_question.explanation) {{
                            document.getElementById('explanation-text').innerText = data.current_question.explanation;
                            expBox.classList.remove('hidden');
                        }} else {{
                            expBox.classList.add('hidden');
                        }}

                        const responses = data.participant_responses || [];
                        const correctList = document.getElementById('list-correct-players');
                        const wrongList = document.getElementById('list-wrong-players');
                        correctList.innerHTML = '';
                        wrongList.innerHTML = '';

                        let correctCount = 0;
                        let wrongCount = 0;

                        responses.forEach(p => {{
                            const li = document.createElement('li');
                            if (p.status === 'Correct') {{
                                correctCount++;
                                li.className = 'player-pill-item is-correct';
                                li.innerHTML = `
                                    <strong>✅ ${{p.name}}</strong>
                                    <span style="color:var(--accent-cyan); font-size:0.85rem;">⚡ ${{p.time}} | +${{p.points}} pts</span>
                                `;
                                correctList.appendChild(li);
                            }} else {{
                                wrongCount++;
                                li.className = 'player-pill-item is-wrong';
                                li.innerHTML = `
                                    <strong>❌ ${{p.name}}</strong>
                                    <span style="color:var(--text-muted); font-size:0.85rem;">Picked: ${{p.answer || 'No Answer'}}</span>
                                `;
                                wrongList.appendChild(li);
                            }}
                        }});

                        document.getElementById('lbl-correct-badge').innerText = correctCount;
                        document.getElementById('lbl-wrong-badge').innerText = wrongCount;

                        if (correctCount === 0) {{
                            correctList.innerHTML = '<li style="color:var(--text-muted); text-align:center; padding:12px;">No players got it right!</li>';
                        }}
                        if (wrongCount === 0) {{
                            wrongList.innerHTML = '<li style="color:var(--text-muted); text-align:center; padding:12px;">Everyone got it right! 🎉</li>';
                        }}
                    }} else {{
                        resultsSection.style.display = 'none';
                    }}
                }}

                async function sendControl(action) {{
                    try {{
                        await fetch(`${{apiBase}}/api/admin/quiz/${{quizId}}/control`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ action: action }})
                        }});
                        fetchStageData();
                    }} catch(e) {{ console.error(e); }}
                }}

                initStageWS();
                fetchStageData();
                setInterval(fetchStageData, 1500);
            </script>
        </body>
        </html>
        """

        components.html(live_screen_html, height=1050, scrolling=True)

    finally:
        db.close()
