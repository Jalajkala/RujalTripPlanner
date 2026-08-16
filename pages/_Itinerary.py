import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

st.title("🗺️ Day-by-Day Itinerary Planner")

if not st.session_state.get("active_trip_id"):
    st.warning("⚠️ Please select an active trip from the main Home page first!")
    st.stop()

active_trip_id = st.session_state.active_trip_id

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

try:
    conn = get_connection()
    df_trip = pd.read_sql("SELECT start_date FROM trips WHERE id = %s;", conn, params=(active_trip_id,))
    conn.close()
    default_start_date = pd.to_datetime(df_trip.iloc[0]["start_date"]).date() if not df_trip.empty else date.today()
except Exception:
    default_start_date = date.today()

# --- CREATE (Add Activity) ---
with st.expander("➕ Add New Itinerary Activity", expanded=False):
    with st.form("add_itinerary_form", clear_on_submit=True):
        i1, i2 = st.columns(2)
        day_date = i1.date_input("Activity Date", value=default_start_date)
        activity_title = i2.text_input("Activity / Place to Visit")
        
        i3, i4 = st.columns(2)
        location = i3.text_input("Location / Address")
        desc = i4.text_area("Description / Notes")
        
        if st.form_submit_button("Save Activity"):
            if not activity_title.strip():
                st.error("Please provide an activity title.")
            else:
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO itinerary (trip_id, day_date, activity_title, description, location)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (active_trip_id, day_date, activity_title, desc, location))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Activity added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving activity: {e}")

st.divider()
st.markdown("### 📋 Manage Itinerary")

# --- READ, UPDATE, DELETE ---
try:
    conn = get_connection()
    itinerary_df = pd.read_sql("SELECT id, day_date, activity_title, description, location FROM itinerary WHERE trip_id = %s ORDER BY day_date ASC;", conn, params=(active_trip_id,))
    conn.close()
except Exception:
    itinerary_df = pd.DataFrame()

if not itinerary_df.empty:
    itinerary_df['day_date'] = pd.to_datetime(itinerary_df['day_date']).dt.date
    for _, row in itinerary_df.iterrows():
        item_id = row['id']
        with st.container(border=True):
            col_info, col_actions = st.columns([4, 1])
            
            with col_info:
                loc_str = f" @ *{row['location']}*" if row.get('location') else ""
                st.markdown(f"**📅 {row['day_date']} | {row['activity_title']}**{loc_str}")
                if row.get("description"):
                    st.write(row["description"])
            
            with col_actions:
                if st.button("✏️ Edit", key=f"edit_itin_{item_id}"):
                    st.session_state[f"is_editing_itin_{item_id}"] = not st.session_state.get(f"is_editing_itin_{item_id}", False)
                
                if st.button("🗑️ Delete", key=f"del_itin_{item_id}"):
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM itinerary WHERE id = %s;", (item_id,))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Deleted activity!")
                    st.rerun()

            # Inline Update Form
            if st.session_state.get(f"is_editing_itin_{item_id}", False):
                with st.form(f"update_itin_form_{item_id}"):
                    st.markdown("#### Edit Activity")
                    up_date = st.date_input("Date", value=row['day_date'])
                    up_title = st.text_input("Title", value=row['activity_title'])
                    up_loc = st.text_input("Location", value=row['location'] if row['location'] else "")
                    up_desc = st.text_area("Description", value=row['description'] if row['description'] else "")
                    
                    if st.form_submit_button("Update Activity"):
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE itinerary SET day_date = %s, activity_title = %s, location = %s, description = %s
                            WHERE id = %s;
                        """, (up_date, up_title, up_loc, up_desc, item_id))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.session_state[f"is_editing_itin_{item_id}"] = False
                        st.success("Updated successfully!")
                        st.rerun()
else:
    st.info("No itinerary activities planned yet.")
