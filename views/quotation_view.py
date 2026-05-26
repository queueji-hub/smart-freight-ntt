"""
Quotation Management View
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
                placeholder="Type minimum 2 characters to look up..."
            )
            
            if len(typed) >= 2:
                try:
                    matches = search_customers(typed) or []
                except Exception:
                    matches = []
                
                if matches:
                    cust_options = ["-- Select Customer --"] + [m["company_name"] for m in matches]
                    st.selectbox(
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
    
    # Header Blueprint