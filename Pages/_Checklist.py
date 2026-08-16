import streamlit as st
import psycopg2
import pandas as pd

st.title("✅ Preparation Checklist")

if not st.session_state.get("active_trip_id"):
    st.warning("⚠️ Please select an active trip from the main Home page first!")
    st.stop()

active_trip_id = st.session_state.active_trip_id

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# Fetch members for assignment dropdown
conn = get_connection()
trip_members_df = pd.read_sql("""
    SELECT fm.id, fm.name 
    FROM trip_members tm 
    JOIN family_members fm ON tm.family_member_id = fm.id 
    WHERE tm.trip_id = %s;
""", conn, params=(active_trip_id,))
conn.close()
member_dict = {row["name"]: row["id"] for _, row in trip_members_df.iterrows()}

with st.form("add_task_form", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    task_name = c1.text_input("Task Description")
    category = c2.selectbox("Category", ["Documents", "Packing", "Health", "Bookings", "General"])
    assigned_to_name = c3.selectbox("Assign To", options=["Unassigned"] + list(member_dict.keys()))
    
    submitted_task = st.form_submit_button("Add Task")
    if submitted_task and task_name:
        assigned_id = member_dict.get(assigned_to_name, None) if assigned_to_name != "Unassigned" else None
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO checklist (trip_id, task, category, assigned_to) VALUES (%s, %s, %s, %s);", 
                    (active_trip_id, task_name, category, assigned_id))
        conn.commit()
        cur.close()
        conn.close()
        st.rerun()

conn = get_connection()
tasks_df = pd.read_sql("""
    SELECT c.id, c.task, c.category, fm.name as assigned_to, c.is_completed 
    FROM checklist c 
    LEFT JOIN family_members fm ON c.assigned_to = fm.id 
    WHERE c.trip_id = %s;
""", conn, params=(active_trip_id,))
conn.close()

if not tasks_df.empty:
    for _, row in tasks_df.iterrows():
        col_check, col_text, col_cat, col_del = st.columns([1, 6, 3, 1])
        is_done = col_check.checkbox("", value=row["is_completed"], key=f"task_{row['id']}")
        if is_done != row["is_completed"]:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE checklist SET is_completed = %s WHERE id = %s;", (is_done, row['id']))
            conn.commit()
            cur.close()
            conn.close()
            st.rerun()
            
        col_text.write(f"**{row['task']}** (Assigned: *{row['assigned_to'] if row['assigned_to'] else 'None'}*)")
        col_cat.write(f"`{row['category']}`")
        if col_del.button("🗑️", key=f"del_task_{row['id']}"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM checklist WHERE id = %s;", (row['id'],))
            conn.commit()
            cur.close()
            conn.close()
            st.rerun()
