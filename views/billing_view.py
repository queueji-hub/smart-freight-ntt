"""
Billing / Financial module view
PostgreSQL Production Ready (ERP Grade)
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
    list_invoices,
    record_payment,
    get_outstanding_summary,
)
from managers.shipment_manager import list_shipments

# =========================================================
# CONFIG
# =========================================================
DOC_TYPES = {
    "INV": "📄 Invoice",
    "BN": "📑 Billing Note",
    "CN": "📉 Credit Note",
    "DN": "📈 Debit Note",
    "SOA": "📊 Statement of Account",
}

CURRENCIES = ["THB", "USD", "EUR", "CNY"]

# =========================================================
# MAIN RENDER
# =========================================================
def render():

    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "billing")

    st.title("💰 Billing & Finance")
    st.caption("PostgreSQL ERP Financial System")

    _render_kpis()
    st.divider()

    tabs = ["📋 Documents", "💳 Payments"]
    if can_edit:
        tabs.insert(0, "➕ Create")

    tab = st.tabs(tabs)

    if can_edit:
        with tab[0]:
            _create_form(user)
        with tab[1]:
            _list_view()
        with tab[2]:
            _payment_view()
    else:
        with tab[0]:
            _list_view()
        with tab[1]:
            st.info("Read-only mode")


# =========================================================
# KPI (POSTGRES SAFE)
# =========================================================
def _render_kpis():
    try:
        kpi = get_outstanding_summary() or {}
    except Exception:
        kpi = {}

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Billed", f"฿{kpi.get('billed', 0):,.2f}")
    c2.metric("Total Paid", f"฿{kpi.get('paid', 0):,.2f}")
    c3.metric("Outstanding", f"฿{kpi.get('outstanding', 0):,.2f}", delta_color="inverse")


# =========================================================
# CREATE FORM
# =========================================================
def _empty_item():
    return {
        "id": str(uuid.uuid4())[:8],
        "description": "",
        "quantity": 1,
        "unit_price": 0.0,
        "tax_type": "VAT 7%",
        "wht_type": "None",
    }


def _create_form(user):

    st.subheader("Create Invoice / Billing Document")

    col1, col2 = st.columns(2)

    # =========================
    # LEFT
    # =========================
    with col1:

        doc_type = st.selectbox(
            "Document Type",
            list(DOC_TYPES.keys()),
            format_func=lambda x: DOC_TYPES[x],
        )

        customers = list_customers() or []

        cust_options = [(0, "-- Select Customer --")] + [
            (c["id"], c.get("company_name", ""))
            for c in customers
        ]

        idx = st.selectbox(
            "Customer",
            range(len(cust_options)),
            format_func=lambda i: cust_options[i][1],
        )

        cust_id, cust_name = cust_options[idx]

        cust_data = get_customer(cust_id) if cust_id else {}
        credit_days = int(cust_data.get("credit_terms_days", 30))

        shipments = list_shipments() or []

        ship_options = [("", "-- No Shipment --")] + [
            (s.get("job_no"), f"{s.get('job_no')} — {s.get('customer_name','')}")
            for s in shipments[:100]
        ]

        ship_idx = st.selectbox(
            "Link Shipment",
            range(len(ship_options)),
            format_func=lambda i: ship_options[i][1],
        )

        job_no = ship_options[ship_idx][0]

    # =========================
    # RIGHT
    # =========================
    with col2:

        issue_date = st.date_input("Issue Date", value=date.today())
        due_date = st.date_input(
            "Due Date",
            value=date.today() + timedelta(days=credit_days),
        )

        currency = st.selectbox("Currency", CURRENCIES)
        ref_doc = st.text_input("Reference No.")

    # =====================================================
    # ITEMS (SESSION STATE SAFE)
    # =====================================================
    if "billing_items" not in st.session_state:
        st.session_state["billing_items"] = [_empty_item()]

    st.markdown("### Items")

    for item in st.session_state["billing_items"]:

        cols = st.columns([4, 1, 1.5, 1.5, 1, 0.5])

        item["description"] = cols[0].text_input(
            "desc",
            value=item["description"],
            key=f"d_{item['id']}",
            label_visibility="collapsed",
        )

        item["quantity"] = cols[1].number_input(
            "qty",
            value=float(item["quantity"]),
            key=f"q_{item['id']}",
            label_visibility="collapsed",
        )

        item["unit_price"] = cols[2].number_input(
            "price",
            value=float(item["unit_price"]),
            key=f"p_{item['id']}",
            label_visibility="collapsed",
        )

        amount = item["quantity"] * item["unit_price"]
        cols[3].write(f"{amount:,.2f}")

        item["tax_type"] = cols[4].selectbox(
            "tax",
            TAX_TYPES,
            index=TAX_TYPES.index(item["tax_type"]),
            key=f"t_{item['id']}",
            label_visibility="collapsed",
        )

        if cols[5].button("🗑", key=f"del_{item['id']}"):
            st.session_state["billing_items"].remove(item)
            st.rerun()

    if st.button("➕ Add Item"):
        st.session_state["billing_items"].append(_empty_item())
        st.rerun()

    # =====================================================
    # SUMMARY
    # =====================================================
    summary = calculate_summary(st.session_state["billing_items"])

    st.markdown(f"### 💰 Grand Total: **฿{summary.get('grand_total',0):,.2f}**")

    remark = st.text_area("Remark")

    # =====================================================
    # SUBMIT
    # =====================================================
    if st.button("🚀 Issue Invoice", type="primary"):

        if not cust_id:
            st.error("Please select customer")
            return

        try:
            doc_no = create_invoice(
                {
                    "doc_type": doc_type,
                    "job_no": job_no or None,
                    "customer_id": cust_id,
                    "customer_name": cust_name,
                    "issue_date": issue_date.isoformat(),
                    "due_date": due_date.isoformat(),
                    "currency": currency,
                    "ref_doc_no": ref_doc,
                    "remark": remark,
                    "created_by": user.get("username"),
                },
                st.session_state["billing_items"],
            )

            st.success(f"Created: {doc_no}")

            st.session_state["billing_items"] = [_empty_item()]
            st.rerun()

        except Exception as e:
            st.error(f"Error: {str(e)}")


# =========================================================
# LIST VIEW
# =========================================================
def _list_view():

    try:
        rows = list_invoices() or []
    except Exception:
        rows = []

    if not rows:
        st.info("No invoices found")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)


# =========================================================
# PAYMENT VIEW
# =========================================================
def _payment_view():

    st.subheader("💳 Record Payment")

    try:
        invoices = list_invoices() or []
    except Exception:
        invoices = []

    if not invoices:
        st.info("No invoices available")
        return

    inv_map = {f"{i['doc_no']} - {i.get('customer_name','')}": i for i in invoices}

    selected = st.selectbox("Select Invoice", list(inv_map.keys()))
    inv = inv_map[selected]

    amount = st.number_input("Payment Amount", min_value=0.0)

    method = st.selectbox("Payment Method", ["Cash", "Bank Transfer", "Cheque"])

    if st.button("Record Payment"):

        try:
            record_payment(
                {
                    "doc_no": inv["doc_no"],
                    "amount": amount,
                    "method": method,
                    "date": date.today().isoformat(),
                }
            )

            st.success("Payment recorded")
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")