import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./quizarena.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Auto-migration for SQLite schema updates
    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            columns_to_add = [
                ("quizzes", "mode", "VARCHAR(30) DEFAULT 'CLASSIC'"),
                ("quizzes", "mode_settings_json", "TEXT DEFAULT '{}'"),
                ("quizzes", "enable_powerups", "BOOLEAN DEFAULT 0"),
                ("quizzes", "enable_team_buzzer", "BOOLEAN DEFAULT 0"),
                ("quizzes", "show_explanation", "BOOLEAN DEFAULT 1"),
                ("quizzes", "current_round", "INTEGER DEFAULT 1"),
                ("quizzes", "total_rounds", "INTEGER DEFAULT 1"),
                ("questions", "round_number", "INTEGER DEFAULT 1"),
                ("participants", "lives", "INTEGER DEFAULT 3"),
                ("participants", "is_eliminated", "BOOLEAN DEFAULT 0"),
                ("participants", "eliminated_in_round", "INTEGER NULL"),
                ("participants", "is_team_captain", "BOOLEAN DEFAULT 0"),
                ("teams", "captain_id", "VARCHAR(50) NULL"),
                ("teams", "score", "FLOAT DEFAULT 0.0"),
                ("buzz_events", "penalty_applied", "FLOAT DEFAULT 0.0"),
                ("buzz_events", "is_second_chance", "BOOLEAN DEFAULT 0")
            ]
            for table, col, col_type in columns_to_add:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                    conn.commit()
                except Exception:
                    # Column already exists
                    pass
