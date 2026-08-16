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

# --- CREATE (Add Travel Booking) ---
with st.expander("➕ Add New Travel / Taxi Booking", expanded=False):
    with st.form("add_travel_form", clear_on_submit=True):
        t1, t2, t3 = st.columns(3)
        transport_type = t1.selectbox("Transport Type", ["Flight", "Train", "Taxi/Transfer", "Car Rental", "Bus"])
        provider = t2.text_input("Provider / Airline / App (e.g., Delta, Uber)")
        ref_code = t3.text_input("Reference Code / Seat Info")
        
        t4, t5, t6 = st.columns(3)
        dep_time = t4.text_input("Departure Time (YYYY-MM-DD HH:MM)", value=str(datetime.now().strftime("%Y-%m-%d %H:%M")))
        arr_time = t5.text_input("Arrival Time (YYYY-MM-DD HH:MM)", value=str(datetime.now().strftime("%Y-%m-%d %H:%M")))
        cost = t6.number_input("Cost (₹)", min_value=0.0)
        
        if st.form_submit_button("Save Booking"):
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO travel (trip_id, transport_type, provider, departure_time, arrival_time, reference_code, cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (active_trip_id, transport_type, provider, dep_time, arr_time, ref_code, cost))
                conn.commit()
                cur.close()
                conn.close()
                st.success("Booking added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding booking: {e}")

st.divider()
st.markdown("### 📋 Manage Travel & Bookings")

# --- READ, UPDATE, DELETE ---
try:
    conn = get_connection()
    travel_df = pd.read_sql("SELECT id, transport_type, provider, departure_time, arrival_time, reference_code, cost FROM travel WHERE trip_id = %s;", conn, params=(active_trip_id,))
    conn.close()
except Exception:
    travel_df = pd.DataFrame()

if not travel_df.empty:
    for _, row in travel_df.iterrows():
        travel_id = row['id']
        with st.container(border=True):
            col_info, col_actions = st.columns([4, 1])
            
            with col_info:
                st.markdown(f"### 🚀 {row['transport_type']} - {row['provider'] if row['provider'] else 'General'}")
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Departure:** {row['departure_time']}")
                c2.write(f"**Arrival:** {row['arrival_time']}")
                c3.write(f"**Ref / Code:** {row['reference_code'] if row['reference_code'] else 'N/A'}")
                st.write(f"**Cost:** ₹{row['cost']:,.2f}" if row['cost'] else "Cost: ₹0.00")
            
            with col_actions:
                if st.button("✏️ Edit", key=f"edit_travel_{travel_id}"):
                    st.session_state[f"is_editing_travel_{travel_id}"] = not st.session_state.get(f"is_editing_travel_{travel_id}", False)
                
                if st.button("🗑️ Delete", key=f"del_travel_{travel_id}"):
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM travel WHERE id = %s;", (travel_id,))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Deleted booking!")
                    st.rerun()

            # Inline Update Form
            if st.session_state.get(f"is_editing_travel_{travel_id}", False):
                with st.form(f"update_travel_form_{travel_id}"):
                    st.markdown("#### Edit Travel Booking")
                    up_type = st.selectbox("Transport Type", ["Flight", "Train", "Taxi/Transfer", "Car Rental", "Bus"], index=["Flight", "Train", "Taxi/Transfer", "Car Rental", "Bus"].index(row['transport_type']) if row['transport_type'] in ["Flight", "Train", "Taxi/Transfer", "Car Rental", "Bus"] else 0)
                    up_prov = st.text_input("Provider", value=row['provider'] if row['provider'] else "")
                    up_ref = st.text_input("Reference Code", value=row['reference_code'] if row['reference_code'] else "")
                    
                    uc1, uc2, uc3 = st.columns(3)
                    up_dep = uc1.text_input("Departure Time", value=str(row['departure_time']))
                    up_arr = uc2.text_input("Arrival Time", value=str(row['arrival_time']))
                    up_cost = uc3.number_input("Cost (₹)", min_value=0.0, value=float(row['cost']) if row['cost'] else 0.0)
                    
                    if st.form_submit_button("Update Booking"):
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE travel SET transport_type = %s, provider = %s, departure_time = %s, arrival_time = %s, reference_code = %s, cost = %s
                            WHERE id = %s;
                        """, (up_type, up_prov, up_dep, up_arr, up_ref, up_cost, travel_id))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.session_state[f"is_editing_travel_{travel_id}"] = False
                        st.success("Updated successfully!")
                        st.rerun()
else:
    st.info("No travel bookings added yet.")
