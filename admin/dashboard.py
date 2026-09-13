import streamlit as st
import pandas as pd
from database.database import SessionLocal
from database.repositories import get_all_quizzes, get_quiz_participants, get_quiz_questions
from database.models import Quiz, Question, Participant

def render_dashboard(set_page_callback):
    st.title("Dashboard")
    admin_email = st.session_state.get("admin_user", "")
    admin_name = admin_email.split("@")[0].title() if "@" in admin_email else "Admin"
    st.caption(f"Welcome back, {admin_name}!")

    db = SessionLocal()
    try:
        quizzes = db.query(Quiz).order_by(Quiz.created_at.desc()).all()
        total_quizzes = len(quizzes)
        
        # Only genuinely active in-progress quizzes
        active_statuses = ["QUESTION_ACTIVE", "BUZZER_ACTIVE", "STARTING", "ANSWERING"]
        active_quizzes = sum(1 for q in quizzes if q.status in active_statuses)
        completed_quizzes = sum(1 for q in quizzes if q.status in ["FINISHED", "COMPLETED"])
        
        total_participants = db.query(Participant).count()
        total_questions = db.query(Question).count()

        # Quick Actions custom CSS styles
        st.markdown("""
        <style>
        .quick-btn-blue button {
            background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 12px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important;
        }
        .quick-btn-green button {
            background: linear-gradient(135deg, #10B981, #059669) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 12px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3) !important;
        }
        .quick-btn-purple button {
            background: linear-gradient(135deg, #8B5CF6, #7C3AED) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 12px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 14px rgba(139, 92, 246, 0.3) !important;
        }
        .quick-btn-orange button {
            background: linear-gradient(135deg, #F97316, #EA580C) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 12px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 14px rgba(249, 115, 22, 0.3) !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Render Stat Cards matching img1 layout
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 28px;">
            <div style="background: #1C2541; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 20px 16px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.35);">
                <div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(59, 130, 246, 0.15); color: #3B82F6; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px auto; font-size: 1.3rem;">📋</div>
                <div style="font-family: 'Outfit', sans-serif; font-size: 2.2rem; font-weight: 800; color: #FFFFFF; line-height: 1;">{total_quizzes}</div>
                <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 700; letter-spacing: 0.5px; margin-top: 8px;">TOTAL QUIZZES</div>
            </div>
            <div style="background: #1C2541; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 20px 16px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.35);">
                <div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(16, 185, 129, 0.15); color: #10B981; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px auto; font-size: 1.3rem;">🟢</div>
                <div style="font-family: 'Outfit', sans-serif; font-size: 2.2rem; font-weight: 800; color: #10B981; line-height: 1;">{active_quizzes}</div>
                <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 700; letter-spacing: 0.5px; margin-top: 8px;">ACTIVE QUIZZES</div>
            </div>
            <div style="background: #1C2541; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 20px 16px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.35);">
                <div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(245, 158, 11, 0.15); color: #F59E0B; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px auto; font-size: 1.3rem;">👥</div>
                <div style="font-family: 'Outfit', sans-serif; font-size: 2.2rem; font-weight: 800; color: #FFFFFF; line-height: 1;">{total_participants}</div>
                <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 700; letter-spacing: 0.5px; margin-top: 8px;">TOTAL PARTICIPANTS</div>
            </div>
            <div style="background: #1C2541; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 20px 16px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.35);">
                <div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(139, 92, 246, 0.15); color: #8B5CF6; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px auto; font-size: 1.3rem;">❓</div>
                <div style="font-family: 'Outfit', sans-serif; font-size: 2.2rem; font-weight: 800; color: #FFFFFF; line-height: 1;">{total_questions}</div>
                <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 700; letter-spacing: 0.5px; margin-top: 8px;">TOTAL QUESTIONS</div>
            </div>
            <div style="background: #1C2541; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 20px 16px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.35);">
                <div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(236, 72, 153, 0.15); color: #EC4899; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px auto; font-size: 1.3rem;">🏆</div>
                <div style="font-family: 'Outfit', sans-serif; font-size: 2.2rem; font-weight: 800; color: #FFFFFF; line-height: 1;">{completed_quizzes}</div>
                <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 700; letter-spacing: 0.5px; margin-top: 8px;">COMPLETED QUIZZES</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_main, col_side = st.columns([3, 1.2])

        with col_main:
            st.subheader("Recent Quizzes")
            if quizzes:
                data = []
                for q in quizzes[:12]:
                    p_count = len(get_quiz_participants(db, q.id))
                    data.append({
                        "Quiz ID": q.id,
                        "Name": q.name,
                        "Join Code": q.join_code,
                        "Status": q.status,
                        "Questions": len(q.questions),
                        "Participants": f"{p_count} / {q.max_participants}",
                        "Mode": q.mode,
                        "Created At": q.created_at.strftime("%b %d, %Y %H:%M") if q.created_at else "N/A"
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                with st.expander("🗑️ Manage / Delete Quizzes"):
                    q_del_map = {f"{q.name} [{q.id}] ({len(q.questions)} Qs, Status: {q.status})": q.id for q in quizzes}
                    del_choice = st.selectbox("Select Quiz to Delete", list(q_del_map.keys()))
                    if st.button("🗑️ Delete Selected Quiz", type="primary"):
                        target_id = q_del_map[del_choice]
                        to_del = db.query(Quiz).filter(Quiz.id == target_id).first()
                        if to_del:
                            db.delete(to_del)
                            db.commit()
                            st.success(f"Quiz '{del_choice}' deleted successfully!")
                            st.rerun()
            else:
                st.info("No quizzes created yet. Click 'Create New Quiz' to get started!")

        with col_side:
            st.subheader("Quick Actions")
            qa_col1, qa_col2 = st.columns(2)
            with qa_col1:
                st.markdown('<div class="quick-btn-blue">', unsafe_allow_html=True)
                if st.button("➕ Create Quiz", use_container_width=True, key="qa_create"):
                    set_page_callback("Create Quiz")
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div class="quick-btn-purple">', unsafe_allow_html=True)
                if st.button("📚 Question Bank", use_container_width=True, key="qa_qbank"):
                    set_page_callback("Question Bank")
                st.markdown('</div>', unsafe_allow_html=True)

            with qa_col2:
                st.markdown('<div class="quick-btn-green">', unsafe_allow_html=True)
                if st.button("📄 Upload PDF", use_container_width=True, key="qa_pdf"):
                    set_page_callback("Create Quiz")
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div class="quick-btn-orange">', unsafe_allow_html=True)
                if st.button("📱 Active Quiz", use_container_width=True, key="qa_active"):
                    set_page_callback("Active Quiz")
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🧹 Clean Test / Empty Quizzes", use_container_width=True):
                # Clean quizzes with 0 questions or test names
                test_quizzes = db.query(Quiz).filter(
                    (Quiz.name.like("%Test%")) | (Quiz.name.like("%Sample%")) | (Quiz.name.like("%Timer Extend%"))
                ).all()
                for t_q in test_quizzes:
                    db.delete(t_q)
                db.commit()
                st.success(f"Cleaned {len(test_quizzes)} test quizzes!")
                st.rerun()
    finally:
        db.close()

