# init_db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Admin
from werkzeug.security import generate_password_hash

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL environment variable is not set.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Create all tables
Base.metadata.create_all(engine)
print("✅ Tables created successfully!")

# Ensure a super admin exists
db = SessionLocal()
try:
    if not db.query(Admin).filter_by(username="super_admin").first():
        admin = Admin(
            username="super_admin",
            password_hash=generate_password_hash("admin123")  # choose a secure password
        )
        db.add(admin)
        db.commit()
        print("✅ Super admin created (username: super_admin, password: admin123)")
finally:
    db.close()
