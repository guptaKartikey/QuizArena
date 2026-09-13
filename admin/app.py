import streamlit as st
import os
import sys
import pandas as pd

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from admin.auth_ui import render_login_page
from admin.dashboard import render_dashboard
from admin.quiz_creator import render_quiz_creator
from admin.question_manager import render_question_manager
from admin.active_quiz import render_active_quiz
from admin.live_screen import render_live_screen
from admin.analytics import render_analytics
from admin.results_ui import render_results
from admin.settings_ui import render_settings
from database.database import SessionLocal
from database.repositories import get_all_quizzes, get_quiz_participants, get_quiz_leaderboard

st.set_page_config(
    page_title="QuizArena Admin",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global dark navy custom styling matching reference mockup UI
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');

/* Global styles */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    border-right: 1px solid rgba(255,255,255,0.1);
}

.sidebar-logo {
    text-align: center;
    padding: 20px 10px;
}
.sidebar-brand {
    font-family: 'Outfit', sans-serif;
    font-size: 1.5rem;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: 1px;
}
.sidebar-tagline {
    font-size: 0.65rem;
    font-weight: 700;
    color: #3B82F6;
    letter-spacing: 1px;
}

/* Stat card metrics */
div[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif;
    font-size: 2rem;
    font-weight: 800;
}

/* Primary Button Styling */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
    color: #FFFFFF !important;
    border-radius: 10px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
}

/* Sidebar Radio Options White Text & Pill Cards Styling matching img1 */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label[data-baseweb="radio"] p,
[data-testid="stSidebar"] div[role="radiogroup"] label div p,
[data-testid="stSidebar"] div[role="radiogroup"] label span {
    color: #FFFFFF !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.2px !important;
}

[data-testid="stSidebar"] label[data-baseweb="radio"] {
    background-color: transparent !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    margin-bottom: 4px !important;
    transition: all 0.2s ease !important;
    border: none !important;
}

[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
    background-color: rgba(255, 255, 255, 0.08) !important;
}

/* Active selected navigation item matching img1 blue fill */
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
    background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
}
</style>
""", unsafe_allow_html=True)

# Authentication check
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    render_login_page(api_url)
    st.stop()

label_to_page = {
    "📊 Dashboard": "Dashboard",
    "➕ Create Quiz": "Create Quiz",
    "📚 Question Bank": "Question Bank",
    "📱 Active Quiz": "Active Quiz",
    "📺 Live Stage Screen": "Live Stage Screen",
    "👥 Participants": "Participants",
    "🏆 Leaderboard": "Leaderboard",
    "📑 Results": "Results",
    "⚙️ Settings": "Settings"
}
page_to_label = {v: k for k, v in label_to_page.items()}

# Helper callback to change active sidebar page
def set_page(page_name):
    st.session_state["nav_page"] = page_name
    st.rerun()

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Dashboard"

# Ensure sidebar_radio is always synchronized with nav_page BEFORE rendering st.radio
target_label = page_to_label.get(st.session_state["nav_page"], "📊 Dashboard")
st.session_state["sidebar_radio"] = target_label

def on_sidebar_change():
    selected = st.session_state.get("sidebar_radio")
    if selected in label_to_page:
        st.session_state["nav_page"] = label_to_page[selected]

# Sidebar Navigation
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div style="font-size: 2.2rem;">🏆</div>
        <div class="sidebar-brand">QUIZARENA</div>
        <div class="sidebar-tagline">SCAN • BUZZ • ANSWER • WIN</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    nav_labels = [
        "📊 Dashboard",
        "➕ Create Quiz",
        "📚 Question Bank",
        "📱 Active Quiz",
        "📺 Live Stage Screen",
        "👥 Participants",
        "🏆 Leaderboard",
        "📑 Results",
        "⚙️ Settings"
    ]

    selected_label = st.radio(
        "Navigation",
        nav_labels,
        key="sidebar_radio",
        on_change=on_sidebar_change
    )
    st.session_state["nav_page"] = label_to_page[selected_label]

    st.markdown("---")

    # Show logged-in admin name
    admin_email = st.session_state.get("admin_user", "")
    admin_name = admin_email.split("@")[0].title() if "@" in admin_email else "Admin"
    st.markdown(f"""
    <div style="text-align:center; padding:4px 0 12px 0;">
        <span style="font-size:0.8rem; color:#94A3B8;">Logged in as</span><br>
        <span style="font-family:'Outfit',sans-serif; font-size:0.95rem; font-weight:700; color:#FFFFFF;">{admin_name}</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Logout", use_container_width=True, type="primary"):
        st.session_state["authenticated"] = False
        st.session_state["nav_page"] = "Dashboard"
        st.rerun()

    # Style the logout button red
    st.markdown("""
    <style>
    [data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #DC2626, #B91C1C) !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4) !important;
        padding: 8px 16px !important;
    }
    [data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #EF4444, #DC2626) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Route to selected page
page = st.session_state["nav_page"]

if page == "Dashboard":
    render_dashboard(set_page)
elif page == "Create Quiz":
    render_quiz_creator(set_page)
elif page == "Question Bank":
    render_question_manager()
elif page == "Active Quiz":
    render_active_quiz()
elif page == "Live Stage Screen":
    render_live_screen()
elif page == "Participants":
    st.title("Participants Directory")
    db = SessionLocal()
    try:
        quizzes = get_all_quizzes(db)
        if quizzes:
            q_dict = {f"{q.name} ({q.id})": q.id for q in quizzes}
            sel_q = st.selectbox("Select Quiz", list(q_dict.keys()))
            p_list = get_quiz_participants(db, q_dict[sel_q])
            if p_list:
                import pandas as pd
                st.dataframe(pd.DataFrame([{"ID": p.id, "Name": p.name, "Session Token": p.session_token[:12]+"...", "Joined At": p.joined_at} for p in p_list]), use_container_width=True)
            else:
                st.info("No participants joined yet.")
    finally:
        db.close()
elif page == "Leaderboard":
    st.title("Live Leaderboard View")
    db = SessionLocal()
    try:
        quizzes = get_all_quizzes(db)
        if quizzes:
            q_dict = {f"{q.name} ({q.id})": q.id for q in quizzes}
            sel_q = st.selectbox("Select Quiz", list(q_dict.keys()))
            lb = get_quiz_leaderboard(db, q_dict[sel_q])
            if lb:
                import pandas as pd
                st.dataframe(pd.DataFrame(lb), use_container_width=True, hide_index=True)
            else:
                st.info("No leaderboard scores yet.")
    finally:
        db.close()
elif page == "Results":
    render_results()
elif page == "Settings":
    render_settings()

# ── Footer on every admin page ──
st.markdown("---")
st.markdown("""
<div style="text-align:center; padding:18px 0 10px 0; opacity:0.7;">
    <span style="font-family:'Outfit',sans-serif; font-size:0.85rem; font-weight:600; color:#94A3B8; letter-spacing:0.5px;">
        Made By <span style="color:#3B82F6; font-weight:700;">KARTIKEY GUPTA</span>
    </span>
</div>
""", unsafe_allow_html=True)
