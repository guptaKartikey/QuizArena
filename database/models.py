import datetime
import json
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from database.database import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(String(50), primary_key=True, index=True) # e.g. QA-2026-001
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    join_code = Column(String(10), unique=True, index=True, nullable=False) # e.g. X7K29
    max_participants = Column(Integer, default=50)
    status = Column(String(30), default="WAITING") # WAITING, STARTING, QUESTION_ACTIVE, BUZZER_ACTIVE, ANSWERING, QUESTION_RESULT, LEADERBOARD, ROUND_END, ELIMINATION, NEXT_ROUND, PAUSED, FINISHED
    
    # Quiz Mode: CLASSIC, FIRST_TO_BUZZ, SPEED_QUIZ, TEAM_BATTLE, SURVIVAL, KNOCKOUT, CHAMPIONSHIP
    mode = Column(String(30), default="CLASSIC")
    
    # Mode-Specific Detailed Configuration (JSON string/Text)
    mode_settings_json = Column(Text, default="{}")

    # Rules & Modifiers
    question_timer = Column(Integer, default=30)
    correct_points = Column(Float, default=10.0)
    wrong_points = Column(Float, default=-5.0)
    no_answer_points = Column(Float, default=0.0)
    enable_negative_marking = Column(Boolean, default=True)
    enable_speed_bonus = Column(Boolean, default=True)
    enable_buzzer = Column(Boolean, default=False)
    enable_random_questions = Column(Boolean, default=False)
    enable_random_options = Column(Boolean, default=False)
    allow_late_joining = Column(Boolean, default=False)
    show_answer_after = Column(Boolean, default=True)
    show_leaderboard_after = Column(Boolean, default=True)
    automatic_next_question = Column(Boolean, default=False)
    enable_powerups = Column(Boolean, default=False)
    enable_team_buzzer = Column(Boolean, default=False)
    show_explanation = Column(Boolean, default=True)
    allow_answer_change = Column(Boolean, default=True)

    # Round / Tournament tracking
    current_round = Column(Integer, default=1)
    total_rounds = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    participants = relationship("Participant", back_populates="quiz", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="quiz", cascade="all, delete-orphan")

    @property
    def mode_settings(self):
        try:
            return json.loads(self.mode_settings_json or "{}")
        except Exception:
            return {}

    @mode_settings.setter
    def mode_settings(self, val):
        self.mode_settings_json = json.dumps(val)

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(String(50), ForeignKey("quizzes.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False) # JSON encoded array e.g. ["A. Earth", "B. Mars", ...]
    correct_answer = Column(String(10), nullable=False) # A, B, C, D
    explanation = Column(Text, nullable=True)
    order_number = Column(Integer, default=1)
    round_number = Column(Integer, default=1) # For multi-round/knockout/championship

    quiz = relationship("Quiz", back_populates="questions")

    @property
    def options(self):
        try:
            return json.loads(self.options_json)
        except Exception:
            return []

    @options.setter
    def options(self, val):
        self.options_json = json.dumps(val)

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(String(50), ForeignKey("quizzes.id"), nullable=False)
    name = Column(String(50), nullable=False)
    captain_id = Column(String(50), nullable=True)
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    quiz = relationship("Quiz", back_populates="teams")
    members = relationship("Participant", back_populates="team")

class Participant(Base):
    __tablename__ = "participants"

    id = Column(String(50), primary_key=True, index=True) # Unique UUID/string
    quiz_id = Column(String(50), ForeignKey("quizzes.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    name = Column(String(50), nullable=False)
    session_token = Column(String(100), unique=True, index=True, nullable=False)
    connected = Column(Boolean, default=True)
    
    # Mode State
    is_alive = Column(Boolean, default=True) # For survival mode
    lives = Column(Integer, default=3) # Lives remaining in Survival mode
    is_eliminated = Column(Boolean, default=False) # For Knockout / Survival
    eliminated_in_round = Column(Integer, nullable=True)
    is_team_captain = Column(Boolean, default=False)

    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

    quiz = relationship("Quiz", back_populates="participants")
    team = relationship("Team", back_populates="members")
    answers = relationship("Answer", back_populates="participant", cascade="all, delete-orphan")
    buzz_events = relationship("BuzzEvent", back_populates="participant", cascade="all, delete-orphan")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(String(50), ForeignKey("quizzes.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    participant_id = Column(String(50), ForeignKey("participants.id"), nullable=False)
    selected_answer = Column(String(10), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    response_time = Column(Float, default=0.0) # Seconds taken
    points = Column(Float, default=0.0)
    speed_bonus = Column(Float, default=0.0)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)

    participant = relationship("Participant", back_populates="answers")

class BuzzEvent(Base):
    __tablename__ = "buzz_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(String(50), ForeignKey("quizzes.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    participant_id = Column(String(50), ForeignKey("participants.id"), nullable=False)
    timestamp_ns = Column(Integer, nullable=False) # Nanosecond server timestamp
    position = Column(Integer, default=1) # 1 = first buzzer, 2 = second, etc.
    result = Column(String(20), default="PENDING") # WON, LOST, PENALTY, PASSED
    penalty_applied = Column(Float, default=0.0)
    is_second_chance = Column(Boolean, default=False)

    participant = relationship("Participant", back_populates="buzz_events")
