"""Quotation Management view."""
import streamlit as st
from datetime import date, timedelta
import pandas as pd

from config import JOB_TYPES, DEFAULT_TERMS
from managers.quotation_manager import (
    create_quotation, get_quotation_by_no, list_quotations,
    update_quotation, duplicate_quotation,
)
from managers.customer_manager import (
    search_customers, get_customer_by_name,
)
from managers.booking_manager import create_booking
from managers.auth_manager import can_write

# PDF generator (optional)
_PDF_AVAILABLE = True
_PDF_ERROR = None
try:
    from pdf.quotation_pdf import generate_quotation_pdf
except Exception as _e:
    _PDF_AVAILABLE = False
    _PDF_ERROR = str(_e)


QUOTATION_STATUS = ["Draft", "Sent", "Accepted", "Rejected", "Expired"]


def _on_customer_picked(prefix: str):
    """Callback fired when user picks a customer from the dropdown.
    
    Explicitly sets all related widget session_state keys so the form
    fields update instantly on the next rerun (no manual refresh needed).
    """
    pick_key = f"{prefix}_cust_pick"
    picked = st.session_state.get(pick_key, "")
    if not picked:
        return
    
    cust = get_customer_by_name(picked)
    if not cust:
        return
    
    # Write directly to widget keys so the inputs auto-populate
    st.session_state[f"{prefix}_cust_search"] = picked
    st.session_state[f"{prefix}_attn"] = cust.get("contact_person") or ""
    st.session_state[f"{prefix}_tel"] = cust.get("tel") or ""
    # Also persist for re-use
    st.session_state[f"{prefix}_picked_customer"] = picked
    st.session_state[f"{prefix}_picked_attention"] = cust.get("contact_person") or ""
    st.session_state[f"{prefix}_picked_tel"] = cust.get("tel") or ""
    st.session_state[f"{prefix}_picked_email"] = cust.get("email") or ""
    st.session_state[f"{prefix}_picked_address"] = cust.get("address") or ""
    st.session_state[f"{prefix}_picked_tax_id"] = cust.get("tax_id") or ""


def _customer_autocomplete(prefix, default_value=""):
    """Customer search + auto-fill all contact fields when one is picked."""
    search_key = f"{prefix}_cust_search"
    
    # Initialize default value if not yet set
    if search_key not in st.session_state and default_value:
        st.session_state[search_key] = default_value
    
    typed = st.text_input(
        "Customer * (พิมพ์เพื่อค้นหา)",
        key=search_key,
        help="พิมพ์ชื่อบางส่วน เช่น 'Sun' จะแสดงรายชื่อลูกค้าที่เคยใช้ — "
             "เลือกแล้วระบบจะเติม Contact Person และ Tel ให้อัตโนมัติ",
    )
    
    if typed and typed.strip() and len(typed.strip()) >= 2:
        try:
            matches = search_customers(typed)
        except Exception:
            matches = []
        
        # If exact match exists, don't show dropdown
        exact_match = any(
            m["company_name"].strip().lower() == typed.strip().lower()
            for m in matches
        )
        
        if matches and not exact_match:
            options = [""] + [m["company_name"] for m in matches]
            st.selectbox(
                f"💡 พบลูกค้า {len(matches)} ราย — เลือกเพื่อ auto-fill:",
                options, index=0,
                key=f"{prefix}_cust_pick",
                on_change=_on_customer_picked,
                args=(prefix,),
            )
        elif exact_match:
            # User has a complete match → show subtle confirmation + auto-fill once
            cust = get_customer_by_name(typed)
            if cust and not st.session_state.get(f"{prefix}_autofilled_for") == typed:
                # Only auto-fill if the input fields are empty (don't overwrite manual edits)
                if not st.session_state.get(f"{prefix}_attn"):
                    st.session_state[f"{prefix}_attn"] = cust.get("contact_person") or ""
                if not st.session_state.get(f"{prefix}_tel"):
                    st.session_state[f"{prefix}_tel"] = cust.get("tel") or ""
                st.session_state[f"{prefix}_autofilled_for"] = typed
                st.rerun()
            st.caption(f"✅ ลูกค้า: **{typed}** "
                       f"(Contact: {cust.get('contact_person','—') if cust else '—'} · "
                       f"Tel: {cust.get('tel','—') if cust else '—'})")
    
    return typed


def _quotation_form(prefix, defaults=None):
    d = defaults or {}
    
    # Initialize Attention/Tel from defaults (for Edit mode)
    if d.get("attention") and f"{prefix}_attn" not in st.session_state:
        st.session_state[f"{prefix}_attn"] = d.get("attention", "")
    if d.get("tel") and f"{prefix}_tel" not in st.session_state:
        st.session_state[f"{prefix}_tel"] = d.get("tel", "")
    
    col1, col2 = st.columns(2)
    with col1:
        job_type = st.selectbox(
            "Job Type *", options=list(JOB_TYPES.keys()),
            format_func=lambda k: f"{k} — {JOB_TYPES[k]}",
            index=list(JOB_TYPES.keys()).index(d.get("job_type", "SI"))
                if d.get("job_type") in JOB_TYPES else 1,
            key=f"{prefix}_job_type",
        )
        # Customer search → auto-fills Attention + Tel via callback
        customer_name = _customer_autocomplete(prefix, d.get("customer_name", ""))
        
        shipper_cnee = st.text_input("Shpr/Cnee",
            value=d.get("shipper_cnee", ""), key=f"{prefix}_shipper")
        carrier = st.text_input("Carrier",
            value=d.get("carrier", ""), key=f"{prefix}_carrier")
        pol = st.text_input("POL", value=d.get("pol", ""), key=f"{prefix}_pol")
        pod = st.text_input("POD", value=d.get("pod", ""), key=f"{prefix}_pod")
        
        # These read from session_state set by the customer auto-fill callback
        attention = st.text_input(
            "Attention (Contact Person)",
            key=f"{prefix}_attn",
            help="Auto-filled when customer is selected"
        )
        tel = st.text_input(
            "Tel.",
            key=f"{prefix}_tel",
            help="Auto-filled when customer is selected"
        )
        incoterm = st.text_input("Incoterm",
            value=d.get("incoterm", ""), key=f"{prefix}_incoterm")
    with col2:
        q_date = d.get("quotation_date")
        if isinstance(q_date, str) and q_date:
            q_date = date.fromisoformat(q_date)
        quotation_date = st.date_input("Quotation Date *",
            value=q_date or date.today(), key=f"{prefix}_qdate")
        v_date = d.get("validity_date")
        if isinstance(v_date, str) and v_date:
            v_date = date.fromisoformat(v_date)
        validity_date = st.date_input("Validity Date *",
            value=v_date or (date.today() + timedelta(days=30)),
            key=f"{prefix}_vdate")
        payment_term = st.text_input("Payment Term",
            value=d.get("payment_term", ""), key=f"{prefix}_payment")
        service_type = st.text_input("Service Type",
            value=d.get("service_type", ""), key=f"{prefix}_svc")
        commodity = st.text_input("Commodity",
            value=d.get("commodity", ""), key=f"{prefix}_commodity")
        weight = st.text_input("Weight",
            value=d.get("weight", ""), key=f"{prefix}_weight")
        quantity_desc = st.text_input("Quantity",
            value=d.get("quantity_desc", ""), key=f"{prefix}_qty")
        subject = st.text_input("Subject",
            value=d.get("subject", ""), key=f"{prefix}_subject")

    items_df = _items_editor(prefix, d)
    st.markdown("---")
    st.subheader("Terms & Conditions")
    terms = st.text_area("Terms (one per line)",
        value=d.get("terms_conditions") or DEFAULT_TERMS,
        height=200, key=f"{prefix}_terms")

    return {
        "job_type": job_type, "customer_name": customer_name,
        "shipper_cnee": shipper_cnee, "carrier": carrier, "pol": pol, "pod": pod,
        "service_type": service_type, "attention": attention, "tel": tel,
        "incoterm": incoterm, "commodity": commodity, "weight": weight,
        "quantity_desc": quantity_desc, "payment_term": payment_term,
        "quotation_date": quotation_date.isoformat(),
        "validity_date": validity_date.isoformat(),
        "subject": subject, "terms_conditions": terms,
    }, items_df


def _items_editor(prefix, d):
    st.markdown("---")
    st.subheader("Quotation Items")
    st.caption("กรอกรายการ · กด 🗑 เพื่อลบ · กด ➕ เพื่อเพิ่มท้าย")
    
    import uuid
    
    items_key = f"{prefix}_items_list"
    
    def _empty_row():
        return {
            "id": str(uuid.uuid4())[:8],
            "description": "",
            "currency": "USD",
            "price": 0.0,
            "unit": "",
            "remark": "",
        }
    
    if items_key not in st.session_state:
        if d.get("items"):
            st.session_state[items_key] = [
                {
                    "id": str(uuid.uuid4())[:8],
                    "description": i.get("description", "") or "",
                    "currency": i.get("currency", "USD") or "USD",
                    "price": float(i.get("price", 0) or 0),
                    "unit": i.get("unit", "") or "",
                    "remark": i.get("remark", "") or "",
                }
                for i in d["items"]]
        else:
            st.session_state[items_key] = [_empty_row()]
    
    items = st.session_state[items_key]
    
    # Ensure every existing row has an id (migrate if loaded from old data)
    for it in items:
        if not it.get("id"):
            it["id"] = str(uuid.uuid4())[:8]
    
    def _sync_from_widgets():
        """Read widget values back into items list (by row id)."""
        for row in st.session_state[items_key]:
            rid = row["id"]
            for field, suffix in [
                ("description", "desc"), ("currency", "cur"),
                ("price", "p"), ("unit", "u"), ("remark", "r"),
            ]:
                wkey = f"{prefix}_{suffix}_{rid}"
                if wkey in st.session_state:
                    row[field] = st.session_state[wkey]
    
    # Header row — wider Unit column (1.4 instead of 0.8)
    h = st.columns([3, 0.9, 1.1, 1.4, 2, 0.4])
    h[0].markdown("**Description**")
    h[1].markdown("<div style='text-align:center'><b>CURR</b></div>",
                  unsafe_allow_html=True)
    h[2].markdown("<div style='text-align:center'><b>Price</b></div>",
                  unsafe_allow_html=True)
    h[3].markdown("<div style='text-align:center'><b>Unit</b></div>",
                  unsafe_allow_html=True)
    h[4].markdown("**Remark**")
    h[5].markdown("**🗑**")
    
    # Track which row to delete (process AFTER all widgets render)
    delete_id = None
    
    for row in items:
        rid = row["id"]
        c = st.columns([3, 0.9, 1.1, 1.4, 2, 0.4])
        c[0].text_input("d", value=row.get("description", ""),
            key=f"{prefix}_desc_{rid}", label_visibility="collapsed")
        c[1].selectbox("c", ["USD", "THB", "CNY", "EUR"],
            index=["USD","THB","CNY","EUR"].index(row.get("currency","USD"))
                if row.get("currency") in ["USD","THB","CNY","EUR"] else 0,
            key=f"{prefix}_cur_{rid}", label_visibility="collapsed")
        c[2].number_input("p", value=float(row.get("price", 0)),
            min_value=0.0, format="%.2f",
            key=f"{prefix}_p_{rid}", label_visibility="collapsed")
        c[3].text_input("u", value=row.get("unit", "") or "",
            key=f"{prefix}_u_{rid}", label_visibility="collapsed",
            placeholder="e.g. /Container, /Job")
        c[4].text_input("r", value=row.get("remark", "") or "",
            key=f"{prefix}_r_{rid}", label_visibility="collapsed")
        
        if c[5].button("🗑", key=f"{prefix}_del_{rid}",
                        disabled=(len(items) <= 1), help="ลบรายการนี้"):
            delete_id = rid
    
    # Process delete AFTER all widgets rendered
    if delete_id:
        _sync_from_widgets()
        st.session_state[items_key] = [
            r for r in st.session_state[items_key] if r["id"] != delete_id
        ]
        st.rerun()
    
    # Sync any text edits before returning
    _sync_from_widgets()
    items = st.session_state[items_key]

    if st.button("➕ Add Item at End", key=f"{prefix}_add_end"):
        _sync_from_widgets()
        st.session_state[items_key].append(_empty_row())
        st.rerun()
    return pd.DataFrame(items)


def _extract_valid_items(items_df):
    valid = []
    for _, row in items_df.iterrows():
        desc = str(row.get("description") or "").strip()
        if not desc:
            continue
        try:
            price = float(row.get("price") or 0)
        except (TypeError, ValueError):
            price = 0
        valid.append({
            "description": desc,
            "currency": str(row.get("currency") or "USD"),
            "price": price,
            "unit": str(row.get("unit") or "").strip(),
            "remark": str(row.get("remark") or "").strip(),
        })
    return valid


def _clear_form_state(prefix):
    keys_to_clear = [k for k in st.session_state.keys() if k.startswith(f"{prefix}_")]
    for k in keys_to_clear:
        del st.session_state[k]


def render():
    """Render Quotation Management page."""
    st.title("📄 Quotation Management")
    if not _PDF_AVAILABLE:
        st.warning(f"📄 PDF generation disabled: {_PDF_ERROR}")

    tab_create, tab_all = st.tabs(["➕ Create New", "📋 All Quotations"])

    with tab_create:
        st.subheader("Create New Quotation")
        form_data, items_df = _quotation_form("create")

        if st.button("🚀 Generate Quotation", type="primary", key="btn_create"):
            errors = []
            if not form_data["customer_name"]:
                errors.append("Customer is required")
            if form_data["validity_date"] < form_data["quotation_date"]:
                errors.append("Validity Date must be ≥ Quotation Date")
            valid_items = _extract_valid_items(items_df)
            if not valid_items:
                errors.append("At least one item is required")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    qno = create_quotation(form_data, valid_items)
                    st.success(f"✅ Quotation **{qno}** created!")
                    if _PDF_AVAILABLE:
                        saved = get_quotation_by_no(qno)
                        pdf_path = generate_quotation_pdf(saved, saved["items"])
                        with open(pdf_path, "rb") as f:
                            st.download_button(f"📥 Download {qno}.pdf", f.read(),
                                f"{qno}.pdf", "application/pdf", type="primary")
                except Exception as ex:
                    st.error(f"Failed: {ex}")

    with tab_all:
        st.subheader("📋 All Quotations")

        search_col1, search_col2 = st.columns([2, 3])
        with search_col1:
            search_qno = st.text_input("🔍 ค้นหา Quotation No.",
                placeholder="เช่น SI26050004", key="search_qno")
        with search_col2:
            filter_type = st.selectbox("Filter by Job Type",
                ["All"] + list(JOB_TYPES.keys()), key="all_filter")

        rows = list_quotations(
            job_type=None if filter_type == "All" else filter_type)
        if search_qno and search_qno.strip():
            q = search_qno.strip().lower()
            rows = [r for r in rows if q in r["quotation_no"].lower()]

        if not rows:
            st.info("No quotations found.")
        else:
            df = pd.DataFrame(rows)
            display_cols = ["quotation_no", "job_type", "customer_name", "carrier",
                            "pol", "pod", "quotation_date", "validity_date"]
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True,
                         hide_index=True, height=300)
            st.markdown("---")

            sel_col, act_col1, act_col2, act_col3, act_col4 = st.columns([3, 1, 1, 1, 1.4])
            with sel_col:
                sel_qno = st.selectbox("เลือก Quotation",
                    df["quotation_no"].tolist(), key="all_sel")
            with act_col1:
                st.write(""); st.write("")
                view_btn = st.button("📥 PDF", use_container_width=True,
                                      disabled=not _PDF_AVAILABLE)
            with act_col2:
                st.write(""); st.write("")
                edit_btn = st.button("✏️ Edit", use_container_width=True)
            with act_col3:
                st.write(""); st.write("")
                copy_btn = st.button("📑 Copy", use_container_width=True)
            with act_col4:
                st.write(""); st.write("")
                convert_btn = st.button("➡️ → Booking",
                    use_container_width=True,
                    help="Create Booking Confirmation from this Quotation")

            if view_btn and _PDF_AVAILABLE:
                saved = get_quotation_by_no(sel_qno)
                if saved:
                    pdf_path = generate_quotation_pdf(saved, saved["items"])
                    with open(pdf_path, "rb") as f:
                        st.download_button(f"📥 Download {sel_qno}.pdf", f.read(),
                            f"{sel_qno}.pdf", "application/pdf", type="primary")

            if edit_btn:
                _clear_form_state("edit")
                st.session_state["edit_loaded"] = sel_qno

            if copy_btn:
                new_no = duplicate_quotation(sel_qno)
                if new_no:
                    st.success(f"✅ Duplicated → New Quotation: **{new_no}**")
                    _clear_form_state("edit")
                    st.session_state["edit_loaded"] = new_no
                    st.rerun()
                else:
                    st.error("Duplication failed")
            
            if convert_btn:
                # Convert quotation → booking
                src = get_quotation_by_no(sel_qno)
                if src:
                    user = st.session_state.get("user", {})
                    try:
                        booking_no = create_booking({
                            "job_type": src.get("job_type", "SE"),
                            "customer_name": src.get("customer_name"),
                            "shipper": src.get("shipper_cnee"),
                            "carrier": src.get("carrier"),
                            "pol": src.get("pol"),
                            "pod": src.get("pod"),
                            "commodity": src.get("commodity"),
                            "quotation_id": src.get("id"),
                            "remark": f"From Quotation: {sel_qno}",
                            "created_by": user.get("username"),
                        })
                        st.success(f"✅ Created Booking: **{booking_no}**")
                        st.info(f"Go to Booking page to add CY/CFS details")
                    except Exception as ex:
                        st.error(f"Failed: {ex}")

            if st.session_state.get("edit_loaded"):
                loaded = get_quotation_by_no(st.session_state["edit_loaded"])
                if loaded:
                    st.markdown("---")
                    st.markdown(f"### ✏️ Editing: `{loaded['quotation_no']}`")
                    if st.button("❌ Close Editor", key="btn_close_edit"):
                        _clear_form_state("edit")
                        del st.session_state["edit_loaded"]
                        st.rerun()
                    new_qno = st.text_input("Quotation No. (แก้ไขเลขที่ได้)",
                        value=loaded["quotation_no"], key="edit_new_qno")
                    form_data, items_df = _quotation_form("edit", defaults=loaded)
                    if st.button("💾 Save Changes", type="primary", key="btn_save_edit"):
                        valid_items = _extract_valid_items(items_df)
                        if not valid_items:
                            st.error("At least one item is required")
                        elif not new_qno.strip():
                            st.error("Quotation No. cannot be empty")
                        else:
                            new_no_val = (new_qno.strip()
                                          if new_qno.strip() != loaded["quotation_no"]
                                          else None)
                            ok = update_quotation(loaded["quotation_no"],
                                form_data, valid_items, new_quotation_no=new_no_val)
                            if ok:
                                final_no = new_qno.strip()
                                st.session_state["edit_loaded"] = final_no
                                st.success(f"✅ Updated {final_no}")
                                if _PDF_AVAILABLE:
                                    saved = get_quotation_by_no(final_no)
                                    pdf_path = generate_quotation_pdf(saved, saved["items"])
                                    with open(pdf_path, "rb") as f:
                                        st.download_button(f"📥 Download updated PDF",
                                            f.read(), f"{final_no}.pdf",
                                            "application/pdf", type="primary")
                            else:
                                st.error("Update failed")
