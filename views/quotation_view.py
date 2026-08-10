"""
Quotation Management View — Enterprise Grade
Smart Freight NTT, — Full Rewrite with st.form, Validation, Audit, PDF, UX
"""

import re
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import streamlit as st

from config import JOB_TYPES, DEFAULT_TERMS
from managers.quotation_manager import (
    create_quotation, get_quotation_by_no, list_quotations,
    update_quotation, duplicate_quotation,
)
from managers.customer_manager import search_customers, get_customer_by_name
from core.audit import log_action

_PDF_AVAILABLE = True
try:
    from pdf.quotation_pdf import generate_quotation_pdf
except ImportError:
    _PDF_AVAILABLE = False


# =========================================================
# HELPERS
# =========================================================
def _current_user() -> str:
    """Returns the logged-in username from session for audit trail."""
    return st.session_state.get("username", "system")


def _current_user_id() -> int:
    """Returns the logged-in user ID from session for audit trail."""
    return st.session_state.get("user_id", 1)


def _clear_form_state(prefix: str) -> None:
    """Purges session keys for a given form prefix to reset the form."""
    keys_to_remove = [k for k in st.session_state.keys() if k.startswith(f"{prefix}_")]
    for k in keys_to_remove:
        del st.session_state[k]


def _init_items(prefix: str, defaults: list = None) -> None:
    """Initialises line items in session state if not already present."""
    key = f"{prefix}_items"
    if key not in st.session_state:
        if defaults:
            st.session_state[key] = [
                {
                    "uid": row.get("id", str(uuid.uuid4())[:8]),
                    "description": row.get("description", ""),
                    "basis": row.get("basis", ""),
                    "quantity": float(row.get("quantity", 1)),
                    "unit": row.get("unit", "SHPMT"),
                    "currency": row.get("currency", "USD"),
                    "unit_rate": float(row.get("unit_rate", 0)),
                    "price": float(row.get("price", 0)), # Display amount
                    "remark": row.get("remark", ""),
                }
                for row in defaults
            ]
        else:
            st.session_state[key] = [_blank_item()]


def _blank_item() -> dict:
    return {
        "uid": str(uuid.uuid4())[:8],
        "description": "",
        "basis": "",
        "quantity": 1.0,
        "unit": "SHPMT",
        "currency": "USD",
        "unit_rate": 0.0,
        "price": 0.0,
        "remark": "",
    }


def _add_row(prefix: str) -> None:
    st.session_state[f"{prefix}_items"].append(_blank_item())


def _del_row(prefix: str, uid: str) -> None:
    items = st.session_state.get(f"{prefix}_items", [])
    st.session_state[f"{prefix}_items"] = [r for r in items if r["uid"] != uid]


# =========================================================
# VALIDATION ENGINE
# =========================================================
def _validate_form(data: dict, items: list) -> List[str]:
    """Returns a list of human-readable validation error messages."""
    errors = []

    job_type = data.get("job_type", "")
    
    # Mandatory fields for all modes
    if not data.get("customer_name", "").strip():
        errors.append("Customer Name is required.")
    if not data.get("salesperson", "").strip():
        errors.append("Salesperson is required.")
        
    # Conditional logic based on Mode
    if job_type in ["SE", "SI"]: # SEA
        if not data.get("pol", "").strip():
            errors.append("Port of Loading (POL) is required for Sea Freight.")
        if not data.get("pod", "").strip():
            errors.append("Port of Discharge (POD) is required for Sea Freight.")
        if not data.get("commodity", "").strip():
            errors.append("Commodity is required for Sea Freight.")
        if not data.get("incoterm", "").strip():
            errors.append("Incoterm is required for Sea Freight.")
        if not data.get("service_type", "").strip():
            errors.append("Service Type (e.g. FCL/LCL) is required.")
            
        if data.get("service_type") == "FCL":
            if not data.get("container_type", "").strip():
                errors.append("Container Type is required for FCL.")
            if not data.get("container_quantity"):
                errors.append("Container Quantity is required for FCL.")
        elif data.get("service_type") == "LCL":
            if not data.get("weight_kg") and not data.get("volume_cbm"):
                errors.append("Weight or CBM is required for LCL.")
                
    elif job_type in ["AE", "AI"]: # AIR
        if not data.get("origin", "").strip():
            errors.append("Origin Airport is required for Air Freight.")
        if not data.get("destination", "").strip():
            errors.append("Destination Airport is required for Air Freight.")
        if not data.get("commodity", "").strip():
            errors.append("Commodity is required for Air Freight.")
        if not data.get("weight_kg"):
            errors.append("Chargeable Weight is required for Air Freight.")
            
    elif job_type in ["TE", "TI"]: # TRUCK
        if not data.get("origin", "").strip():
            errors.append("Origin is required for Trucking.")
        if not data.get("destination", "").strip():
            errors.append("Destination is required for Trucking.")

    # Date logic
    try:
        q_date = date.fromisoformat(data.get("quotation_date", ""))
        v_date = date.fromisoformat(data.get("validity_date", ""))
        if v_date < q_date:
            errors.append("Validity Date cannot be earlier than Issue Date.")
    except (ValueError, TypeError):
        errors.append("Issue Date or Validity Date is invalid.")

    # Line items
    if not items:
        errors.append("At least one charge line item is required.")
    else:
        for i, item in enumerate(items, 1):
            if not item.get("description", "").strip():
                errors.append(f"Line #{i}: Description is empty.")
            p = float(item.get("price", 0))
            if p < 0:
                errors.append(f"Line #{i}: Price cannot be negative.")

    return errors


# The legacy line item editor was removed to utilize Streamlit's native st.data_editor# =========================================================
# THE FORM (inside st.form for atomic submit)
# =========================================================
def _quotation_form(prefix: str, defaults: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Renders the quotation header fields inside an st.form.
    Returns the collected form data dict on submit (or empty dict if not submitted).
    """
    d = defaults or {}

    q_date = date.today()
    v_date = date.today() + timedelta(days=30)
    try:
        if d.get("quotation_date"):
            q_date = date.fromisoformat(str(d["quotation_date"])[:10])
        if d.get("validity_date"):
            v_date = date.fromisoformat(str(d["validity_date"])[:10])
    except (ValueError, TypeError):
        pass

    with st.form(key=f"{prefix}_form", clear_on_submit=False):
        # ── General Parameters ──────────────────────────────
        with st.container(border=True):
            st.markdown("**📋 General Document Parameters**")
            c1, c2 = st.columns(2)

            with c1:
                job_type = st.selectbox(
                    "Job Type *",
                    options=list(JOB_TYPES.keys()),
                    format_func=lambda x: f"{x} — {JOB_TYPES[x]}",
                    index=list(JOB_TYPES.keys()).index(d.get("job_type")) if d.get("job_type") in JOB_TYPES else 0,
                    key=f"{prefix}_job_type",
                    help="SE=Sea Export, SI=Sea Import, AE=Air Export, AI=Air Import"
                )
                customer_name = st.text_input(
                    "Customer Name *", value=d.get("customer_name", ""),
                    key=f"{prefix}_cust", placeholder="e.g. KUMIKI CO.,LTD.",
                    help="Type the full registered company name of the client."
                )
                customer_address = st.text_area(
                    "Customer Address", value=d.get("customer_address", ""),
                    key=f"{prefix}_caddr", placeholder="123 Street, City, Country", height=68
                )
                attention = st.text_input(
                    "Attention (Contact Person)", value=d.get("attention", ""),
                    key=f"{prefix}_attn", help="The person at the client who should receive this document."
                )
                tel = st.text_input(
                    "Telephone", value=d.get("tel", ""), key=f"{prefix}_tel"
                )
                customer_email = st.text_input(
                    "Email", value=d.get("customer_email", ""), key=f"{prefix}_email"
                )

            with c2:
                quotation_date = st.date_input(
                    "Issue Date *", q_date, key=f"{prefix}_qdate",
                    help="The date this quotation is formally issued."
                )
                validity_date = st.date_input(
                    "Validity Date *", v_date, key=f"{prefix}_vdate",
                    help="Rate guarantee expires after this date. Must be >= Issue Date."
                )
                salesperson = st.text_input(
                    "Salesperson *", value=d.get("salesperson", _current_user()),
                    key=f"{prefix}_sales", help="The sales representative for this quote."
                )
                payment_term = st.text_input(
                    "Payment Terms", value=d.get("payment_term", "Net 30"),
                    key=f"{prefix}_pay", help="e.g. Net 30, COD, TT in advance."
                )
                subject = st.text_input(
                    "Subject / Heading", value=d.get("subject", ""),
                    key=f"{prefix}_subj", placeholder="e.g. Ocean Freight proposal Q3-2026"
                )

        # ── Routing & Cargo Details ─────────────────────────────
        with st.container(border=True):
            st.markdown("**⚓ Routing & Cargo Information**")
            r1, r2, r3 = st.columns(3)
            
            with r1:
                shipper = st.text_input("Shipper", value=d.get("shipper", ""), key=f"{prefix}_ship")
                origin = st.text_input("Origin", value=d.get("origin", ""), key=f"{prefix}_origin", placeholder="City/Country")
                pol = st.text_input("Port of Loading (POL)", value=d.get("pol", ""), key=f"{prefix}_pol", placeholder="THLCH")
                service_type = st.selectbox(
                    "Service Type", options=["", "FCL", "LCL", "AIR", "LTL", "FTL", "RO-RO"], 
                    index=["", "FCL", "LCL", "AIR", "LTL", "FTL", "RO-RO"].index(d.get("service_type")) if d.get("service_type") in ["", "FCL", "LCL", "AIR", "LTL", "FTL", "RO-RO"] else 0,
                    key=f"{prefix}_srv"
                )
                commodity = st.text_input("Commodity", value=d.get("commodity", ""), key=f"{prefix}_cmdty", placeholder="General Cargo")
                quantity = st.number_input("Quantity", value=float(d.get("quantity") or 0.0), key=f"{prefix}_qty", step=1.0)

            with r2:
                consignee = st.text_input("Consignee", value=d.get("consignee", ""), key=f"{prefix}_cnee")
                destination = st.text_input("Destination", value=d.get("destination", ""), key=f"{prefix}_dest", placeholder="City/Country")
                pod = st.text_input("Port of Discharge (POD)", value=d.get("pod", ""), key=f"{prefix}_pod", placeholder="JPNAH")
                incoterm = st.selectbox(
                    "Incoterm", options=["", "EXW", "FCA", "FOB", "CFR", "CIF", "DAP", "DDP", "DDU"], 
                    index=["", "EXW", "FCA", "FOB", "CFR", "CIF", "DAP", "DDP", "DDU"].index(d.get("incoterm")) if d.get("incoterm") in ["", "EXW", "FCA", "FOB", "CFR", "CIF", "DAP", "DDP", "DDU"] else 0,
                    key=f"{prefix}_inco"
                )
                hs_code = st.text_input("HS Code", value=d.get("hs_code", ""), key=f"{prefix}_hs")
                package_type = st.text_input("Package Type", value=d.get("package_type", ""), key=f"{prefix}_pkg", placeholder="Cartons, Pallets")

            with r3:
                carrier = st.text_input("Carrier / Line", value=d.get("carrier", ""), key=f"{prefix}_carrier", placeholder="Maersk")
                freight_term = st.selectbox(
                    "Freight Term", options=["", "PREPAID", "COLLECT"], 
                    index=["", "PREPAID", "COLLECT"].index(d.get("freight_term")) if d.get("freight_term") in ["", "PREPAID", "COLLECT"] else 0,
                    key=f"{prefix}_frt"
                )
                weight_kg = st.number_input("Weight (KGs)", value=float(d.get("weight_kg") or 0.0), key=f"{prefix}_wgt", step=10.0)
                volume_cbm = st.number_input("Volume (CBM)", value=float(d.get("volume_cbm") or 0.0), key=f"{prefix}_vol", step=1.0)
                container_type = st.text_input("Container Type", value=d.get("container_type", ""), key=f"{prefix}_cnt", placeholder="20'GP, 40'HC")
                container_quantity = st.number_input("Container Qty", value=int(d.get("container_quantity") or 0), key=f"{prefix}_cntq", step=1)
                is_dg = st.checkbox("Dangerous Goods (DG)", value=bool(d.get("is_dg") or False), key=f"{prefix}_dg")

        # ── Terms & Conditions ──────────────────────────────
        terms = st.text_area(
            "Terms & Conditions",
            value=d.get("terms_conditions", DEFAULT_TERMS),
            key=f"{prefix}_terms", height=100,
            help="Legal clauses printed at the bottom of the quotation PDF."
        )

        # ── Line Items (Data Editor) ────────────────────────
        st.markdown("**📊 Pricing Line Items**")
        
        # Load items from defaults, or provide one blank item
        initial_items = d.get("items", [])
        if not initial_items:
            initial_items = [_blank_item()]
            
        df_items = pd.DataFrame(initial_items)
        
        edited_items_df = st.data_editor(
            df_items,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "uid": None, # Hide UID
                "description": st.column_config.TextColumn("Description *", required=True),
                "basis": st.column_config.TextColumn("Basis"),
                "quantity": st.column_config.NumberColumn("Qty", min_value=0.0, format="%.3f", default=1.0),
                "unit": st.column_config.TextColumn("Unit", default="SHPMT"),
                "currency": st.column_config.SelectboxColumn("Currency", options=["USD", "THB", "CNY", "EUR", "JPY"], default="USD"),
                "unit_rate": st.column_config.NumberColumn("Unit Rate *", min_value=0.0, format="%.2f", default=0.0),
                "price": st.column_config.NumberColumn("Amount (Auto)", format="%.2f", disabled=True),
                "remark": st.column_config.TextColumn("Remark")
            },
            key=f"{prefix}_items_editor"
        )
        
        # Total Summary Display
        if not edited_items_df.empty:
            # Auto-calculate amount for display
            edited_items_df["price"] = pd.to_numeric(edited_items_df["quantity"], errors='coerce').fillna(1.0) * pd.to_numeric(edited_items_df["unit_rate"], errors='coerce').fillna(0.0)
            
            # Group by currency
            totals_html = "<div style='text-align: right; font-weight: bold; font-size: 16px; color: #0068c9; padding: 10px; background-color: rgba(0, 104, 201, 0.1); border-radius: 5px; margin-top: 10px;'>"
            grouped = edited_items_df.groupby("currency")["price"].sum()
            totals = [f"{curr}: {val:,.2f}" for curr, val in grouped.items() if val > 0]
            if totals:
                totals_html += "TOTAL ➜ " + " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(totals)
            else:
                totals_html += "TOTAL ➜ 0.00"
            totals_html += "</div>"
            st.markdown(totals_html, unsafe_allow_html=True)

        # ── Submit Button ───────────────────────────────────
        btn_label = "💾 Update Quotation" if defaults else "🚀 Create & Generate Quotation"
        submitted = st.form_submit_button(btn_label, type="primary", use_container_width=True)

    # Build payload (always returned; caller checks `submitted`)
    payload = {
        "job_type": job_type,
        "customer_name": customer_name.strip(),
        "customer_address": customer_address.strip(),
        "attention": attention.strip(),
        "tel": tel.strip(),
        "customer_email": customer_email.strip(),
        "salesperson": salesperson.strip(),
        "carrier": carrier.strip(),
        "pol": pol.strip(),
        "pod": pod.strip(),
        "quotation_date": quotation_date.isoformat(),
        "validity_date": validity_date.isoformat(),
        "payment_term": payment_term.strip(),
        "commodity": commodity.strip(),
        "subject": subject.strip(),
        "terms_conditions": terms.strip(),
        "shipper": shipper.strip(),
        "consignee": consignee.strip(),
        "service_type": service_type.strip(),
        "origin": origin.strip(),
        "destination": destination.strip(),
        "incoterm": incoterm.strip(),
        "freight_term": freight_term.strip(),
        "hs_code": hs_code.strip(),
        "quantity": float(quantity),
        "package_type": package_type.strip(),
        "weight_kg": float(weight_kg),
        "volume_cbm": float(volume_cbm),
        "container_type": container_type.strip(),
        "container_quantity": int(container_quantity),
        "is_dg": bool(is_dg),
        "created_by": _current_user(),
        "updated_by": _current_user(),
        "_items": edited_items_df.to_dict('records') if not edited_items_df.empty else [],
        "_submitted": submitted,
    }
    return payload


# =========================================================
# MASTER RENDER FUNCTION
# =========================================================
def render() -> None:
    st.subheader("💼 Quotation Management")
    st.caption("Create, edit and export pro-forma quotations for freight services.")

    tab_create, tab_list = st.tabs(["➕ New Quotation", "📋 Quotation Ledger"])

    # ── TAB 1: CREATE ───────────────────────────────────────
    with tab_create:
        # Form fields + submit button
        payload = _quotation_form("new")

        if payload["_submitted"]:
            items = payload.get("_items", [])
            errors = _validate_form(payload, items)

            if errors:
                for err in errors:
                    st.error(f"⛔ {err}")
            else:
                with st.spinner("Saving quotation..."):
                    try:
                        items_clean = [
                            {k: v for k, v in it.items() if k != "uid"}
                            for it in items
                        ]
                        qno = create_quotation(payload, items_clean)

                        log_action(
                            user_id=_current_user_id(),
                            tenant_id="ntt",
                            entity="quotation",
                            entity_id=qno,
                            action="CREATE",
                            details=f"Created by {_current_user()}"
                        )

                        st.success(f"✅ Quotation **{qno}** created successfully!")

                        # Auto-generate PDF
                        if _PDF_AVAILABLE:
                            try:
                                qt = get_quotation_by_no(qno)
                                if qt:
                                    pdf_path = generate_quotation_pdf(qt, items_clean)
                                    with open(pdf_path, "rb") as f:
                                        st.download_button(
                                            "📥 Download Quotation PDF",
                                            data=f.read(),
                                            file_name=f"{qno}.pdf",
                                            mime="application/pdf",
                                        )
                            except Exception as pdf_err:
                                st.warning(f"PDF generation skipped: {pdf_err}")

                        _clear_form_state("new")
                        if "new_items" in st.session_state:
                            del st.session_state["new_items"]

                    except Exception as e:
                        st.error(f"🚨 Save failed: {e}")

    # ── TAB 2: LIST & EDIT ──────────────────────────────────
    with tab_list:
        try:
            records = list_quotations() or []
        except Exception as e:
            st.error(f"Failed loading quotations: {e}")
            records = []

        if not records:
            st.info("No quotations found in the database. Create your first one above!")
            return

        df = pd.DataFrame(records)

        # Filters
        c1, c2 = st.columns([3, 1])
        search_q = c1.text_input(
            "🔍 Search", placeholder="Customer name, quotation number...",
            key="qt_search"
        )
        if search_q:
            mask = df.apply(lambda r: search_q.lower() in str(r.values).lower(), axis=1)
            df = df[mask]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "quotation_no": st.column_config.TextColumn("Quotation No.", width="medium"),
                "customer_name": st.column_config.TextColumn("Customer", width="large"),
                "job_type": st.column_config.TextColumn("Type", width="small"),
                "quotation_date": st.column_config.DateColumn("Issue Date", format="YYYY-MM-DD"),
                "validity_date": st.column_config.DateColumn("Valid Until", format="YYYY-MM-DD"),
                "status": st.column_config.TextColumn("Status", width="small"),
            },
        )

        # ── Document Operations ─────────────────────────────
        st.divider()
        st.markdown("**🛠️ Document Operations**")

        q_list = df["quotation_no"].tolist() if "quotation_no" in df.columns else []
        if not q_list:
            return

        s1, s2, s3, s4 = st.columns([2, 1, 1, 1])
        sel_qno = s1.selectbox("Select Quotation", options=q_list, key="qt_sel")

        with s2:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state["qt_edit_target"] = sel_qno
                _clear_form_state("edit")
                if "edit_items" in st.session_state:
                    del st.session_state["edit_items"]
                st.rerun()

        with s3:
            if st.button("📋 Duplicate", use_container_width=True):
                try:
                    new_qno = duplicate_quotation(sel_qno)
                    log_action(
                        user_id=_current_user_id(), tenant_id="ntt",
                        entity="quotation", entity_id=new_qno, action="DUPLICATE",
                        details=f"Duplicated from {sel_qno} by {_current_user()}"
                    )
                    st.success(f"✅ Duplicated as **{new_qno}**")
                    st.rerun()
                except Exception as e:
                    st.error(f"Duplication failed: {e}")

        with s4:
            if _PDF_AVAILABLE:
                try:
                    loaded_qt = get_quotation_by_no(sel_qno)
                    if loaded_qt:
                        pdf_path = generate_quotation_pdf(loaded_qt, loaded_qt.get("items", []))
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                "📄 PDF",
                                data=f.read(),
                                file_name=f"{sel_qno}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                except Exception as pdf_err:
                    st.error(f"PDF Error: {pdf_err}")
            else:
                st.button("📄 PDF", disabled=True, help="PDF module not available", use_container_width=True)

        # ── Edit Drawer ─────────────────────────────────────
        if "qt_edit_target" in st.session_state:
            target_no = st.session_state["qt_edit_target"]
            st.markdown("---")
            st.markdown(f"#### ✏️ Editing: `{target_no}`")

            try:
                loaded = get_quotation_by_no(target_no)
            except Exception as e:
                st.error(f"Failed to load quotation: {e}")
                loaded = None

            if loaded:
                loaded["items"] = loaded.get("items", []) # Inject items into defaults
                payload_edit = _quotation_form("edit", defaults=loaded)

                if payload_edit["_submitted"]:
                    items = payload_edit.get("_items", [])
                    errors = _validate_form(payload_edit, items)

                    if errors:
                        for err in errors:
                            st.error(f"⛔ {err}")
                    else:
                        try:
                            items_clean = [
                                {k: v for k, v in it.items() if k != "uid"}
                                for it in items
                            ]
                            update_quotation(target_no, payload_edit, items_clean)

                            log_action(
                                user_id=_current_user_id(), tenant_id="ntt",
                                entity="quotation", entity_id=target_no, action="UPDATE",
                                details=f"Updated by {_current_user()}"
                            )
                            st.success(f"✅ Quotation **{target_no}** updated successfully!")
                            del st.session_state["qt_edit_target"]
                            _clear_form_state("edit")
                            if "edit_items" in st.session_state:
                                del st.session_state["edit_items"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"🚨 Update failed: {e}")

                if st.button("❌ Cancel Editing", key="qt_cancel_edit"):
                    del st.session_state["qt_edit_target"]
                    _clear_form_state("edit")
                    if "edit_items" in st.session_state:
                        del st.session_state["edit_items"]
                    st.rerun()
            else:
                st.warning(f"Quotation `{target_no}` not found. It may have been deleted.")
                del st.session_state["qt_edit_target"]