import streamlit as st
import os
import requests

def render_login_page(api_base_url: str):
    # Initialize auth mode in session state if not set
    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "login"

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Inter:wght@400;500;600;700&display=swap');

    /* ── 1. HIDE ALL STREAMLIT SIDEBAR ON AUTH PAGE ── */
    [data-testid="stSidebar"], 
    section[data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {
        display: none !important;
        width: 0 !important;
        visibility: hidden !important;
    }

    /* ── 2. PAGE BACKGROUND ── */
    [data-testid="stAppViewContainer"],
    .stApp {
        background: #0B132B !important;
        min-height: 100vh !important;
    }
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* ── 3. STRICT CARD SIZING (NEVER STRETCH WIDE) ── */
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        max-width: 440px !important;
        width: 100% !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
        padding-top: 36px !important;
        padding-bottom: 40px !important;
        margin: 0 auto !important;
    }

    /* ── 4. BRAND HEADER ── */
    .brand-box {
        text-align: center;
        margin-bottom: 22px;
    }
    .brand-trophy {
        font-size: 3.5rem;
        line-height: 1;
        margin-bottom: 6px;
        filter: drop-shadow(0 4px 12px rgba(245, 158, 11, 0.4));
    }
    .brand-name {
        font-family: 'Outfit', sans-serif;
        font-size: 2.1rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: 2px;
        line-height: 1.1;
    }
    .brand-tagline {
        font-family: 'Inter', sans-serif;
        font-size: 0.72rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.7);
        letter-spacing: 2px;
        margin-top: 5px;
    }

    /* ── 5. AUTH TOGGLE PILLS (LOGIN / SIGN UP) ── */
    .stTabs [data-baseweb="tab-list"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 6px !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        border-radius: 28px !important;
        padding: 4px 6px !important;
        width: fit-content !important;
        min-width: 260px !important;
        max-width: 100% !important;
        margin: 0 auto 18px auto !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        overflow: visible !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 22px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        color: #94A3B8 !important;
        padding: 7px 20px !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0066FF !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(0, 102, 255, 0.4) !important;
        border: none !important;
        outline: none !important;
    }

    /* REMOVE ALL WHITE ARTIFACTS, BASEWEB HIGHLIGHT BARS, BORDERS & SCROLL CHEVRONS */
    [data-baseweb="tab-highlight"],
    [data-baseweb="tab-border"],
    div[data-baseweb="tab-highlight"],
    div[data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        background: transparent !important;
        border: none !important;
        opacity: 0 !important;
    }

    /* Remove any right-side scroll button or chevron icon */
    .stTabs [data-baseweb="tab-list"] > button:not([role="tab"]),
    .stTabs [data-baseweb="tab-list"] > div:not([role="tab"]),
    .stTabs [data-baseweb="tab-list"] svg {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
    }

    /* Tab panel styling */
    [data-baseweb="tab-panel"],
    [data-testid="stTabContent"] {
        padding-top: 0 !important;
        border: none !important;
        background: transparent !important;
    }

    div[data-testid="stTabs"] > div:first-child,
    div[data-testid="stTabs"] div[role="tablist"],
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        border-bottom: none !important;
    }

    /* ── 6. THE WHITE CARD (MATCHING IMG6) ── */
    [data-testid="stForm"] {
        background: #FFFFFF !important;
        border-radius: 14px !important;
        border: none !important;
        padding: 34px 28px 24px 28px !important;
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.45) !important;
        width: 100% !important;
    }

    /* Card Title & Subtitle */
    .card-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.55rem;
        font-weight: 700;
        color: #1E293B;
        text-align: center;
        margin-bottom: 4px;
    }
    .card-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 0.82rem;
        color: #64748B;
        text-align: center;
        margin-bottom: 22px;
    }

    /* Input Labels */
    [data-testid="stForm"] label {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #334155 !important;
        margin-bottom: 4px !important;
    }

    /* Input Boxes */
    [data-testid="stForm"] input {
        background-color: #F8FAFC !important;
        color: #1E293B !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.92rem !important;
        padding: 10px 12px !important;
    }
    [data-testid="stForm"] input:focus {
        border-color: #0066FF !important;
        box-shadow: 0 0 0 2px rgba(0, 102, 255, 0.2) !important;
        background-color: #FFFFFF !important;
    }

    /* Submit Button */
    [data-testid="stForm"] button[kind="primary"] {
        background: #0066FF !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        padding: 12px 0 !important;
        margin-top: 10px !important;
        box-shadow: 0 4px 12px rgba(0, 102, 255, 0.35) !important;
        transition: background 0.15s ease !important;
    }
    [data-testid="stForm"] button[kind="primary"]:hover {
        background: #0052CC !important;
        box-shadow: 0 6px 16px rgba(0, 102, 255, 0.45) !important;
    }

    /* Default creds footer note (dev) */
    .default-creds-note {
        font-family: 'Inter', sans-serif;
        font-size: 0.78rem;
        color: #64748B;
        text-align: center;
        margin-top: 18px;
        padding-top: 14px;
        border-top: 1px solid #E2E8F0;
        line-height: 1.5;
    }
    .default-creds-note strong {
        color: #334155;
    }

    /* Bottom footer */
    .made-by-footer {
        text-align: center;
        padding-top: 20px;
        padding-bottom: 8px;
        opacity: 0.55;
    }
    .made-by-footer span {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        color: #94A3B8;
    }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

    # ── Brand Header ──
    st.markdown("""
    <div class="brand-box">
        <div class="brand-trophy">🏆</div>
        <div class="brand-name">QUIZARENA</div>
        <div class="brand-tagline">SCAN • BUZZ • ANSWER • WIN</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs: Login and Sign Up ──
    tab_login, tab_signup = st.tabs(["🔐 Login", "📝 Sign Up"])

    # ════════════════════════════════════════
    # TAB 1: ADMIN LOGIN (MATCHING IMG6 EXACTLY)
    # ════════════════════════════════════════
    with tab_login:
        with st.form("admin_login_form", clear_on_submit=False):
            st.markdown("""
            <div class="card-title">Admin Login</div>
            <div class="card-subtitle">Please enter your credentials to continue</div>
            """, unsafe_allow_html=True)

            login_user = st.text_input(
                "👤 Username",
                placeholder="Username",
                key="login_user_field"
            )
            login_pass = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Password",
                key="login_pass_field"
            )

            login_btn = st.form_submit_button(
                "Login",
                use_container_width=True,
                type="primary"
            )

            if login_btn:
                if not login_user or not login_pass:
                    st.error("Please enter both username and password.")
                else:
                    success = False
                    # 1. Direct DB authentication
                    try:
                        from backend.auth import authenticate_admin
                        if authenticate_admin(login_user.strip(), login_pass):
                            success = True
                    except Exception:
                        pass
                    
                    # 2. HTTP API fallback
                    if not success:
                        try:
                            clean_url = api_base_url.strip().rstrip("/")
                            if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
                                clean_url = "https://" + clean_url
                            res = requests.post(
                                f"{clean_url}/api/admin/login",
                                json={"email": login_user.strip(), "password": login_pass},
                                timeout=5
                            )
                            if res.status_code == 200 and res.json().get("success"):
                                success = True
                        except Exception:
                            pass

                    if success:
                        st.session_state["authenticated"] = True
                        st.session_state["admin_user"] = login_user.strip()
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password.")

    # ════════════════════════════════════════
    # TAB 2: ADMIN SIGN UP
    # ════════════════════════════════════════
    with tab_signup:
        with st.form("admin_signup_form", clear_on_submit=False):
            st.markdown("""
            <div class="card-title">Admin Sign Up</div>
            <div class="card-subtitle">Create an admin account to manage quizzes</div>
            """, unsafe_allow_html=True)

            signup_email = st.text_input(
                "📧 Email Address",
                placeholder="name@example.com",
                key="signup_email_field"
            )
            signup_pass = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Min 6 characters",
                key="signup_pass_field"
            )
            signup_confirm = st.text_input(
                "🔒 Confirm Password",
                type="password",
                placeholder="Re-enter password",
                key="signup_confirm_field"
            )
            signup_invite = st.text_input(
                "🔑 Invite Code",
                type="password",
                placeholder="Enter secret invite code",
                key="signup_invite_field"
            )

            signup_btn = st.form_submit_button(
                "Create Account",
                use_container_width=True,
                type="primary"
            )

            if signup_btn:
                if not signup_email or not signup_pass or not signup_invite:
                    st.error("Please fill in all fields.")
                elif len(signup_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                elif signup_pass != signup_confirm:
                    st.error("Passwords do not match.")
                else:
                    success = False
                    err_msg = "Sign up failed."
                    # 1. Direct DB registration
                    try:
                        from backend.auth import register_admin
                        ok, msg = register_admin(signup_email.strip(), signup_pass, signup_invite.strip())
                        if ok:
                            success = True
                        else:
                            err_msg = msg
                    except Exception as ex:
                        err_msg = str(ex)

                    # 2. HTTP API fallback if direct failed
                    if not success and "Invalid invite code" not in err_msg and "already exists" not in err_msg:
                        try:
                            clean_url = api_base_url.strip().rstrip("/")
                            if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
                                clean_url = "https://" + clean_url
                            res = requests.post(
                                f"{clean_url}/api/admin/signup",
                                json={
                                    "email": signup_email.strip(),
                                    "password": signup_pass,
                                    "invite_code": signup_invite.strip()
                                },
                                timeout=5
                            )
                            data = res.json()
                            if res.status_code == 200 and data.get("success"):
                                success = True
                            else:
                                err_msg = data.get("message", err_msg)
                        except Exception:
                            pass

                    if success:
                        st.success("✅ Account created successfully! Please switch to Login tab.")
                        st.balloons()
                    else:
                        st.error(f"❌ {err_msg}")

    # ── Page Footer ──
    st.markdown("""
    <div class="made-by-footer">
        <span>Made By <strong style="color:#3B82F6;">KARTIKEY GUPTA</strong></span>
    </div>
    """, unsafe_allow_html=True)




