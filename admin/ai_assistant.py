import streamlit as st
import json
from database.database import SessionLocal
from database.repositories import get_all_quizzes, get_quiz_questions
from database.models import Question, Quiz
from services.ai_service import generate_questions_with_ai

@st.dialog("🤖 AI Quiz Question Assistant", width="medium")
def open_ai_assistant_dialog(set_page_callback=None):
    st.markdown("""
    <div style="text-align: center; margin-bottom: 16px;">
        <div style="font-size: 2.5rem; line-height: 1;">🤖</div>
        <h3 style="margin: 4px 0 2px 0; color: #1E293B;">AI Question Generator</h3>
        <p style="color: #64748B; font-size: 0.85rem; margin: 0;">
            Enter any topic and quantity — Grok AI will generate questions, options, answers, and load them straight into your Question Bank!
        </p>
    </div>
    """, unsafe_allow_html=True)

    db = SessionLocal()
    try:
        quizzes = get_all_quizzes(db)
        if not quizzes:
            st.warning("⚠️ No quizzes found! Please create a quiz first from the **Create Quiz** menu.")
            return

        quiz_map = {f"📋 {q.name} (Code: {q.join_code})": q.id for q in quizzes}
        selected_quiz_label = st.selectbox("Target Quiz *", list(quiz_map.keys()), help="Select which quiz to load generated questions into")
        selected_quiz_id = quiz_map[selected_quiz_label]

        topic = st.text_input(
            "Topic / Subject *",
            placeholder="e.g. Python Programming, World War II, Space Exploration, Cricket GK",
            help="What topic should the questions cover?"
        )

        c1, c2 = st.columns(2)
        with c1:
            count = st.slider("Number of Questions", min_value=1, max_value=20, value=5)
        with c2:
            difficulty = st.selectbox("Difficulty Level", ["Mixed / Normal", "Easy", "Medium", "Hard"])

        submit_btn = st.button("🚀 Generate & Load Questions", use_container_width=True, type="primary")

        if submit_btn:
            if not topic or not topic.strip():
                st.error("Please enter a topic first.")
                return

            with st.spinner("🤖 Grok AI is generating high-quality questions..."):
                try:
                    full_topic = f"{topic.strip()} (Difficulty: {difficulty})"
                    questions_data = generate_questions_with_ai(full_topic, count=count)

                    existing_questions = get_quiz_questions(db, selected_quiz_id)
                    start_order = len(existing_questions) + 1

                    for idx, q in enumerate(questions_data):
                        options = q.get("options", [])
                        if not isinstance(options, list) or len(options) < 2:
                            continue

                        new_q = Question(
                            quiz_id=selected_quiz_id,
                            question_text=q.get("question", f"Question {idx+1}"),
                            options_json=json.dumps(options),
                            correct_answer=q.get("answer", "A").strip().upper()[:1],
                            explanation=q.get("explanation", ""),
                            order_number=start_order + idx
                        )
                        db.add(new_q)

                    db.commit()
                    st.success(f"🎉 Successfully generated and added {len(questions_data)} questions!")

                    # Redirect to Question Bank
                    st.session_state["nav_page"] = "Question Bank"
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate questions: {e}")
    finally:
        db.close()
