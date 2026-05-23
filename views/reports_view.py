import streamlit as st
import pandas as pd
from datetime import date, timedelta
from managers.shipment_manager import list_shipments
from managers.invoice_manager import list_invoices, get_outstanding_summary
from managers.customer_manager import list_customers

def render():
    st.title("📊 Reports & Analytics")
    
    # 1. Date Range
    col1, col2 = st.columns(2)
    start_date = col1.date_input("From", value=date.today() - timedelta(days=30))
    end_date = col2.date_input("To", value=date.today())
    
    # --- SHIPMENT KPIs ---
    st.subheader("🚢 Shipment Activity")
    all_ships = list_shipments()
    filtered_ships = [s for s in all_ships if start_date.isoformat() <= (s.get("created_at", "")[:10] or "") <= end_date.isoformat()]
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Jobs", len(filtered_ships))
    k2.metric("Proceed", sum(1 for s in filtered_ships if s.get("status") == "Proceed"))
    k3.metric("Finished", sum(1 for s in filtered_ships if s.get("status") == "Finished"))
    k4.metric("Closed", sum(1 for s in filtered_ships if s.get("status") == "Closed"))

    # 2. Revenue Trend (New)
    if filtered_ships:
        df = pd.DataFrame(filtered_ships)
        df['date'] = pd.to_datetime(df['created_at'])
        daily_trend = df.groupby(df['date'].dt.date).size()
        st.line_chart(daily_trend, use_container_width=True)

    st.markdown("---")
    
    # --- FINANCIAL KPIs ---
    st.subheader("💰 Financial Overview")
    summary = get_outstanding_summary()
    f1, f2, f3 = st.columns(3)
    f1.metric("Billed", f"฿{summary['billed']:,.0f}")
    f2.metric("Collected", f"฿{summary['paid']:,.0f}")
    f3.metric("Outstanding", f"฿{summary['outstanding']:,.0f}")

    # Top Customers with Download Excel
    invs = list_invoices(doc_type="INV")
    if invs:
        df_inv = pd.DataFrame(invs)
        top = df_inv.groupby("customer_name").agg({
            "total_amount": "sum", "paid_amount": "sum", "outstanding": "sum"
        }).reset_index().sort_values("outstanding", ascending=False)
        
        # 3. Add Excel Export
        st.download_button(
            label="📥 Download Report to Excel",
            data=top.to_csv(index=False).encode('utf-8'),
            file_name='top_customers_report.csv',
            mime='text/csv'
        )
        
        # แสดงตารางด้วย Highlight
        st.dataframe(top, use_container_width=True, hide_index=True, 
            column_config={
                "outstanding": st.column_config.NumberColumn("Outstanding", format="฿%.0f")
            }
        )

    # --- CUSTOMER DATABASE ---
    with st.expander("👥 Customer Database Overview"):
        customers = list_customers()
        st.write(f"Total Active Clients: {len(customers)}")
        # สามารถเพิ่มข้อมูล Credit limit ในส่วนนี้ได้