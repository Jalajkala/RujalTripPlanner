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

# --- CREATE (Add Hotel) ---
with st.expander("➕ Add New Accommodation", expanded=False):
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
        
        if st.form_submit_button("Save Hotel"):
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
                    st.success("Hotel added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding hotel: {e}")

st.divider()
st.markdown("### 📋 Manage Accommodations")

# --- READ, UPDATE, DELETE ---
try:
    conn = get_connection()
    hotels_df = pd.read_sql("SELECT id, hotel_name, address, maps_link, check_in, check_out, confirmation_code, total_cost FROM hotels WHERE trip_id = %s;", conn, params=(active_trip_id,))
    conn.close()
except Exception:
    hotels_df = pd.DataFrame()

if not hotels_df.empty:
    for _, row in hotels_df.iterrows():
        hotel_id = row['id']
        with st.container(border=True):
            col_info, col_actions = st.columns([4, 1])
            
            with col_info:
                st.markdown(f"### 🏨 {row['hotel_name']}")
                st.write(f"📍 **Address:** {row['address'] if row['address'] else 'N/A'}")
                if row['maps_link']:
                    st.markdown(f"🗺️ [Open Location in Google Maps]({row['maps_link']})", unsafe_allow_html=True)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**Check-In:** {row['check_in']}")
                c2.write(f"**Check-Out:** {row['check_out']}")
                c3.write(f"**Confirmation:** {row['confirmation_code'] if row['confirmation_code'] else 'N/A'}")
                c4.write(f"**Cost:** ₹{row['total_cost']:,.2f}" if row['total_cost'] else "₹0.00")
            
            with col_actions:
                edit_key = f"edit_hotel_{hotel_id}"
                delete_key = f"del_hotel_{hotel_id}"
                
                if st.button("✏️ Edit", key=edit_key):
                    st.session_state[f"is_editing_hotel_{hotel_id}"] = not st.session_state.get(f"is_editing_hotel_{hotel_id}", False)
                
                if st.button("🗑️ Delete", key=delete_key):
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM hotels WHERE id = %s;", (hotel_id,))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Deleted hotel!")
                    st.rerun()

            # Inline Update Form
            if st.session_state.get(f"is_editing_hotel_{hotel_id}", False):
                with st.form(f"update_hotel_form_{hotel_id}"):
                    st.markdown("#### Edit Hotel Details")
                    up_name = st.text_input("Hotel Name", value=row['hotel_name'])
                    up_addr = st.text_input("Address", value=row['address'] if row['address'] else "")
                    up_map = st.text_input("Google Maps Link", value=row['maps_link'] if row['maps_link'] else "")
                    
                    uc1, uc2 = st.columns(2)
                    up_in = uc1.date_input("Check-In", value=pd.to_datetime(row['check_in']).date())
                    up_out = uc2.date_input("Check-Out", value=pd.to_datetime(row['check_out']).date())
                    
                    uc3, uc4 = st.columns(2)
                    up_conf = uc3.text_input("Confirmation Code", value=row['confirmation_code'] if row['confirmation_code'] else "")
                    up_cost = uc4.number_input("Total Cost (₹)", min_value=0.0, value=float(row['total_cost']) if row['total_cost'] else 0.0)
                    
                    if st.form_submit_button("Update Changes"):
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE hotels SET hotel_name = %s, address = %s, maps_link = %s, check_in = %s, check_out = %s, confirmation_code = %s, total_cost = %s
                            WHERE id = %s;
                        """, (up_name, up_addr, up_map, up_in, up_out, up_conf, up_cost, hotel_id))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.session_state[f"is_editing_hotel_{hotel_id}"] = False
                        st.success("Updated successfully!")
                        st.rerun()
else:
    st.info("No hotel bookings added yet.")
