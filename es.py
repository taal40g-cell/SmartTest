import streamlit as st
import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

# -----------------------------
# Get DATABASE_URL from env
# -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("⚠️ DATABASE_URL not set in environment variables.")
else:
    st.write(f"Using DATABASE_URL: `{DATABASE_URL}`")

    try:
        # Create SQLAlchemy engine
        engine = create_engine(DATABASE_URL)

        # Inspect tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        st.success("✅ Connected to database successfully!")
        st.write("Tables found:")
        st.write(tables)

    except SQLAlchemyError as e:
        st.error("❌ Database connection failed!")
        st.text(str(e))
