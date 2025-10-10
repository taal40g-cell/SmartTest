import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# =====================================
# Database URL Configuration
# =====================================

# Try to get DATABASE_URL from environment (for Render or cloud)
DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ Fallback to SQLite if not found (for local development)
if not DATABASE_URL:
    print("⚠️ DATABASE_URL not found in environment variables. Using local SQLite database instead.")
    DATABASE_URL = "sqlite:///smarttest.db"

# =====================================
# Engine Setup
# =====================================

# For SQLite, need a special argument to allow multithreading in Streamlit
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)

# =====================================
# Session and Base
# =====================================

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =====================================
# Helper Functions
# =====================================

def get_session():
    """Create a new SQLAlchemy session."""
    return SessionLocal()


def test_db_connection() -> bool:
    """
    Simple test to check database connectivity.
    Returns True if connection is successful, otherwise False.
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
