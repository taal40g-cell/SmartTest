# helpers.py (Cleaned — duplicates removed, minimal safe consolidation)

# ==============================
# Standard Library Imports
# ==============================
import json
import random
import string
import hashlib
from datetime import datetime
import traceback


# ==============================
# Third-Party Imports
# ==============================
import streamlit as st
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from werkzeug.security import generate_password_hash, check_password_hash



# ==============================
# Database Imports
# ==============================
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    UniqueConstraint
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# -----------------------------
# Database Setup
# -----------------------------
DB_PATH = "smarttest.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_session() -> Session:
    return SessionLocal()


# -----------------------------
# Models
# -----------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    access_code = Column(String, unique=True, nullable=False)
    can_retake = Column(Boolean, default=True)
    submitted = Column(Boolean, default=False)


class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # hashed
    role = Column(String, default="admin")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    class_name = Column(String, nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON string
    correct_answer = Column(String, nullable=False)
    subject = Column(String, nullable=True)


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    answers = Column(Text)  # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow)


class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)


class Retake(Base):
    __tablename__ = "retakes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    access_code = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    allowed = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("access_code", "subject", name="uq_retake"),)


# -----------------------------
# DB Initialization
# -----------------------------
def init_db():
    Base.metadata.create_all(bind=engine)


# ===============================
# Password Helpers (Unified + compatible)
# ===============================
# We use passlib bcrypt as the canonical hasher, but allow verification
# against Werkzeug hashes and legacy SHA256 hex digests for backward compatibility.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt (passlib)."""
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against a stored hash.
    Tries, in order:
      1) passlib (bcrypt)
      2) werkzeug's check_password_hash (if format matches)
      3) legacy SHA256 hex comparison (if stored as 64-char hex)
    """
    if not hashed_password:
        return False

    # 1) Try passlib/bcrypt
    try:
        return pwd_context.verify(password, hashed_password)
    except UnknownHashError:
        # unknown scheme to passlib - fall through to other checks
        pass
    except Exception:
        # any other passlib error -> fallthrough
        pass

    # 2) Try Werkzeug's check_password_hash (handles pbkdf2, etc.)
    try:
        if check_password_hash(hashed_password, password):
            return True
    except Exception:
        pass

    # 3) Legacy raw SHA256 hex (common earlier in your file)
    try:
        if hashlib.sha256(password.encode()).hexdigest() == hashed_password:
            return True
    except Exception:
        pass

    return False


# ===============================
# Admin CRUD (single copy)
# ===============================
def set_admin(username: str, password: str, role: str = "admin"):
    """Create or update an admin (stores bcrypt hash)."""
    db = get_session()
    try:
        username = username.strip()
        hashed_pw = hash_password(password)
        admin = db.query(Admin).filter(Admin.username.ilike(username)).first()
        if admin:
            admin.password = hashed_pw
            admin.role = role
        else:
            admin = Admin(username=username, password=hashed_pw, role=role)
            db.add(admin)
        db.commit()
        return True
    finally:
        db.close()


def add_admin(username: str, password: str, role: str = "admin"):
    """Add new admin (bcrypt). Returns True if added, False if duplicate."""
    db = get_session()
    try:
        if db.query(Admin).filter(Admin.username.ilike(username)).first():
            return False
        hashed_pw = hash_password(password)
        db.add(Admin(username=username.strip(), password=hashed_pw, role=role))
        db.commit()
        return True
    finally:
        db.close()


def get_admin(username: str):
    db = get_session()
    try:
        return db.query(Admin).filter(Admin.username.ilike(username)).first()
    finally:
        db.close()


def get_admins(as_dict=False):
    db = get_session()
    try:
        result = db.query(Admin).all()
        if as_dict:
            return {a.username: a.role for a in result}
        return result
    finally:
        db.close()

def verify_admin(username: str, password: str):
    """
    Verify credentials, returning the Admin object on success or None on failure.
    Uses verify_password() which supports multiple legacy hash formats.
    """
    admin = get_admin(username)
    if admin and verify_password(password, admin.password):
        return admin
    return None



def update_admin_password(username: str, new_hashed_password: str) -> bool:
    """
    Update admin password in DB. (Expecting caller to provide hashed password,
    which matches existing usage in your UI where you pass hash_password(new_pw).)
    """
    db = get_session()
    try:
        admin = db.query(Admin).filter(Admin.username.ilike(username)).first()
        if not admin:
            return False
        admin.password = new_hashed_password
        db.commit()
        return True
    finally:
        db.close()


# -----------------------------
# Ensure Super Admin Exists (single copy)
# -----------------------------
def ensure_super_admin_exists():
    """
    Ensure default super_admin exists.
    If present but password is in legacy format and doesn't verify, re-set to bcrypt('1234').
    """
    db = get_session()
    try:
        admin = db.query(Admin).filter_by(username="super_admin").first()
        if not admin:
            default_pass = hash_password("1234")
            db.add(Admin(username="super_admin", password=default_pass, role="super_admin"))
            db.commit()
            print("✅ Created default super_admin (username=super_admin, password=1234)")
        else:
            # ensure role
            if admin.role != "super_admin":
                admin.role = "super_admin"
            # if current password does NOT verify for the known default, reset it
            # (this is safe — it ensures a working default super_admin on legacy DBs)
            if not verify_password("1234", admin.password):
                admin.password = hash_password("1234")
                db.commit()
                print("🔄 Reset super_admin password to bcrypt (1234)")
    finally:
        db.close()

# ensure_super_admin_exists is intentionally called here so the admin is available on module load
ensure_super_admin_exists()


# -----------------------------
# Admin Login UI (Streamlit) — preserved logic
# -----------------------------
def require_admin_login():
    # ✅ Already logged in?
    if st.session_state.get("admin_logged_in", False):
        return True

    st.subheader("🔑 Admin Login")
    username = st.text_input("Username", key="admin_username_input")
    password = st.text_input("Password", type="password", key="admin_password_input")

    col1, col2 = st.columns([3, 1])

    with col1:
        if st.button("Login"):
            admin = get_admin(username.strip())
            if admin and verify_password(password, admin.password):
                # Save session state
                st.session_state.admin_username = admin.username
                st.session_state.admin_logged_in = True
                st.session_state.admin_role = admin.role
                st.success(f"✅ Logged in as {admin.username} ({admin.role})")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

    # Only allow password reset for super_admin
    with col2:
        if st.button("Reset Password (Super Admin Only)"):
            st.session_state.show_reset_pw = True  # toggle UI

    if st.session_state.get("show_reset_pw", False):
        st.info("🔐 Super Admin Password Reset")
        super_admin = st.text_input("Super Admin Username", key="super_admin_user")
        super_pass = st.text_input("Super Admin Password", type="password", key="super_admin_pass")

        if st.button("Authenticate Super Admin"):
            sa = get_admin(super_admin.strip())
            if sa and sa.role == "super_admin" and verify_password(super_pass, sa.password):
                st.session_state.super_admin_authenticated = True
                st.success("✅ Super Admin authenticated! You can now reset any admin password.")
            else:
                st.error("❌ Invalid super admin credentials")

        if st.session_state.get("super_admin_authenticated", False):
            reset_user = st.text_input("Username to Reset", key="reset_target_user")
            new_password = st.text_input("New Password", type="password", key="reset_new_pw")
            if st.button("Confirm Reset"):
                target = get_admin(reset_user.strip())
                if target:
                    # keep your existing usage: update_admin_password expects hashed input
                    update_admin_password(reset_user.strip(), hash_password(new_password))
                    st.success(f"✅ Password for {reset_user} reset successfully!")
                    st.session_state.show_reset_pw = False
                    st.session_state.super_admin_authenticated = False
                else:
                    st.error("❌ User not found")

    return False


# -----------------------------
# Student Management (unchanged logic, cleaned)
# -----------------------------
def generate_access_code(length=6):
    db = get_session()
    try:
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            exists = db.query(User).filter_by(access_code=code).first()
            if not exists:
                return code
    finally:
        db.close()

def add_student_db(name, class_name):
    db = get_session()
    try:
        code = generate_access_code()
        student = User(name=name, class_name=class_name, access_code=code)
        db.add(student)
        db.commit()
        db.refresh(student)  # ✅ refresh to get auto-generated ID
        return student.id, student.access_code  # ✅ return both
    finally:
        db.close()

def bulk_add_students_db(student_list):
    """
    Add multiple students and return a list of dicts:
    [{"id": 1, "name": "John", "class": "JHS1", "access_code": "ABC123"}, ...]
    """
    db = get_session()
    results = []
    try:
        for name, class_name in student_list:
            code = generate_access_code()
            new_student = User(name=name, class_name=class_name, access_code=code)
            db.add(new_student)
            db.commit()
            db.refresh(new_student)  # ✅ Get generated ID
            results.append({
                "id": new_student.id,
                "name": name,
                "class": class_name,
                "access_code": code,
            })
        return results
    finally:
        db.close()


def get_student_by_access_code_db(access_code):
    db = get_session()
    try:
        return db.query(User).filter(User.access_code == access_code).first()
    finally:
        db.close()


def update_student_submission_db(access_code):
    db = get_session()
    try:
        student = db.query(User).filter(User.access_code == access_code).first()
        if student:
            student.submitted = True
            db.commit()
    finally:
        db.close()


def reset_student_retake_db(access_code):
    db = get_session()
    try:
        student = db.query(User).filter(User.access_code == access_code).first()
        if student:
            student.can_retake = True
            student.submitted = False
            db.commit()
    finally:
        db.close()


def get_users():
    db = get_session()
    try:
        users = db.query(User).all()
        return {
            u.access_code: {
                "name": u.name,
                "class": u.class_name,
                "can_retake": u.can_retake,
                "submitted": u.submitted
            } for u in users
        }
    finally:
        db.close()


# -----------------------------
# Question Management (unchanged logic)
# -----------------------------
def add_question_db(class_name, text, options, correct, subject=None):
    db = get_session()
    try:
        db.add(Question(
            class_name=class_name,
            question_text=text,
            options=json.dumps(options),
            correct_answer=correct,
            subject=subject
        ))
        db.commit()
    finally:
        db.close()


def get_questions_db(class_name, subject=None):
    db = get_session()
    try:
        q = db.query(Question).filter(Question.class_name == class_name)
        if subject:
            q = q.filter(Question.subject == subject)
        return q.all()
    finally:
        db.close()


# ✅ Use your existing get_session() and Question from helpers.py
# (do NOT import from models or db_helpers)

def validate_question(q):
    """Check if a question dict is valid."""
    if not isinstance(q, dict):
        return False
    if not all(k in q for k in ("question", "options", "answer")):
        return False
    if not isinstance(q["options"], list) or len(q["options"]) < 2:
        return False
    if not isinstance(q["answer"], str):
        return False
    if q["answer"].strip() not in [opt.strip() for opt in q["options"]]:
        return False
    return True


def handle_uploaded_questions(file, class_name, subject_name):
    """Upload JSON questions to DB (clear old ones first, then insert new)."""
    try:
        # --- Step 1: Parse uploaded file ---
        try:
            content = file.read().decode("utf-8").strip()
            questions = json.loads(content)
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON format: {e}")
            st.info("Make sure your file uses double quotes and is valid JSON.")
            return {"success": False, "error": str(e)}

        # Support both {"questions": [...]} and [...] formats
        if isinstance(questions, dict) and "questions" in questions:
            questions = questions["questions"]

        if not isinstance(questions, list):
            st.error("❌ Uploaded file must be a JSON list or contain a 'questions' key with a list.")
            return {"success": False, "error": "Invalid JSON structure"}

        # Validate question structure
        valid_questions = [q for q in questions if validate_question(q)]
        if not valid_questions:
            st.error("❌ No valid questions found.")
            return {"success": False, "error": "No valid questions"}

        # --- Step 2: Save to DB ---
        db: Session = get_session()
        try:
            cls = class_name.strip().upper()
            subj = subject_name.strip().upper()

            # Delete old questions for class+subject
            deleted = db.query(Question).filter(
                Question.class_name == cls,
                Question.subject == subj
            ).delete(synchronize_session=False)

            # Insert new questions
            new_records = [
                Question(
                    class_name=cls,
                    subject=subj,
                    question_text=q["question"].strip(),
                    options=json.dumps([opt.strip() for opt in q["options"]]),
                    correct_answer=q["answer"].strip()
                )
                for q in valid_questions
            ]

            db.bulk_save_objects(new_records)  # faster for bulk insert
            db.commit()

            st.success(f"✅ Uploaded {len(new_records)} questions for {cls} - {subj} "
                       f"(replaced {deleted} old ones)")
            return {"success": True, "inserted": len(new_records), "deleted": deleted}

        finally:
            db.close()

    except Exception as e:
        st.error(f"⚠️ Error during upload: {e}")
        st.text(traceback.format_exc())
        return {"success": False, "error": str(e)}


def load_questions_db(class_name: str, subject: str):
    """Load all questions for given class and subject from DB."""
    db: Session = get_session()
    try:
        cls = class_name.strip().upper()
        subj = subject.strip().upper()

        query = db.query(Question).filter(
            Question.class_name == cls,
            Question.subject == subj
        )

        questions = query.all()
        return [
            {
                "id": q.id,
                "question": q.question_text,
                "options": json.loads(q.options),  # convert back to list
                "answer": q.correct_answer,
            }
            for q in questions
        ]
    finally:
        db.close()

def delete_questions_db(class_name=None, subject=None):
    """Delete questions from DB by class and/or subject with consistent normalization."""
    db = get_session()
    try:
        query = db.query(Question)

        # Normalize input to match stored format
        if class_name:
            class_name = class_name.strip().upper()
            query = query.filter(Question.class_name == class_name)

        if subject:
            subject = subject.strip().upper()
            query = query.filter(Question.subject == subject)

        count = query.count()
        if count == 0:
            return 0  # nothing to delete

        query.delete(synchronize_session=False)
        db.commit()
        return count
    finally:
        db.close()

# -----------------------------
# Submissions (unchanged logic)
# -----------------------------
def add_submission_db(student_name: str, class_name: str, subject: str, score: int, answers: dict):
    db = get_session()
    try:
        sub = Submission(
            student_name=student_name,
            class_name=class_name,
            subject=subject,
            score=score,
            answers=json.dumps(answers),
        )
        db.add(sub)
        db.commit()
    finally:
        db.close()


def get_submission_db(student_name: str, class_name: str, subject: str):
    db = get_session()
    try:
        return (
            db.query(Submission)
            .filter_by(student_name=student_name, class_name=class_name, subject=subject)
            .first()
        )
    finally:
        db.close()


def set_submission_db(access_code, subject, score, questions, answers):
    student = get_student_by_access_code_db(access_code)
    if not student:
        raise ValueError("Invalid student access code")

    answers_dict = {
        q.get("id"): answers[i] if i < len(answers) else "No Answer"
        for i, q in enumerate(questions)
    }
    add_submission_db(student.name, student.class_name, subject, score, answers_dict)



def get_all_submissions_db():
    """Return all submissions in the database (no filters)."""
    db = get_session()
    try:
        return db.query(Submission).all()
    finally:
        db.close()


def get_submissions_by_access_code(access_code: str):
    """
    Fetch all submissions for a given access code.
    """
    student = get_student_by_access_code_db(access_code)
    if not student:
        return []  # Return empty list if code not found

    db = get_session()
    try:
        return (
            db.query(Submission)
            .filter_by(student_name=student.name, class_name=student.class_name)
            .all()
        )
    finally:
        db.close()

# -----------------------------
# Retakes (unchanged logic)
# -----------------------------
def set_retake_db(access_code: str, subject: str, allowed: int = 1):
    """Grant or revoke retake for a student (per subject)."""
    db = get_session()
    try:
        retake = db.query(Retake).filter_by(access_code=access_code, subject=subject).first()
        if retake:
            retake.allowed = allowed
        else:
            retake = Retake(access_code=access_code, subject=subject, allowed=allowed)
            db.add(retake)
        db.commit()
    finally:
        db.close()


def get_retake_db(access_code: str, subject: str):
    """Return number of retakes allowed for this student+subject."""
    db = get_session()
    try:
        retake = db.query(Retake).filter_by(access_code=access_code, subject=subject).first()
        return retake.allowed if retake else 0
    finally:
        db.close()


def decrement_retake(access_code: str, subject: str):
    """Decrement retake count after a test is taken (if > 0)."""
    db = get_session()
    try:
        r = db.query(Retake).filter_by(access_code=access_code, subject=subject).first()
        if r and r.allowed > 0:
            r.allowed -= 1
            db.commit()
    finally:
        db.close()


def can_take_test(access_code: str, subject: str):
    """
    Check if a student can take a test for a subject.
    Handles both first attempt and retake logic (consumes a retake if allowed).
    """
    student = get_student_by_access_code_db(access_code)
    if not student:
        return False, "❌ Invalid access code"

    # Check if student has already submitted this subject
    submission = get_submission_db(student.name, student.class_name, subject)
    if submission:
        # Already taken once — check for retakes
        allowed_count = get_retake_db(access_code, subject)
        if allowed_count > 0:
            decrement_retake(access_code, subject)  # consume one retake
            return True, f"✅ Retake allowed ({allowed_count - 1} remaining)"
        else:
            return False, f"❌ You have already taken {subject}. Retake not allowed."

    # First attempt — always allowed
    return True, "✅ Allowed to take test (first attempt)"

# -----------------------------
# Score Calculation (unchanged logic)
# -----------------------------
def calculate_score_db(questions, answers):
    score = 0
    detailed = []
    for i, q in enumerate(questions):
        user_ans = answers[i] if i < len(answers) and answers[i] else "No Answer"
        correct_ans = q["answer"] if "answer" in q else q.get("correct_answer", "N/A")
        correct = user_ans.strip().lower() == correct_ans.strip().lower()
        if correct:
            score += 1
        detailed.append({
            "question": q.get("question", q.get("question_text", "Unknown")),
            "your_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": correct
        })
    return score, detailed


# -----------------------------
# Question Tracker (UI only) (unchanged logic)
# -----------------------------
def show_question_tracker(questions, current_index, answers):
    total = len(questions)
    marked = st.session_state.get("marked_for_review", set())
    show_all = st.session_state.get("show_all_tracker", False)
    st.session_state.current_q = current_index

    st.markdown(
        '<div style="position:sticky; top:0; z-index:999; background:#f0f2f6; '
        'padding:10px; border-bottom:1px solid #ccc;">',
        unsafe_allow_html=True
    )
    st.markdown("### Progress Tracker")
    st.session_state.show_all_tracker = st.checkbox("Show all", value=show_all)

    def render_range(start, end):
        cols = st.columns(10)
        for i in range(start, end):
            if i in marked:
                color = "orange"
            elif i < len(answers) and answers[i]:
                color = "green"
            else:
                color = "red"

            label = f"Q{i+1}"
            if cols[i % 10].button(label, key=f"jump_{i}", use_container_width=True):
                st.session_state.current_q = i
            cols[i % 10].markdown(
                f"<div style='background-color:{color}; color:white; padding:5px; "
                f"text-align:center; border-radius:4px;'>{label}</div>",
                unsafe_allow_html=True
            )

    if show_all or total <= 10:
        render_range(0, total)
    else:
        render_range(0, 10)
        with st.expander(f"Show remaining {total-10} questions"):
            render_range(10, total)

    st.markdown("</div>", unsafe_allow_html=True)


# =====================================================================
# QUESTION UPLOAD HANDLER (DB VERSION) (unchanged logic)
# =====================================================================

# =====================================================================
# Load helpers for test duration (updated to use Config)
# =====================================================================
def get_test_duration(default=30):
    """Fetch test duration from DB. Fallback to default if not set."""
    session = SessionLocal()
    try:
        cfg = session.query(Config).filter_by(key="test_duration").first()
        if cfg and cfg.value:
            return int(cfg.value)
        return default
    finally:
        session.close()


def set_test_duration(minutes):
    """Save or update test duration in DB."""
    session = SessionLocal()
    try:
        cfg = session.query(Config).filter_by(key="test_duration").first()
        if not cfg:
            cfg = Config(key="test_duration", value=str(minutes))
            session.add(cfg)
        else:
            cfg.value = str(minutes)
        session.commit()
        return True
    finally:
        session.close()


def preview_questions_db(class_name=None, subject=None, limit=5):
    """
    Preview questions currently in the DB for a given class & subject.
    Returns a list of dicts with id, question, subject.
    """
    db = get_session()
    try:
        query = db.query(Question)

        if class_name:
            class_name = class_name.strip().upper()
            query = query.filter(Question.class_name == class_name)

        if subject:
            subject = subject.strip().upper()
            query = query.filter(Question.subject == subject)

        results = query.limit(limit).all()

        return [
            {
                "id": q.id,
                "class": q.class_name,
                "subject": q.subject,
                "question": q.question_text
            }
            for q in results
        ]
    finally:
        db.close()


def count_questions_db(class_name=None, subject=None):
    """
    Return the total number of questions in the DB for the given class and subject.
    """
    db = get_session()
    try:
        query = db.query(Question)

        if class_name:
            class_name = class_name.strip().upper()
            query = query.filter(Question.class_name == class_name)

        if subject:
            subject = subject.strip().upper()
            query = query.filter(Question.subject == subject)

        return query.count()
    finally:
        db.close()


def clear_students_db():
    db = get_session()
    try:
        db.query(User).delete()
        db.commit()
    finally:
        db.close()

def clear_questions_db():
    db = get_session()
    try:
        db.query(Question).delete()
        db.commit()
    finally:
        db.close()

    # db_helpers.py (add these)


def update_student_db(student_id: int, new_name: str, new_class: str) -> bool:
    """
    Update a student's name and class by their DB id.
    Returns True if updated, False if student not found.
    """
    db = get_session()
    try:
        student = db.query(User).filter(User.id == student_id).first()
        if not student:
            return False
        student.name = new_name.strip()
        student.class_name = new_class.strip()
        db.commit()
        return True
    finally:
        db.close()


def delete_student_db(student_id: int, cascade: bool = True) -> bool:
    """
    Delete a student by DB id.
    If cascade=True, attempt to delete related Submissions and Retake rows (if those models exist).
    Returns True if deleted, False if student not found.
    """
    db = get_session()
    try:
        student = db.query(User).filter(User.id == student_id).first()
        if not student:
            return False

        # Save values for cascade deletion
        access_code = getattr(student, "access_code", None)
        student_name = getattr(student, "name", None)

        # Cascade-delete related records if possible
        if cascade:
            # delete submissions referring to this student (by name or access_code)
            try:
                # If your Submission model stores access_code, prefer that
                if access_code is not None:
                    db.query(Submission).filter(Submission.access_code == access_code).delete()
                # fallback: delete by student_name + class_name
                db.query(Submission).filter(
                    Submission.student_name == student_name,
                    Submission.class_name == student.class_name
                ).delete()
            except Exception:
                # model might not exist or columns differ — ignore and proceed
                pass

            # delete retake entries tied to this access code
            try:
                if access_code is not None:
                    db.query(Retake).filter(Retake.access_code == access_code).delete()
            except Exception:
                pass

        # finally delete the user
        db.delete(student)
        db.commit()
        return True
    finally:
        db.close()


def clear_submissions_db():
    db = get_session()
    try:
        db.query(Submission).delete()
        db.commit()
    finally:
        db.close()




# db_helpers.py (add this)

def save_questions_db(questions):
    """
    Save one or multiple Question objects to the database.
    - Accepts a single Question instance or a list of Question instances.
    - Returns number of inserted rows.
    """
    db = get_session()
    inserted = 0
    try:
        if not questions:
            return 0

        # Normalize to list
        if not isinstance(questions, (list, tuple)):
            questions = [questions]

        for q in questions:
            db.add(q)
            inserted += 1

        db.commit()
        return inserted
    finally:
        db.close()

def reset_test(student_id):
    """
    Resets a student's test status completely:
    - Deletes submissions
    - Clears retake permissions
    - Clears Streamlit session flags for the student
    """
    db = SessionLocal()
    try:
        # Fetch the student
        student = db.query(User).filter(User.id == student_id).first()
        if not student:
            raise ValueError(f"Student with ID {student_id} not found.")
        access_code = student.access_code

        # 1️⃣ Delete submissions
        deleted_subs = db.query(Submission).filter(Submission.access_code == access_code).delete()

        # 2️⃣ Reset retakes
        db.query(Retake).filter(Retake.access_code == access_code).delete()

        db.commit()

        # 3️⃣ Clear session state flags (if student currently logged in)
        session_keys = [
            "student_logged_in", "student", "test_started", "current_question",
            "answers", "submitted", "score", "test_start_time"
        ]
        for key in session_keys:
            if key in st.session_state:
                del st.session_state[key]

        return {"success": True, "deleted_submissions": deleted_subs}

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
