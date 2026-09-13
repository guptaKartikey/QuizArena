import streamlit as st
import os

def render_settings():
    st.title("System Settings")
    st.caption("Configure environment parameters and admin credentials.")

    st.subheader("Admin Profile")
    st.text_input("Username", value=os.getenv("ADMIN_USERNAME", "admin"), disabled=True)
    st.text_input("Current Password", value="••••••••", type="password", disabled=True)

    st.markdown("---")
    st.subheader("Server Configuration")
    st.text_input("FastAPI Host", value=os.getenv("HOST", "0.0.0.0"), disabled=True)
    st.text_input("FastAPI Port", value=os.getenv("PORT", "8000"), disabled=True)
    st.text_input("Database URL", value=os.getenv("DATABASE_URL", "sqlite:///./quizarena.db"), disabled=True)
    st.text_input("Redis Connection", value=os.getenv("REDIS_URL", "redis://localhost:6379/0"), disabled=True)

    st.info("Environment variables can be updated in the `.env` configuration file.")
