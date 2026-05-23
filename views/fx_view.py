"""FX Rate Management view (admin)."""
import streamlit as st
import pandas as pd
from datetime import date
from managers.fx_manager import (
    SUPPORTED_CURRENCIES, set_rate, get_rate, list_rates,
    convert, latest_rates, seed_default_rates,
)
from managers.auth_manager import can_write

def render():
    user = st.session_state.get("user", {})
    can_edit = can_write(user.get("role", ""), "billing") or user.get("role") == "admin"
    
    st.title("💱 Exchange Rates")
    seed_default_rates()
    
    # 1. Latest Rates KPI
    rates = latest_rates()
    cols = st.columns(len(rates))
    for col, (cur, rate) in zip(cols, rates.items()):
        with col:
            st.metric(cur, f"{rate:.4f}" if rate > 0 else "—")
    
    st.markdown("---")
    
    # 2. Set Exchange Rate (Admin Only)
    if can_edit:
        with st.expander("➕ Set Exchange Rate"):
            with st.form("set_fx_form"):
                c1, c2, c3, c4 = st.columns(4)
                cur = c1.selectbox("Currency", [c for c in SUPPORTED_CURRENCIES if c != "THB"])
                # ใช้ key เพื่อให้ค่าเปลี่ยนตาม selectbox
                rate_val = c2.number_input("Rate (1 unit = ? THB)", min_value=0.0001, 
                                          value=float(get_rate(cur) or 1.0), format="%.4f")
                eff = c3.date_input("Effective Date", value=date.today())
                
                if c4.form_submit_button("💾 Save Rate", type="primary", use_container_width=True):
                    set_rate(cur, rate_val, eff)
                    st.toast(f"Saved: 1 {cur} = {rate_val:.4f} THB", icon="✅")
                    st.rerun()

    # 3. Quick Converter
    with st.expander("🔄 Quick Converter", expanded=True):
        col_amt, col_f, col_icon, col_t = st.columns([2, 1.5, 0.5, 1.5])
        amount = col_amt.number_input("Amount", min_value=0.0, value=100.0, format="%.2f")
        from_cur = col_f.selectbox("From", SUPPORTED_CURRENCIES, index=1)
        col_icon.markdown("<br>→", unsafe_allow_html=True)
        to_cur = col_t.selectbox("To", SUPPORTED_CURRENCIES, index=0)
        
        result = convert(amount, from_cur, to_cur)
        st.success(f"### {result:,.2f} {to_cur}", icon="💱")

    # 4. History Table
    st.markdown("##### 📜 Rate History")
    rows = list_rates(limit=20)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)