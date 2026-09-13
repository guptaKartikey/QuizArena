import sys
import os

# Set test database URL before any modules import database.py
os.environ["DATABASE_URL"] = "sqlite:///./test_quizarena.db"

# Add root project directory to sys.path for pytest
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
