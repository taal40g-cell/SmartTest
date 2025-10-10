from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

# ------------------------------
# Database setup
# ------------------------------
DATABASE_URL = "postgresql+psycopg2://postgres:1Onomatopoeia@localhost:5432/smarttest"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# ------------------------------
# Normalization function
# ------------------------------
def normalize_text(text):
    if not text:
        return ""
    return (
        str(text)
        .strip()
        .lower()
        .replace("₂", "2")
        .replace("₃", "3")
        .replace("₄", "4")
        .replace("’", "'")
        .replace("æ", "ae")  # fix special chars like She doesnÆt
    )

# ------------------------------
# Load questions
# ------------------------------
subject = "English"
result = session.execute(
    text("SELECT id, question_text, options, answer FROM questions WHERE subject = :subject LIMIT 5"),
    {"subject": subject}
).mappings().all()  # <--- returns dict-like rows

questions = []
for row in result:
    opts = row["options"]
    if isinstance(opts, str):
        try:
            opts = json.loads(opts)
        except:
            opts = [o.strip() for o in opts.split(",") if o.strip()]

    questions.append({
        "id": row["id"],
        "question_text": row["question_text"],
        "options": opts,
        "answer": normalize_text(row["answer"])
    })

# ------------------------------
# Example student answers
# ------------------------------
student_answers = {
    row["id"]: normalize_text(ans)
    for row, ans in zip(result, ["children", "went", "sad", "she doesn't like mangoes.", "mice"])
}

# ------------------------------
# Check correctness
# ------------------------------
for q in questions:
    selected = student_answers.get(q["id"], "")
    is_correct = selected == q["answer"]
    print(f"QID {q['id']}: Your answer: {selected}, Correct: {q['answer']}, Match: {is_correct}")

session.close()
