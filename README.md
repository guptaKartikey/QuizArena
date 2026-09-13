# 🏆 QuizArena — Real-Time QR Multiplayer Quiz Platform

> **Tagline**: SCAN • BUZZ • ANSWER • WIN

QuizArena is a production-style, real-time multiplayer quiz platform built in Python. An Admin can upload question papers (PDF, TXT, CSV, XLSX), review/edit parsed questions, set scoring/gameplay rules, generate a QR code, and host real-time quiz rooms. Participants join instantly from their phones or browsers by scanning the QR code — **no app installation required**.

---

## 🌟 Key Features

1. **Admin Control Room & Dashboard**
   - Streamlit Admin Dashboard styled with a dark navy UI matching commercial quiz platforms.
   - Comprehensive metrics, quick action shortcuts, recent quizzes history.
2. **Multi-Format Question Paper Processing**
   - Automatic question extraction from **PDF**, **TXT**, **CSV**, and **XLSX**.
   - **Interactive Editable Table**: Review and edit parsed questions before publishing so no misparsed question is ever published silently.
3. **QR Code & Short Join Code**
   - Automatic generation of QR codes and 5-character join codes (e.g. `X7K29`) pointing to `/join/{join_code}`.
   - Downloadable QR PNG images.
4. **Mobile-First Player Web Interface**
   - Zero-install lightweight web app for iOS, Android, and desktop browsers.
   - Responsive touch-friendly option cards, giant animated red BUZZ button, timer pills, and instant feedback.
5. **Real-Time Game Engine & WebSockets**
   - Server-authoritative state machine: `WAITING`, `STARTING`, `QUESTION_ACTIVE`, `BUZZER_ACTIVE`, `ANSWERING`, `QUESTION_RESULT`, `LEADERBOARD`, `PAUSED`, `FINISHED`.
   - Synchronized server-authoritative countdown timers.
6. **Multiple Quiz Modes**
   - **Normal Mode**: All players answer simultaneously within the timer.
   - **First-to-Buzz (Buzzer Mode)**: Nanosecond-precise concurrency lock (`asyncio.Lock()`) resolves microsecond races between simultaneous buzzes. Winner locks out other players and answers first!
   - **Speed Quiz**: Latency-based speed bonus rewards quick responses.
   - **Team Quiz**: Individual and team scoreboard aggregation.
   - **Survival Mode**: Elimination mode where incorrect answers eliminate players until 1 remains.
7. **Scoring & Rules Engine**
   - Custom correct points, wrong points (negative marking toggle), speed bonus formula, auto next question toggle.
8. **Interactive Analytics & Export**
   - Plotly visual charts: Score Distribution, Accuracy Trend per question, Response Time analysis, Top Performers.
   - Download results in **CSV**, **Excel (.xlsx)**, and **JSON** formats.
9. **Demo Mode**
   - Populate rooms with 15 simulated bot participants to test multiplayer flow without 20 physical phones.
10. **Reconnection & Security**
    - Browser `localStorage` session preservation.
    - Server-side scoring and secret JWT key authentication.

---

## 🏗️ Project Architecture

```text
QuizArena/
├── admin/                     # Streamlit Admin UI
│   ├── app.py                 # Main entrance & sidebar router
│   ├── auth_ui.py             # Secure login view
│   ├── dashboard.py           # Metrics cards & recent quizzes
│   ├── quiz_creator.py        # 4-step wizard with editable grid
│   ├── question_manager.py    # Question Bank manager
│   ├── active_quiz.py         # Live control room & QR generator
│   ├── analytics.py           # Plotly analytics dashboard
│   ├── results_ui.py          # Results table & exporter
│   └── settings_ui.py         # System configuration
│
├── backend/                   # FastAPI Server & Real-Time Engine
│   ├── main.py                # App init, static mounts & WS endpoints
│   ├── websocket_manager.py   # Connection manager & broadcasting
│   ├── game_engine.py         # Server-authoritative Quiz state machine
│   ├── scoring.py             # Scoring & speed bonus engine
│   ├── buzzer.py              # Microsecond concurrency buzzer manager
│   ├── auth.py                # Admin password hashing & verification
│   └── api_routes.py          # REST APIs for join, parse, control, export
│
├── player/                    # Mobile Web Player Interface
│   ├── templates/player.html  # Responsive single-page app HTML
│   └── static/                # CSS (style.css) & WebSocket JS (app.js)
│
├── database/                  # Data Storage Layer
│   ├── database.py            # SQLAlchemy engine (SQLite / PostgreSQL)
│   ├── models.py              # Admin, Quiz, Question, Participant, Answer, BuzzEvent
│   └── repositories.py        # CRUD repositories
│
├── pdf_processor/             # File Parsing Engine
│   ├── parser.py              # PyMuPDF & pdfplumber text extractors
│   └── question_extractor.py  # Structured regex Q&A extractor
│
├── qr/                        # QR Code Generator
│   └── generator.py           # QR PNG generator & Base64 encoder
│
├── services/                  # Business Logic Layer
│   ├── quiz_service.py        # Quiz creation & query helper
│   ├── participant_service.py # Player joining & demo generator
│   └── result_service.py     # Analytics & CSV/Excel/JSON exporters
│
├── sample_data/               # Pre-loaded Data
│   ├── sample_quiz.json       # 20+ questions across 4 categories
│   ├── create_sample_pdf.py   # PDF generator script
│   └── sample_questions.pdf   # Pre-generated PDF for immediate testing
│
├── tests/                     # Automated Test Suite
│   ├── test_pdf_parser.py     # PDF parser tests
│   ├── test_scoring.py        # Scoring & negative marking tests
│   ├── test_buzzer.py         # 10 simultaneous buzzers race test
│   ├── test_game_engine.py    # State machine transition tests
│   └── test_api.py            # REST & WebSocket endpoint tests
│
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── run.py                     # Single-command launcher
└── README.md                  # Complete documentation
```

---

## ⚡ Quick Start (Running Locally)

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/your-username/QuizArena.git
cd QuizArena

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

Default credentials:
- **Username**: `admin`
- **Password**: `change_me`

### 3. Launch QuizArena

Run the unified single-command launcher:

```bash
python run.py
```

This will automatically launch:
- **FastAPI Backend Server**: `http://localhost:8000`
- **Streamlit Admin Dashboard**: `http://localhost:8501`

---

## 🎮 How to Play & Host a Quiz

1. **Log in as Admin**: Open `http://localhost:8501` and enter `admin` / `change_me`.
2. **Create Quiz**:
   - Go to **Create Quiz**.
   - Step 1: Fill quiz details (Name, Max Participants, Timer, Quiz Mode).
   - Step 2: Upload `sample_data/sample_questions.pdf` or any PDF/TXT/CSV/XLSX file.
   - Step 3: Review and edit parsed questions in the interactive grid.
   - Step 4: Configure negative marking and speed bonus settings, then click **Publish Quiz Room**.
3. **Share QR Code**: Go to **Active Quiz** to see the generated QR code and Join Code.
4. **Join Quiz**: Scan the QR code with your phone or open `http://localhost:8000/join/X7K29` in your browser. Enter your name and click **Join Quiz**.
5. **Test Demo Mode**: Click **Add 15 Demo Players** in the Admin Active Quiz panel to add 15 simulated participants automatically.
6. **Start & Control Quiz**: Click `[START QUIZ]` from the Admin Dashboard to broadcast questions in real time!
7. **View Results & Export**: At the end of the quiz, view Plotly analytics and export results as **CSV**, **Excel**, or **JSON**.

---

## 🧪 Running Automated Tests

Run the pytest suite to verify parser logic, scoring formulas, state machine transitions, and buzzer concurrency:

```bash
python -m pytest tests/
```

---

## 🚀 Production & Deployment

For production deployments:
- **Database**: Set `DATABASE_URL=postgresql://user:pass@localhost:5432/quizarena` in `.env`.
- **State Store**: Enable Redis by setting `USE_REDIS=true` and `REDIS_URL=redis://localhost:6379/0`.
- **Environment Variables**: Change `SECRET_KEY` and `ADMIN_PASSWORD` in `.env`.
