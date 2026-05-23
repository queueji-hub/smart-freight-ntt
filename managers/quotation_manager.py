import streamlit as st
from datetime import datetime
from io import BytesIO
from managers.quotation_number import generate_quotation_number
from managers.quotation_persistence import save_quotation
from core.audit import log_action


# =========================================================
# STATE INIT (SESSION SAFE)
# =========================================================

def init_state():

    if "quotation_items" not in st.session_state:
        st.session_state["quotation_items"] = []

    if "quotation_draft" not in st.session_state:
        st.session_state["quotation_draft"] = {
            "job_type": "FREIGHT",
            "customer_name": ""
        }


# =========================================================
# ITEM OPERATIONS
# =========================================================

def add_item():
    st.session_state["quotation_items"].append({
        "description": "",
        "currency": "USD",
        "price": 0.0,
        "unit": "",
        "remark": ""
    })


def remove_item(index: int):
    if 0 <= index < len(st.session_state["quotation_items"]):
        st.session_state["quotation_items"].pop(index)


# =========================================================
# CALCULATE TOTAL
# =========================================================

def calculate_total(items):
    return sum(float(i.get("price", 0)) for i in items)


# =========================================================
# SIMPLE PDF (MIGRATION READY)
# =========================================================

def generate_pdf(data, items):

    content = []
    content.append("QUOTATION")
    content.append("=" * 50)
    content.append(f"Quotation No: {data.get('quotation_no', '-')}")
    content.append(f"Customer: {data.get('customer_name')}")
    content.append(f"Job Type: {data.get('job_type')}")
    content.append(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    content.append("\nITEMS\n")

    for i, item in enumerate(items, 1):
        content.append(
            f"{i}. {item['description']} | {item['price']} {item['currency']}"
        )

    content.append("\n")
    content.append(f"TOTAL: {calculate_total(items)}")

    return "\n".join(content).encode("utf-8")


# =========================================================
# MAIN UI (PRODUCTION SAFE)
# =========================================================

def render_quotation_form(mode="create", defaults=None):

    init_state()

    # =========================
    # LOAD EDIT DATA SAFELY
    # =========================
    if mode == "edit" and defaults:

        if not st.session_state["quotation_items"]:
            st.session_state["quotation_items"] = defaults.get("items", [])

        st.session_state["quotation_draft"] = {
            "job_type": defaults.get("job_type", "FREIGHT"),
            "customer_name": defaults.get("customer_name", "")
        }

    st.title("📦 Quotation System (SaaS Production)")

    # =========================
    # ADD ITEM BUTTON (FIX DUPLICATE)
    # =========================
    st.button(
        "➕ Add Item",
        on_click=add_item,
        key=f"add_item_{id(st.session_state)}"
    )

    st.markdown("---")

    # =========================
    # ITEMS UI
    # =========================
    updated_items = []

    for i, item in enumerate(st.session_state["quotation_items"]):

        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            desc = st.text_input(
                "Description",
                value=item.get("description", ""),
                key=f"desc_{i}_{mode}"
            )

        with col2:
            price = st.number_input(
                "Price",
                value=float(item.get("price", 0)),
                key=f"price_{i}_{mode}"
            )

        with col3:
            if st.button("🗑️", key=f"del_{i}_{mode}"):
                remove_item(i)
                st.rerun()

        updated_items.append({
            "description": desc,
            "currency": item.get("currency", "USD"),
            "price": price,
            "unit": item.get("unit", ""),
            "remark": item.get("remark", "")
        })

    st.session_state["quotation_items"] = updated_items

    st.markdown("---")

    # =========================
    # FORM DATA
    # =========================
    form_data = st.session_state["quotation_draft"]

    # =========================
    # SAVE QUOTATION (CORE FLOW)
    # =========================
    if st.button("💾 Save Quotation", key=f"save_{mode}"):

        quotation_no = generate_quotation_number(
            form_data.get("job_type"),
            datetime.now()
        )

        form_data["quotation_no"] = quotation_no

        save_quotation(form_data, updated_items)

        log_action(
            user_id=1,
            tenant_id="demo",
            entity="quotation",
            entity_id=quotation_no,
            action="CREATE"
        )

        st.success(f"Saved: {quotation_no}")

    # =========================
    # PDF EXPORT
    # =========================
    pdf_bytes = generate_pdf(form_data, updated_items)

    st.download_button(
        label="📄 Download Quotation",
        data=pdf_bytes,
        file_name=f"quotation_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
        key=f"pdf_{mode}"
    )

    return form_data, updated_items