import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.database import SessionLocal
from database.repositories import get_all_quizzes
from services.result_service import get_quiz_analytics

def render_analytics():
    st.title("Analytics Dashboard")
    st.caption("Deep performance metrics and mode-aware visual charts.")

    db = SessionLocal()
    try:
        quizzes = get_all_quizzes(db)
        if not quizzes:
            st.info("No quizzes found.")
            return

        quiz_dict = {f"{q.name} [{q.mode}] ({q.id})": q.id for q in quizzes}
        selected_label = st.selectbox("Select Quiz for Analytics", list(quiz_dict.keys()))
        quiz_id = quiz_dict[selected_label]

        analytics = get_quiz_analytics(db, quiz_id)
        if not analytics or analytics.get("total_participants", 0) == 0:
            st.warning("No participant data available for this quiz yet.")
            return

        st.info(f"Active Game Mode: **{analytics.get('mode', 'CLASSIC')}**")

        # Top Summary Metrics Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Participants", analytics["total_participants"])
        with c2:
            st.metric("Average Score", analytics["avg_score"])
        with c3:
            st.metric("Highest Score", analytics["highest_score"])
        with c4:
            st.metric("Average Accuracy", f"{analytics['avg_accuracy']}%")

        # Mode Specific Metrics Callout
        mode_an = analytics.get("mode_analytics", {})
        if analytics.get("mode") == "FIRST_TO_BUZZ" and mode_an:
            st.markdown("#### 🔔 Buzzer Mode Metrics")
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Total Buzzes", mode_an.get("total_buzzes", 0))
            with m2: st.metric("Buzz Win Rate", f"{mode_an.get('buzz_win_rate', 0)}%")
            with m3: st.metric("Second Chances Triggered", mode_an.get("second_chances_given", 0))

        elif analytics.get("mode") == "SURVIVAL" and mode_an:
            st.markdown("#### ☠️ Survival Mode Status")
            s1, s2 = st.columns(2)
            with s1: st.metric("Active Survivors ❤️", mode_an.get("survivors_count", 0))
            with s2: st.metric("Eliminated Players 💀", mode_an.get("eliminated_count", 0))

        elif analytics.get("mode") == "TEAM_BATTLE" and analytics.get("team_leaderboard"):
            st.markdown("#### 👥 Team Battle Scoreboard")
            st.dataframe(pd.DataFrame(analytics["team_leaderboard"]), use_container_width=True, hide_index=True)

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Score Distribution")
            leaderboard = analytics.get("leaderboard", [])
            if leaderboard:
                df_lb = pd.DataFrame(leaderboard)
                fig_score = px.bar(
                    df_lb,
                    x="name",
                    y="score",
                    color="score",
                    color_continuous_scale="Blues",
                    labels={"name": "Participant", "score": "Score (pts)"},
                    title="Score Breakdown per Player"
                )
                fig_score.update_layout(template="plotly_dark", background_color="rgba(0,0,0,0)")
                st.plotly_chart(fig_score, use_container_width=True)

        with col2:
            st.subheader("Question Performance Accuracy")
            q_stats = analytics.get("question_stats", [])
            if q_stats:
                df_q = pd.DataFrame(q_stats)
                fig_acc = px.line(
                    df_q,
                    x="order_number",
                    y="accuracy",
                    markers=True,
                    labels={"order_number": "Question #", "accuracy": "Accuracy %"},
                    title="Accuracy Trend per Question"
                )
                fig_acc.update_traces(line_color="#10B981", line_width=3)
                fig_acc.update_layout(template="plotly_dark", background_color="rgba(0,0,0,0)")
                st.plotly_chart(fig_acc, use_container_width=True)

        col3, col4 = st.columns(2)

        with col3:
            st.subheader("Average Response Time (seconds)")
            if q_stats:
                df_q = pd.DataFrame(q_stats)
                fig_time = px.line(
                    df_q,
                    x="order_number",
                    y="avg_time",
                    markers=True,
                    labels={"order_number": "Question #", "avg_time": "Avg Response Time (s)"},
                    title="Response Time per Question"
                )
                fig_time.update_traces(line_color="#F59E0B", line_width=3)
                fig_time.update_layout(template="plotly_dark", background_color="rgba(0,0,0,0)")
                st.plotly_chart(fig_time, use_container_width=True)

        with col4:
            st.subheader("Top Performers")
            if leaderboard:
                top_5 = leaderboard[:5]
                st.dataframe(pd.DataFrame(top_5)[["rank", "name", "score", "correct", "wrong", "avg_time"]], use_container_width=True, hide_index=True)

    finally:
        db.close()
