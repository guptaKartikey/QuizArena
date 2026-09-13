import streamlit as st
import pandas as pd
import json
from database.database import SessionLocal
from services.quiz_service import create_full_quiz
from pdf_processor.parser import (
    extract_text_from_pdf,
    parse_txt_content,
    parse_csv_file,
    parse_excel_file
)
from pdf_processor.question_extractor import parse_questions_from_text
from services.ai_service import generate_questions_with_ai

# 7 Game Modes definition
GAME_MODES_INFO = [
    {
        "key": "CLASSIC",
        "icon": "🧠",
        "title": "CLASSIC QUIZ",
        "tagline": "Standard multiplayer quiz experience",
        "best_for": "General Quiz & Education",
        "description": "All players answer simultaneously. Points awarded for correct answers."
    },
    {
        "key": "FIRST_TO_BUZZ",
        "icon": "🔔",
        "title": "FIRST-TO-BUZZ",
        "tagline": "Fastest player answers first",
        "best_for": "Competitive Trivia & Game Shows",
        "description": "Server locks out all other players. Winner gets the exclusive chance to answer."
    },
    {
        "key": "SPEED QUIZ",
        "icon": "⚡",
        "title": "SPEED QUIZ",
        "tagline": "Faster answers = more points",
        "best_for": "Fast-Paced Action & Reflexes",
        "description": "Tiered or continuous speed bonus rewards lightning-fast responses."
    },
    {
        "key": "TEAM_BATTLE",
        "icon": "👥",
        "title": "TEAM BATTLE",
        "tagline": "Teams compete together",
        "best_for": "Group Play & Corporate Events",
        "description": "Players split into teams. Compete with Captain Only, Majority Vote, or Any Member modes."
    },
    {
        "key": "SURVIVAL",
        "icon": "☠️",
        "title": "SURVIVAL",
        "tagline": "Last player standing",
        "best_for": "High-Stakes Elimination",
        "description": "Players start with lives (❤️ ❤️ ❤️). Wrong answer loses a life. Last survivor wins!"
    },
    {
        "key": "KNOCKOUT",
        "icon": "🥊",
        "title": "KNOCKOUT",
        "tagline": "Elimination rounds",
        "best_for": "Tournaments & Stage Shows",
        "description": "Bottom N players are eliminated after each round until the final winner emerges."
    },
    {
        "key": "CHAMPIONSHIP",
        "icon": "🏆",
        "title": "CHAMPIONSHIP",
        "tagline": "Multi-round tournament",
        "best_for": "League & Championship Finals",
        "description": "Multi-round series with cumulative standings across multiple quiz rounds."
    }
]

def render_quiz_creator(set_page_callback):
    st.title("Create Quiz & Select Game Mode")

    if "wizard_step" not in st.session_state:
        st.session_state["wizard_step"] = 1
    if "selected_mode" not in st.session_state:
        st.session_state["selected_mode"] = "CLASSIC"

    if "quiz_draft" not in st.session_state:
        st.session_state["quiz_draft"] = {
            "name": "General Knowledge Arena",
            "description": "An exciting real-time multiplayer quiz competition",
            "max_participants": 50,
            "question_timer": 30,
            "mode": "CLASSIC",
            "mode_settings": {
                "wrong_buzz_penalty": 5.0,
                "allow_second_chance": True,
                "max_chances": 2,
                "num_teams": 2,
                "team_answer_mode": "ANY",
                "initial_lives": 3,
                "rounds_count": 3,
                "eliminate_per_round": 10,
                "speed_tiers": [
                    {"min_s": 0, "max_s": 5, "pts": 10},
                    {"min_s": 5, "max_s": 10, "pts": 8},
                    {"min_s": 10, "max_s": 15, "pts": 6},
                    {"min_s": 15, "max_s": 20, "pts": 4},
                    {"min_s": 20, "max_s": 30, "pts": 2}
                ]
            },
            "correct_points": 10.0,
            "wrong_points": -5.0,
            "no_answer_points": 0.0,
            "enable_negative_marking": True,
            "enable_speed_bonus": True,
            "enable_buzzer": False,
            "enable_random_questions": False,
            "enable_random_options": False,
            "allow_late_joining": False,
            "show_answer_after": True,
            "show_leaderboard_after": True,
            "automatic_next_question": False,
            "enable_powerups": False,
            "enable_team_buzzer": False,
            "show_explanation": True,
            "allow_answer_change": True,
            "questions": []
        }

    step = st.session_state["wizard_step"]
    
    # Wizard Navigation Bar
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"**{'1. Mode & Details' if step == 1 else '1. Mode & Details'}**")
    with col2:
        st.markdown(f"**{'2. AI / Upload Questions' if step == 2 else '2. AI / Upload Questions'}**")
    with col3:
        st.markdown(f"**{'3. Review Questions' if step == 3 else '3. Review Questions'}**")
    with col4:
        st.markdown(f"**{'4. Rules & Publish' if step == 4 else '4. Rules & Publish'}**")

    st.markdown("---")

    # STEP 1: Select Game Mode & Basic Details
    if step == 1:
        st.subheader("Step 1: Select Game Mode")
        st.caption("Choose the game mode that fits your quiz competition style.")

        # Grid layout for 7 Game Mode Cards
        grid_cols = st.columns(3)
        for idx, mode in enumerate(GAME_MODES_INFO):
            col = grid_cols[idx % 3]
            is_selected = (st.session_state["selected_mode"] == mode["key"])
            border_style = "2px solid #3B82F6" if is_selected else "1px solid rgba(255,255,255,0.1)"
            bg_style = "#1E293B" if is_selected else "#1C2541"
            
            with col:
                st.markdown(f"""
                <div style="background-color: {bg_style}; border: {border_style}; border-radius: 14px; padding: 18px; margin-bottom: 16px; min-height: 220px;">
                    <div style="font-size: 2rem;">{mode['icon']}</div>
                    <h4 style="margin: 6px 0; color: #FFFFFF;">{mode['title']}</h4>
                    <p style="font-size: 0.85rem; color: #3B82F6; font-weight: 700; margin-bottom: 8px;">{mode['tagline']}</p>
                    <p style="font-size: 0.8rem; color: #94A3B8;">{mode['description']}</p>
                    <p style="font-size: 0.75rem; color: #64748B;"><b>Best for:</b> {mode['best_for']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                btn_label = "✅ SELECTED" if is_selected else "SELECT MODE"
                if st.button(btn_label, key=f"btn_mode_{mode['key']}", use_container_width=True, type="primary" if is_selected else "secondary"):
                    st.session_state["selected_mode"] = mode["key"]
                    st.session_state["quiz_draft"]["mode"] = mode["key"]
                    st.rerun()

        st.markdown("---")
        st.subheader("Quiz Basic Details")
        name = st.text_input("Quiz Name *", value=st.session_state["quiz_draft"]["name"])
        desc = st.text_area("Description (Optional)", value=st.session_state["quiz_draft"]["description"])
        
        c1, c2 = st.columns(2)
        with c1:
            max_p = st.number_input("Maximum Participants", min_value=1, max_value=1000, value=st.session_state["quiz_draft"]["max_participants"])
        with c2:
            timer = st.selectbox("Question Timer", [5, 10, 15, 20, 30, 60], index=4)

        if st.button("Next: Add Questions (AI / Upload) ➔", type="primary"):
            st.session_state["quiz_draft"]["name"] = name
            st.session_state["quiz_draft"]["description"] = desc
            st.session_state["quiz_draft"]["max_participants"] = max_p
            st.session_state["quiz_draft"]["question_timer"] = timer
            st.session_state["wizard_step"] = 2
            st.rerun()

    # STEP 2: Add Questions (AI Generator or Document Upload)
    elif step == 2:
        st.subheader("Step 2: Add Questions for Target Quiz")
        st.caption(f"Quiz Name: **{st.session_state['quiz_draft']['name']}** | Game Mode: **{st.session_state['selected_mode']}**")

        tab_ai, tab_upload = st.tabs(["🤖 Generate with Grok AI Assistant", "📄 Upload Document (PDF / CSV / XLSX / TXT)"])

        with tab_ai:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(37, 99, 235, 0.15), rgba(139, 92, 246, 0.15)); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 12px; padding: 14px; margin-bottom: 16px;">
                <div style="font-size: 1.8rem; margin-bottom: 4px;">🤖</div>
                <h4 style="margin: 0; color: #FFFFFF;">AI Question Generator for "{st.session_state['quiz_draft']['name']}"</h4>
                <p style="font-size: 0.85rem; color: #94A3B8; margin: 4px 0 0 0;">
                    Type your topic, and Grok AI will generate questions tailored for your <b>{st.session_state['selected_mode']}</b> game mode!
                </p>
            </div>
            """, unsafe_allow_html=True)

            ai_topic = st.text_input("Topic / Subject *", placeholder="e.g. Space Exploration, Python Basics, Cricket World Cup, Science GK", key="creator_ai_topic")
            
            c_cnt, c_diff = st.columns(2)
            with c_cnt:
                ai_count = st.slider("Number of Questions", min_value=1, max_value=20, value=5, key="creator_ai_count")
            with c_diff:
                ai_diff = st.selectbox("Difficulty Level", ["Mixed / Normal", "Easy", "Medium", "Hard"], key="creator_ai_diff")

            if st.button("🚀 Generate & Add to Quiz Draft", type="primary", use_container_width=True, key="btn_creator_ai_gen"):
                if not ai_topic or not ai_topic.strip():
                    st.error("Please enter a topic first.")
                else:
                    with st.spinner("🤖 Grok AI is generating questions for this quiz..."):
                        try:
                            full_topic = f"{ai_topic.strip()} (Difficulty: {ai_diff}, Target Mode: {st.session_state['selected_mode']})"
                            generated = generate_questions_with_ai(full_topic, count=ai_count)
                            
                            formatted = []
                            for q in generated:
                                options = q.get("options", [])
                                if not isinstance(options, list) or len(options) < 2:
                                    continue
                                formatted.append({
                                    "question_text": q.get("question", "Sample Question"),
                                    "options": options,
                                    "correct_answer": q.get("answer", "A").strip().upper()[:1],
                                    "explanation": q.get("explanation", "")
                                })

                            if formatted:
                                current_qs = st.session_state["quiz_draft"].get("questions", [])
                                current_qs.extend(formatted)
                                st.session_state["quiz_draft"]["questions"] = current_qs
                                st.success(f"🎉 Successfully generated {len(formatted)} questions! Proceeding to review...")
                                st.session_state["wizard_step"] = 3
                                st.rerun()
                            else:
                                st.error("No valid questions were returned. Please try again.")
                        except Exception as e:
                            st.error(f"Error generating questions: {e}")

        with tab_upload:
            uploaded_file = st.file_uploader("Upload PDF, TXT, CSV, or XLSX file", type=["pdf", "txt", "csv", "xlsx"])

            if uploaded_file is not None:
                if st.button("Extract Questions from File", type="primary"):
                    content = uploaded_file.read()
                    filename = uploaded_file.name.lower()
                    extracted = []

                    if filename.endswith(".pdf"):
                        text = extract_text_from_pdf(content)
                        extracted = parse_questions_from_text(text)
                    elif filename.endswith(".txt"):
                        text = content.decode("utf-8", errors="ignore")
                        extracted = parse_questions_from_text(text)
                    elif filename.endswith(".csv"):
                        import io
                        extracted = parse_csv_file(io.BytesIO(content))
                    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
                        import io
                        extracted = parse_excel_file(io.BytesIO(content))

                    if extracted:
                        st.session_state["quiz_draft"]["questions"] = extracted
                        st.success(f"Successfully extracted {len(extracted)} questions!")
                        st.session_state["wizard_step"] = 3
                        st.rerun()

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("⬅ Back"):
                st.session_state["wizard_step"] = 1
                st.rerun()
        with c2:
            if st.button("Skip / Add Manually ➔"):
                st.session_state["wizard_step"] = 3
                st.rerun()

    # STEP 3: Review Questions Editable Table
    elif step == 3:
        st.subheader("Step 3: Review & Edit Questions")
        raw_questions = st.session_state.get("quiz_draft", {}).get("questions")
        if not isinstance(raw_questions, list):
            raw_questions = []
            st.session_state["quiz_draft"]["questions"] = raw_questions

        with st.expander("🤖 Want to add more questions using AI Assistant?"):
            c_top, c_cnt = st.columns([3, 1])
            with c_top:
                more_topic = st.text_input("Topic for Additional Questions", placeholder="e.g. Advanced Python, Data Structures", key="more_ai_topic")
            with c_cnt:
                more_count = st.slider("Count", min_value=1, max_value=10, value=3, key="more_ai_count")
            
            if st.button("✨ Generate & Append Questions", type="primary", key="btn_more_ai_gen"):
                if more_topic.strip():
                    with st.spinner("Generating extra questions..."):
                        try:
                            more_generated = generate_questions_with_ai(more_topic, count=more_count)
                            for q in more_generated:
                                options = q.get("options", [])
                                if isinstance(options, list) and len(options) >= 2:
                                    raw_questions.append({
                                        "question_text": q.get("question", ""),
                                        "options": options,
                                        "correct_answer": q.get("answer", "A").strip().upper()[:1],
                                        "explanation": q.get("explanation", "")
                                    })
                            st.session_state["quiz_draft"]["questions"] = raw_questions
                            st.success(f"Added {len(more_generated)} new questions!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to generate questions: {e}")

        editor_rows = []
        for idx, q in enumerate(raw_questions, start=1):
            if isinstance(q, dict):
                opts = q.get("options", [])
                q_text = q.get("question_text", q.get("question", ""))
                ans = q.get("correct_answer", q.get("answer", "A"))
                exp = q.get("explanation", "")
            else:
                opts = getattr(q, "options", [])
                q_text = getattr(q, "question_text", str(q))
                ans = getattr(q, "correct_answer", "A")
                exp = getattr(q, "explanation", "")

            if not isinstance(opts, list):
                opts = []

            editor_rows.append({
                "#": idx,
                "Question": q_text,
                "Option A": opts[0] if len(opts) > 0 else "",
                "Option B": opts[1] if len(opts) > 1 else "",
                "Option C": opts[2] if len(opts) > 2 else "",
                "Option D": opts[3] if len(opts) > 3 else "",
                "Answer": ans,
                "Explanation": exp
            })

        if not editor_rows:
            editor_rows.append({
                "#": 1,
                "Question": "Which planet is known as the Red Planet?",
                "Option A": "A. Earth",
                "Option B": "B. Mars",
                "Option C": "C. Jupiter",
                "Option D": "D. Venus",
                "Answer": "B",
                "Explanation": "Mars is iron oxide rich."
            })

        df_editor = pd.DataFrame(editor_rows)
        edited_df = st.data_editor(df_editor, num_rows="dynamic", use_container_width=True)

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("⬅ Back to Upload"):
                st.session_state["wizard_step"] = 2
                st.rerun()
        with c2:
            if st.button("Next: Configure Mode & Rules ➔", type="primary"):
                updated_questions = []
                for _, row in edited_df.iterrows():
                    opts = [
                        str(row.get("Option A", "")),
                        str(row.get("Option B", "")),
                        str(row.get("Option C", "")),
                        str(row.get("Option D", ""))
                    ]
                    opts = [o for o in opts if o.strip()]
                    ans = str(row.get("Answer", "A")).strip().upper()
                    if ans not in ["A", "B", "C", "D", "E"]:
                        ans = "A"

                    updated_questions.append({
                        "question_text": str(row.get("Question", "")),
                        "options": opts if opts else ["A. Choice 1", "B. Choice 2"],
                        "correct_answer": ans,
                        "explanation": str(row.get("Explanation", ""))
                    })
                
                st.session_state["quiz_draft"]["questions"] = updated_questions
                st.session_state["wizard_step"] = 4
                st.rerun()

    # STEP 4: Dynamic Mode-Specific Settings & Rules/Modifiers
    elif step == 4:
        st.subheader(f"Step 4: Configure Rules for [{st.session_state['selected_mode']}] Mode")
        draft = st.session_state["quiz_draft"]
        selected_mode = st.session_state["selected_mode"]
        m_settings = draft["mode_settings"]

        st.markdown("### ⚙️ Mode-Specific Settings")

        # 1. FIRST-TO-BUZZ Specific Settings
        if selected_mode == "FIRST_TO_BUZZ":
            st.info("🔔 Configure Buzzer Lock & Second Chance Rules")
            c1, c2 = st.columns(2)
            with c1:
                buzz_pen = st.number_input("Wrong Buzz Penalty (pts)", value=float(m_settings.get("wrong_buzz_penalty", 5.0)))
                ans_time_buzz = st.number_input("Answer Time Given After Buzz (sec)", value=10, min_value=5, max_value=30)
            with c2:
                allow_2nd = st.toggle("Allow Second Chance (Pass to Next Fastest Player)", value=m_settings.get("allow_second_chance", True))
                max_chances = st.number_input("Max Second Chances", value=m_settings.get("max_chances", 2), min_value=1, max_value=5)
            
            m_settings["wrong_buzz_penalty"] = buzz_pen
            m_settings["answer_time_after_buzz"] = ans_time_buzz
            m_settings["allow_second_chance"] = allow_2nd
            m_settings["max_chances"] = max_chances

        # 2. SPEED QUIZ Specific Settings
        elif selected_mode == "SPEED_QUIZ":
            st.info("⚡ Configure Speed Scoring Tiers")
            st.caption("Players answering within faster time brackets earn tiered speed bonus points.")
            
            tiers_data = m_settings.get("speed_tiers", [
                {"min_s": 0, "max_s": 5, "pts": 10},
                {"min_s": 5, "max_s": 10, "pts": 8},
                {"min_s": 10, "max_s": 15, "pts": 6},
                {"min_s": 15, "max_s": 20, "pts": 4},
                {"min_s": 20, "max_s": 30, "pts": 2}
            ])
            df_tiers = st.data_editor(pd.DataFrame(tiers_data), num_rows="dynamic", use_container_width=True)
            m_settings["speed_tiers"] = df_tiers.to_dict(orient="records")

        # 3. TEAM BATTLE Specific Settings
        elif selected_mode == "TEAM_BATTLE":
            st.info("👥 Configure Teams & Team Answer Mode")
            c1, c2 = st.columns(2)
            with c1:
                num_teams = st.selectbox("Number of Teams", [2, 3, 4, 6, 8], index=0)
                team_answer_mode = st.selectbox("Team Answer Mode", ["ANY", "CAPTAIN", "MAJORITY"], index=0, help="ANY = First member answer locks team answer | CAPTAIN = Captain only | MAJORITY = Majority vote")
            with c2:
                enable_team_buzz = st.toggle("Enable Team Buzzer", value=draft.get("enable_team_buzzer", False))
                auto_assign = st.toggle("Automatic Team Assignment", value=True)
            
            m_settings["num_teams"] = num_teams
            m_settings["team_answer_mode"] = team_answer_mode
            draft["enable_team_buzzer"] = enable_team_buzz

        # 4. SURVIVAL MODE Specific Settings
        elif selected_mode == "SURVIVAL":
            st.info("☠️ Configure Lives & Elimination Rules")
            c1, c2 = st.columns(2)
            with c1:
                init_lives = st.slider("Initial Lives per Player", min_value=1, max_value=5, value=3)
            with c2:
                allow_revival = st.toggle("Allow Revival Round", value=False)
            m_settings["initial_lives"] = init_lives
            m_settings["allow_revival"] = allow_revival

        # 5. KNOCKOUT MODE Specific Settings
        elif selected_mode == "KNOCKOUT":
            st.info("🥊 Configure Knockout Round Eliminations")
            c1, c2 = st.columns(2)
            with c1:
                rounds_count = st.slider("Total Knockout Rounds", min_value=2, max_value=5, value=3)
                eliminate_per = st.number_input("Players Eliminated Per Round", value=10, min_value=1, max_value=50)
            with c2:
                tie_breaker = st.selectbox("Tie Breaker Option", ["Fastest Response", "First-to-Buzz", "Admin Decision"])
            
            m_settings["rounds_count"] = rounds_count
            m_settings["eliminate_per_round"] = eliminate_per
            m_settings["tie_breaker"] = tie_breaker
            m_settings["knockout_rounds"] = [{"round": r, "eliminate_count": eliminate_per} for r in range(1, rounds_count + 1)]

        # 6. CHAMPIONSHIP MODE Specific Settings
        elif selected_mode == "CHAMPIONSHIP":
            st.info("🏆 Configure Championship Tournament Series")
            rounds_count = st.slider("Total Tournament Rounds", min_value=2, max_value=6, value=4)
            m_settings["total_rounds"] = rounds_count

        st.markdown("---")
        st.markdown("### 🎛️ Rules & Modifiers System")

        c1, c2 = st.columns(2)
        with c1:
            correct_pts = st.number_input("Correct Answer Base Points", value=float(draft["correct_points"]))
            enable_neg = st.toggle("[ON/OFF] Negative Marking", value=draft["enable_negative_marking"])
            wrong_pts = st.number_input("Wrong Answer Points", value=float(draft["wrong_points"])) if enable_neg else 0.0
            enable_speed = st.toggle("[ON/OFF] Speed Bonus", value=draft["enable_speed_bonus"])
            enable_power = st.toggle("[ON/OFF] Power-ups", value=draft.get("enable_powerups", False))

        with c2:
            rand_q = st.toggle("[ON/OFF] Random Questions Order", value=draft["enable_random_questions"])
            rand_opt = st.toggle("[ON/OFF] Random Options Order", value=draft["enable_random_options"])
            show_ans = st.toggle("[ON/OFF] Show Correct Answer After Question", value=draft["show_answer_after"])
            show_lb = st.toggle("[ON/OFF] Show Leaderboard After Question", value=draft["show_leaderboard_after"])
            late_join = st.toggle("[ON/OFF] Allow Late Joining", value=draft["allow_late_joining"])
            auto_next = st.toggle("[ON/OFF] Automatic Next Question", value=draft["automatic_next_question"])
            show_exp = st.toggle("[ON/OFF] Show Question Explanations", value=draft.get("show_explanation", True))
            allow_ans_change = st.toggle("[ON/OFF] Allow Changing Answer Before Timer Ends", value=draft.get("allow_answer_change", True), help="When ON, players can switch their selected option as many times as they like before the question timer runs out.")

        st.markdown("---")

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("⬅ Back to Review"):
                st.session_state["wizard_step"] = 3
                st.rerun()
        with c2:
            if st.button("🚀 PUBLISH GAME ROOM", type="primary", use_container_width=True):
                db = SessionLocal()
                try:
                    settings = {
                        "question_timer": draft["question_timer"],
                        "correct_points": correct_pts,
                        "wrong_points": wrong_pts,
                        "no_answer_points": draft["no_answer_points"],
                        "enable_negative_marking": enable_neg,
                        "enable_speed_bonus": enable_speed,
                        "enable_buzzer": (selected_mode == "FIRST_TO_BUZZ"),
                        "enable_random_questions": rand_q,
                        "enable_random_options": rand_opt,
                        "allow_late_joining": late_join,
                        "show_answer_after": show_ans,
                        "show_leaderboard_after": show_lb,
                        "automatic_next_question": auto_next,
                        "enable_powerups": enable_power,
                        "enable_team_buzzer": draft.get("enable_team_buzzer", False),
                        "show_explanation": show_exp,
                        "allow_answer_change": allow_ans_change
                    }

                    quiz = create_full_quiz(
                        db=db,
                        name=draft["name"],
                        description=draft["description"],
                        max_participants=draft["max_participants"],
                        settings=settings,
                        questions=draft["questions"]
                    )

                    # Update specific mode and mode settings
                    quiz.mode = selected_mode
                    quiz.mode_settings = m_settings
                    db.commit()

                    st.session_state["active_quiz_id"] = quiz.id
                    st.success(f"Quiz Room Published! Mode: [{selected_mode}] | Join Code: {quiz.join_code}")
                    st.session_state["wizard_step"] = 1
                    set_page_callback("Active Quiz")
                finally:
                    db.close()
