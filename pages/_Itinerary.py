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

# Safely fetch start date with fallback if empty
conn = get_connection()
df_trip = pd.read_sql("SELECT start_date FROM trips WHERE id = %s;", conn, params=(active_trip_id,))
conn.close()

default_start_date = df_trip.iloc[0]["start_date"] if not df_trip.empty else date.today()

with st.form("add_itinerary_form", clear_on_submit=True):
    i1, i2 = st.columns(2)
    day_date = i1.date_input("Activity Date", value=default_start_date)
    activity_title = i2.text_input("Activity / Place to Visit")
    
    i3, i4 = st.columns(2)
    location = i3.text_input("Location / Address")
    desc = i4.text_area("Description / Notes")
    
    if st.form_submit_button("Add Activity"):
        if not activity_title:
            st.error("Please provide an activity title.")
        else:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO itinerary (trip_id, day_date, activity_title, description, location)
                VALUES (%s, %s, %s, %s, %s);
            """, (active_trip_id, day_date, activity_title, desc, location))
            conn.commit()
            cur.close()
            conn.close()
            st.success("Activity added to itinerary!")
            st.rerun()
        
conn = get_connection()
itinerary_df = pd.read_sql("SELECT * FROM itinerary WHERE trip_id = %s ORDER BY day_date ASC;", conn, params=(active_trip_id,))
conn.close()

if not itinerary_df.empty:
    for day, group in itinerary_df.groupby("day_date"):
        st.markdown(f"### 📅 {day}")
        for _, row in group.iterrows():
            with st.expander(f"{row['activity_title']} {f'(@ {row[\"location\"]})' if row['location'] else ''}"):
                if row["description"]:
                    st.write(row["description"])
else:
    st.info("No activities planned for this trip yet. Use the form above to add places to visit!")
