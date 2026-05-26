"""
Business Intelligence Analytics & Executive Financial Dashboard
PostgreSQL Core Connected - 100% Professional ERP Grade Interface
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from managers.shipment_manager import list_shipments
from managers.invoice_manager import list_invoices, get_outstanding_summary
from managers.customer_manager import list_customers

# =========================================================
# SYSTEM VIEW ROUTER ENTRYPOINT
# =========================================================
def render():
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Corporate Decision Intelligence</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>📊 Reports & Operational Analytics</h2>", unsafe_allow_html=True)
    st.caption("Central Business Intelligence — Real-time tracking metrics, daily freight trends, transactional billing cycles, and client exposure matrices.")

    # =========================================================
    # GLOBAL FILTER CONTROL DESK
    # =========================================================
    st.markdown("<div style='padding: 14px; border: 1px solid #1E293B; background-color: #0F172A; border-radius: 12px; margin-bottom: 20px;'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Analysis Window (From) *", value=date.today() - timedelta(days=30), key="bi_start_date")
    end_date = col2.date_input("Analysis Window (To) *", value=date.today(), key="bi_end_date")
    st.markdown("</div>", unsafe_allow_html=True)

    if start_date > end_date:
        st.error("⚠️ Validation Error: 'From' date window cannot transcend 'To' final date parameters.")
        return

    # =========================================================
    # SECTION 1: SHIPMENT PERFORMANCES (KPI GRID)
    # =========================================================
    st.markdown("#### 🚢 Intermodal Freight Activity Ledger")
    
    with st.spinner("Compiling shipment metrics data..."):
        try:
            all_ships = list_shipments() or []
        except Exception as e:
            st.error(f"Failed to extract operational shipment data frames: {str(e)}")
            all_ships = []

    # Safe dynamic conversion using Pandas vectorized features
    if all_ships:
        df_ships = pd.DataFrame(all_ships)
        # Handle string parsing or datetime dynamic types safely
        df_ships['clean_date'] = pd.to_datetime(df_ships['created_at'], errors='coerce').dt.date
        
        # Apply strict parameters filter range
        filtered_mask = (df_ships['clean_date'] >= start_date) & (df_ships['clean_date'] <= end_date)
        filtered_ships_df = df_ships[filtered_mask]
        filtered_ships_list = filtered_ships_df.to_dict(orient="records")
    else:
        filtered_ships_df = pd.DataFrame()
        filtered_ships_list = []

    # Render Executive Performance Scorecard
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Freight Jobs", len(filtered_ships_list))
    k2.metric("In Transit (Proceed)", sum(1 for s in filtered_ships_list if str(s.get("status")).strip() == "Proceed"))
    k3.metric("Operation Finished", sum(1 for s in filtered_ships_list if str(s.get("status")).strip() == "Finished"))
    k4.metric("Audited & Closed", sum(1 for s in filtered_ships_list if str(s.get("status")).strip() == "Closed"))

    # Daily Freight Volume Chart
    if not filtered_ships_df.empty:
        st.markdown("<p style='font-size:13px; font-weight:700; color:#94A3B8; margin-top:15px; margin-bottom:5px;'>📈 Daily Booking Volume Trendline</p>", unsafe_allow_html=True)
        # Resample logic via DataFrame group operators
        daily_trend = filtered_ships_df.groupby('clean_date').size().rename("Bookings Counter")
        st.line_chart(daily_trend, use_container_width=True, color="#38bdf8")
    else:
        st.info("ℹ️ No historical shipping logs matched your specified window interval criteria.")

    st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
    st.divider()

    # =========================================================
    # SECTION 2: FINANCIAL OPERATIONS OVERVIEW (EXPOSURE)
    # =========================================================
    st.markdown("#### 💰 Corporate Revenue & Accounts Receivable (AR)")
    
    with st.spinner("Auditing financial ledgers..."):
        try:
            summary = get_outstanding_summary() or {"billed": 0, "paid": 0, "outstanding": 0}
            invs = list_invoices(doc_type="INV") or []
        except Exception as e:
            st.error(f"Financial subsystem blocked execution parameters: {str(e)}")
            summary = {"billed": 0, "paid": 0, "outstanding": 0}
            invs = []

    # Financial Scorecard Overview
    f1, f2, f3 = st.columns(3)
    f1.metric("Gross Revenue Billed", f"฿ {summary.get('billed', 0):,.2f}")
    f2.metric("Capital Liquidated (Paid)", f"฿ {summary.get('paid', 0):,.2f}")
    f3.metric("Outstanding Exposure Risk", f"฿ {summary.get('outstanding', 0):,.2f}", delta=f"฿ {summary.get('outstanding', 0):,.0f}", delta_color="inverse")

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:14px; font-weight:700; color:#F1F5F9; margin-bottom:5px;'>👥 Client Exposure & Outstanding Aging Directory</p>", unsafe_allow_html=True)

    if invs:
        df_inv = pd.DataFrame(invs)
        
        # Guard against zero data columns layout failures
        required_cols = ["customer_name", "total_amount", "paid_amount", "outstanding"]
        for col in required_cols:
            if col not in df_inv.columns:
                df_inv[col] = 0.0

        # Run multi-variable pivot aggregate operations safely
        top_exposure = df_inv.groupby("customer_name").agg({
            "total_amount": "sum",
            "paid_amount": "sum",
            "outstanding": "sum"
        }).reset_index().sort_values("outstanding", ascending=False)

        # Map semantic names for downstream corporate operations
        column_configs = {
            "customer_name": st.column_config.TextColumn("Corporate Client Identification", width="medium"),
            "total_amount": st.column_config.NumberColumn("Total Billed Portfolio", format="฿%,.2f"),
            "paid_amount": st.column_config.NumberColumn("Settled Capital", format="฿%,.2f"),
            "outstanding": st.column_config.NumberColumn("Outstanding Aging Arrears", format="฿%,.2f"),
        }

        # Excel Export Pipeline Control Interface (Using UTF-8-SIG to enforce smooth Excel parsing on Windows nodes)
        csv_payload = top_exposure.to_csv(index=False).encode('utf-8-sig')
        
        st.download_button(
            label="📥 Export Financial Exposure Ledger to Excel (CSV)",
            data=csv_payload,
            file_name=f'ar_exposure_report_{date.today().isoformat()}.csv',
            mime='text/csv',
            use_container_width=True,
            key="bi_ar_download_trigger_btn"
        )

        st.dataframe(
            top_exposure,
            use_container_width=True,
            hide_index=True,
            column_config=column_configs
        )
    else:
        st.info("ℹ️ Account general registers contain zero compiled invoice documents.")

    # =========================================================
    # SECTION 3: CRM IDENTITY DIRECTORY EXTENSION
    # =========================================================
    st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
    with st.expander("👥 Integrated Client CRM Base Metrics Overview", expanded=False):
        try:
            customers = list_customers() or []
            st.markdown(f"**Total Registered System Trading Accounts:** `{len(customers)} Corporate Entities`")
            
            if customers:
                df_cust = pd.DataFrame(customers)
                safe_crm_cols = [c for c in ["code", "name", "tax_id", "credit_limit"] if c in df_cust.columns]
                
                crm_mapping = {
                    "code": "CRM ID",
                    "name": "Registered Company Trading Title",
                    "tax_id": "Corporate Tax Identifier",
                    "credit_limit": "Approved Credit Ceiling Limit"
                }
                
                st.dataframe(
                    df_cust[safe_crm_cols].rename(columns=crm_mapping),
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Approved Credit Ceiling Limit": st.column_config.NumberColumn(format="฿%,.0f")}
                )
        except Exception as crm_ex:
            st.caption(f"CRM Indexing subsystem offline: {str(crm_ex)}")