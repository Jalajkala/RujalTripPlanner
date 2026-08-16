import streamlit as st
import psycopg2
import pandas as pd

st.title("🏨 Accommodation Manager")

if not st.session_state.get("active_trip_id"):
    st.warning("⚠️ Please select an active trip from the main Home page first!")
    st.stop()

active_trip_id = st.session_state.active_trip_id

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

with st.form("add_hotel_form", clear_on_submit=True):
    h1, h2 = st.columns(2)
    hotel_name = h1.text_input("Hotel Name")
    address = h2.text_input("Address")
    
    h3, h4, h5, h6 = st.columns(4)
    check_in = h3.date_input("Check-In Date")
    check_out = h4.date_input("Check-Out Date")
    conf_code = h5.text_input("Confirmation Code")
    cost = h6.number_input("Total Cost ($)", min_value=0.0)
    
    if st.form_submit_button("Add Hotel"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO hotels (trip_id, hotel_name, address, check_in, check_out, confirmation_code, total_cost)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (active_trip_id, hotel_name, address, check_in, check_out, conf_code, cost))
        conn.commit()
        cur.close()
        conn.close()
        st.success("Hotel added!")
        st.rerun()
        
conn = get_connection()
hotels_df = pd.read_sql("SELECT * FROM hotels WHERE trip_id = %s;", conn, params=(active_trip_id,))
conn.close()

if not hotels_df.empty:
    st.dataframe(hotels_df[["hotel_name", "address", "check_in", "check_out", "confirmation_code", "total_cost"]], hide_index=True)
