"""
Billing / Financial module view.
Production SaaS Stable Version (FIXED)
"""

import uuid
from datetime import date, timedelta
import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.customer_manager import get_customer, list_customers
from managers.invoice_manager import (
    TAX_TYPES,
    WHT_TYPES,
    calculate_summary,
    create_invoice,
    get_outstanding_summary,
    list_invoices,
    record_payment,
)
from managers.shipment_manager import list_shipments

# =========================================================
# CONSTANTS
# =========================================================
DOC_TYPES = {
    "INV": "📄 Invoice",
    "BN": "📑 Billing Note",
    "CN": "📉 Credit Note",
    "DN": "📈 Debit Note",
    "SOA": "📊 Statement of Account",
}

# =========================================================
# STATE INIT (IMPORTANT FIX)
# =========================================================
def init_state():
    if "finance_items" not in st.session_state:
        st.session_state.finance_items = []

# =========================================================
# RENDER
# =========================================================
def render():
    init_state()

    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "billing")

    st.title("💰 Billing & Financial System")
    st.caption("Production SaaS Finance Module")

    _render_kpis()
    st.divider()

    tabs = ["📋 Documents", "💳 Payments"]
    if can_edit:
        tabs.insert(0, "➕ Create")

    tab_objs = st.tabs(tabs)

    if can_edit:
        with tab_objs[0]: _create_form(user)
        with tab_objs[1]: _list_view()
        with tab_objs[2]: _payment_view()
    else:
        with tab_objs[0]: _list_view()
        with tab_objs[1]: st.info("Read-only mode")

# =========================================================
# KPI
# =========================================================
def _render_kpis():
    summary = get_outstanding_summary()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Billed", f"฿{summary.get('billed', 0):,.2f}")
    c2.metric("Total Paid", f"฿{summary.get('paid', 0):,.2f}")
    c3.metric("Outstanding", f"฿{summary.get('outstanding', 0):,.2f}")

# =========================================================
# EMPTY ROW
# =========================================================
def _empty_row():
    return {
        "id": str(uuid.uuid4()),
        "description": "",
        "quantity": 1.0,
        "unit_price": 0.0,
        "amount": 0.0,
        "tax_type": "VAT 7%",
        "wht_type": "None",
    }

# =========================================================
# CREATE FORM (FIXED STREAMLIT SAFE)
# =========================================================
def _create_form(user):

    st.subheader("Create Invoice")

    col1, col2 = st.columns(2)

    with col1:
        doc_type = st.selectbox(
            "Document Type",
            list(DOC_TYPES.keys()),
            format_func=lambda x: DOC_TYPES[x],
            key="doc_type_select"
        )

        customers = list_customers()
        cust_options = [(0, "-- Select --")] + [(c["id"], c["company_name"]) for c in customers]

        cust_idx = st.selectbox(
            "Customer",
            range(len(cust_options)),
            format_func=lambda i: cust_options[i][1],
            key="customer_select"
        )

        cust_id, cust_name = cust_options[cust_idx]
        cust_data = get_customer(cust_id) if cust_id else {}

    with col2:
        issue_date = st.date_input("Issue Date", value=date.today(), key="issue_date")
        due_date = st.date_input(
            "Due Date",
            value=date.today() + timedelta(days=30),
            key="due_date"
        )

        currency = st.selectbox(
            "Currency",
            ["THB", "USD", "EUR"],
            key="currency_select"
        )

    # =========================================================
    # INIT ITEMS
    # =========================================================
    if len(st.session_state.finance_items) == 0:
        st.session_state.finance_items.append(_empty_row())

    st.markdown("### Items")

    # =========================================================
    # ITEMS LOOP (FIXED UNIQUE KEY)
    # =========================================================
    new_items = []

    for idx, row in enumerate(st.session_state.finance_items):

        rid = row["id"]

        c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 1, 1.5, 1.5, 1.5, 1.5, 0.5])

        row["description"] = c1.text_input(
            "desc",
            value=row["description"],
            key=f"desc_{rid}"
        )

        row["quantity"] = c2.number_input(
            "qty",
            value=float(row["quantity"]),
            key=f"qty_{rid}"
        )

        row["unit_price"] = c3.number_input(
            "price",
            value=float(row["unit_price"]),
            key=f"price_{rid}"
        )

        row["amount"] = row["quantity"] * row["unit_price"]
        c4.write(f"{row['amount']:,.2f}")

        row["tax_type"] = c5.selectbox(
            "tax",
            TAX_TYPES,
            key=f"tax_{rid}"
        )

        row["wht_type"] = c6.selectbox(
            "wht",
            WHT_TYPES,
            key=f"wht_{rid}"
        )

        if c7.button("🗑", key=f"del_{rid}"):
            continue

        new_items.append(row)

    st.session_state.finance_items = new_items

    # =========================================================
    # ADD ITEM (FIXED KEY)
    # =========================================================
    if st.button("➕ Add Item", key="add_finance_item"):
        st.session_state.finance_items.append(_empty_row())
        st.rerun()

    # =========================================================
    # SUMMARY
    # =========================================================
    summary = calculate_summary(st.session_state.finance_items)
    st.write(f"### Total: {summary['grand_total']:,.2f}")

    remark = st.text_area("Remark", key="remark")

    # =========================================================
    # SUBMIT
    # =========================================================
    if st.button("🚀 Create Invoice", type="primary", key="create_invoice_btn"):

        if cust_id == 0:
            st.error("Select customer")
            return

        doc_no = create_invoice(
            {
                "doc_type": doc_type,
                "customer_id": cust_id,
                "customer_name": cust_name,
                "issue_date": issue_date.isoformat(),
                "due_date": due_date.isoformat(),
                "currency": currency,
                "remark": remark,
                "created_by": user.get("username", "")
            },
            st.session_state.finance_items
        )

        st.success(f"Created: {doc_no}")
        st.session_state.finance_items = []
        st.rerun()

# =========================================================
# LIST VIEW (SAFE)
# =========================================================
def _list_view():
    rows = list_invoices()

    if not rows:
        st.info("No invoices")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

# =========================================================
# PAYMENT VIEW (SIMPLE SAFE)
# =========================================================
def _payment_view():
    st.subheader("Record Payment")

    rows = list_invoices()
    if not rows:
        st.info("No invoices")
        return

    options = {r["doc_no"]: r["id"] for r in rows}

    doc = st.selectbox("Invoice", list(options.keys()), key="pay_doc")
    amount = st.number_input("Amount", min_value=0.0, key="pay_amount")

    if st.button("Submit Payment", key="pay_submit"):
        record_payment(options[doc], amount)
        st.success("Payment recorded")
        st.rerun()