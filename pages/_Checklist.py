import streamlit as st
import psycopg2
import pandas as pd

st.title("✅ Preparation Checklist & Task Manager")

if not st.session_state.get("active_trip_id"):
    st.warning("⚠️ Please select an active trip from the main Home page first!")
    st.stop()

active_trip_id = st.session_state.active_trip_id

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# Fetch trip members for assignment dropdown
try:
    conn = get_connection()
    trip_members_df = pd.read_sql("""
        SELECT fm.id, fm.name 
        FROM trip_members tm 
        JOIN family_members fm ON tm.family_member_id = fm.id 
        WHERE tm.trip_id = %s;
    """, conn, params=(active_trip_id,))
    conn.close()
except Exception:
    trip_members_df = pd.DataFrame()

member_dict = {row["name"]: row["id"] for _, row in trip_members_df.iterrows()}

# --- CREATE (Add Task) ---
with st.expander("➕ Add New Preparation Task", expanded=False):
    with st.form("add_task_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        task_name = c1.text_input("Task Description")
        category = c2.selectbox("Category", ["Documents", "Packing", "Health", "Bookings", "General"])
        assigned_to_name = c3.selectbox("Assign To", options=["Unassigned"] + list(member_dict.keys()))
        
        submitted_task = st.form_submit_button("Save Task")
        if submitted_task and task_name.strip():
            assigned_id = member_dict.get(assigned_to_name, None) if assigned_to_name != "Unassigned" else None
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO checklist (trip_id, task, category, assigned_to, status) 
                    VALUES (%s, %s, %s, %s, 'Pending');
                """, (active_trip_id, task_name, category, assigned_id))
                conn.commit()
                cur.close()
                conn.close()
                st.success("Task added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding task: {e}")

st.divider()
st.markdown("### 📋 Manage Tasks")

# --- READ, UPDATE, DELETE ---
try:
    conn = get_connection()
    tasks_df = pd.read_sql("""
        SELECT c.id, c.task, c.category, c.assigned_to, fm.name as assigned_to_name, c.status 
        FROM checklist c 
        LEFT JOIN family_members fm ON c.assigned_to = fm.id 
        WHERE c.trip_id = %s;
    """, conn, params=(active_trip_id,))
    conn.close()
except Exception:
    tasks_df = pd.DataFrame()

if not tasks_df.empty:
    status_options = ["Pending", "In Progress", "Completed"]
    
    for _, row in tasks_df.iterrows():
        task_id = row['id']
        with st.container(border=True):
            col_info, col_status, col_actions = st.columns([3, 2, 1])
            
            with col_info:
                st.markdown(f"**{row['task']}**")
                st.caption(f"Category: `{row['category']}` | Assigned: *{row['assigned_to_name'] if row['assigned_to_name'] else 'Unassigned'}*")
            
            with col_status:
                # Inline status dropdown selector
                current_status = row["status"] if row["status"] in status_options else "Pending"
                new_status = st.selectbox(
                    "Status", 
                    options=status_options, 
                    index=status_options.index(current_status), 
                    key=f"status_select_{task_id}",
                    label_visibility="collapsed"
                )
                
                # Update status immediately if changed
                if new_status != current_status:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE checklist SET status = %s WHERE id = %s;", (new_status, task_id))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.rerun()

            with col_actions:
                bc1, bc2 = st.columns(2)
                if bc1.button("✏️", key=f"edit_task_{task_id}", help="Edit Task Details"):
                    st.session_state[f"is_editing_task_{task_id}"] = not st.session_state.get(f"is_editing_task_{task_id}", False)
                
                if bc2.button("🗑️", key=f"del_task_{task_id}", help="Delete Task"):
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM checklist WHERE id = %s;", (task_id,))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Deleted task!")
                    st.rerun()

            # Inline Edit Form
            if st.session_state.get(f"is_editing_task_{task_id}", False):
                with st.form(f"update_task_form_{task_id}"):
                    st.markdown("#### Edit Task Details")
                    up_task = st.text_input("Task Description", value=row['task'])
                    
                    uc1, uc2 = st.columns(2)
                    categories = ["Documents", "Packing", "Health", "Bookings", "General"]
                    up_cat = uc1.selectbox("Category", options=categories, index=categories.index(row['category']) if row['category'] in categories else 0)
                    
                    member_names = ["Unassigned"] + list(member_dict.keys())
                    current_assignee_name = row['assigned_to_name'] if row['assigned_to_name'] in member_dict else "Unassigned"
                    up_assignee = uc2.selectbox("Assigned To", options=member_names, index=member_names.index(current_assignee_name))
                    
                    if st.form_submit_button("Update Task"):
                        up_assignee_id = member_dict.get(up_assignee, None) if up_assignee != "Unassigned" else None
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE checklist SET task = %s, category = %s, assigned_to = %s WHERE id = %s;
                        """, (up_task, up_cat, up_assignee_id, task_id))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.session_state[f"is_editing_task_{task_id}"] = False
                        st.success("Task updated successfully!")
                        st.rerun()
else:
    st.info("No preparation tasks added yet.")
