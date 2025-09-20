import streamlit as st
import pandas as pd
import time
import io
import json
from db_helpers import (
    SessionLocal,
    Question,
    add_admin,
    get_admin,set_admin,verify_admin,
    add_student_db,save_questions_db,
    get_student_by_access_code_db,
    add_question_db,reset_test,
    get_questions_db,update_student_db,delete_student_db,
    get_submission_db,
    get_users,get_admins,clear_students_db,clear_questions_db,clear_submissions_db,
    set_retake_db,preview_questions_db,count_questions_db,
    get_retake_db, update_admin_password,bulk_add_students_db,
    reset_student_retake_db,hash_password,handle_uploaded_questions,
    ensure_super_admin_exists,require_admin_login,get_all_submissions_db,
    get_submissions_by_access_code,

)



# ==============================
# CONFIG
# ==============================
CLASSES = ["JHS1", "JHS2", "JHS3"]
SUBJECTS = [
    "English", "Math", "Science", "History", "Geography",
    "Physics", "Chemistry", "Biology", "ICT", "Economics"
]

ROLE_TABS = {
    "super_admin": [
        "➕ Add User",
        "📥 Bulk Add Students",
        "👥 Manage Students",
        "🛡️ Manage Admins",
        "🔑 Change Password",
        "📤 Upload Questions",
        "🗑️ Delete Questions & Duration",
        "🏆 View Leaderboard",
        "🔄 Allow Retake",
        "🖨️ Generate Access Slips",
        "♻️ Reset Tests",
        "📦 Data Export",  # <--- ADD HERE
        "🚪 Logout"
    ],

    "admin": [
        "➕ Add User",
        "📥 Bulk Add Students",
        "👥 Manage Students",
        "🔑 Change Password",
        "📤 Upload Questions",
        "🗑️ Delete Questions & Duration",
        "🏆 View Leaderboard",
        "🔄 Allow Retake",
        "🖨️ Generate Access Slips",
        "🚪 Logout"
    ],
    "teacher": [
        "👥 Manage Students",
        "📤 Upload Questions",
        "🗑️ Delete Questions & Duration",
        "🏆 View Leaderboard",
        "🚪 Logout"
    ],
    "moderator": [
        "🏆 View Leaderboard",
        "🚪 Logout"
    ]
}

# ==============================
# MAIN ADMIN FUNCTION
# ==============================
def run_admin_mode():
    """Full database-driven admin panel with role-based access."""
    if not require_admin_login():
        return

    # Load current admin & role
    current_user = st.session_state.get("admin_username", "")
    all_admins = get_admins(as_dict=True)
    current_role = all_admins.get(current_user, "admin")

    available_tabs = ROLE_TABS.get(current_role, ROLE_TABS["admin"])

    st.sidebar.title(f"⚙️ Admin Panel ({current_user} – {current_role})")

    # ✅ FIXED: Stable tab switching using `key`
    selected_tab = st.sidebar.radio(
        "Choose Action",
        available_tabs,
        key="selected_tab_radio"
    )

    # Save current selection (optional, for other logic)
    st.session_state["selected_tab"] = selected_tab

    st.title("🛠️ Admin Dashboard")
    # ==============================
    # ➕ Add User
    # ==============================
    if selected_tab == "➕ Add User":
        st.subheader("Add a Student")
        name = st.text_input("Student Name")
        class_name = st.selectbox("Class", CLASSES)
        if st.button("Add Student"):
            if not name.strip():
                st.error("❌ Enter student name.")
            else:
                code = add_student_db(name, class_name)
                st.success(f"✅ {name} added | Access Code: {code}")

    # ==============================
    # 📥 Bulk Add Students
    # ==============================
    elif selected_tab == "📥 Bulk Add Students":
        st.subheader("📥 Bulk Upload Students (CSV)")
        uploaded = st.file_uploader("Upload CSV with 'name' & 'class'", type=["csv"])

        if uploaded:
            try:
                df = pd.read_csv(uploaded)

                if not {"name", "class"}.issubset(df.columns):
                    st.error("❌ CSV must have 'name' and 'class' columns")
                else:
                    students_list = [
                        (str(row["name"]).strip(), str(row["class"]).strip())
                        for _, row in df.iterrows()
                    ]

                    # Call our DB function to add students (with duplicate check)
                    added_students, skipped_students = bulk_add_students_db(students_list)

                    if added_students:
                        # Ensure returned list contains Student ID + Access Code
                        result_df = pd.DataFrame(added_students, columns=["Student ID", "Access Code", "Name", "Class"])
                        st.success(f"✅ {len(added_students)} students added successfully!")
                        st.dataframe(result_df, use_container_width=True)

                        # CSV download with IDs and Access Codes
                        csv_data = result_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📥 Download Access Codes CSV",
                            data=csv_data,
                            file_name="bulk_added_students.csv",
                            mime="text/csv",
                        )

                    if skipped_students:
                        st.warning(
                            f"⚠️ {len(skipped_students)} students skipped (already exist): "
                            + ", ".join([f"{n} ({c})" for n, c in skipped_students])
                        )

            except Exception as e:
                st.error(f"⚠️ Error reading CSV: {e}")

    elif selected_tab == "👥 Manage Students":
        st.subheader("👥 Manage Students")
        users = get_users()

        if not users:
            st.info("No students found.")
        else:
            df = pd.DataFrame(users.values())
            st.dataframe(df, use_container_width=True)

            # Select student to edit/delete
            student_ids = [u["id"] for u in users.values()]
            selected_id = st.selectbox("Select Student ID", student_ids)

            if selected_id:
                selected_student = next((u for u in users.values() if u["id"] == selected_id), None)
                if selected_student:
                    st.write(f"✏️ Editing **{selected_student['name']}** (Class: {selected_student['class_name']})")

                    new_name = st.text_input("Update Name", value=selected_student["name"])
                    new_class = st.selectbox("Update Class", CLASSES,
                                             index=CLASSES.index(selected_student["class_name"]))

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Save Changes"):
                            update_student_db(selected_id, new_name, new_class)
                            st.success("✅ Student updated successfully!")
                            st.rerun()

                    with col2:
                        if st.button("🗑️ Delete Student", type="primary"):
                            delete_student_db(selected_id)
                            st.warning("⚠️ Student deleted.")
                            st.rerun()

            # Export all students to CSV
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Students CSV", csv_data, "students_backup.csv", "text/csv")

    # ==============================
    # 🛡️ Manage Admins
    # ==============================
    elif selected_tab == "🛡️ Manage Admins" and current_role == "super_admin":
        st.header("🛡️ Manage Admins")
        admins = get_admins()
        st.dataframe(pd.DataFrame([{"username": a.username, "role": a.role} for a in admins]))

        new_user = st.text_input("👤 Username")
        new_pass = st.text_input("🔑 Password", type="password")
        new_role = st.selectbox("🎭 Role", ["admin", "teacher", "moderator", "super_admin"])
        if st.button("Add Admin"):
            if not new_user.strip() or not new_pass.strip():
                st.error("❌ Username & password required.")
            else:
                ok = set_admin(new_user.strip(), new_pass.strip(), new_role)
                st.success(f"✅ Admin '{new_user}' added or updated.") if ok else st.error("❌ Failed to add admin.")
                if ok: st.rerun()
    # ==============================
    # 🔑 Change Password
    # ==============================
    elif selected_tab == "🔑 Change Password":
        st.subheader("Change Admin Password")

        current_user = st.session_state.get("admin_username")
        old_pw = st.text_input("Current Password", type="password", key="old_pw")
        new_pw = st.text_input("New Password", type="password", key="new_pw")
        confirm_pw = st.text_input("Confirm New Password", type="password", key="confirm_pw")

        if st.button("Update Password"):
            if not old_pw or not new_pw or not confirm_pw:
                st.error("❌ Please fill in all fields.")
            elif new_pw != confirm_pw:
                st.error("❌ New passwords do not match.")
            else:
                from db_helpers import verify_admin, update_admin_password, hash_password

                admin = verify_admin(current_user, old_pw)
                if admin:
                    hashed_new_pw = hash_password(new_pw)
                    success = update_admin_password(current_user, hashed_new_pw)
                    if success:
                        st.success("✅ Password updated successfully.")
                        st.info("🔑 You will be logged out in 3 seconds. Please log in again.")

                        # ✅ Create placeholder and sleep without freezing Streamlit completely
                        placeholder = st.empty()
                        for i in range(3, 0, -1):
                            placeholder.info(f"⏳ Logging out in {i}...")
                            time.sleep(1)

                        # ✅ Then reset session state and rerun
                        st.session_state["admin_logged_in"] = False
                        st.session_state["admin_username"] = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to update password. Try again.")
                else:
                    st.error("❌ Current password is incorrect.")

    # ==============================
    # 📤 Upload Questions
    # ==============================
    elif selected_tab == "📤 Upload Questions":
        st.subheader("📤 Upload Questions to Database")

        cls = st.selectbox("Class", CLASSES, key="upload_class")
        sub = st.selectbox("Subject", SUBJECTS, key="upload_subject")

        existing_count = count_questions_db(cls, sub)
        st.info(f"📊 Currently {existing_count} questions in DB for {cls} - {sub}")

        if st.button("🔍 Preview Existing Questions", key="preview_btn"):
            data = preview_questions_db(cls, sub, limit=10)
            if data:
                st.json(data)
            else:
                st.info("No questions found for this selection.")

        uploaded = st.file_uploader("Upload Question JSON", type=["json"], key="upload_file")

        if uploaded:
            st.success(f"✅ File selected: {uploaded.name}")
            if st.button("✅ Confirm Upload", key="confirm_upload_btn"):
                result = handle_uploaded_questions(uploaded, cls, sub)
                if result.get("success"):
                    st.success(f"🎯 {result['inserted']} questions uploaded successfully "
                               f"(replaced {result['deleted']} old ones).")
                    st.session_state.pop("upload_file", None)
                    st.rerun()
                else:
                    st.error(f"❌ Upload failed: {result.get('error')}")

    # ==============================
    # 🗑️ Delete Questions & Duration
    # ==============================
    elif selected_tab == "🗑️ Delete Questions & Duration":
        st.subheader("🗑 Delete Question Sets")
        cls = st.selectbox("Class", CLASSES)
        sub = st.selectbox("Subject", SUBJECTS)  # ✅ DROPDOWN here too

        if cls and sub:
            existing = get_questions_db(cls, subject=sub)
            if existing:
                st.info(f"Found {len(existing)} questions for {cls} - {sub}")

                confirm = st.checkbox("⚠️ I confirm I want to delete these questions", value=False)
                delete_btn = st.button("🗑️ Delete Questions", type="primary")

                if delete_btn:
                    if not confirm:
                        st.error("❌ Please check the confirmation box before deleting.")
                    else:
                        db = SessionLocal()
                        try:
                            db.query(Question).filter(
                                Question.class_name == cls,
                                Question.subject == sub
                            ).delete()
                            db.commit()
                            st.success(f"✅ Deleted all {len(existing)} questions for {cls} - {sub}")
                        finally:
                            db.close()  # ✅ close FIRST

                        st.rerun()  # ✅ rerun AFTER closing DB

            else:
                st.warning(f"No questions found for {cls} - {sub}")

    # ==============================
    # 🏆 View Leaderboard
    # ==============================
    elif selected_tab == "🏆 View Leaderboard":
        st.subheader("🏆 View Leaderboard")

        access_code_input = st.text_input("Enter Access Code to Search", key="lb_access_code")

        col1, col2 = st.columns([2, 1])
        with col1:
            search_btn = st.button("🔎 Search", type="primary")
        with col2:
            show_all_btn = st.button("📋 Show Full Leaderboard")

        if search_btn and access_code_input:
            subs = get_submissions_by_access_code(access_code_input.strip())
            if subs:
                df = pd.DataFrame([{
                    "Student": s.student_name,
                    "Class": s.class_name,
                    "Subject": s.subject,
                    "Score": s.score,
                    "Date": s.timestamp.strftime("%Y-%m-%d %H:%M")
                } for s in subs])
                df = df.sort_values(by="Score", ascending=False)
                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Download Results (CSV)",
                    csv,
                    f"results_{access_code_input.strip()}.csv",
                    "text/csv",
                    use_container_width=True,
                )
            else:
                st.warning("No submissions found for this access code.")

        elif show_all_btn:
            all_subs = get_all_submissions_db()
            if all_subs:
                all_df = pd.DataFrame([{
                    "Student": s.student_name,
                    "Class": s.class_name,
                    "Subject": s.subject,
                    "Score": s.score,
                    "Date": s.timestamp.strftime("%Y-%m-%d %H:%M")
                } for s in all_subs]).sort_values(by="Score", ascending=False)

                st.dataframe(all_df, use_container_width=True)
                all_csv = all_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download All (CSV)",
                    all_csv,
                    "leaderboard_all.csv",
                    "text/csv",
                    use_container_width=True,
                )
            else:
                st.info("No submissions in the database yet.")
    # ==============================
    # 🔄 Allow Retake
    # ==============================
    elif selected_tab == "🔄 Allow Retake":
        code = st.text_input("Student Access Code")
        if code:
            student = get_student_by_access_code_db(code)
            if not student:
                st.error("Invalid code.")
            else:
                st.info(f"Student: {student.name} | Class: {student.class_name}")
                for subj in SUBJECTS:
                    allow = st.checkbox(subj, value=(get_retake_db(code, subj) > 0))
                    if st.button(f"Save {subj} Retake"):
                        set_retake_db(code, subj, allowed=1 if allow else 0)
                        st.success(f"Retake for {subj} updated.")

    # ==============================
    # 🖨️ Generate Access Slips
    # ==============================
    elif selected_tab == "🖨️ Generate Access Slips":
        st.subheader("🖨️ Generate Student Access Slips")

        users = get_users()
        if not users:
            st.info("No students found.")
        else:
            df = pd.DataFrame(users.values())
            st.dataframe(df, use_container_width=True)

            if st.button("📄 Generate Access Slips for All Students"):
                slips_df = df[["name", "class_name", "access_code"]]
                csv_data = slips_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Access Slips CSV",
                    csv_data,
                    "access_slips.csv",
                    "text/csv"
                )
                st.success(f"✅ Generated {len(slips_df)} access slips successfully!")

    # ==============================
    # ♻️ Reset Tests
    # ==============================
    elif selected_tab == "♻️ Reset Tests":
        st.subheader("♻️ Reset Student Test Status")

        users = get_users()
        if users:
            student_codes = list(users.keys())
            student_options = [f"{users[code]['name']} ({users[code]['class']})" for code in student_codes]

            selected_idx = st.selectbox(
                "Select Student to Edit/Delete",
                range(len(student_codes)),
                format_func=lambda i: student_options[i]
            )

            selected_code = student_codes[selected_idx]
            selected_student = users[selected_code]

            st.write(f"✏️ Editing **{selected_student['name']}** (Class: {selected_student['class']})")

            new_name = st.text_input("Update Name", value=selected_student["name"])
            new_class = st.selectbox("Update Class", CLASSES,
                                     index=CLASSES.index(selected_student["class"]))

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Changes"):
                    update_student_db(selected_code, new_name, new_class)
                    st.success("✅ Student updated successfully!")
                    st.rerun()

            with col2:
                if st.button("🗑️ Delete Student", type="primary"):
                    delete_student_db(selected_code)
                    st.warning("⚠️ Student deleted.")
                    st.rerun()

    # ==============================
    # 📦 Data Export (Super Admin Only)
    # ==============================
    elif selected_tab == "📦 Data Export" and current_role == "super_admin":
        # ... existing Data Export code ...
        st.subheader("📦 Backup & Restore Database")

        # -----------------------------
        # 🔽 EXPORT SECTION
        # -----------------------------
        st.markdown("### 🔽 Export Current Data")

        # --- Students ---
        students = get_users()
        students_df = pd.DataFrame(students.values()) if students else pd.DataFrame()
        st.write(f"👥 Students: {len(students_df)} records")

        # --- Questions ---
        questions_list = []
        for cls in CLASSES:
            for sub in SUBJECTS:
                qs = get_questions_db(cls, sub)
                if qs:
                    questions_list.extend(qs)

        # Convert Question objects to dict safely
        questions_data = []
        for q in questions_list:
            questions_data.append({
                "id": getattr(q, "id", ""),
                "class_name": getattr(q, "class_name", ""),
                "subject": getattr(q, "subject", ""),
                "question_text": getattr(q, "question_text", ""),
                "options": getattr(q, "options", ""),
                "answer": getattr(q, "answer", "")
            })
        questions_df = pd.DataFrame(questions_data) if questions_data else pd.DataFrame()
        st.write(f"❓ Questions: {len(questions_df)} records")

        # --- Submissions ---
        subs = get_all_submissions_db()
        submissions_data = []
        if subs:
            for s in subs:
                submissions_data.append({
                    "Student": getattr(s, "student_name", ""),
                    "Class": getattr(s, "class_name", ""),
                    "Subject": getattr(s, "subject", ""),
                    "Score": getattr(s, "score", ""),
                    "Date": s.timestamp.strftime("%Y-%m-%d %H:%M") if hasattr(s, "timestamp") else ""
                })
        submissions_df = pd.DataFrame(submissions_data) if submissions_data else pd.DataFrame()
        st.write(f"📝 Submissions: {len(submissions_df)} records")

        # --- CSV Downloads ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("⬇️ Students CSV", students_df.to_csv(index=False), "students.csv")
        with col2:
            st.download_button("⬇️ Questions CSV", questions_df.to_csv(index=False), "questions.csv")
        with col3:
            st.download_button("⬇️ Submissions CSV", submissions_df.to_csv(index=False), "submissions.csv")

        # --- Excel (Multi-Sheet) Download ---
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            students_df.to_excel(writer, index=False, sheet_name="Students")
            questions_df.to_excel(writer, index=False, sheet_name="Questions")
            submissions_df.to_excel(writer, index=False, sheet_name="Submissions")
        excel_buffer.seek(0)
        st.download_button(
            "⬇️ Download All Data (Excel)",
            excel_buffer,
            "smarttest_backup.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # --- JSON Full Backup ---
        full_backup = {
            "students": students,
            "questions": questions_data,
            "submissions": submissions_data,
        }
        json_bytes = json.dumps(full_backup, indent=2).encode("utf-8")
        st.download_button(
            "⬇️ Full JSON Backup",
            json_bytes,
            "smarttest_backup.json",
            mime="application/json",
        )

        st.divider()

        # -----------------------------
        # 🔄 RESTORE SECTION
        # -----------------------------
        st.markdown("### 🔄 Restore From Backup")
        uploaded_backup = st.file_uploader("Upload JSON Backup", type=["json"])

        if uploaded_backup:
            try:
                backup_data = json.load(uploaded_backup)

                if st.button("⚠️ Restore Now"):
                    # 🔐 Confirm restore
                    if st.confirm("This will overwrite your database. Continue?"):
                        # Import students
                        clear_students_db()
                        for s in backup_data.get("students", {}).values():
                            add_student_db(s["name"], s["class_name"])

                        # Import questions
                        clear_questions_db()
                        for q in backup_data.get("questions", []):
                            save_questions_db(q)

                        # Import submissions
                        from db_helpers import add_submission_db, clear_submissions_db
                        clear_submissions_db()
                        for s in backup_data.get("submissions", []):
                            add_submission_db(
                                s.get("Student", ""),
                                s.get("Class", ""),
                                s.get("Subject", ""),
                                s.get("Score", 0),
                                {}  # answers left blank
                            )

                        st.success("✅ Database restored successfully!")
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to restore: {e}")

    # ==============================
    # 🚪 Logout
    # ==============================
    elif selected_tab == "🚪 Logout":
        st.session_state["admin_logged_in"] = False
        st.success("Logged out.")
        st.rerun()
