import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

st.title("📊 Trip Master Summary Dashboard")

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

# --- 1. Trip Details & Countdown ---
st.subheader(f"🎉 {active_trip['title']}")
col1, col2, col3 = st.columns(3)

try:
    start_dt = pd.to_datetime(active_trip['start_date']).date()
    days_to_trip = (start_dt - date.today()).days
except Exception:
    days_to_trip = 0

with col1:
    st.metric("Countdown", f"{days_to_trip} Days" if days_to_trip >= 0 else "Trip Started/Ended")
    st.write(f"**Dates:** {active_trip['start_date']} to {active_trip['end_date']}")

with col2:
    st.metric("Destination", active_trip['destination'])
    st.metric("Total Budget", f"₹{active_trip['total_budget']:,.2f}" if active_trip['total_budget'] else "₹0.00")

with col3:
    try:
        conn = get_connection()
        exp_sum = pd.read_sql("SELECT SUM(amount) as total FROM expenses WHERE trip_id = %s;", conn, params=(active_trip_id,)).iloc[0]['total']
        conn.close()
        total_spent = exp_sum if exp_sum else 0.0
    except Exception:
        total_spent = 0.0
    st.metric("Total Expenses Incurred", f"₹{total_spent:,.2f}")

st.divider()

# --- 2. People Going on Trip ---
st.markdown("### 👥 Participants on this Trip")
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
    st.dataframe(trip_members_df, hide_index=True)

st.divider()

# --- 3. Checklist Status ---
st.markdown("### ✅ Checklist Status")
try:
    conn = get_connection()
    tasks_df = pd.read_sql("""
        SELECT c.task, c.category, fm.name as assigned_to, c.is_completed 
        FROM checklist c 
        LEFT JOIN family_members fm ON c.assigned_to = fm.id 
        WHERE c.trip_id = %s;
    """, conn, params=(active_trip_id,))
    conn.close()
except Exception:
    tasks_df = pd.DataFrame()

if not tasks_df.empty:
    total_tasks = len(tasks_df)
    completed_tasks = int(tasks_df['is_completed'].sum())
    progress_val = float(completed_tasks / total_tasks) if total_tasks > 0 else 0.0
    
    st.progress(progress_val)
    st.write(f"**Progress:** {completed_tasks} of {total_tasks} tasks completed.")
    st.dataframe(tasks_df, hide_index=True)
else:
    st.info("No preparation tasks added yet.")

st.divider()

# --- 4. Hotel Bookings ---
st.markdown("### 🏨 Hotel Bookings So Far")
try:
    conn = get_connection()
    hotels_df = pd.read_sql("SELECT hotel_name, address, check_in, check_out, confirmation_code, total_cost FROM hotels WHERE trip_id = %s;", conn, params=(active_trip_id,))
    conn.close()
except Exception:
    hotels_df = pd.DataFrame()

if not hotels_df.empty:
    st.dataframe(hotels_df, hide_index=True)
else:
    st.info("No hotel bookings added yet.")

st.divider()

# --- 5. Travel Bookings ---
st.markdown("### ✈️ Travel Bookings So Far")
try:
    conn = get_connection()
    travel_df = pd.read_sql("SELECT transport_type, provider, departure_time, arrival_time, reference_code, cost FROM travel WHERE trip_id = %s;", conn, params=(active_trip_id,))
    conn.close()
except Exception:
    travel_df = pd.DataFrame()

if not travel_df.empty:
    st.dataframe(travel_df, hide_index=True)
else:
    st.info("No travel bookings added yet.")

st.divider()

# --- 6. Itinerary Summary ---
st.markdown("### 🗺️ Itinerary Overview")
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
