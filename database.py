import os
import time
import traceback
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import urlparse

# ==============================
# Load environment variables
# ==============================
load_dotenv()

Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL not found in environment variables.")

# ==============================
# Engine Setup
# ==============================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,        # Increased for concurrency
    max_overflow=40,
    echo=False,
    future=True
)

parsed_url = urlparse(DATABASE_URL)
db_name = parsed_url.path.lstrip("/")
db_user = parsed_url.username
print(f"✅ Connected to PostgreSQL | DB: {db_name} | User: {db_user}")

DB_TYPE = "postgres"

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_session():
    return SessionLocal()

def init_db():
    Base.metadata.create_all(bind=engine)

def test_db_connection():
    """Test connection to the database."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT NOW()"))
            server_time = result.scalar()
            print(f"✅ Database connection successful! Server time: {server_time}")
            return True
    except Exception as e:
        print("❌ Database connection failed!")
        print(f"Error: {e}")
        traceback.print_exc()
        return False

# ==============================
# Optimized Fetch Functions
# ==============================
import streamlit as st

@st.cache_data(ttl=60)
def fetch_students():
    """Return all students (cached for 60 sec)."""
    start = time.time()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, name, class_name, access_code, unique_id FROM students")
        )
        rows = result.mappings().all()
    print(f"⏱ fetch_students took {time.time() - start:.3f}s | {len(rows)} rows")
    return [dict(row) for row in rows]

def get_student_by_code(code: str):
    """Fetch a single student by access code (no caching needed)."""
    start = time.time()
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, name, class_name, access_code, unique_id
                FROM students
                WHERE access_code = :code
            """),
            {"code": code}
        )
        row = result.mappings().first()
    print(f"⏱ get_student_by_code took {time.time() - start:.3f}s")
    return dict(row) if row else None

@st.cache_data(ttl=60)
def load_questions(class_name: str, subject: str, limit: int = 30):
    """Load questions for a given class & subject, cached for 60s."""
    start = time.time()
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, question_text, options, correct_answer
                FROM questions
                WHERE class_name = :cls AND subject = :sub
                ORDER BY RANDOM()
                LIMIT :limit
            """),
            {"cls": class_name, "sub": subject, "limit": limit}
        )
        rows = result.mappings().all()
    print(f"⏱ load_questions took {time.time() - start:.3f}s | {len(rows)} questions")
    return [dict(row) for row in rows]


