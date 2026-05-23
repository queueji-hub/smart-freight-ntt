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
    role = user.get("role", "")
    can_edit = can_write(role, "billing") or role == "admin"
    
    st.title("💱 Exchange Rates")
    st.caption("Manage EX rates · All amounts displayed in THB-equivalent")
    
    # Seed defaults if empty
    seed_default_rates()
    
    # Latest rates KPI strip
    rates = latest_rates()
    cols = st.columns(len(rates))
    for col, (cur, rate) in zip(cols, rates.items()):
        with col:
            if cur == "THB":
                st.metric(cur, "1.00 (base)")
            elif rate > 0:
                st.metric(cur, f"{rate:.4f}", help=f"1 {cur} = {rate:.4f} THB")
            else:
                st.metric(cur, "—", help="No rate set")
    
    st.markdown("---")
    
    if can_edit:
        with st.expander("➕ Set Exchange Rate", expanded=False):
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                cur = st.selectbox("Currency",
                    [c for c in SUPPORTED_CURRENCIES if c != "THB"],
                    key="fx_cur")
            with col2:
                rate_val = st.number_input("Rate (1 unit = ? THB)",
                    min_value=0.0001, value=float(get_rate(cur) or 1.0),
                    format="%.4f", key="fx_rate")
            with col3:
                eff = st.date_input("Effective Date",
                    value=date.today(), key="fx_date")
            with col4:
                st.write(""); st.write("")
                if st.button("💾 Save Rate", type="primary",
                              use_container_width=True):
                    set_rate(cur, rate_val, eff)
                    st.success(f"Saved: 1 {cur} = {rate_val:.4f} THB on {eff}")
                    st.rerun()
    
    # Currency converter
    with st.expander("🔄 Quick Converter", expanded=True):
        c1, c2, c3, c4 = st.columns([1.5, 1, 1.5, 1])
        with c1:
            amount = st.number_input("Amount", min_value=0.0, value=100.0,
                                       format="%.2f", key="conv_amt")
        with c2:
            from_cur = st.selectbox("From", SUPPORTED_CURRENCIES,
                                      index=1, key="conv_from")
        with c3:
            st.write(""); st.write("")
            st.markdown("→")
        with c4:
            to_cur = st.selectbox("To", SUPPORTED_CURRENCIES,
                                    index=0, key="conv_to")
        
        result = convert(amount, from_cur, to_cur)
        st.markdown(f"""
        <div style="background:#101113;border:1px solid #23252B;
                    border-radius:8px;padding:1rem;margin-top:8px">
            <div style="font-size:0.85rem;color:#9CA0A8">
                {amount:,.2f} {from_cur} =
            </div>
            <div style="font-size:1.6rem;font-weight:700;
                        color:#26B574;font-family:monospace">
                {result:,.2f} {to_cur}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Historical rates
    st.markdown("##### 📜 Rate History")
    rows = list_rates(limit=50)
    if not rows:
        st.info("No rate history.")
    else:
        df = pd.DataFrame(rows)
        st.dataframe(df[["currency", "rate_to_thb", "effective_date", "source"]],
            use_container_width=True, hide_index=True, height=280,
            column_config={
                "currency": "Currency",
                "rate_to_thb": st.column_config.NumberColumn(
                    "Rate (THB)", format="%.4f"),
                "effective_date": "Effective",
                "source": "Source",
            })
