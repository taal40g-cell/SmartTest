# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_PATH = "smarttest.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    """Create all tables if they don't exist."""
    from models import Admin, User, Question, Submission, Config, Retake
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()
