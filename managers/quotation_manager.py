import streamlit as st

# =========================================================
# INIT STATE
# =========================================================

def init_quotation_state():
    if "items" not in st.session_state:
        st.session_state.items = []


# =========================================================
# ADD ITEM
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

def remove_item(index: int):
    if 0 <= index < len(st.session_state.items):
        st.session_state.items.pop(index)


# =========================================================
# MAIN FORM (COPY-PASTE THIS)
# =========================================================

def _quotation_form(mode="create", defaults=None):

    init_quotation_state()

    # load defaults (edit mode)
    if defaults and mode == "edit" and not st.session_state.items:
        st.session_state.items = defaults.get("items", [])

    st.title("📦 Quotation System (Production Safe)")

    # =====================================================
    # ADD ITEM BUTTON (NO DUPLICATE BUG)
    # =====================================================
    st.button(
        "➕ Add Item",
        on_click=add_item,
        key="add_item_btn"
    )

    st.markdown("---")

    # =====================================================
    # ITEMS RENDER
    # =====================================================
    updated_items = []

    for i, item in enumerate(st.session_state.items):

        st.markdown(f"### Item {i+1}")

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

        updated_items.append({
            "description": desc,
            "currency": item.get("currency", "USD"),
            "price": price,
            "unit": item.get("unit", ""),
            "remark": item.get("remark", "")
        })

    # sync state
    st.session_state.items = updated_items

    st.markdown("---")

    # =====================================================
    # SAVE BUTTON
    # =====================================================
    submitted = st.button("💾 Save Quotation", key="save_btn")

    form_data = {
        "mode": mode,
        "job_type": "FREIGHT",
        "customer_name": "DEMO CUSTOMER"
    }

    return form_data, st.session_state.items