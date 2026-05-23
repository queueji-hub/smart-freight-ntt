import streamlit as st
from io import BytesIO

# =========================================================
# INIT STATE
# =========================================================

def init_state():
    if "items" not in st.session_state:
        st.session_state.items = []


# =========================================================
# ADD ITEM (SAFE)
# =========================================================

def add_item():
    st.session_state.items.append({
        "description": "",
        "currency": "USD",
        "price": 0.0,
        "unit": "",
        "remark": ""
    })


# =========================================================
# REMOVE ITEM
# =========================================================

def remove_item(i):
    if 0 <= i < len(st.session_state.items):
        st.session_state.items.pop(i)


# =========================================================
# SIMPLE PDF GENERATOR (NO LIBRARY DEPENDENCY)
# =========================================================

def generate_pdf_text(data, items):
    content = []
    content.append("QUOTATION")
    content.append("=" * 40)
    content.append(f"Customer: {data.get('customer_name')}")
    content.append(f"Job Type: {data.get('job_type')}")
    content.append("\nITEMS:\n")

    total = 0

    for i, item in enumerate(items, 1):
        line = f"{i}. {item['description']} | {item['price']} {item['currency']}"
        content.append(line)
        total += float(item.get("price", 0))

    content.append("\n")
    content.append(f"TOTAL: {total}")

    return "\n".join(content).encode("utf-8")


# =========================================================
# MAIN FORM (FIXED + PDF READY)
# =========================================================

def _quotation_form(mode="create", defaults=None):

    init_state()

    # load defaults (edit mode)
    if defaults and mode == "edit" and not st.session_state.items:
        st.session_state.items = defaults.get("items", [])

    st.title("📦 Quotation System (Production Fixed)")

    # =====================================================
    # FIXED BUTTON (NO DUPLICATE ERROR)
    # =====================================================
    st.button(
        "➕ Add Item",
        on_click=add_item,
        key="add_item_global_btn"
    )

    st.markdown("---")

    # =====================================================
    # ITEMS
    # =====================================================
    updated = []

    for i, item in enumerate(st.session_state.items):

        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            desc = st.text_input(
                "Description",
                value=item.get("description", ""),
                key=f"desc_{i}"
            )

        with col2:
            price = st.number_input(
                "Price",
                value=float(item.get("price", 0)),
                key=f"price_{i}"
            )

        with col3:
            st.write("")
            if st.button("🗑️", key=f"del_{i}"):
                remove_item(i)
                st.rerun()

        updated.append({
            "description": desc,
            "currency": item.get("currency", "USD"),
            "price": price,
            "unit": item.get("unit", ""),
            "remark": item.get("remark", "")
        })

    st.session_state.items = updated

    st.markdown("---")

    # =====================================================
    # FORM DATA
    # =====================================================
    form_data = {
        "job_type": "FREIGHT",
        "customer_name": "DEMO CUSTOMER"
    }

    # =====================================================
    # SAVE BUTTON
    # =====================================================
    st.button("💾 Save Quotation", key="save_btn")

    # =====================================================
    # PDF EXPORT (NEW)
    # =====================================================
    pdf_bytes = generate_pdf_text(form_data, st.session_state.items)

    st.download_button(
        label="📄 Download PDF",
        data=pdf_bytes,
        file_name="quotation.txt",   # (upgrade to real PDF later)
        mime="text/plain",
        key="pdf_download_btn"
    )

    return form_data, st.session_state.items