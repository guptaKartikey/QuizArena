import streamlit as st
import pandas as pd
from database.database import SessionLocal
from database.repositories import get_all_quizzes, get_quiz_questions
from database.models import Question, Quiz

def render_question_manager():
    st.title("Question Bank")
    st.caption("Manage all questions across your quizzes.")

    db = SessionLocal()
    try:
        quizzes = get_all_quizzes(db)
        if not quizzes:
            st.info("No quizzes found. Create a quiz first to see questions.")
            return

        quiz_options = {f"{q.name} ({q.id})": q.id for q in quizzes}
        c_sel, c_del = st.columns([4, 1])
        with c_sel:
            selected_quiz_label = st.selectbox("Select Quiz", list(quiz_options.keys()))
            selected_quiz_id = quiz_options[selected_quiz_label]
        with c_del:
            st.write("")
            st.write("")
            if st.button("🗑️ Delete Quiz", type="secondary", help="Delete this entire quiz and its questions"):
                to_del = db.query(Quiz).filter(Quiz.id == selected_quiz_id).first()
                if to_del:
                    db.delete(to_del)
                    db.commit()
                    st.success("Quiz deleted successfully!")
                    st.rerun()

        questions = get_quiz_questions(db, selected_quiz_id)

        search_query = st.text_input("Search Questions", placeholder="Type keyword to filter...")
        
        filtered = questions
        if search_query.strip():
            query_lower = search_query.lower()
            filtered = [q for q in questions if query_lower in q.question_text.lower()]

        st.subheader(f"Questions ({len(filtered)})")

        if filtered:
            data = []
            for q in filtered:
                opts = q.options
                data.append({
                    "ID": q.id,
                    "Order": q.order_number,
                    "Question": q.question_text,
                    "Option A": opts[0] if len(opts) > 0 else "",
                    "Option B": opts[1] if len(opts) > 1 else "",
                    "Option C": opts[2] if len(opts) > 2 else "",
                    "Option D": opts[3] if len(opts) > 3 else "",
                    "Answer": q.correct_answer,
                    "Explanation": q.explanation or ""
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("No questions found matching your search.")

        st.markdown("---")
        st.subheader("Add Question Manually")
        with st.form("add_question_form"):
            q_text = st.text_input("Question Text *")
            c1, c2 = st.columns(2)
            with c1:
                opt_a = st.text_input("Option A *", value="A. ")
                opt_b = st.text_input("Option B *", value="B. ")
            with c2:
                opt_c = st.text_input("Option C", value="C. ")
                opt_d = st.text_input("Option D", value="D. ")
            
            c3, c4 = st.columns(2)
            with c3:
                correct_ans = st.selectbox("Correct Answer", ["A", "B", "C", "D"])
            with c4:
                explanation = st.text_input("Explanation (Optional)")

            submit = st.form_submit_button("Save Question to Quiz", type="primary")
            if submit and q_text.strip():
                opts = [opt_a, opt_b]
                if opt_c.strip(): opts.append(opt_c)
                if opt_d.strip(): opts.append(opt_d)

                import json
                new_q = Question(
                    quiz_id=selected_quiz_id,
                    question_text=q_text.strip(),
                    options_json=json.dumps(opts),
                    correct_answer=correct_ans,
                    explanation=explanation.strip(),
                    order_number=len(questions) + 1
                )
                db.add(new_q)
                db.commit()
                st.success("Question added successfully!")
                st.rerun()

    finally:
        db.close()
