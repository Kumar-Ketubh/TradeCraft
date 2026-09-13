import os
import sys

# Ensure we can import from the app module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import get_db, create_db_engine, Base
from app.models.user import User
from app.models.workspace import Workspace
from app.core.security import get_password_hash
from sqlalchemy.orm import sessionmaker

def seed_admin():
    engine = create_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    admin_email = "admin@tradecraft.com"
    admin_password = "admin"
    
    try:
        user = db.query(User).filter(User.email == admin_email).first()
        if not user:
            print("Creating Admin User...")
            user = User(
                name="System Admin",
                email=admin_email,
                password_hash=get_password_hash(admin_password)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            print("Creating Admin Workspace...")
            ws = Workspace(
                name="Admin Workspace",
                user_id=user.id
            )
            db.add(ws)
            db.commit()
            
            print(f"✅ Success! You can now log in with:")
            print(f"   Email: {admin_email}")
            print(f"   Password: {admin_password}")
        else:
            print("✅ Admin user already exists!")
            print(f"   Email: {admin_email}")
            print(f"   Password: {admin_password}")
            
    except Exception as e:
        print(f"❌ Error seeding admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
