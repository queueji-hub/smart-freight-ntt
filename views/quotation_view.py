import streamlit as st
from datetime import date, timedelta
import pandas as pd
import uuid

from config import JOB_TYPES, DEFAULT_TERMS
from managers.quotation_manager import (
    create_quotation, get_quotation_by_no, list_quotations,
    update_quotation, duplicate_quotation,
)
from managers.customer_manager import search_customers, get_customer_by_name
from managers.booking_manager import create_booking

# PDF Setup
_PDF_AVAILABLE = True
try:
    from pdf.quotation_pdf import generate_quotation_pdf
except:
    _PDF_AVAILABLE = False

def _clear_form_state(prefix):
    for k in list(st.session_state.keys()):
        if k.startswith(f"{prefix}_"):
            del st.session_state[k]

# --- CALLBACKS ---
def _on_customer_picked(prefix):
    picked = st.session_state.get(f"{prefix}_cust_pick")
    if picked:
        cust = get_customer_by_name(picked)
        if cust:
            st.session_state[f"{prefix}_attn"] = cust.get("contact_person", "")
            st.session_state[f"{prefix}_tel"] = cust.get("tel", "")

def _add_item(prefix):
    st.session_state[f"{prefix}_items_list"].append({
        "id": str(uuid.uuid4())[:8], "description": "", "currency": "USD",
        "price": 0.0, "unit": "", "remark": ""
    })

def _del_item(prefix, rid):
    items = st.session_state[f"{prefix}_items_list"]
    st.session_state[f"{prefix}_items_list"] = [i for i in items if i["id"] != rid]

# --- UI COMPONENTS ---
def _quotation_form(prefix, defaults=None):
    d = defaults or {}
    items_key = f"{prefix}_items_list"
    
    if items_key not in st.session_state:
        st.session_state[items_key] = d.get("items", []) or [{
            "id": str(uuid.uuid4())[:8], "description": "", "currency": "USD",
            "price": 0.0, "unit": "", "remark": ""
        }]

    col1, col2 = st.columns(2)
    with col1:
        job_type = st.selectbox("Job Type *", list(JOB_TYPES.keys()), key=f"{prefix}_job_type")
        
        # Customer Search
        typed = st.text_input("Customer *", value=d.get("customer_name", ""), key=f"{prefix}_cust_search")
        matches = search_customers(typed) if len(typed) >= 2 else []
        if matches:
            st.selectbox("Select Customer to Autofill", [""] + [m["company_name"] for m in matches], 
                         key=f"{prefix}_cust_pick", on_change=_on_customer_picked, args=(prefix,))
        
        attention = st.text_input("Attention", value=d.get("attention", ""), key=f"{prefix}_attn")
        tel = st.text_input("Tel.", value=d.get("tel", ""), key=f"{prefix}_tel")
        carrier = st.text_input("Carrier", value=d.get("carrier", ""), key=f"{prefix}_carrier")
        pol = st.text_input("POL", value=d.get("pol", ""), key=f"{prefix}_pol")
        pod = st.text_input("POD", value=d.get("pod", ""), key=f"{prefix}_pod")
    
    with col2:
        q_date = date.fromisoformat(d["quotation_date"]) if isinstance(d.get("quotation_date"), str) else date.today()
        v_date = date.fromisoformat(d["validity_date"]) if isinstance(d.get("validity_date"), str) else (date.today() + timedelta(days=30))
        
        quotation_date = st.date_input("Quotation Date", q_date, key=f"{prefix}_qdate")
        validity_date = st.date_input("Validity Date", v_date, key=f"{prefix}_vdate")
        payment_term = st.text_input("Payment Term", value=d.get("payment_term", ""), key=f"{prefix}_payment")
        commodity = st.text_input("Commodity", value=d.get("commodity", ""), key=f"{prefix}_commodity")
        subject = st.text_input("Subject", value=d.get("subject", ""), key=f"{prefix}_subject")

    # Items Editor
    st.markdown("### Items")
    for i, row in enumerate(st.session_state[items_key]):
        cols = st.columns([3, 1, 1, 1, 2, 0.5])
        row["description"] = cols[0].text_input("Desc", row["description"], key=f"{prefix}_desc_{i}")
        row["currency"] = cols[1].selectbox("Curr", ["USD", "THB", "CNY"], ["USD", "THB", "CNY"].index(row.get("currency", "USD")), key=f"{prefix}_cur_{i}")
        row["price"] = cols[2].number_input("Price", row["price"], key=f"{prefix}_p_{i}")
        row["unit"] = cols[3].text_input("Unit", row["unit"], key=f"{prefix}_u_{i}")
        row["remark"] = cols[4].text_input("Remark", row["remark"], key=f"{prefix}_r_{i}")
        if cols[5].button("🗑", key=f"{prefix}_del_{i}"):
            _del_item(prefix, row["id"])
            st.rerun()

    st.button("➕ Add Item", on_click=_add_item, args=(prefix,))
    terms = st.text_area("Terms & Conditions", value=d.get("terms_conditions", DEFAULT_TERMS), key=f"{prefix}_terms")

    return {
        "job_type": job_type, "customer_name": typed, "attention": attention, "tel": tel,
        "carrier": carrier, "pol": pol, "pod": pod, "quotation_date": quotation_date.isoformat(),
        "validity_date": validity_date.isoformat(), "payment_term": payment_term,
        "commodity": commodity, "subject": subject, "terms_conditions": terms
    }, pd.DataFrame(st.session_state[items_key])

# --- MAIN PAGE ---
def render():
    st.title("📄 Quotation Management")
    tab_create, tab_all = st.tabs(["➕ Create", "📋 List"])

    with tab_create:
        form_data, items_df = _quotation_form("create")
        if st.button("🚀 Generate Quotation"):
            qno = create_quotation(form_data, items_df.to_dict('records'))
            st.success(f"✅ Created {qno}")

    with tab_all:
        df = pd.DataFrame(list_quotations())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            sel_qno = st.selectbox("Select", df["quotation_no"].tolist())
            if st.button("✏️ Edit"):
                st.session_state["edit_loaded"] = sel_qno
                st.rerun()

        if "edit_loaded" in st.session_state:
            loaded = get_quotation_by_no(st.session_state["edit_loaded"])
            st.markdown(f"### Editing {loaded['quotation_no']}")
            form_data, items_df = _quotation_form("edit", defaults=loaded)
            if st.button("💾 Save"):
                update_quotation(loaded["quotation_no"], form_data, items_df.to_dict('records'))
                st.success("Updated!")
                del st.session_state["edit_loaded"]
                st.rerun()