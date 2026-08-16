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
    
    h3, h4 = st.columns(2)
    maps_link = h3.text_input("Google Maps Link (URL)")
    conf_code = h4.text_input("Confirmation Code")
    
    h5, h6, h7 = st.columns(3)
    check_in = h5.date_input("Check-In Date")
    check_out = h6.date_input("Check-Out Date")
    cost = h7.number_input("Total Cost (₹)", min_value=0.0)
    
    if st.form_submit_button("Add Hotel"):
        if not hotel_name.strip():
            st.error("Please provide a hotel name.")
        else:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO hotels (trip_id, hotel_name, address, maps_link, check_in, check_out, confirmation_code, total_cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, (active_trip_id, hotel_name, address, maps_link, check_in, check_out, conf_code, cost))
                conn.commit()
                cur.close()
                conn.close()
                st.success("Hotel added!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding hotel: {e}")
        
try:
    conn = get_connection()
    hotels_df = pd.read_sql("SELECT hotel_name, address, maps_link, check_in, check_out, confirmation_code, total_cost FROM hotels WHERE trip_id = %s;", conn, params=(active_trip_id,))
    conn.close()
except Exception:
    hotels_df = pd.DataFrame()

if not hotels_df.empty:
    st.markdown("### Saved Accommodations")
    for _, row in hotels_df.iterrows():
        with st.container(border=True):
            st.markdown(f"### 🏨 {row['hotel_name']}")
            st.write(f"📍 **Address:** {row['address'] if row['address'] else 'N/A'}")
            
            if row['maps_link']:
                st.markdown(f"🗺️ [Open Location in Google Maps]({row['maps_link']})", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"**Check-In:** {row['check_in']}")
            c2.write(f"**Check-Out:** {row['check_out']}")
            c3.write(f"**Confirmation:** {row['confirmation_code'] if row['confirmation_code'] else 'N/A'}")
            c4.write(f"**Cost:** ₹{row['total_cost']:,.2f}" if row['total_cost'] else "₹0.00")
else:
    st.info("No hotel bookings added yet.")
