from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

# -----------------------------
# Users
# -----------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    access_code = Column(String, unique=True, nullable=False)
    can_retake = Column(Boolean, default=True)
    submitted = Column(Boolean, default=False)


class AdminConfig(Base):
    __tablename__ = "admin_config"
    id = Column(Integer, primary_key=True, index=True)
    duration = Column(Integer, nullable=False, default=30)  # test duration in minutes

# models.py
from sqlalchemy import Column, Integer, String, Float
from database import Base

class Leaderboard(Base):
    __tablename__ = "leaderboard"

    id = Column(Integer, primary_key=True)
    student_name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    timestamp = Column(String, nullable=False)

# -----------------------------
# Admins
# -----------------------------
class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # store hashed passwords
    role = Column(String, default="admin")    # "admin" or "super_admin"

    def verify_password(self, raw_password: str, check_func):
        """Verify password using provided hashing function."""
        return check_func(raw_password, self.password)


# -----------------------------
# Questions
# -----------------------------
class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    class_name = Column(String, nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON string
    correct_answer = Column(String, nullable=False)
    subject = Column(String, nullable=True)


# -----------------------------
# Submissions
# -----------------------------
class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    answers = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


# -----------------------------
# Configurations (for test duration or other settings)
# -----------------------------
class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)


# -----------------------------
# Retakes
# -----------------------------
class Retake(Base):
    __tablename__ = "retakes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    access_code = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    allowed = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("access_code", "subject", name="uq_retake"),)
