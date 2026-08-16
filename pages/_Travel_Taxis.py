import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

st.title("✈️ Travel & Taxi Bookings")

if not st.session_state.get("active_trip_id"):
    st.warning("⚠️ Please select an active trip from the main Home page first!")
    st.stop()

active_trip_id = st.session_state.active_trip_id

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

with st.form("add_travel_form", clear_on_submit=True):
    t1, t2, t3 = st.columns(3)
    transport_type = t1.selectbox("Transport Type", ["Flight", "Train", "Taxi/Transfer", "Car Rental", "Bus"])
    provider = t2.text_input("Provider / Airline / App (e.g., Delta, Uber)")
    ref_code = t3.text_input("Reference Code / Seat Info")
    
    t4, t5, t6 = st.columns(3)
    dep_time = t4.text_input("Departure Time (YYYY-MM-DD HH:MM)", value=str(datetime.now().strftime("%Y-%m-%d %H:%M")))
    arr_time = t5.text_input("Arrival Time (YYYY-MM-DD HH:MM)", value=str(datetime.now().strftime("%Y-%m-%d %H:%M")))
    cost = t6.number_input("Cost (₹)", min_value=0.0)
    
    if st.form_submit_button("Add Booking"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO travel (trip_id, transport_type, provider, departure_time, arrival_time, reference_code, cost)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (active_trip_id, transport_type, provider, dep_time, arr_time, ref_code, cost))
        conn.commit()
        cur.close()
        conn.close()
        st.success("Travel booking added!")
        st.rerun()
        
conn = get_connection()
travel_df = pd.read_sql("SELECT * FROM travel WHERE trip_id = %s;", conn, params=(active_trip_id,))
conn.close()

if not travel_df.empty:
    st.dataframe(travel_df[["transport_type", "provider", "departure_time", "arrival_time", "reference_code", "cost"]], hide_index=True)

