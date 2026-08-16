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

# Fetch trip members for dropdowns
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
    # --- CREATE (Record Expense) ---
    with st.expander("➕ Record New Expense", expanded=False):
        with st.form("add_expense_form", clear_on_submit=True):
            e1, e2, e3 = st.columns(3)
            title = e1.text_input("Expense Title (e.g., Dinner at Port)")
            amount = e2.number_input("Amount (₹)", min_value=0.01)
            paid_by_name = e3.selectbox("Paid By", options=list(member_dict.keys()))
            
            e4, e5 = st.columns(2)
            category = e4.selectbox("Category", ["Food & Drinks", "Transport", "Stay", "Activities", "Shopping"])
            exp_date = e5.date_input("Date", value=date.today())
            
            if st.form_submit_button("Save Expense"):
                paid_by_id = member_dict[paid_by_name]
                try:
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
                except Exception as e:
                    st.error(f"Error recording expense: {e}")
            
    st.divider()
    st.markdown("### 📋 Expense History & Management")

    # --- READ, UPDATE, DELETE ---
    try:
        conn = get_connection()
        expenses_df = pd.read_sql("""
            SELECT e.id, e.title, e.amount, e.paid_by, fm.name as paid_by_name, e.category, e.expense_date 
            FROM expenses e 
            JOIN family_members fm ON e.paid_by = fm.id 
            WHERE e.trip_id = %s 
            ORDER BY e.expense_date DESC;
        """, conn, params=(active_trip_id,))
        conn.close()
    except Exception:
        expenses_df = pd.DataFrame()
    
    if not expenses_df.empty:
        for _, row in expenses_df.iterrows():
            exp_id = row['id']
            with st.container(border=True):
                col_info, col_actions = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"**📅 {row['expense_date']} | {row['title']}** (`{row['category']}`)")
                    st.write(f"Paid **₹{row['amount']:,.2f}** by *{row['paid_by_name']}*")
                
                with col_actions:
                    if st.button("✏️ Edit", key=f"edit_exp_{exp_id}"):
                        st.session_state[f"is_editing_exp_{exp_id}"] = not st.session_state.get(f"is_editing_exp_{exp_id}", False)
                    
                    if st.button("🗑️ Delete", key=f"del_exp_{exp_id}"):
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("DELETE FROM expenses WHERE id = %s;", (exp_id,))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("Deleted expense!")
                        st.rerun()

                # Inline Update Form
                if st.session_state.get(f"is_editing_exp_{exp_id}", False):
                    with st.form(f"update_exp_form_{exp_id}"):
                        st.markdown("#### Edit Expense")
                        up_title = st.text_input("Title", value=row['title'])
                        up_amt = st.number_input("Amount (₹)", min_value=0.01, value=float(row['amount']))
                        up_cat = st.selectbox("Category", ["Food & Drinks", "Transport", "Stay", "Activities", "Shopping"], index=["Food & Drinks", "Transport", "Stay", "Activities", "Shopping"].index(row['category']) if row['category'] in ["Food & Drinks", "Transport", "Stay", "Activities", "Shopping"] else 0)
                        up_payer = st.selectbox("Paid By", options=list(member_dict.keys()), index=list(member_dict.keys()).index(row['paid_by_name']) if row['paid_by_name'] in member_dict else 0)
                        up_date = st.date_input("Date", value=pd.to_datetime(row['expense_date']).date())
                        
                        if st.form_submit_button("Update Expense"):
                            payer_id = member_dict[up_payer]
                            conn = get_connection()
                            cur = conn.cursor()
                            cur.execute("""
                                UPDATE expenses SET title = %s, amount = %s, paid_by = %s, category = %s, expense_date = %s
                                WHERE id = %s;
                            """, (up_title, up_amt, payer_id, up_cat, up_date, exp_id))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.session_state[f"is_editing_exp_{exp_id}"] = False
                            st.success("Updated successfully!")
                            st.rerun()

        st.divider()
        st.markdown("### 📊 Settlement Summary")
        total_spent = expenses_df["amount"].sum()
        num_members = len(trip_members_df)
        fair_share = total_spent / num_members if num_members > 0 else 0
        
        st.write(f"**Total Spent:** ₹{total_spent:,.2f} | **Fair Share per Person ({num_members} members):** ₹{fair_share:,.2f}")
        
        paid_per_member = expenses_df.groupby("paid_by_name")["amount"].sum().to_dict()
        
        balances = []
        for _, row in trip_members_df.iterrows():
            name = row["name"]
            paid = paid_per_member.get(name, 0.0)
            balance = paid - fair_share
            balances.append({"Member": name, "Total Paid": paid, "Balance": balance})
            
        balances_df = pd.DataFrame(balances)
        st.dataframe(balances_df, hide_index=True, use_container_width=True)
    else:
        st.info("No expenses recorded yet.")
