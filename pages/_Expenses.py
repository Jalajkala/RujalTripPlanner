import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

st.title("💰 Expense & Split Tracker")

if not st.session_state.get("active_trip_id"):
    st.warning("⚠️ Please select an active trip from the main Home page first!")
    st.stop()

active_trip_id = st.session_state.active_trip_id

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

conn = get_connection()
trip_members_df = pd.read_sql("""
    SELECT fm.id, fm.name 
    FROM trip_members tm 
    JOIN family_members fm ON tm.family_member_id = fm.id 
    WHERE tm.trip_id = %s;
""", conn, params=(active_trip_id,))
conn.close()

member_dict = {row["name"]: row["id"] for _, row in trip_members_df.iterrows()}

if trip_members_df.empty:
    st.warning("Please assign family members to this trip first from the main page to record expenses.")
else:
    with st.form("add_expense_form", clear_on_submit=True):
        e1, e2, e3 = st.columns(3)
        title = e1.text_input("Expense Title (e.g., Dinner at Port)")
        amount = e2.number_input("Amount (₹)", min_value=0.01)
        paid_by_name = e3.selectbox("Paid By", options=list(member_dict.keys()))
        
        e4, e5 = st.columns(2)
        category = e4.selectbox("Category", ["Food & Drinks", "Transport", "Stay", "Activities", "Shopping"])
        exp_date = e5.date_input("Date", value=date.today())
        
        if st.form_submit_button("Record Expense"):
            paid_by_id = member_dict[paid_by_name]
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO expenses (trip_id, title, amount, paid_by, category, expense_date)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (active_trip_id, title, amount, paid_by_id, category, exp_date))
            conn.commit()
            cur.close()
            conn.close()
            st.success("Expense recorded!")
            st.rerun()
            
    conn = get_connection()
    expenses_df = pd.read_sql("""
        SELECT e.id, e.title, e.amount, fm.name as paid_by, e.category, e.expense_date 
        FROM expenses e 
        JOIN family_members fm ON e.paid_by = fm.id 
        WHERE e.trip_id = %s 
        ORDER BY e.expense_date DESC;
    """, conn, params=(active_trip_id,))
    conn.close()
    
    if not expenses_df.empty:
        st.markdown("### Expense History")
        st.dataframe(expenses_df[["expense_date", "title", "category", "amount", "paid_by"]], hide_index=True)
        
        st.markdown("### 📊 Settlement Summary")
        total_spent = expenses_df["amount"].sum()
        num_members = len(trip_members_df)
        fair_share = total_spent / num_members if num_members > 0 else 0
        
       st.write(f"**Total Spent:** ₹{total_spent:,.2f} | **Fair Share per Person ({num_members} members):** ₹{fair_share:,.2f}")
        
        paid_per_member = expenses_df.groupby("paid_by")["amount"].sum().to_dict()
        
        balances = []
        for _, row in trip_members_df.iterrows():
            name = row["name"]
            paid = paid_per_member.get(name, 0.0)
            balance = paid - fair_share
            balances.append({"Member": name, "Total Paid": paid, "Balance": balance})
            
        balances_df = pd.DataFrame(balances)
        st.dataframe(balances_df, hide_index=True)
