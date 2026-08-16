import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

st.title("📊 Trip Dashboard")

if not st.session_state.get("active_trip_id"):
    st.warning("⚠️ Please select an active trip from the main Home page first!")
    st.stop()

active_trip_id = st.session_state.active_trip_id
conn = psycopg2.connect(st.secrets["DATABASE_URL"])
active_trip = pd.read_sql("SELECT * FROM trips WHERE id = %s;", conn, params=(active_trip_id,)).iloc[0]
conn.close()

st.subheader(f"🎉 {active_trip['title']}")
st.write(f"📍 **Destination:** {active_trip['destination']}")

col1, col2, col3 = st.columns(3)
days_to_trip = (active_trip['start_date'] - date.today()).days

with col1:
    st.metric("Countdown", f"{days_to_trip} Days" if days_to_trip >= 0 else "Trip Started/Ended")
    st.write(f"Dates: {active_trip['start_date']} to {active_trip['end_date']}")

with col2:
    st.metric("Total Budget", f"${active_trip['total_budget']:,.2f}" if active_trip['total_budget'] else "$0.00")

with col3:
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    exp_sum = pd.read_sql("SELECT SUM(amount) as total FROM expenses WHERE trip_id = %s;", conn, params=(active_trip_id,)).iloc[0]['total']
    conn.close()
    total_spent = exp_sum if exp_sum else 0.0
    st.metric("Total Expenses Incurred", f"${total_spent:,.2f}")

st.divider()
st.markdown("### 👥 Participants on this Trip")
conn = psycopg2.connect(st.secrets["DATABASE_URL"])
trip_members_df = pd.read_sql("""
    SELECT fm.name 
    FROM trip_members tm 
    JOIN family_members fm ON tm.family_member_id = fm.id 
    WHERE tm.trip_id = %s;
""", conn, params=(active_trip_id,))
conn.close()

if trip_members_df.empty:
    st.info("No members assigned to this trip yet.")
else:
    st.write(", ".join(trip_members_df["name"].tolist()))
