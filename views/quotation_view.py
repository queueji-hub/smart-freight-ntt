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
                    "currency": row.get("currency", "USD"),
                    "price": float(row.get("price", 0)),
                    "unit": row.get("unit", "SHPMT"),
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
        "currency": "USD",
        "price": 0.0,
        "unit": "SHPMT",
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

    # Mandatory fields
    if not data.get("customer_name", "").strip():
        errors.append("Customer Name is required.")
    if not data.get("pol", "").strip():
        errors.append("Port of Loading (POL) is required.")
    if not data.get("pod", "").strip():
        errors.append("Port of Discharge (POD) is required.")

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


# =========================================================
# LINE ITEMS EDITOR (outside st.form — Streamlit limitation)
# =========================================================
def _render_items_editor(prefix: str) -> None:
    """Renders an interactive line-item grid with Add/Delete buttons."""
    _init_items(prefix)
    items = st.session_state[f"{prefix}_items"]

    st.markdown("### 📊 Pricing Line Items")

    # Column headers
    hdr = st.columns([3, 1, 1.2, 1, 2, 0.5])
    hdr[0].caption("**Description**")
    hdr[1].caption("**Currency**")
    hdr[2].caption("**Unit Price**")
    hdr[3].caption("**Billing Unit**")
    hdr[4].caption("**Remark**")
    hdr[5].caption("**Del**")

    CURRENCIES = ["USD", "THB", "CNY", "EUR", "JPY"]

    for row in items:
        uid = row["uid"]
        c = st.columns([3, 1, 1.2, 1, 2, 0.5])

        row["description"] = c[0].text_input(
            "desc", row["description"], key=f"{prefix}_d_{uid}",
            label_visibility="collapsed", placeholder="Ocean Freight, THC..."
        )
        cur_idx = CURRENCIES.index(row["currency"]) if row["currency"] in CURRENCIES else 0
        row["currency"] = c[1].selectbox(
            "cur", CURRENCIES, index=cur_idx, key=f"{prefix}_c_{uid}",
            label_visibility="collapsed"
        )
        row["price"] = c[2].number_input(
            "price", value=float(row["price"]), min_value=0.0, step=50.0,
            format="%.2f", key=f"{prefix}_p_{uid}", label_visibility="collapsed"
        )
        row["unit"] = c[3].text_input(
            "unit", row["unit"], key=f"{prefix}_u_{uid}",
            label_visibility="collapsed", placeholder="CBM / BL"
        )
        row["remark"] = c[4].text_input(
            "rmk", row["remark"], key=f"{prefix}_r_{uid}",
            label_visibility="collapsed", placeholder="Notes..."
        )
        c[5].button("🗑", key=f"{prefix}_x_{uid}", on_click=_del_row, args=(prefix, uid),
                     help="Remove this line")

    st.button("➕ Add Charge Line", key=f"{prefix}_add_btn", on_click=_add_row, args=(prefix,))


# =========================================================
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
                attention = st.text_input(
                    "Attention (Contact Person)", value=d.get("attention", ""),
                    key=f"{prefix}_attn", help="The person at the client who should receive this document."
                )
                tel = st.text_input(
                    "Telephone", value=d.get("tel", ""), key=f"{prefix}_tel"
                )
                carrier = st.text_input(
                    "Carrier / Shipping Line", value=d.get("carrier", ""),
                    key=f"{prefix}_carrier", placeholder="e.g. Maersk, Emirates SkyCargo",
                    help="The ocean/air carrier used for this shipment."
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
                payment_term = st.text_input(
                    "Payment Terms", value=d.get("payment_term", "Net 30"),
                    key=f"{prefix}_pay", help="e.g. Net 30, COD, TT in advance."
                )
                commodity = st.text_input(
                    "Commodity Description", value=d.get("commodity", ""),
                    key=f"{prefix}_cmdty", placeholder="General Cargo, Fresh Goods",
                    help="Brief description of the type of cargo."
                )
                subject = st.text_input(
                    "Subject / Heading", value=d.get("subject", ""),
                    key=f"{prefix}_subj", placeholder="e.g. Ocean Freight proposal Q3-2026"
                )

        # ── Routing ─────────────────────────────────────────
        with st.container(border=True):
            st.markdown("**⚓ Routing Information**")
            r1, r2 = st.columns(2)
            pol = r1.text_input(
                "Port of Loading (POL) *", value=d.get("pol", ""),
                key=f"{prefix}_pol", placeholder="THLCH — Laem Chabang",
                help="UN/LOCODE of origin port."
            )
            pod = r2.text_input(
                "Port of Discharge (POD) *", value=d.get("pod", ""),
                key=f"{prefix}_pod", placeholder="JPNAH — Naha, Okinawa",
                help="UN/LOCODE of destination port."
            )

        # ── Terms & Conditions ──────────────────────────────
        terms = st.text_area(
            "Terms & Conditions",
            value=d.get("terms_conditions", DEFAULT_TERMS),
            key=f"{prefix}_terms", height=100,
            help="Legal clauses printed at the bottom of the quotation PDF."
        )

        # ── Submit Button ───────────────────────────────────
        btn_label = "💾 Update Quotation" if defaults else "🚀 Create & Generate Quotation"
        submitted = st.form_submit_button(btn_label, type="primary", use_container_width=True)

    # Build payload (always returned; caller checks `submitted`)
    payload = {
        "job_type": job_type,
        "customer_name": customer_name.strip(),
        "attention": attention.strip(),
        "tel": tel.strip(),
        "carrier": carrier.strip(),
        "pol": pol.strip(),
        "pod": pod.strip(),
        "quotation_date": quotation_date.isoformat(),
        "validity_date": validity_date.isoformat(),
        "payment_term": payment_term.strip(),
        "commodity": commodity.strip(),
        "subject": subject.strip(),
        "terms_conditions": terms.strip(),
        "created_by": _current_user(),
        "updated_by": _current_user(),
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
        # Items editor lives outside the form (Streamlit forms can't have dynamic rows)
        _init_items("new")
        _render_items_editor("new")

        st.divider()

        # Form fields + submit button
        payload = _quotation_form("new")

        if payload["_submitted"]:
            items = st.session_state.get("new_items", [])
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

        s1, s2, s3 = st.columns([2, 1, 1])
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
                _init_items("edit", defaults=loaded.get("items", []))
                _render_items_editor("edit")

                st.divider()
                edit_payload = _quotation_form("edit", defaults=loaded)

                if edit_payload["_submitted"]:
                    edit_items = st.session_state.get("edit_items", [])
                    errors = _validate_form(edit_payload, edit_items)

                    if errors:
                        for err in errors:
                            st.error(f"⛔ {err}")
                    else:
                        try:
                            items_clean = [
                                {k: v for k, v in it.items() if k != "uid"}
                                for it in edit_items
                            ]
                            update_quotation(target_no, edit_payload, items_clean)

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