import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="Rujal Trip Planner - Hub",
    page_icon="🌍",
    layout="wide"
)

# --- Database Connection Helper ---
def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# --- Auto-Initialize Database Tables ---
def init_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                phone VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS trips (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                destination VARCHAR(255) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                total_budget NUMERIC(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS trip_members (
                id SERIAL PRIMARY KEY,
                trip_id INT REFERENCES trips(id) ON DELETE CASCADE,
                family_member_id INT REFERENCES family_members(id) ON DELETE CASCADE,
                UNIQUE(trip_id, family_member_id)
            );
            CREATE TABLE IF NOT EXISTS checklist (
                id SERIAL PRIMARY KEY,
                trip_id INT REFERENCES trips(id) ON DELETE CASCADE,
                task VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                assigned_to INT REFERENCES family_members(id) ON DELETE SET NULL,
                is_completed BOOLEAN DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS hotels (
                id SERIAL PRIMARY KEY,
                trip_id INT REFERENCES trips(id) ON DELETE CASCADE,
                hotel_name VARCHAR(255) NOT NULL,
                address TEXT,
                check_in TIMESTAMP NOT NULL,
                check_out TIMESTAMP NOT NULL,
                confirmation_code VARCHAR(100),
                total_cost NUMERIC(10, 2)
            );
            CREATE TABLE IF NOT EXISTS travel (
                id SERIAL PRIMARY KEY,
                trip_id INT REFERENCES trips(id) ON DELETE CASCADE,
                transport_type VARCHAR(50) NOT NULL,
                provider VARCHAR(100),
                departure_time TIMESTAMP,
                arrival_time TIMESTAMP,
                reference_code VARCHAR(100),
                cost NUMERIC(10, 2)
            );
            CREATE TABLE IF NOT EXISTS itinerary (
                id SERIAL PRIMARY KEY,
                trip_id INT REFERENCES trips(id) ON DELETE CASCADE,
                day_date DATE NOT NULL,
                activity_title VARCHAR(255) NOT NULL,
                description TEXT,
                location VARCHAR(255),
                scheduled_time TIME
            );
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                trip_id INT REFERENCES trips(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                amount NUMERIC(10, 2) NOT NULL,
                paid_by INT REFERENCES family_members(id) ON DELETE CASCADE,
                category VARCHAR(100),
                expense_date DATE NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        return False

init_db()

# Session state initialization
if "active_trip_id" not in st.session_state:
    st.session_state.active_trip_id = None

st.title("🌍 Rujal Trip Planner - Hub")
st.write("Welcome! Manage your master family directory, create new trips, or jump into an existing trip using the sidebar navigation.")

# --- Sidebar: Master Family Members Hub ---
st.sidebar.title("👥 Global Family Members")
with st.sidebar.expander("Manage Family Directory"):
    conn = get_connection()
    df_members = pd.read_sql("SELECT * FROM family_members ORDER BY name;", conn)
    conn.close()
    
    if not df_members.empty:
        st.dataframe(df_members[["name", "email", "phone"]], hide_index=True)
        
    with st.form("add_member_form"):
        new_name = st.text_input("Name")
        new_email = st.text_input("Email")
        new_phone = st.text_input("Phone")
        submitted = st.form_submit_button("Add Member")
        if submitted and new_name:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO family_members (name, email, phone) VALUES (%s, %s, %s)", (new_name, new_email, new_phone))
            conn.commit()
            cur.close()
            conn.close()
            st.success(f"Added {new_name}!")
            st.rerun()

st.sidebar.divider()

# --- Trip Selection & Creation Hub ---
conn = get_connection()
trips_df = pd.read_sql("SELECT id, title, destination FROM trips ORDER BY start_date DESC;", conn)
conn.close()

trip_options = {row["title"] + f" ({row['destination']})": row["id"] for _, row in trips_df.iterrows()}
trip_options["+ Create New Trip"] = None

selected_trip_label = st.sidebar.selectbox("Select Active Trip", options=list(trip_options.keys()))

if trip_options[selected_trip_label] is None:
    st.header("🛠️ Create a New Trip")
    with st.form("create_trip_form"):
        title = st.text_input("Trip Title (e.g., Summer Europe 2026)")
        destination = st.text_input("Destination")
        start_date = st.date_input("Start Date", value=date.today())
        end_date = st.date_input("End Date", value=date.today())
        total_budget = st.number_input("Total Budget ($)", min_value=0.0, value=2000.0)
        
        conn = get_connection()
        master_members = pd.read_sql("SELECT id, name FROM family_members ORDER BY name;", conn)
        conn.close()
        
        selected_members = []
        if not master_members.empty:
            st.write("Select Family Members Participating in this Trip:")
            for _, m in master_members.iterrows():
                if st.checkbox(m["name"], key=f"member_{m['id']}"):
                    selected_members.append(m["id"])
                    
        submit_trip = st.form_submit_button("Create Trip")
        if submit_trip and title:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO trips (title, destination, start_date, end_date, total_budget) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
                (title, destination, start_date, end_date, total_budget)
            )
            new_trip_id = cur.fetchone()[0]
            
            for mem_id in selected_members:
                cur.execute("INSERT INTO trip_members (trip_id, family_member_id) VALUES (%s, %s);", (new_trip_id, mem_id))
                
            conn.commit()
            cur.close()
            conn.close()
            st.success("Trip created successfully!")
            st.session_state.active_trip_id = new_trip_id
            st.rerun()
else:
    st.session_state.active_trip_id = trip_options[selected_trip_label]
    conn = get_connection()
    active_trip = pd.read_sql("SELECT * FROM trips WHERE id = %s;", conn, params=(st.session_state.active_trip_id,)).iloc[0]
    conn.close()
    
    st.success(f"Currently active trip: **{active_trip['title']}** to **{active_trip['destination']}**")
    st.info("👈 Use the left sidebar pages to manage the Checklist, Accommodations, Travel, Itinerary, and Expenses for this trip!")
