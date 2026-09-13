import os
import hashlib
import hmac
from dotenv import load_dotenv

load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change_me")
SECRET_KEY = os.getenv("SECRET_KEY", "quizarena_super_secret_jwt_key_2026")
ADMIN_INVITE_CODE = os.getenv("ADMIN_INVITE_CODE", "QUIZARENA2026")

def hash_password(password: str) -> str:
    salt = SECRET_KEY.encode('utf-8')
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(hash_password(plain_password), hashed_password)

def authenticate_admin(email: str, password: str) -> bool:
    # Support default admin dev credentials (admin / change_me)
    if (email.strip() == ADMIN_USERNAME or email.strip() == "admin@quizarena.com") and password == ADMIN_PASSWORD:
        return True

    from database.database import SessionLocal
    from database.models import Admin
    
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.email == email.strip()).first()
        if not admin:
            return False
        return verify_password(password, admin.password_hash)
    finally:
        db.close()

