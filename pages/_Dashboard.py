import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

if not st.session_state.get("active_trip_id"):
    st.warning("⚠️ Please select an active trip from the main Home page first!")
    st.stop()

active_trip_id = st.session_state.active_trip_id

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# Fetch trip details
try:
    conn = get_connection()
    df_trip = pd.read_sql("SELECT * FROM trips WHERE id = %s;", conn, params=(active_trip_id,))
    conn.close()
except Exception as e:
    st.error(f"Error loading trip: {e}")
    st.stop()

if df_trip.empty:
    st.error("Trip not found.")
    st.stop()

active_trip = df_trip.iloc[0]

# --- Modern Header Section ---
st.title(f"Trip : {active_trip['title']}")
st.markdown(f"### 📍 Destination: **{active_trip['destination']}**")

try:
    start_dt = pd.to_datetime(active_trip['start_date']).date()
    days_to_trip = (start_dt - date.today()).days
except Exception:
    days_to_trip = 0

try:
    conn = get_connection()
    exp_sum = pd.read_sql("SELECT SUM(amount) as total FROM expenses WHERE trip_id = %s;", conn, params=(active_trip_id,)).iloc[0]['total']
    conn.close()
    total_spent = exp_sum if exp_sum else 0.0
except Exception:
    total_spent = 0.0

# Top Metric Cards layout using modern containers
col1, col2, col3 = st.columns(3)
with col1:
    with st.container(border=True):
        st.metric("⏳ Countdown", f"{days_to_trip} Days" if days_to_trip >= 0 else "Trip Completed")
with col2:
    with st.container(border=True):
        st.metric("📅 Travel Dates", f"{active_trip['start_date']} to {active_trip['end_date']}")
with col3:
    with st.container(border=True):
        st.metric("💸 Total Expenses Incurred", f"₹{total_spent:,.2f}")

st.markdown("<br>", unsafe_allow_html=True)

# --- Two Column Modern Card Layout ---
left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    # Participants Card
    with st.container(border=True):
        st.markdown("### 👥 Participants")
        try:
            conn = get_connection()
            trip_members_df = pd.read_sql("""
                SELECT fm.name, fm.email, fm.phone 
                FROM trip_members tm 
                JOIN family_members fm ON tm.family_member_id = fm.id 
                WHERE tm.trip_id = %s;
            """, conn, params=(active_trip_id,))
            conn.close()
        except Exception:
            trip_members_df = pd.DataFrame()

        if trip_members_df.empty:
            st.info("No members assigned to this trip yet.")
        else:
            st.dataframe(trip_members_df, hide_index=True, use_container_width=True)

    # Hotel Bookings Card
    with st.container(border=True):
        st.markdown("### 🏨 Hotel Bookings")
        try:
            conn = get_connection()
            hotels_df = pd.read_sql("SELECT hotel_name, address, maps_link, check_in, check_out, confirmation_code, total_cost FROM hotels WHERE trip_id = %s;", conn, params=(active_trip_id,))
            conn.close()
        except Exception:
            hotels_df = pd.DataFrame()

        if not hotels_df.empty:
            for _, row in hotels_df.iterrows():
                st.write(f"**{row['hotel_name']}** ({row['check_in']} to {row['check_out']})")
                if row['maps_link']:
                    st.markdown(f"🗺️ [Google Maps]({row['maps_link']})", unsafe_allow_html=True)
                st.divider()
        else:
            st.info("No hotel bookings added yet.")

    # Travel Bookings Card
    with st.container(border=True):
        st.markdown("### ✈️ Travel Bookings")
        try:
            conn = get_connection()
            travel_df = pd.read_sql("SELECT transport_type, provider, departure_time, arrival_time, reference_code, cost FROM travel WHERE trip_id = %s;", conn, params=(active_trip_id,))
            conn.close()
        except Exception:
            travel_df = pd.DataFrame()

        if not travel_df.empty:
            st.dataframe(travel_df, hide_index=True, use_container_width=True)
        else:
            st.info("No travel bookings added yet.")

with right_col:
    # Checklist Card
    with st.container(border=True):
        st.markdown("### ✅ Checklist Progress")
        try:
            conn = get_connection()
            tasks_df = pd.read_sql("""
                SELECT c.task, c.category, fm.name as assigned_to, c.status 
                FROM checklist c 
                LEFT JOIN family_members fm ON c.assigned_to = fm.id 
                WHERE c.trip_id = %s;
            """, conn, params=(active_trip_id,))
            conn.close()
        except Exception:
            tasks_df = pd.DataFrame()

        if not tasks_df.empty:
            total_tasks = len(tasks_df)
            completed_tasks = int((tasks_df['status'] == 'Completed').sum())
            progress_val = float(completed_tasks / total_tasks) if total_tasks > 0 else 0.0
            
            st.progress(progress_val)
            st.caption(f"**{completed_tasks}** of **{total_tasks}** tasks completed.")
            st.dataframe(tasks_df, hide_index=True, use_container_width=True)
        else:
            st.info("No preparation tasks added yet.")

    # Itinerary Card
    with st.container(border=True):
        st.markdown("### 🗺️ Itinerary Highlights")
        try:
            conn = get_connection()
            itinerary_df = pd.read_sql("SELECT day_date, activity_title, location, description FROM itinerary WHERE trip_id = %s ORDER BY day_date ASC;", conn, params=(active_trip_id,))
            conn.close()
        except Exception:
            itinerary_df = pd.DataFrame()

        if not itinerary_df.empty:
            itinerary_df['day_date'] = pd.to_datetime(itinerary_df['day_date']).dt.date
            for day, group in itinerary_df.groupby("day_date"):
                st.markdown(f"**📅 {day}**")
                for _, row in group.iterrows():
                    loc_str = f" @ *{row['location']}*" if row.get('location') else ""
                    desc_str = f": {row['description']}" if row.get('description') else ""
                    st.write(f"- **{row['activity_title']}**{loc_str}{desc_str}")
        else:
            st.info("No itinerary activities planned yet.")
