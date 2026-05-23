"""Profit Sheet view - AR/AP cost lines + sign-off PDF generation."""
import streamlit as st
import pandas as pd
from datetime import datetime

from managers.shipment_manager import list_shipments
from managers.profit_manager import (
    AR_CATEGORIES, AP_CATEGORIES,
    add_cost_line, delete_cost_line,
    get_cost_lines, get_profit_summary,
    create_profit_sheet, list_profit_sheets, update_signoff,
)
from managers.fx_manager import SUPPORTED_CURRENCIES
from managers.auth_manager import can_write

def role_has_approve(user) -> bool:
    return user.get("role") in ("admin", "accounting")

def render():
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "shipment") or can_write(role, "billing")
    
    st.title("📊 Job Profitability Sheet")
    
    # Reset PDF preview เมื่อเปลี่ยน Job
    if "prev_shipment" not in st.session_state:
        st.session_state.prev_shipment = None
    
    # ===== Select Shipment =====
    ships = list_shipments()
    if not ships:
        st.info("No shipments to analyze.")
        return
    
    options = {f"{s['job_no']} — {s.get('customer_name','—')}": s for s in ships[:200]}
    sel_label = st.selectbox("Select Shipment", list(options.keys()), key="ps_sel")
    ship = options[sel_label]
    
    # ล้างไฟล์ PDF เก่าเมื่อเปลี่ยน Shipment
    if st.session_state.prev_shipment != ship["id"]:
        if "latest_ps_pdf" in st.session_state:
            del st.session_state["latest_ps_pdf"]
        st.session_state.prev_shipment = ship["id"]
    
    # ===== Job header info =====
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Job No.", ship["job_no"])
    c2.metric("Customer", (ship.get("customer_name") or "—")[:15])
    c3.metric("Status", ship.get("status", "Proceed"))
    c4.metric("Container", ship.get("container_no") or "—")
    
    st.markdown("---")
    
    # ===== Profit Summary KPI =====
    summary = get_profit_summary(ship["id"])
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Revenue (AR)", f"฿{summary['total_ar']:,.0f}")
    s2.metric("Cost (AP)", f"฿{summary['total_ap']:,.0f}")
    net = summary["net_profit"]
    s3.metric("Net Profit", f"฿{net:,.0f}", delta=f"{summary['profit_margin']:.1f}%")
    s4.metric("Status", "🟢 Profit" if net >= 0 else "🔴 Loss")
    
    st.markdown("---")
    
    # ===== AR/AP Cost Tables =====
    tab_ar, tab_ap, tab_sheets = st.tabs(["💰 AR", "💸 AP", "📋 Profit Sheets"])
    
    with tab_ar:
        _render_cost_section(ship, "AR", AR_CATEGORIES, can_edit, user)
    with tab_ap:
        _render_cost_section(ship, "AP", AP_CATEGORIES, can_edit, user)
    with tab_sheets:
        _render_sheets_section(ship, summary, can_edit, user)

def _render_cost_section(ship, cost_type, categories, can_edit, user):
    lines = get_cost_lines(ship["id"], cost_type)
    
    if can_edit:
        with st.expander(f"➕ Add {cost_type} Line"):
            with st.form(f"add_{cost_type}"):
                c1, c2 = st.columns(2)
                cat = c1.selectbox("Category", categories)
                desc = c1.text_input("Description")
                qty = c2.number_input("Quantity", min_value=0.0, value=1.0)
                price = c2.number_input("Unit Price", min_value=0.0, format="%.2f")
                
                if st.form_submit_button("Add Line"):
                    add_cost_line({
                        "shipment_id": ship["id"], "cost_type": cost_type,
                        "category": cat, "description": desc,
                        "quantity": qty, "unit_price": price,
                        "amount": qty * price, "created_by": user.get("username")
                    })
                    st.rerun()

    if lines:
        df = pd.DataFrame(lines)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        if can_edit:
            del_id = st.selectbox(f"Select to delete", [(l["id"], l["description"]) for l in lines], 
                                  format_func=lambda x: x[1], key=f"del_{cost_type}")
            if st.button(f"🗑 Delete", key=f"btn_del_{cost_type}"):
                delete_cost_line(del_id[0])
                st.rerun()

def _render_sheets_section(ship, summary, can_edit, user):
    sheets = list_profit_sheets(ship["id"])
    
    if can_edit:
        if st.button("🚀 Generate Profit Sheet PDF", type="primary"):
            with st.status("Generating PDF...", expanded=True) as status:
                try:
                    from pdf.profit_pdf import generate_profit_pdf
                    sheet = create_profit_sheet(ship["id"], prepared_by=user.get("full_name"))
                    ar = get_cost_lines(ship["id"], "AR")
                    ap = get_cost_lines(ship["id"], "AP")
                    pdf_path = generate_profit_pdf(ship, ar, ap, summary, sheet)
                    
                    with open(pdf_path, "rb") as f:
                        st.session_state["latest_ps_pdf"] = {"data": f.read(), "name": f"{sheet['sheet_no']}.pdf"}
                    status.update(label="✅ Success!", state="complete")
                except Exception as e:
                    st.error(f"Error: {e}")

    if "latest_ps_pdf" in st.session_state:
        pdf = st.session_state["latest_ps_pdf"]
        st.download_button("📥 Download Generated PDF", pdf["data"], pdf["name"], use_container_width=True)

    for s in sheets:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.markdown(f"**{s['sheet_no']}**")
            c2.metric("Net", f"฿{s.get('net_profit', 0):,.0f}")
            if can_edit:
                if not s.get("reviewed_by"):
                    if c3.button("👁 Review", key=f"rev_{s['id']}"):
                        update_signoff(s["id"], "review", user.get("full_name"))
                        st.rerun()
                elif not s.get("approved_by") and role_has_approve(user):
                    if c3.button("✅ Approve", key=f"app_{s['id']}"):
                        update_signoff(s["id"], "approve", user.get("full_name"))
                        st.rerun()