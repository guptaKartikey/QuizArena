import argparse
import sys
from database.database import SessionLocal, init_db, engine
from database.models import Admin
from backend.auth import hash_password

def setup_admin():
    parser = argparse.ArgumentParser(description="Create a new Admin user for QuizArena.")
    parser.add_argument("email", type=str, help="Admin email address")
    parser.add_argument("password", type=str, help="Admin password")
    
    args = parser.parse_args()

    # Ensure the admins table exists (without dropping existing data)
    Admin.__table__.create(engine, checkfirst=True)

    db = SessionLocal()
    try:
        existing = db.query(Admin).filter(Admin.email == args.email).first()
        if existing:
            print(f"Error: Admin with email '{args.email}' already exists.")
            sys.exit(1)
        
        hashed = hash_password(args.password)
        new_admin = Admin(email=args.email, password_hash=hashed)
        db.add(new_admin)
        db.commit()
        print(f"Success: Admin '{args.email}' has been successfully created.")
    except Exception as e:
        print(f"Failed to create admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_admin()
