import streamlit as st
from ui import set_background
from selections.student import run_student_mode
from selections.admin import run_admin_mode
from database import engine
from models import Base

# Create tables if not exist
Base.metadata.create_all(bind=engine)


# --- Session state defaults ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "access_code" not in st.session_state:
    st.session_state.access_code = ""
if "menu_selection" not in st.session_state:
    st.session_state.menu_selection = "Student Mode"
if "trigger_refresh" not in st.session_state:
    st.session_state.trigger_refresh = False
if "admin_username" not in st.session_state:  # 🟢 important!
    st.session_state.admin_username = ""
if "admin_logged_in" not in st.session_state:  # 🟢 good to add too
    st.session_state.admin_logged_in = False

# --- Results page ---
def results_page():
    query_params = st.query_params
    access_code = query_params.get("access_code", [None])[0]

    st.title("Results Page" if access_code else "SmarTest App")
    if access_code:
        st.success(f"Showing results for access code: {access_code}")
    else:
        st.write("No access code provided. Use Student/Admin menu below.")

# --- Main app ---
def main():
    set_background("assets/scr.png")

    # Handle results page query param
    page = st.query_params.get("page", [None])[0]
    if page == "results":
        results_page()
        return

    # App header
    st.markdown(
        "<h1 style='text-align: center; text-decoration: underline; "
        "font-weight: bold; color: white; background-color: '></h1>",
        unsafe_allow_html=True
    )

    # Refresh logic
    if st.session_state.get("trigger_refresh", False):
        st.session_state.trigger_refresh = False
        st.session_state.menu_selection = "Student Mode"
        st.rerun()

    # --- Sidebar menu ---
    menu_options = ["Student Mode", "Admin Panel", "Exit App"]

    # ✅ Simpler: only set once if not exists
    st.session_state.setdefault("menu_selection", "Student Mode")

    # ✅ No manual index, just bind directly
    mode = st.sidebar.radio(
        "📋 Menu",
        menu_options,
        key="menu_selection"
    )

    # Mode selection
    if mode == "Student Mode":
        run_student_mode()
    elif mode == "Admin Panel":
        run_admin_mode()
    elif mode == "Exit App":
        # ✅ Clear everything & force rerun to reset UI instantly
        st.session_state.clear()
        st.session_state.menu_selection = "Student Mode"
        st.success("👋 All sessions cleared.")
        st.rerun()


if __name__ == "__main__":
    main()
