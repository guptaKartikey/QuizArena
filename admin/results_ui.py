import streamlit as st
import pandas as pd
from database.database import SessionLocal
from database.repositories import get_all_quizzes, get_quiz_leaderboard
from services.result_service import (
    export_results_csv,
    export_results_excel,
    export_results_json
)

def render_results():
    st.title("Quiz Results & Export")
    st.caption("View final scoreboards and download reports.")

    db = SessionLocal()
    try:
        quizzes = get_all_quizzes(db)
        if not quizzes:
            st.info("No quizzes found.")
            return

        quiz_dict = {f"{q.name} ({q.id})": q.id for q in quizzes}
        selected_label = st.selectbox("Select Quiz for Results", list(quiz_dict.keys()))
        quiz_id = quiz_dict[selected_label]

        leaderboard = get_quiz_leaderboard(db, quiz_id)

        st.subheader("Full Scoreboard")
        if leaderboard:
            df = pd.DataFrame(leaderboard)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Export Results")
            c1, c2, c3 = st.columns(3)

            with c1:
                csv_data = export_results_csv(db, quiz_id)
                st.download_button(
                    label="📄 Download CSV",
                    data=csv_data,
                    file_name=f"QuizArena_Results_{quiz_id}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with c2:
                excel_data = export_results_excel(db, quiz_id)
                st.download_button(
                    label="📊 Download Excel (.xlsx)",
                    data=excel_data,
                    file_name=f"QuizArena_Results_{quiz_id}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            with c3:
                json_data = export_results_json(db, quiz_id)
                st.download_button(
                    label="📌 Download JSON",
                    data=json_data,
                    file_name=f"QuizArena_Results_{quiz_id}.json",
                    mime="application/json",
                    use_container_width=True
                )
        else:
            st.warning("No results recorded for this quiz yet.")

    finally:
        db.close()
