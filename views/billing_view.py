"""
Billing / Financial module view.
Production-ready version

Features:
- Invoice / Billing Note / CN / DN / SOA
- Per-row VAT / Advance / WHT
- Auto financial breakdown
- Payment tracking
- PDF export
- Outstanding dashboard
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
    cancel_invoice,
    create_invoice,
    get_invoice_by_no,
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
# MAIN RENDER
# =========================================================

def render():

    user = st.session_state.get("user", {})
    role = user.get("role", "")

    can_edit = can_write(role, "billing")

    st.title("💰 Billing & Financial")
    st.caption(
        "VAT / Advance / WHT Financial System"
    )

    _render_kpis()

    st.divider()

    tabs = ["📋 Documents", "💳 Payments"]

    if can_edit:
        tabs.insert(0, "➕ Create")

    tab_objs = st.tabs(tabs)

    if can_edit:

        with tab_objs[0]:
            _create_form(user)

        with tab_objs[1]:
            _list_view()

        with tab_objs[2]:
            _payment_view()

    else:

        with tab_objs[0]:
            _list_view()

        with tab_objs[1]:
            st.info("Read-only access")


# =========================================================
# KPI
# =========================================================

def _render_kpis():

    summary = get_outstanding_summary()

    k1, k2, k3 = st.columns(3)

    with k1:
        st.metric(
            "Total Billed",
            f"฿{summary.get('billed', 0):,.2f}"
        )

    with k2:
        st.metric(
            "Total Paid",
            f"฿{summary.get('paid', 0):,.2f}"
        )

    with k3:
        st.metric(
            "Outstanding",
            f"฿{summary.get('outstanding', 0):,.2f}",
            delta_color="inverse",
        )


# =========================================================
# EMPTY ITEM
# =========================================================

def _empty_inv_row():

    return {
        "id": str(uuid.uuid4())[:8],
        "description": "",
        "quantity": 1.0,
        "unit_price": 0.0,
        "amount": 0.0,
        "tax_type": "VAT 7%",
        "wht_type": "None",
    }


# =========================================================
# CREATE FORM
# =========================================================

def _create_form(user):

    st.subheader("Create Financial Document")

    # =====================================================
    # HEADER
    # =====================================================

    col1, col2 = st.columns(2)

    with col1:

        doc_type = st.selectbox(
            "Document Type",
            options=list(DOC_TYPES.keys()),
            format_func=lambda x: DOC_TYPES[x],
        )

        customers = list_customers()

        cust_options = [
            (0, "-- Select Customer --")
        ] + [
            (c["id"], c["company_name"])
            for c in customers
        ]

        cust_idx = st.selectbox(
            "Customer",
            range(len(cust_options)),
            format_func=lambda i: cust_options[i][1],
        )

        cust_id = cust_options[cust_idx][0]

        cust_name = (
            cust_options[cust_idx][1]
            if cust_idx > 0
            else ""
        )

        cust_data = (
            get_customer(cust_id)
            if cust_id
            else None
        )

        credit_terms = (
            cust_data.get("credit_terms_days", 30)
            if cust_data
            else 30
        )

        shipments = list_shipments()

        ship_options = [
            ("", "-- No Shipment --")
        ] + [
            (
                s["job_no"],
                f"{s['job_no']} — "
                f"{s.get('customer_name', '')}"
            )
            for s in shipments[:100]
        ]

        ship_idx = st.selectbox(
            "Link Shipment",
            range(len(ship_options)),
            format_func=lambda i: ship_options[i][1],
        )

        job_no = ship_options[ship_idx][0]

    with col2:

        issue_date = st.date_input(
            "Issue Date",
            value=date.today(),
        )

        due_date = st.date_input(
            "Due Date",
            value=date.today() + timedelta(days=int(credit_terms)),
        )

        currency = st.selectbox(
            "Currency",
            ["THB", "USD", "EUR", "CNY"],
        )

        ref_doc = st.text_input(
            "Reference Doc No.",
        )

    # =====================================================
    # ITEMS
    # =====================================================

    st.divider()

    st.subheader("Line Items")

    st.caption(
        "Advance = no VAT / no WHT"
    )

    items_key = "billing_items"

    if items_key not in st.session_state:
        st.session_state[items_key] = [_empty_inv_row()]

    items = st.session_state[items_key]

    delete_row = None

    header = st.columns([
        3,
        0.8,
        1.2,
        1.2,
        1.5,
        1.2,
        0.4,
    ])

    header[0].markdown("**Description**")
    header[1].markdown("**Qty**")
    header[2].markdown("**Unit Price**")
    header[3].markdown("**Amount**")
    header[4].markdown("**VAT**")
    header[5].markdown("**WHT**")
    header[6].markdown("**Del**")

    for row in items:

        rid = row["id"]

        cols = st.columns([
            3,
            0.8,
            1.2,
            1.2,
            1.5,
            1.2,
            0.4,
        ])

        desc = cols[0].text_input(
            "desc",
            value=row["description"],
            key=f"desc_{rid}",
            label_visibility="collapsed",
        )

        qty = cols[1].number_input(
            "qty",
            value=float(row["quantity"]),
            min_value=0.0,
            step=1.0,
            key=f"qty_{rid}",
            label_visibility="collapsed",
        )

        unit = cols[2].number_input(
            "unit",
            value=float(row["unit_price"]),
            min_value=0.0,
            format="%.2f",
            key=f"unit_{rid}",
            label_visibility="collapsed",
        )

        amount = qty * unit

        cols[3].markdown(
            f"""
            <div style="
                padding-top:8px;
                text-align:right;
                font-family:monospace;
            ">
                ฿{amount:,.2f}
            </div>
            """,
            unsafe_allow_html=True,
        )

        tax_type = cols[4].selectbox(
            "tax",
            TAX_TYPES,
            index=TAX_TYPES.index(
                row.get("tax_type", "VAT 7%")
            ),
            key=f"tax_{rid}",
            label_visibility="collapsed",
        )

        wht_type = cols[5].selectbox(
            "wht",
            WHT_TYPES,
            index=WHT_TYPES.index(
                row.get("wht_type", "None")
            ),
            key=f"wht_{rid}",
            label_visibility="collapsed",
        )

        if cols[6].button(
            "🗑",
            key=f"del_{rid}",
            disabled=(len(items) <= 1),
        ):
            delete_row = rid

        row["description"] = desc
        row["quantity"] = qty
        row["unit_price"] = unit
        row["amount"] = amount
        row["tax_type"] = tax_type
        row["wht_type"] = wht_type

    # DELETE
    if delete_row:

        st.session_state[items_key] = [
            r
            for r in items
            if r["id"] != delete_row
        ]

        st.rerun()

    # ADD
    if st.button("➕ Add Item"):

        st.session_state[items_key].append(
            _empty_inv_row()
        )

        st.rerun()

    # =====================================================
    # SUMMARY
    # =====================================================

    summary = calculate_summary(items)

    sym = "฿" if currency == "THB" else f"{currency} "

    st.divider()

    st.subheader("Financial Summary")

    st.markdown(
        f"""
        <div style="
            background:#111827;
            border:1px solid #374151;
            border-radius:10px;
            padding:18px;
            font-family:monospace;
        ">

        <div style="display:flex;justify-content:space-between">
            <span>1. Total Before VAT</span>
            <span>{sym}{summary['total_before_vat']:,.2f}</span>
        </div>

        <div style="display:flex;justify-content:space-between">
            <span>2. VAT 7%</span>
            <span>{sym}{summary['total_vat_7']:,.2f}</span>
        </div>

        <div style="display:flex;justify-content:space-between;color:#C084FC">
            <span>3. Advance</span>
            <span>{sym}{summary['total_advance']:,.2f}</span>
        </div>

        <hr>

        <div style="display:flex;justify-content:space-between">
            <span>4. Before WHT</span>
            <span>{sym}{summary['total_before_wht']:,.2f}</span>
        </div>

        <div style="display:flex;justify-content:space-between;color:#F87171">
            <span>5. WHT 1%</span>
            <span>-{sym}{summary['wht_1_amount']:,.2f}</span>
        </div>

        <div style="display:flex;justify-content:space-between;color:#F87171">
            <span>6. WHT 3%</span>
            <span>-{sym}{summary['wht_3_amount']:,.2f}</span>
        </div>

        <hr>

        <div style="
            display:flex;
            justify-content:space-between;
            font-size:1.3rem;
            font-weight:700;
            color:#4ADE80;
        ">
            <span>7. GRAND TOTAL</span>
            <span>{sym}{summary['grand_total']:,.2f}</span>
        </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # REMARK
    # =====================================================

    remark = st.text_area(
        "Remark",
        height=100,
    )

    # =====================================================
    # SUBMIT
    # =====================================================

    if st.button(
        "🚀 Issue Document",
        type="primary",
        use_container_width=True,
    ):

        valid_items = [
            i
            for i in items
            if i["description"].strip()
        ]

        if cust_id == 0:

            st.error("Please select customer")
            return

        if not valid_items:

            st.error("Please add line items")
            return

        try:

            doc_no = create_invoice(
                {
                    "doc_type": doc_type,
                    "shipment_id": None,
                    "job_no": job_no or None,
                    "customer_id": cust_id,
                    "customer_name": cust_name,
                    "issue_date": issue_date.isoformat(),
                    "due_date": due_date.isoformat(),
                    "currency": currency,
                    "ref_doc_no": ref_doc,
                    "remark": remark,
                    "credit_terms_days": int(credit_terms),
                    "created_by": user.get("username", ""),
                },
                valid_items,
            )

            st.success(
                f"✅ Document Created : {doc_no}"
            )

            del st.session_state[items_key]

            st.rerun()

        except Exception as ex:

            st.error(f"Create failed : {ex}")


# =========================================================
# LIST VIEW
# =========================================================

def _list_view():

    st.subheader("Financial Documents")

    f1, f2, f3 = st.columns(3)

    with f1:

        filter_type = st.selectbox(
            "Document Type",
            ["All"] + list(DOC_TYPES.keys()),
            format_func=lambda x:
            "All"
            if x == "All"
            else DOC_TYPES[x],
        )

    with f2:

        filter_status = st.selectbox(
            "Payment Status",
            [
                "All",
                "Unpaid",
                "Partial",
                "Paid",
                "Cancelled",
            ],
        )

    with f3:

        st.write("")
        st.write("")

        st.button(
            "🔄 Refresh",
            use_container_width=True,
        )

    rows = list_invoices(
        doc_type=None
        if filter_type == "All"
        else filter_type,

        payment_status=None
        if filter_status == "All"
        else filter_status,
    )

    if not rows:

        st.info("No document found")
        return

    df = pd.DataFrame(rows)

    cols = [
        "doc_no",
        "doc_type",
        "customer_name",
        "issue_date",
        "due_date",
        "total_amount",
        "paid_amount",
        "outstanding",
        "payment_status",
    ]

    cols = [
        c
        for c in cols
        if c in df.columns
    ]

    st.dataframe(
        df[cols],
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config={
            "total_amount":
                st.column_config.NumberColumn(
                    "Total",
                    format="฿%.2f",
                ),

            "paid_amount":
                st.column_config.NumberColumn(
                    "Paid",
                    format="฿%.2f",
                ),

            "outstanding":
                st.column_config.NumberColumn(
                    "Outstanding",
                    format="฿%.2f",
                ),
        },
    )

    # CSV
    csv = df[cols].to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "📥 Export CSV",
        data=csv,
        file_name="billing_export.csv",
        mime="text/csv",
    )

    st.divider()

    # PDF
    st.subheader("Generate PDF")

    options = [r["doc_no"] for r in rows]

    selected_doc = st.selectbox(
        "Select Document",
        options,
    )

    if st.button(
        "📥 Generate PDF",
        type="primary",
    ):

        try:

            from pdf.invoice_pdf import (
                generate_invoice_pdf
            )

            inv = get_invoice_by_no(
                selected_doc
            )

            cust = (
                get_customer(
                    inv.get("customer_id")
                )
                if inv.get("customer_id")
                else None
            )

            pdf_path = generate_invoice_pdf(
                inv,
                customer=cust,
            )

            with open(pdf_path, "rb") as f:

                st.download_button(
                    f"📥 Download {selected_doc}.pdf",
                    f.read(),
                    file_name=f"{selected_doc}.pdf",
                    mime="application/pdf",
                )

            st.success(
                f"PDF generated : {selected_doc}"
            )

        except Exception as ex:

            st.error(
                f"PDF failed : {ex}"
            )


# =========================================================
# PAYMENT VIEW
# =========================================================

def _payment_view():

    st.subheader("Record Payment")

    unpaid = (
        list_invoices(
            doc_type="INV",
            payment_status="Unpaid",
        )
        +
        list_invoices(
            doc_type="INV",
            payment_status="Partial",
        )
    )

    if not unpaid:

        st.info("No unpaid invoice")
        return

    options = [
        (
            i["doc_no"],
            f"{i['doc_no']} — "
            f"{i.get('customer_name', '')} "
            f"(Outstanding: "
            f"฿{i.get('outstanding', 0):,.2f})"
        )
        for i in unpaid
    ]

    idx = st.selectbox(
        "Select Invoice",
        range(len(options)),
        format_func=lambda i:
        options[i][1],
    )

    selected = unpaid[idx]

    c1, c2 = st.columns(2)

    with c1:

        amount = st.number_input(
            "Payment Amount",
            min_value=0.01,
            value=float(
                selected.get(
                    "outstanding",
                    0
                )
            ),
            format="%.2f",
        )

    with c2:

        pay_date = st.date_input(
            "Payment Date",
            value=date.today(),
        )

    if st.button(
        "💳 Record Payment",
        type="primary",
    ):

        ok = record_payment(
            selected["doc_no"],
            amount,
            pay_date.isoformat(),
        )

        if ok:

            st.success(
                f"Payment recorded : "
                f"฿{amount:,.2f}"
            )

            st.rerun()

        else:

            st.error(
                "Failed to record payment"
            )