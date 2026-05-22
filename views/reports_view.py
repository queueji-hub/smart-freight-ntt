"""Reports & Analytics view."""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from managers.shipment_manager import list_shipments
from managers.invoice_manager import list_invoices, get_outstanding_summary
from managers.customer_manager import list_customers


def render():
    st.title("📊 Reports & Analytics")
    st.caption("Monthly performance · Revenue · Customer activity")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From",
            value=date.today() - timedelta(days=30), key="rep_start")
    with col2:
        end_date = st.date_input("To", value=date.today(), key="rep_end")
    
    st.markdown("---")
    
    # ===== SHIPMENT KPIs =====
    st.subheader("🚢 Shipment Activity")
    all_ships = list_shipments()
    
    # Filter by date
    filtered_ships = []
    for s in all_ships:
        created = s.get("created_at", "")[:10]
        if start_date.isoformat() <= created <= end_date.isoformat():
            filtered_ships.append(s)
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Jobs", len(filtered_ships))
    with k2:
        proceed = sum(1 for s in filtered_ships if s.get("status") == "Proceed")
        st.metric("Proceed", proceed)
    with k3:
        finished = sum(1 for s in filtered_ships if s.get("status") == "Finished")
        st.metric("Finished", finished)
    with k4:
        closed = sum(1 for s in filtered_ships if s.get("status") == "Closed")
        st.metric("Closed", closed)
    
    # Job type breakdown
    if filtered_ships:
        df = pd.DataFrame(filtered_ships)
        if "job_type" in df.columns:
            type_counts = df["job_type"].value_counts().reset_index()
            type_counts.columns = ["Job Type", "Count"]
            st.bar_chart(type_counts.set_index("Job Type"))
    
    st.markdown("---")
    
    # ===== FINANCIAL KPIs =====
    st.subheader("💰 Financial Overview")
    summary = get_outstanding_summary()
    
    f1, f2, f3 = st.columns(3)
    with f1:
        st.metric("Total Billed (All Time)", f"฿{summary['billed']:,.0f}")
    with f2:
        st.metric("Total Collected", f"฿{summary['paid']:,.0f}")
    with f3:
        st.metric("Outstanding", f"฿{summary['outstanding']:,.0f}",
                  delta_color="inverse")
    
    # Top customers
    st.markdown("##### Top Customers by Revenue")
    invs = list_invoices(doc_type="INV")
    if invs:
        df_inv = pd.DataFrame(invs)
        if "customer_name" in df_inv.columns:
            top = df_inv.groupby("customer_name").agg(
                total=("total_amount", "sum"),
                paid=("paid_amount", "sum"),
                outstanding=("outstanding", "sum"),
                invoices=("id", "count"),
            ).reset_index().sort_values("total", ascending=False).head(10)
            st.dataframe(top, use_container_width=True, hide_index=True,
                column_config={
                    "customer_name": "Customer",
                    "total": st.column_config.NumberColumn("Total Billed",
                                                            format="฿%.0f"),
                    "paid": st.column_config.NumberColumn("Paid", format="฿%.0f"),
                    "outstanding": st.column_config.NumberColumn(
                        "Outstanding", format="฿%.0f"),
                    "invoices": "Invoices",
                })
    else:
        st.info("No invoices yet.")
    
    st.markdown("---")
    
    # ===== CUSTOMER STATS =====
    st.subheader("👥 Customer Database")
    customers = list_customers()
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Active Customers", len(customers))
    with c2:
        avg_credit = sum(c.get("credit_terms_days", 30) for c in customers) / max(len(customers), 1)
        st.metric("Avg Credit Terms", f"{avg_credit:.0f} days")
