"""
Billing / Financial Module View
PostgreSQL Production Ready (ERP Grade)
"""

import uuid
from datetime import date, timedelta
from typing import Dict, Any, List

import pandas as pd
import streamlit as st

# Import Backend Managers (คงไว้ตามโครงสร้างระบบเดิมของคุณ)
from managers.auth_manager import can_write
from managers.customer_manager import get_customer, list_customers
from managers.invoice_manager import (
    TAX_TYPES,
    WHT_TYPES,
    calculate_summary,
    create_invoice,
    list_invoices,
    record_payment,
    get_outstanding_summary,
)
from managers.shipment_manager import list_shipments

# =========================================================
# CONFIGURATION & CONSTANTS
# =========================================================
DOC_TYPES: Dict[str, str] = {
    "INV": "📄 Invoice",
    "BN": "📑 Billing Note",
    "CN": "📉 Credit Note",
    "DN": "📈 Debit Note",
    "SOA": "📊 Statement of Account",
}

CURRENCIES: List[str] = ["THB", "USD", "EUR", "CNY"]
PAYMENT_METHODS: List[str] = ["Bank Transfer", "Cash", "Cheque", "Credit Card"]

# =========================================================
# MAIN RENDER
# =========================================================
def render() -> None:
    """Main rendering function for Billing & Finance module."""
    user: Dict[str, Any] = st.session_state.get("user", {})
    role: str = user.get("role", "")
    can_edit: bool = can_write(role, "billing")

    st.title("💰 Billing & Finance")
    st.caption("Enterprise Resource Planning (ERP) - Financial Module")

    _render_kpis()
    st.divider()

    # Dynamic Tabs based on permissions
    tabs: List[str] = ["📋 Documents", "💳 Payments"]
    if can_edit:
        tabs.insert(0, "➕ Create Document")

    tab_instances = st.tabs(tabs)

    if can_edit:
        with tab_instances[0]:
            _create_form(user)
        with tab_instances[1]:
            _list_view()
        with tab_instances[2]:
            _payment_view()
    else:
        with tab_instances[0]:
            _list_view()
        with tab_instances[1]:
            st.info("🔒 Read-only mode: You do not have permission to create or edit financial documents.")

# =========================================================
# KPI DASHBOARD
# =========================================================
def _render_kpis() -> None:
    """Renders Key Performance Indicators with safe error handling."""
    try:
        kpi = get_outstanding_summary() or {}
    except Exception as e:
        st.warning(f"Unable to load KPIs. Database connection issue: {e}")
        kpi = {}

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Billed", f"฿ {kpi.get('billed', 0.0):,.2f}")
    c2.metric("Total Paid", f"฿ {kpi.get('paid', 0.0):,.2f}")
    c3.metric(
        "Outstanding", 
        f"฿ {kpi.get('outstanding', 0.0):,.2f}", 
        delta="Action Required" if kpi.get('outstanding', 0) > 0 else "All Cleared",
        delta_color="inverse" if kpi.get('outstanding', 0) > 0 else "normal"
    )

# =========================================================
# CREATE FORM
# =========================================================
def _empty_item() -> Dict[str, Any]:
    """Generates an empty billing item with a unique ID."""
    return {
        "id": str(uuid.uuid4())[:8],
        "description": "",
        "quantity": 1.0,
        "unit_price": 0.0,
        "tax_type": TAX_TYPES[0] if TAX_TYPES else "VAT 7%",
        "wht_type": WHT_TYPES[0] if WHT_TYPES else "None",
    }

def _create_form(user: Dict[str, Any]) -> None:
    """Renders the robust form for creating financial documents."""
    st.subheader("Create Financial Document")

    col1, col2 = st.columns(2)

    with col1:
        doc_type = st.selectbox(
            "Document Type",
            options=list(DOC_TYPES.keys()),
            format_func=lambda x: DOC_TYPES[x],
            help="Select the type of financial document to generate."
        )

        try:
            customers = list_customers() or []
        except Exception:
            customers = []
            st.error("Failed to load customers from database.")

        cust_options = [(0, "-- Select Customer --")] + [
            (c.get("id"), c.get("company_name", "Unknown")) for c in customers
        ]

        idx = st.selectbox(
            "Customer",
            range(len(cust_options)),
            format_func=lambda i: cust_options[i][1],
        )
        cust_id, cust_name = cust_options[idx]

        # Auto-calculate credit terms safely
        credit_days = 30
        if cust_id:
            try:
                cust_data = get_customer(cust_id) or {}
                credit_days = int(cust_data.get("credit_terms_days", 30))
            except Exception:
                pass

        try:
            shipments = list_shipments() or []
        except Exception:
            shipments = []
            
        ship_options = [("", "-- No Linked Shipment --")] + [
            (s.get("job_no"), f"{s.get('job_no')} — {s.get('customer_name', 'Unknown')}")
            for s in shipments[:200]  # Expanded for better ERP capability
        ]

        ship_idx = st.selectbox(
            "Link Shipment (Optional)",
            range(len(ship_options)),
            format_func=lambda i: ship_options[i][1],
        )
        job_no = ship_options[ship_idx][0]

    with col2:
        issue_date = st.date_input("Issue Date", value=date.today())
        due_date = st.date_input("Due Date", value=date.today() + timedelta(days=credit_days))
        currency = st.selectbox("Currency", CURRENCIES)
        ref_doc = st.text_input("Reference No.", placeholder="e.g., PO-2023-001")

    st.divider()

    # --- ITEM MANAGEMENT (STATE SAFE) ---
    if "billing_items" not in st.session_state:
        st.session_state["billing_items"] = [_empty_item()]

    st.markdown("### Line Items")

    # Header row for structural alignment
    header_cols = st.columns([4, 1, 1.5, 1.5, 1.5, 0.5])
    header_cols[0].write("**Description**")
    header_cols[1].write("**Qty**")
    header_cols[2].write("**Unit Price**")
    header_cols[3].write("**Amount**")
    header_cols[4].write("**Tax**")

    items_to_remove = []

    for i, item in enumerate(st.session_state["billing_items"]):
        cols = st.columns([4, 1, 1.5, 1.5, 1.5, 0.5])

        item["description"] = cols[0].text_input(
            "desc",
            value=item["description"],
            key=f"d_{item['id']}",
            label_visibility="collapsed",
            placeholder="Item description..."
        )

        item["quantity"] = cols[1].number_input(
            "qty",
            value=float(item["quantity"]),
            min_value=0.01,
            step=1.0,
            key=f"q_{item['id']}",
            label_visibility="collapsed",
        )

        item["unit_price"] = cols[2].number_input(
            "price",
            value=float(item["unit_price"]),
            min_value=0.0,
            step=100.0,
            key=f"p_{item['id']}",
            label_visibility="collapsed",
        )

        amount = item["quantity"] * item["unit_price"]
        cols[3].markdown(f"<div style='padding-top: 8px;'>{amount:,.2f}</div>", unsafe_allow_html=True)

        item["tax_type"] = cols[4].selectbox(
            "tax",
            TAX_TYPES,
            index=TAX_TYPES.index(item["tax_type"]) if item["tax_type"] in TAX_TYPES else 0,
            key=f"t_{item['id']}",
            label_visibility="collapsed",
        )

        if cols[5].button("🗑️", key=f"del_{item['id']}", help="Remove item"):
            items_to_remove.append(item)

    # Clean up removed items cleanly to avoid Streamlit exception
    if items_to_remove:
        for item in items_to_remove:
            st.session_state["billing_items"].remove(item)
        st.rerun()

    if st.button("➕ Add Line Item"):
        st.session_state["billing_items"].append(_empty_item())
        st.rerun()

    st.divider()

    # --- SUMMARY & SUBMIT ---
    try:
        summary = calculate_summary(st.session_state["billing_items"])
    except Exception:
        summary = {"grand_total": 0.0}

    col_sum1, col_sum2 = st.columns([3, 1])
    with col_sum1:
        remark = st.text_area("Remarks / Notes", placeholder="Additional information for the customer...")
    
    with col_sum2:
        st.markdown(f"### 💰 Total: **{summary.get('grand_total', 0):,.2f} {currency}**")
        
        if st.button("🚀 Issue Document", type="primary", use_container_width=True):
            if not cust_id:
                st.error("⚠️ Please select a customer before issuing the document.")
                return
            if not st.session_state["billing_items"] or not st.session_state["billing_items"][0]["description"]:
                st.error("⚠️ Please add at least one valid line item.")
                return

            with st.spinner("Processing transaction..."):
                try:
                    payload = {
                        "doc_type": doc_type,
                        "job_no": job_no or None,
                        "customer_id": cust_id,
                        "customer_name": cust_name,
                        "issue_date": issue_date.isoformat(),
                        "due_date": due_date.isoformat(),
                        "currency": currency,
                        "ref_doc_no": ref_doc.strip(),
                        "remark": remark.strip(),
                        "created_by": user.get("username", "System"),
                        "status": "DRAFT", # Enforce default ERP workflow state
                    }
                    doc_no = create_invoice(payload, st.session_state["billing_items"])
                    
                    st.success(f"✅ Successfully created document: {doc_no}")
                    st.session_state["billing_items"] = [_empty_item()] # Reset state
                    st.rerun()

                except Exception as e:
                    st.error(f"🚨 Database Error: {str(e)}")

# =========================================================
# LIST VIEW (DATA GRID)
# =========================================================
def _list_view() -> None:
    """Renders the historical documents with ERP-grade filtering and formatting."""
    st.subheader("📋 Document History")

    try:
        rows = list_invoices() or []
    except Exception as e:
        st.error(f"Failed to fetch invoices: {e}")
        rows = []

    if not rows:
        st.info("No documents found in the system.")
        return

    df = pd.DataFrame(rows)

    # Simple & Fast Filters
    col_f1, col_f2 = st.columns(2)
    search_term = col_f1.text_input("🔍 Search Customer or Doc No.")
    status_filter = col_f2.selectbox("Status Filter", ["All", "DRAFT", "ISSUED", "PAID", "CANCELLED"])

    if search_term:
        df = df[df.apply(lambda row: search_term.lower() in str(row).lower(), axis=1)]
    
    if status_filter != "All" and "status" in df.columns:
        df = df[df["status"].str.upper() == status_filter]

    # Enterprise-grade grid presentation
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "doc_no": st.column_config.TextColumn("Document No.", width="medium"),
            "customer_name": st.column_config.TextColumn("Customer Name", width="large"),
            "issue_date": st.column_config.DateColumn("Issue Date", format="YYYY-MM-DD"),
            "due_date": st.column_config.DateColumn("Due Date", format="YYYY-MM-DD"),
            "grand_total": st.column_config.NumberColumn("Total", format="%.2f"),
            "status": st.column_config.TextColumn("Status"),
        }
    )

# =========================================================
# PAYMENT VIEW
# =========================================================
def _payment_view() -> None:
    """Renders the payment recording interface."""
    st.subheader("💳 Record Payment Receipt")

    try:
        invoices = list_invoices() or []
        # Filter logic assuming backend passes status
        unpaid_invoices = [i for i in invoices if i.get("status", "").upper() != "PAID"]
    except Exception:
        unpaid_invoices = []

    if not unpaid_invoices:
        st.info("✅ No outstanding invoices available for payment.")
        return

    # Create mapping for dropdown 
    inv_map = {f"{i['doc_no']} | {i.get('customer_name', 'Unknown')} | {i.get('grand_total', 0):,.2f} {i.get('currency', 'THB')}": i for i in unpaid_invoices}

    selected = st.selectbox("Select Outstanding Invoice", list(inv_map.keys()))
    inv = inv_map[selected]

    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("Payment Amount", min_value=0.01, value=float(inv.get("grand_total", 0.0)), step=100.0)
    with col2:
        method = st.selectbox("Payment Method", PAYMENT_METHODS)
        
    payment_ref = st.text_input("Transaction / Cheque Reference", placeholder="e.g., TXN-998231")
    payment_date = st.date_input("Payment Date", value=date.today())

    if st.button("Confirm Payment", type="primary"):
        with st.spinner("Recording payment..."):
            try:
                record_payment({
                    "doc_no": inv["doc_no"],
                    "amount": amount,
                    "method": method,
                    "reference": payment_ref.strip(),
                    "date": payment_date.isoformat(),
                })
                st.success(f"✅ Payment of {amount:,.2f} recorded for {inv['doc_no']}.")
                st.rerun()

            except Exception as e:
                st.error(f"🚨 Failed to record payment: {e}")