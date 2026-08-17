import streamlit as st
from core.state import init_state, add_item, remove_item
from services.quotation_service import create_quotation
from pdf.quotation_pdf import generate_quotation_pdf as generate_pdf


def render():

    init_state()

    st.title("📦 SaaS Quotation System")

    # ======================
    # ADD ITEM
    # ======================
    if st.button("➕ Add Item", key="add_item"):
        add_item({
            "description": "",
            "price": 0,
            "currency": "USD"
        })

    st.divider()

    state = st.session_state.quotation

    updated = []

    for i, item in enumerate(state["items"]):

        col1, col2, col3 = st.columns([3,2,1])

        with col1:
            item["description"] = st.text_input(
                "Description",
                value=item["description"],
                key=f"d_{i}"
            )

        with col2:
            item["price"] = st.number_input(
                "Price",
                value=float(item["price"]),
                key=f"p_{i}"
            )

        with col3:
            if st.button("🗑️", key=f"del_{i}"):
                remove_item(i)
                st.rerun()

        updated.append(item)

    state["items"] = updated

    st.divider()

    # ======================
    # SAVE
    # ======================
    if st.button("💾 Save Quotation", key="save"):

        form = {
            "job_type": "FREIGHT",
            "customer_name": "DEMO"
        }

        qid = create_quotation(form)

        st.success(f"Saved Quotation ID: {qid}")

    # ======================
    # PDF EXPORT (REAL)
    # ======================
    if st.button("📄 Export PDF", key="pdf"):

        pdf = generate_pdf(state)

        st.download_button(
            "Download PDF",
            data=pdf,
            file_name="quotation.pdf",
            mime="application/pdf"
        )