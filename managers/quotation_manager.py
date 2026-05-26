"""
Quotation System Module
PostgreSQL Ready & Streamlit Professional UX Optimization
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import streamlit as st

# Import Backend Managers (คงตามโครงสร้างสถาปัตยกรรมระบบเดิมของคุณ)
from managers.quotation_number import generate_quotation_number
from managers.quotation_persistence import save_quotation
from core.audit import log_action

# =========================================================
# CONFIGURATION & CONSTANTS
# =========================================================
JOB_TYPES: Dict[str, str] = {
    "FREIGHT": "🚢 Ocean/Air Freight",
    "TRUCKING": "🚛 Inland Trucking",
    "CUSTOMS": "🛃 Customs Clearance",
    "WAREHOUSE": "🏬 Warehouse & Logistics"
}

CURRENCIES: List[str] = ["USD", "THB", "EUR", "CNY", "SGD"]
UNIT_TYPES: List[str] = ["CBM", "KGS", "BL", "CONTAINER", "TRIP", "SHPMT", "PCS"]

# =========================================================
# STATE INITIALIZATION
# =========================================================
def init_state() -> None:
    """Initializes session states safely preventing data loss on reruns."""
    if "quotation_items" not in st.session_state:
        st.session_state["quotation_items"] = []
    if "quotation_draft" not in st.session_state:
        st.session_state["quotation_draft"] = {
            "job_type": "FREIGHT",
            "customer_name": "",
            "currency": "USD",
            "remark": ""
        }

def _empty_item() -> Dict[str, Any]:
    """Returns a schema-compliant empty line item row."""
    return {
        "id": str(uuid.uuid4())[:8],
        "description": "",
        "currency": st.session_state.get("quotation_draft", {}).get("currency", "USD"),
        "price": 0.0,
        "unit": "SHPMT",
        "remark": ""
    }

# =========================================================
# CALCULATION CALCULATOR
# =========================================================
def calculate_total(items: List[Dict[str, Any]]) -> float:
    """Calculates cumulative monetary volume of provided items."""
    return sum(float(i.get("price", 0.0)) for i in items)

# =========================================================
# EXPORT PRESENTATION GENERATOR
# =========================================================
def generate_pdf(data: Dict[str, Any], items: List[Dict[str, Any]]) -> bytes:
    """Generates formal commercial structural plaintext summary layout."""
    content = []
    content.append("==================================================")
    content.append("                COMMERCIAL QUOTATION              ")
    content.append("==================================================")
    content.append(f"Quotation No : {data.get('quotation_no', 'DRAFT')}")
    content.append(f"Date         : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    content.append(f"Customer     : {data.get('customer_name', 'N/A')}")
    content.append(f"Operation Type: {JOB_TYPES.get(data.get('job_type', 'FREIGHT'), 'Freight')}")
    content.append("--------------------------------------------------")
    content.append(f"{"LN":<3} | {"Description":<25} | {"Unit":<10} | {"Amount":<10}")
    content.append("--------------------------------------------------")
    
    for idx, item in enumerate(items, 1):
        desc = item.get('description', '')[:25]
        content.append(
            f"{idx:<3} | {desc:<25} | {item.get('unit', ''):<10} | {item.get('price', 0.0):>10,.2f}"
        )
        
    content.append("--------------------------------------------------")
    content.append(f"TOTAL AMOUNT ({data.get('currency', 'USD')}): {calculate_total(items):>27,.2f}")
    if data.get("remark"):
        content.append(f"\nNotes/Remarks: {data.get('remark')}")
    content.append("==================================================")
    
    return "\n".join(content).encode("utf-8")

# =========================================================
# CORE RENDER COMPONENT (PRODUCTION SAFE)
# =========================================================
def render_quotation_form(mode: str = "create", defaults: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Renders highly responsive interactive executive level Form Workspace."""
    init_state()

    # --- DEFAULTS HYDRATION MIGRATION SAFE ---
    if mode == "edit" and defaults and not st.session_state.get("form_hydrated", False):
        st.session_state["quotation_items"] = defaults.get("items", [])
        st.session_state["quotation_draft"] = {
            "job_type": defaults.get("job_type", "FREIGHT"),
            "customer_name": defaults.get("customer_name", ""),
            "currency": defaults.get("currency", "USD"),
            "remark": defaults.get("remark", "")
        }
        st.session_state["form_hydrated"] = True

    st.subheader("📝 Quotation Formulation Workspace")
    st.caption("PostgreSQL Cloud Connected Operational Pricing Tool")

    # =========================================================
    # SECTION 1: HEADER CONTROLS
    # =========================================================
    with st.container(border=True):
        st.markdown("**📂 Document Profile Header**")
        col_h1, col_h2, col_h3 = st.columns([2, 2, 1])
        
        draft = st.session_state["quotation_draft"]
        
        with col_h1:
            customer_name = st.text_input(
                "Customer Enterprise Client", 
                value=draft.get("customer_name", ""),
                placeholder="Company Name Co., Ltd.",
                key="input_cust_name"
            )
        with col_h2:
            job_type = st.selectbox(
                "Operational Logistics Track",
                options=list(JOB_TYPES.keys()),
                format_func=lambda x: JOB_TYPES[x],
                index=list(JOB_TYPES.keys()).index(draft.get("job_type", "FREIGHT")),
                key="input_job_type"
            )
        with col_h3:
            base_currency = st.selectbox(
                "Billing Currency",
                options=CURRENCIES,
                index=CURRENCIES.index(draft.get("currency", "USD")),
                key="input_currency"
            )

        remark = st.text_input(
            "Internal Terms & Condition / Shipment Remarks",
            value=draft.get("remark", ""),
            placeholder="Validity: 30 days, Excludes local customs duties...",
            key="input_remark"
        )
        
        # Save modifications back straight to memory
        st.session_state["quotation_draft"] = {
            "customer_name": customer_name,
            "job_type": job_type,
            "currency": base_currency,
            "remark": remark
        }

    # =========================================================
    # SECTION 2: LINE ITEMS WORKBENCH
    # =========================================================
    st.markdown("### 📊 Financial Line Items Breakdown")
    
    current_items = st.session_state["quotation_items"]
    
    if not current_items:
        st.info("💡 No transactional cost items appended yet. Click 'Add Row' below to structure pricing matrix.")
    else:
        # Structured tabular presentation grid titles
        th_cols = st.columns([3, 1.2, 1.2, 1.5, 0.4])
        th_cols[0].caption("**Description Specification**")
        th_cols[1].caption("**Unit Spec**")
        th_cols[2].caption("**Unit Cost**")
        th_cols[3].caption("**Extended Net**")

        items_buffer = []
        for i, item in enumerate(current_items):
            # Ensure safe unique fallback metadata identifier hash
            item_id = item.get("id", f"idx_{i}")
            cols = st.columns([3, 1.2, 1.2, 1.5, 0.4])
            
            with cols[0]:
                desc_val = st.text_input(
                    "Desc", value=item.get("description", ""), 
                    key=f"item_desc_{item_id}", label_visibility="collapsed",
                    placeholder="Ocean Freight / Handling Fee..."
                )
            with cols[1]:
                unit_val = st.selectbox(
                    "Unit", options=UNIT_TYPES, 
                    index=UNIT_TYPES.index(item.get("unit", "SHPMT")) if item.get("unit") in UNIT_TYPES else 0,
                    key=f"item_unit_{item_id}", label_visibility="collapsed"
                )
            with cols[2]:
                price_val = st.number_input(
                    "Price", value=float(item.get("price", 0.0)), step=50.0,
                    key=f"item_price_{item_id}", label_visibility="collapsed"
                )
            with cols[3]:
                # Inline calculations block element
                st.markdown(f"<div style='padding-top: 6px; background-color: rgba(151,151,151,0.05); padding-left:8px; border-radius:4px;'><b>{price_val:,.2f}</b> <small style='color:gray;'>{base_currency}</small></div>", unsafe_allow_html=True)
            with cols[4]:
                if st.button("🗑️", key=f"item_del_{item_id}", help="Purge item line"):
                    current_items.pop(i)
                    st.session_state["quotation_items"] = current_items
                    st.rerun()

            items_buffer.append({
                "id": item_id,
                "description": desc_val,
                "currency": base_currency,
                "price": price_val,
                "unit": unit_val,
                "remark": item.get("remark", "")
            })
        st.session_state["quotation_items"] = items_buffer

    # Utility operations dashboard
    col_add, _ = st.columns([1, 4])
    with col_add:
        if st.button("➕ Add Item Line", use_container_width=True):
            st.session_state["quotation_items"].append(_empty_item())
            st.rerun()

    # =========================================================
    # SECTION 3: COMMERCIAL GRAND SUMMARY & OPERATIONS
    # =========================================================
    st.markdown("---")
    final_form_data = st.session_state["quotation_draft"]
    final_items = st.session_state["quotation_items"]
    grand_total_sum = calculate_total(final_items)

    col_sum1, col_sum2 = st.columns([2, 1])
    
    with col_sum2:
        st.markdown(
            f"""
            <div style="border: 1px solid #4A5568; padding: 15px; border-radius: 8px; background-color: rgba(0, 0, 0, 0.1); text-align: right;">
                <span style="color: gray; font-size: 0.9em; text-transform: uppercase;">Grand Value Total</span><br/>
                <span style="font-size: 1.8em; font-weight: bold; color: #10B981;">{grand_total_sum:,.2f}