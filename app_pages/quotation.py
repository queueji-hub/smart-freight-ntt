"""Streamlit page: create, edit, copy, and download quotation PDFs.

This page MUST be importable even if optional dependencies (reportlab, etc.) fail.
"""
import streamlit as st
from datetime import date, timedelta
import pandas as pd

# Critical imports - if these fail, show error but don't crash page registration
_IMPORT_ERROR = None
try:
    from config import JOB_TYPES, DEFAULT_TERMS
    from database.connection import init_database
    from managers.quotation_manager import (
        create_quotation, get_quotation_by_no, list_quotations,
        update_quotation, duplicate_quotation,
    )
    from managers.customer_manager import (
        search_customers, get_customer_by_name, list_customers,
    )
    from utils.nav import setup_sidebar
except Exception as _e:
    _IMPORT_ERROR = f"Import error: {_e}"

# PDF generator is optional - if reportlab fails, disable PDF features
_PDF_AVAILABLE = True
_PDF_ERROR = None
try:
    from pdf.quotation_pdf import generate_quotation_pdf
except Exception as _e:
    _PDF_AVAILABLE = False
    _PDF_ERROR = str(_e)
    def generate_quotation_pdf(*args, **kwargs):
        raise RuntimeError(f"PDF generation not available: {_PDF_ERROR}")


# Show critical errors but still render the page
if _IMPORT_ERROR:
    st.error(f"⚠️ {_IMPORT_ERROR}")
    st.stop()

# Initialize DB and sidebar
try:
    init_database()
except Exception as e:
    st.warning(f"Database init: {e}")

setup_sidebar()
st.title("📄 Quotation Management")

if not _PDF_AVAILABLE:
    st.warning(f"📄 PDF generation disabled: {_PDF_ERROR}")

tab_create, tab_all = st.tabs(["➕ Create New", "📋 All Quotations"])


def _customer_autocomplete(prefix, default_value=""):
    """Customer name input with autocomplete dropdown."""
    typed = st.text_input(
        "Customer * (พิมพ์เพื่อค้นหา)",
        value=default_value,
        key=f"{prefix}_cust_search",
        help="พิมพ์ชื่อบางส่วน เช่น 'Sun' จะแสดงรายชื่อลูกค้าที่เคยใช้",
    )
    
    if typed and typed.strip() and len(typed.strip()) >= 2:
        try:
            matches = search_customers(typed)
        except Exception:
            matches = []
        if matches:
            options = [""] + [m["company_name"] for m in matches]
            picked = st.selectbox(
                f"💡 พบลูกค้า {len(matches)} รายชื่อ — เลือกเพื่อใช้:",
                options, index=0,
                key=f"{prefix}_cust_pick",
            )
            if picked:
                st.session_state[f"{prefix}_picked_customer"] = picked
                cust = get_customer_by_name(picked)
                if cust:
                    st.session_state[f"{prefix}_picked_attention"] = cust.get("contact_person", "") or ""
                    st.session_state[f"{prefix}_picked_tel"] = cust.get("tel", "") or ""
                return picked
    
    return typed


def _quotation_form(prefix, defaults=None):
    """Reusable quotation form."""
    d = defaults or {}
    
    col1, col2 = st.columns(2)
    with col1:
        job_type = st.selectbox(
            "Job Type *", options=list(JOB_TYPES.keys()),
            format_func=lambda k: f"{k} — {JOB_TYPES[k]}",
            index=list(JOB_TYPES.keys()).index(d.get("job_type", "SI"))
                if d.get("job_type") in JOB_TYPES else 1,
            key=f"{prefix}_job_type",
        )
        
        cust_default = st.session_state.get(
            f"{prefix}_picked_customer", d.get("customer_name", "")
        )
        customer_name = _customer_autocomplete(prefix, cust_default)
        
        shipper_cnee = st.text_input("Shpr/Cnee",
            value=d.get("shipper_cnee", ""), key=f"{prefix}_shipper")
        carrier = st.text_input("Carrier",
            value=d.get("carrier", ""), key=f"{prefix}_carrier")
        pol = st.text_input("POL",
            value=d.get("pol", ""), key=f"{prefix}_pol")
        pod = st.text_input("POD",
            value=d.get("pod", ""), key=f"{prefix}_pod")
        
        attn_default = st.session_state.get(
            f"{prefix}_picked_attention", d.get("attention", "")
        )
        attention = st.text_input("Attention",
            value=attn_default, key=f"{prefix}_attn")
        
        tel_default = st.session_state.get(
            f"{prefix}_picked_tel", d.get("tel", "")
        )
        tel = st.text_input("Tel.",
            value=tel_default, key=f"{prefix}_tel")
        
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
        "job_type": job_type,
        "customer_name": customer_name,
        "shipper_cnee": shipper_cnee,
        "carrier": carrier, "pol": pol, "pod": pod,
        "service_type": service_type,
        "attention": attention, "tel": tel, "incoterm": incoterm,
        "commodity": commodity, "weight": weight,
        "quantity_desc": quantity_desc, "payment_term": payment_term,
        "quotation_date": quotation_date.isoformat(),
        "validity_date": validity_date.isoformat(),
        "subject": subject, "terms_conditions": terms,
    }, items_df


def _items_editor(prefix, d):
    """Items editor with row controls."""
    st.markdown("---")
    st.subheader("Quotation Items")
    st.caption("⬆/⬇ เลื่อน · ⤴ แทรกข้างบน · ⤵ แทรกข้างล่าง · 🗑 ลบ")
    
    items_key = f"{prefix}_items_list"
    if items_key not in st.session_state:
        if d.get("items"):
            st.session_state[items_key] = [
                {"description": i.get("description", "") or "",
                 "currency": i.get("currency", "USD") or "USD",
                 "price": float(i.get("price", 0) or 0),
                 "unit": i.get("unit", "") or "",
                 "remark": i.get("remark", "") or ""}
                for i in d["items"]
            ]
        else:
            st.session_state[items_key] = [
                {"description": "", "currency": "USD", "price": 0.0,
                 "unit": "", "remark": ""}
            ]
    
    items = st.session_state[items_key]
    
    h = st.columns([3, 0.8, 1, 0.8, 2, 0.4, 0.4, 0.4, 0.4, 0.4])
    h[0].markdown("**Description**")
    h[1].markdown("<div style='text-align:center'><b>CURR</b></div>",
                  unsafe_allow_html=True)
    h[2].markdown("<div style='text-align:center'><b>Price</b></div>",
                  unsafe_allow_html=True)
    h[3].markdown("<div style='text-align:center'><b>Unit</b></div>",
                  unsafe_allow_html=True)
    h[4].markdown("**Remark**")
    h[5].markdown("**⬆**")
    h[6].markdown("**⬇**")
    h[7].markdown("**⤴**")
    h[8].markdown("**⤵**")
    h[9].markdown("**🗑**")
    
    for i in range(len(items)):
        c = st.columns([3, 0.8, 1, 0.8, 2, 0.4, 0.4, 0.4, 0.4, 0.4])
        items[i]["description"] = c[0].text_input(
            "d", value=items[i].get("description", ""),
            key=f"{prefix}_desc_{i}", label_visibility="collapsed")
        items[i]["currency"] = c[1].selectbox(
            "c", ["USD","THB","CNY","EUR"],
            index=["USD","THB","CNY","EUR"].index(items[i].get("currency","USD"))
                if items[i].get("currency") in ["USD","THB","CNY","EUR"] else 0,
            key=f"{prefix}_cur_{i}", label_visibility="collapsed")
        items[i]["price"] = c[2].number_input(
            "p", value=float(items[i].get("price",0)), min_value=0.0,
            format="%.2f", key=f"{prefix}_p_{i}", label_visibility="collapsed")
        items[i]["unit"] = c[3].text_input(
            "u", value=items[i].get("unit","") or "",
            key=f"{prefix}_u_{i}", label_visibility="collapsed")
        items[i]["remark"] = c[4].text_input(
            "r", value=items[i].get("remark","") or "",
            key=f"{prefix}_r_{i}", label_visibility="collapsed")
        
        if c[5].button("⬆", key=f"{prefix}_up_{i}", disabled=(i==0),
                        help="เลื่อนขึ้น"):
            items[i-1], items[i] = items[i], items[i-1]
            st.rerun()
        if c[6].button("⬇", key=f"{prefix}_dn_{i}", disabled=(i==len(items)-1),
                        help="เลื่อนลง"):
            items[i+1], items[i] = items[i], items[i+1]
            st.rerun()
        if c[7].button("⤴", key=f"{prefix}_insup_{i}", help="แทรกข้างบน"):
            items.insert(i, {"description":"","currency":"USD",
                             "price":0.0,"unit":"","remark":""})
            st.rerun()
        if c[8].button("⤵", key=f"{prefix}_insdn_{i}", help="แทรกข้างล่าง"):
            items.insert(i+1, {"description":"","currency":"USD",
                               "price":0.0,"unit":"","remark":""})
            st.rerun()
        if c[9].button("🗑", key=f"{prefix}_del_{i}",
                        disabled=(len(items)<=1), help="ลบ"):
            items.pop(i)
            st.rerun()
    
    if st.button("➕ Add Item at End", key=f"{prefix}_add_end"):
        items.append({"description":"","currency":"USD",
                      "price":0.0,"unit":"","remark":""})
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


# =================== CREATE TAB ===================
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


# =================== ALL QUOTATIONS TAB ===================
with tab_all:
    st.subheader("📋 All Quotations")
    
    search_col1, search_col2 = st.columns([2, 3])
    with search_col1:
        search_qno = st.text_input(
            "🔍 ค้นหา Quotation No.",
            placeholder="เช่น SI26050004",
            key="search_qno",
        )
    with search_col2:
        filter_type = st.selectbox(
            "Filter by Job Type",
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
        
        sel_col, act_col1, act_col2, act_col3 = st.columns([3, 1, 1, 1])
        with sel_col:
            sel_qno = st.selectbox(
                "เลือก Quotation",
                df["quotation_no"].tolist(), key="all_sel")
        with act_col1:
            st.write(""); st.write("")
            view_btn = st.button("📥 PDF", use_container_width=True, disabled=not _PDF_AVAILABLE)
        with act_col2:
            st.write(""); st.write("")
            edit_btn = st.button("✏️ Edit", use_container_width=True)
        with act_col3:
            st.write(""); st.write("")
            copy_btn = st.button("📑 Copy", use_container_width=True)
        
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
        
        if st.session_state.get("edit_loaded"):
            loaded = get_quotation_by_no(st.session_state["edit_loaded"])
            if loaded:
                st.markdown("---")
                st.markdown(f"### ✏️ Editing: `{loaded['quotation_no']}`")
                
                if st.button("❌ Close Editor", key="btn_close_edit"):
                    _clear_form_state("edit")
                    del st.session_state["edit_loaded"]
                    st.rerun()
                
                new_qno = st.text_input(
                    "Quotation No. (แก้ไขเลขที่ได้)",
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
                        ok = update_quotation(
                            loaded["quotation_no"], form_data, valid_items,
                            new_quotation_no=new_no_val)
                        if ok:
                            final_no = new_qno.strip()
                            st.session_state["edit_loaded"] = final_no
                            st.success(f"✅ Updated {final_no}")
                            if _PDF_AVAILABLE:
                                saved = get_quotation_by_no(final_no)
                                pdf_path = generate_quotation_pdf(saved, saved["items"])
                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        f"📥 Download updated PDF", f.read(),
                                        f"{final_no}.pdf", "application/pdf",
                                        type="primary")
                        else:
                            st.error("Update failed")
