"""
Quotation Management View Workspace
PostgreSQL Connected - 100% Professional ERP Grade Interface
"""

import uuid
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import streamlit as st

# Configuration & Backend Managers Integration
from config import JOB_TYPES, DEFAULT_TERMS
from managers.quotation_manager import (
    create_quotation, get_quotation_by_no, list_quotations,
    update_quotation, duplicate_quotation,
)
from managers.customer_manager import search_customers, get_customer_by_name
from managers.booking_manager import create_booking

# Centralized Security Audit System Integration
from core.audit import log_action

# Dynamic Presentation Layer Engine Guard
_PDF_AVAILABLE = True
try:
    from pdf.quotation_pdf import generate_quotation_pdf
except ImportError:
    _PDF_AVAILABLE = False


# =========================================================
# STATE UTILITIES & CALLBACKS
# =========================================================
def _clear_form_state(prefix: str) -> None:
    """Purges contextual state keys matching a specific view prefix."""
    for k in list(st.session_state.keys()):
        if k.startswith(f"{prefix}_"):
            del st.session_state[k]

def _on_customer_picked(prefix: str) -> None:
    """Triggered on customer selection change to execute async autofill data."""
    picked = st.session_state.get(f"{prefix}_cust_pick")
    if picked and picked != "-- Select Customer --":
        st.session_state[f"{prefix}_cust_search"] = picked
        try:
            cust = get_customer_by_name(picked)
            if cust:
                st.session_state[f"{prefix}_attn"] = cust.get("contact_person", "")
                st.session_state[f"{prefix}_tel"] = cust.get("tel", "")
        except Exception as e:
            st.error(f"Autofill pipeline error: {str(e)}")

def _add_item(prefix: str) -> None:
    """Appends an isolated clean structural pricing line row to the state matrix."""
    items_key = f"{prefix}_items_list"
    if items_key in st.session_state:
        st.session_state[items_key].append({
            "id": str(uuid.uuid4())[:8],
            "description": "",
            "currency": "USD",
            "price": 0.0,
            "unit": "SHPMT",
            "remark": ""
        })


# =========================================================
# SYSTEM COMPONENT WORKBENCH (THE FORM)
# =========================================================
def _quotation_form(prefix: str, defaults: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Renders an administrative multi-column workspace interface.
    Guarantees strict encapsulation of fields to prevent widget cross-contamination.
    """
    d = defaults or {}
    items_key = f"{prefix}_items_list"
    
    # Secure row instantiation architecture
    if items_key not in st.session_state:
        st.session_state[items_key] = d.get("items", []) or [{
            "id": str(uuid.uuid4())[:8], "description": "", "currency": "USD",
            "price": 0.0, "unit": "SHPMT", "remark": ""
        }]

    # --- HEADER PANEL Layout ---
    with st.container(border=True):
        st.markdown("**📋 General Document Parameters**")
        col1, col2 = st.columns(2)
        
        with col1:
            job_type = st.selectbox(
                "Operational Job Type *", 
                options=list(JOB_TYPES.keys()), 
                format_func=lambda x: JOB_TYPES.get(x, x),
                key=f"{prefix}_job_type",
                index=list(JOB_TYPES.keys()).index(d.get("job_type")) if d.get("job_type") in JOB_TYPES else 0
            )
            
            # Smart Search Auto-completion Layout
            typed = st.text_input(
                "Customer Account Identification *", 
                value=d.get("customer_name", ""), 
                key=f"{prefix}_cust_search",
                placeholder="Type customer name or select matching result below..."
            )
            
            cust_picked_val = None
            if len(typed) >= 1:
                try:
                    matches = search_customers(typed) or []
                except Exception:
                    matches = []
                
                if matches:
                    cust_options = ["-- Select Customer --"] + [m["company_name"] for m in matches]
                    cust_picked_val = st.selectbox(
                        "🎯 Matching Results (Autofill Source)", 
                        options=cust_options, 
                        key=f"{prefix}_cust_pick", 
                        on_change=_on_customer_picked, 
                        args=(prefix,)
                    )
            
            attention = st.text_input("Attention Person (Attn)", value=d.get("attention", ""), key=f"{prefix}_attn")
            tel = st.text_input("Telephone / Extension", value=d.get("tel", ""), key=f"{prefix}_tel")
            carrier = st.text_input("Logistics Carrier / Line", value=d.get("carrier", ""), key=f"{prefix}_carrier", placeholder="e.g., Maersk, Emirates")
        
        with col2:
            # Handle standard ISO Format from PostgreSQL
            q_date_raw = d.get("quotation_date")
            v_date_raw = d.get("validity_date")
            
            q_date = date.fromisoformat(q_date_raw) if isinstance(q_date_raw, str) else date.today()
            v_date = date.fromisoformat(v_date_raw) if isinstance(v_date_raw, str) else (date.today() + timedelta(days=30))
            
            quotation_date = st.date_input("Issuing Date", q_date, key=f"{prefix}_qdate")
            validity_date = st.date_input("Expiration Validity Date", v_date, key=f"{prefix}_vdate")
            payment_term = st.text_input("Payment Credit Terms", value=d.get("payment_term", "Net 30"), key=f"{prefix}_payment")
            commodity = st.text_input("Manifest Commodity Cargo", value=d.get("commodity", ""), key=f"{prefix}_commodity", placeholder="General Cargo, Fresh Goods")
            subject = st.text_input("Commercial Heading / Subject", value=d.get("subject", ""), key=f"{prefix}_subject", placeholder="e.g., Ocean Freight proposal for Q3")

    # --- PORT & ROUTING INFORMATION ---
    with st.container(border=True):
        st.markdown("**⚓ Routing Logistics Manifest**")
        col_p1, col_p2 = st.columns(2)
        pol = col_p1.text_input("Port of Loading (POL)", value=d.get("pol", ""), key=f"{prefix}_pol", placeholder="THLCH - Laem Chabang")
        pod = col_p2.text_input("Port of Discharge (POD)", value=d.get("pod", ""), key=f"{prefix}_pod", placeholder="USLAX - Los Angeles")

    # --- DETAILED COST ITEMS BREAKDOWN (State Grid) ---
    st.markdown("### 📊 Pricing Model Line Items")
    
    header_cols = st.columns([3, 1, 1.2, 1, 2, 0.4])
    header_cols[0].caption("**Charge Item Description Specification**")
    header_cols[1].caption("**Currency**")
    header_cols[2].caption("**Unit Rate Price**")
    header_cols[3].caption("**Billing Unit**")
    header_cols[4].caption("**Transactional Item Remark**")
    header_cols[5].caption("**Action**")

    items_to_remove = []
    updated_items = []

    for i, row in enumerate(st.session_state[items_key]):
        row_id = row.get("id", str(i))
        cols = st.columns([3, 1, 1.2, 1, 2, 0.4])
        
        desc = cols[0].text_input("Desc", row["description"], key=f"{prefix}_desc_{row_id}", label_visibility="collapsed", placeholder="Handling Fee, Freight Charge...")
        curr = cols[1].selectbox("Curr", ["USD", "THB", "CNY", "EUR"], index=["USD", "THB", "CNY", "EUR"].index(row.get("currency", "USD")) if row.get("currency") in ["USD", "THB", "CNY", "EUR"] else 0, key=f"{prefix}_cur_{row_id}", label_visibility="collapsed")
        price = cols[2].number_input("Price", value=float(row["price"]), min_value=0.0, step=50.0, format="%.2f", key=f"{prefix}_p_{row_id}", label_visibility="collapsed")
        unit = cols[3].text_input("Unit", row["unit"], key=f"{prefix}_u_{row_id}", label_visibility="collapsed", placeholder="CBM / BL")
        remark = cols[4].text_input("Remark", row["remark"], key=f"{prefix}_r_{row_id}", label_visibility="collapsed", placeholder="Internal context notes")
        
        if cols[5].button("🗑️", key=f"{prefix}_del_{row_id}", help="Purge this charge line"):
            items_to_remove.append(row_id)

        updated_items.append({
            "id": row_id,
            "description": desc,
            "currency": curr,
            "price": price,
            "unit": unit,
            "remark": remark
        })

    if items_to_remove:
        st.session_state[items_key] = [item for item in updated_items if item["id"] not in items_to_remove]
        st.rerun()
    else:
        st.session_state[items_key] = updated_items

    col_act1, _ = st.columns([1, 4])
    with col_act1:
        st.button("➕ Add Row", on_click=_add_item, args=(prefix,), use_container_width=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    terms = st.text_area("Legal Terms & Contractual Conditions Clauses", value=d.get("terms_conditions", DEFAULT_TERMS), key=f"{prefix}_terms", height=120)

    # Determine final customer name cleanly
    final_customer_name = typed.strip()
    if cust_picked_val and cust_picked_val != "-- Select Customer --":
        final_customer_name = cust_picked_val.strip()

    form_payload = {
        "job_type": job_type, "customer_name": final_customer_name, "attention": attention.strip(), "tel": tel.strip(),
        "carrier": carrier.strip(), "pol": pol.strip(), "pod": pod.strip(), "quotation_date": quotation_date.isoformat(),
        "validity_date": validity_date.isoformat(), "payment_term": payment_term.strip(),
        "commodity": commodity.strip(), "subject": subject.strip(), "terms_conditions": terms.strip()
    }
    
    return form_payload, pd.DataFrame(st.session_state[items_key])


# =========================================================
# CENTRAL INTERFACE ROUTER (THE MISSING RENDER FUNCTION)
# =========================================================
def render() -> None:
    """
    Master presentation shell router for the complete Quotation Module.
    Invoked dynamically by the Core Dashboard compiler.
    """
    st.subheader("💼 Quotation Management Hub")
    st.caption("Commercial Pro-Forma Processing Operations Control Panel")

    tab_create, tab_all = st.tabs(["➕ Structure New Quotation", "📋 Historical Manifest Ledger"])

    # --- TAB 1: FORMATION HUB ---
    with tab_create:
        form_data, items_df = _quotation_form("create")
        
        st.divider()
        col_sub1, _ = st.columns([1.5, 4])
        with col_sub1:
            if st.button("🚀 Finalize & Generate Document", type="primary", use_container_width=True):
                if not form_data.get("customer_name"):
                    form_data["customer_name"] = "Valued Customer"
                
                with st.spinner("Executing secure transactional entry integration..."):
                    try:
                        qno = create_quotation(form_data, items_df.to_dict('records'))
                        
                        # Execute secure structural tracking audit
                        log_action(
                            user_id=1,
                            tenant_id="demo",
                            entity="quotation",
                            entity_id=qno,
                            action="CREATE"
                        )
                        
                        st.success(f"✅ Document Successfully Registered to Ledger: {qno}")
                        _clear_form_state("create")
                        st.rerun()
                    except Exception as transaction_error:
                        st.error(f"🚨 PostgreSQL Ledger Failure: {str(transaction_error)}")

    # --- TAB 2: AUDIT LOGS & ARCHIVES ---
    with tab_all:
        try:
            records = list_quotations() or []
        except Exception as read_error:
            st.error(f"Failed loading indices from database context: {read_error}")
            records = []

        if not records:
            st.info("No quotation manifests matching search context exist inside database indexes.")
            return

        df = pd.DataFrame(records)
        
        col_f1, col_f2 = st.columns([2, 1])
        search_query = col_f1.text_input("🔍 Filter Ledger Records", placeholder="Search Customer Name, Reference Number...")
        
        if search_query:
            df = df[df.apply(lambda r: search_query.lower() in str(r).lower(), axis=1)]

        # Custom high-performance analytical columns visualization configuration
        st.dataframe(
            df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "quotation_no": st.column_config.TextColumn("Quotation No.", width="medium"),
                "customer_name": st.column_config.TextColumn("Client Corporate Account", width="large"),
                "job_type": st.column_config.TextColumn("Operation Track"),
                "quotation_date": st.column_config.DateColumn("Issuing Date", format="YYYY-MM-DD"),
                "validity_date": st.column_config.DateColumn("Expiration", format="YYYY-MM-DD"),
                "status": st.column_config.TextColumn("Status")
            }
        )

        st.divider()
        st.markdown("**🛠️ Selected Document Operation Desk**")
        
        col_sel1, col_sel2, _ = st.columns([2, 1, 2])
        with col_sel1:
            sel_qno = st.selectbox(
                "Active Working Document Selection Target", 
                options=df["quotation_no"].tolist() if "quotation_no" in df.columns else [],
                label_visibility="collapsed"
            )
        
        with col_sel2:
            edit_triggered = st.button("✏️ Check Out & Modify", type="secondary", use_container_width=True)
            
        if edit_triggered and sel_qno:
            st.session_state["edit_loaded"] = sel_qno
            st.rerun()

        # --- LIVE DOCUMENT RECONCILIATION EDIT DRAWER ---
        if "edit_loaded" in st.session_state:
            st.markdown("---")
            target_no = st.session_state["edit_loaded"]
            
            with st.spinner(f"Extracting state payload record index target '{target_no}'..."):
                try:
                    loaded = get_quotation_by_no(target_no)
                except Exception as fetch_err:
                    st.error(f"Failed retrieval transaction pipeline: {fetch_err}")
                    loaded = None

            if loaded:
                st.markdown(f"#### 🔒 Workspace Checkout: Editing Manifest `{loaded['quotation_no']}`")
                
                form_data_edit, items_df_edit = _quotation_form("edit", defaults=loaded)
                
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                col_e1, col_e2, _ = st.columns([1, 1, 3])
                
                with col_e1:
                    if st.button("💾 Apply Overwrite", type="primary", use_container_width=True):
                        try:
                            update_quotation(loaded["quotation_no"], form_data_edit, items_df_edit.to_dict('records'))
                            
                            # Log the edit modification trace
                            log_action(
                                user_id=1,
                                tenant_id="demo",
                                entity="quotation",
                                entity_id=loaded["quotation_no"],
                                action="UPDATE"
                            )
                            
                            st.success("Ledger values modified successfully.")
                            del st.session_state["edit_loaded"]
                            _clear_form_state("edit")
                            st.rerun()
                        except Exception as update_err:
                            st.error(f"Pipeline intercept error: {update_err}")
                            
                with col_e2:
                    if st.button("❌ Close Workspace", use_container_width=True):
                        del st.session_state["edit_loaded"]
                        _clear_form_state("edit")
                        st.rerun()