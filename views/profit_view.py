"""Profit Sheet view - AR/AP cost lines + sign-off PDF generation."""
import streamlit as st
import pandas as pd
from datetime import datetime

from managers.shipment_manager import list_shipments, get_shipment
from managers.profit_manager import (
    AR_CATEGORIES, AP_CATEGORIES,
    add_cost_line, update_cost_line, delete_cost_line,
    get_cost_lines, get_profit_summary,
    create_profit_sheet, list_profit_sheets, has_profit_sheet,
    update_signoff,
)
from managers.fx_manager import SUPPORTED_CURRENCIES
from managers.auth_manager import can_write


def render():
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "shipment") or can_write(role, "billing")
    
    st.title("📊 Job Profitability Sheet")
    st.caption("AR (Revenue) vs AP (Cost) breakdown · Sign-off workflow before Closing job")
    
    # ===== Select Shipment =====
    ships = list_shipments()
    if not ships:
        st.info("No shipments to analyze. Create one in the Shipment module.")
        return
    
    options = {f"{s['job_no']} — {s.get('customer_name','—')}  "
               f"({s.get('pol','?')} → {s.get('pod','?')})": s
               for s in ships[:200]}
    sel_label = st.selectbox("Select Shipment", list(options.keys()),
                              key="ps_sel")
    ship = options[sel_label]
    
    # ===== Job header info =====
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Job No.", ship["job_no"])
    with c2:
        st.metric("Customer", (ship.get("customer_name") or "—")[:20])
    with c3:
        st.metric("Status", ship.get("status", "Proceed"))
    with c4:
        st.metric("Container", ship.get("container_no") or "—")
    
    st.markdown("---")
    
    # ===== Profit Summary KPI =====
    summary = get_profit_summary(ship["id"])
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Revenue (AR)", f"฿{summary['total_ar']:,.0f}")
    with s2:
        st.metric("Cost (AP)", f"฿{summary['total_ap']:,.0f}")
    with s3:
        net = summary["net_profit"]
        st.metric("Net Profit",
            f"฿{net:,.0f}",
            delta=f"{summary['profit_margin']:.2f}%",
            delta_color="normal" if net >= 0 else "inverse")
    with s4:
        margin = summary["profit_margin"]
        margin_color = "🟢 Profit" if net >= 0 else "🔴 Loss"
        st.metric("Status", margin_color)
    
    st.markdown("---")
    
    # ===== AR/AP Cost Tables =====
    tab_ar, tab_ap, tab_sheets = st.tabs([
        "💰 Account Receivables (AR)",
        "💸 Account Payables (AP)",
        "📋 Profit Sheets",
    ])
    
    with tab_ar:
        _render_cost_section(ship, "AR", AR_CATEGORIES, can_edit, user)
    
    with tab_ap:
        _render_cost_section(ship, "AP", AP_CATEGORIES, can_edit, user)
    
    with tab_sheets:
        _render_sheets_section(ship, summary, can_edit, user)


def _render_cost_section(ship, cost_type, categories, can_edit, user):
    """Render AR or AP cost lines + add/edit form."""
    label = "Revenue" if cost_type == "AR" else "Cost"
    icon = "💰" if cost_type == "AR" else "💸"
    
    lines = get_cost_lines(ship["id"], cost_type)
    
    # Add new line
    if can_edit:
        with st.expander(f"➕ Add {cost_type} Line", expanded=False):
            with st.form(f"add_{cost_type}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    category = st.selectbox(f"{label} Category",
                        categories, key=f"add_{cost_type}_cat")
                    description = st.text_input("Description",
                        key=f"add_{cost_type}_desc")
                    supplier = st.text_input(
                        "Customer" if cost_type == "AR" else "Supplier",
                        key=f"add_{cost_type}_sup")
                with c2:
                    quantity = st.number_input("Quantity",
                        min_value=0.0, value=1.0,
                        key=f"add_{cost_type}_qty")
                    unit_price = st.number_input("Unit Price",
                        min_value=0.0, value=0.0, format="%.2f",
                        key=f"add_{cost_type}_up")
                    currency = st.selectbox("Currency",
                        SUPPORTED_CURRENCIES, index=0,
                        key=f"add_{cost_type}_cur")
                with c3:
                    amount = st.number_input("Total Amount",
                        min_value=0.0, value=quantity * unit_price,
                        format="%.2f", key=f"add_{cost_type}_amt",
                        help="Auto = Qty × Unit Price (override if needed)")
                    remark = st.text_input("Remark",
                        key=f"add_{cost_type}_rmk")
                
                submit = st.form_submit_button(
                    f"💾 Add {cost_type}", type="primary",
                    use_container_width=True)
            
            if submit:
                add_cost_line({
                    "shipment_id": ship["id"],
                    "cost_type": cost_type,
                    "category": category,
                    "description": description,
                    "supplier": supplier,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "amount": amount,
                    "currency": currency,
                    "remark": remark,
                    "created_by": user.get("username"),
                })
                st.success(f"Added {cost_type} line")
                st.rerun()
    
    # Display existing lines
    if not lines:
        st.info(f"No {cost_type} lines yet. Add one above.")
        return
    
    st.markdown(f"##### {icon} {label} Lines ({len(lines)})")
    df = pd.DataFrame(lines)
    cols = ["category", "description", "supplier",
            "quantity", "unit_price", "amount", "currency", "amount_thb"]
    cols = [c for c in cols if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True,
        column_config={
            "amount_thb": st.column_config.NumberColumn(
                "THB-Equiv", format="฿%.2f"),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
            "unit_price": st.column_config.NumberColumn(
                "Unit Price", format="%.2f"),
        })
    
    # Delete option
    if can_edit and lines:
        sel_id = st.selectbox(
            f"Delete {cost_type} line",
            [(l["id"], f"#{l['id']} {l.get('category','')} - {l.get('description','')[:30]}")
             for l in lines],
            format_func=lambda x: x[1],
            key=f"del_{cost_type}_sel")
        if st.button(f"🗑️ Delete selected {cost_type} line",
                       key=f"del_{cost_type}_btn"):
            delete_cost_line(sel_id[0])
            st.success("Deleted")
            st.rerun()


def _render_sheets_section(ship, summary, can_edit, user):
    """Render profit sheets list + Generate button."""
    sheets = list_profit_sheets(ship["id"])
    
    # Generate new sheet
    if can_edit:
        with st.container():
            st.markdown("##### 📄 Generate New Profit Sheet")
            
            ar_lines = get_cost_lines(ship["id"], "AR")
            ap_lines = get_cost_lines(ship["id"], "AP")
            
            if not ar_lines and not ap_lines:
                st.warning("⚠️ No AR or AP lines added yet. "
                          "Add at least one line before generating.")
            else:
                col_btn, col_info = st.columns([2, 3])
                with col_btn:
                    if st.button("🚀 Generate Profit Sheet PDF",
                                  type="primary",
                                  use_container_width=True):
                        try:
                            from pdf.profit_pdf import generate_profit_pdf
                            
                            # Create record first
                            sheet = create_profit_sheet(
                                ship["id"],
                                prepared_by=user.get("full_name") or user.get("username"),
                            )
                            
                            # Generate PDF
                            pdf_path = generate_profit_pdf(
                                ship, ar_lines, ap_lines, summary, sheet
                            )
                            
                            with open(pdf_path, "rb") as f:
                                st.session_state["latest_ps_pdf"] = {
                                    "data": f.read(),
                                    "name": f"{sheet['sheet_no']}.pdf"
                                }
                            st.success(f"✅ Generated {sheet['sheet_no']}")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"PDF generation failed: {ex}")
                with col_info:
                    st.info("Sign-off Order: Prepared (CS/Ops) → "
                            "Reviewed (Sales) → Approved (Management)")
    
    # Show download for latest generated
    if "latest_ps_pdf" in st.session_state:
        pdf_info = st.session_state["latest_ps_pdf"]
        st.download_button(f"📥 Download {pdf_info['name']}",
            pdf_info["data"], pdf_info["name"], "application/pdf",
            type="primary", use_container_width=True)
    
    st.markdown("---")
    
    # List existing sheets
    if not sheets:
        st.info("No profit sheets generated yet.")
        return
    
    st.markdown("##### 📋 Existing Sheets")
    for s in sheets:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            with c1:
                st.markdown(f"**{s['sheet_no']}**")
                st.caption(f"Generated: {s.get('created_at','')[:16]}")
            with c2:
                profit = s.get("net_profit", 0)
                color = "#26B574" if profit >= 0 else "#E5484D"
                st.markdown(f"<div style='color:{color};font-weight:600'>"
                           f"Net: ฿{profit:,.2f}</div>",
                           unsafe_allow_html=True)
                st.caption(f"Margin: {s.get('profit_margin', 0):.2f}%")
            with c3:
                prep = s.get("prepared_by") or "—"
                rev = s.get("reviewed_by") or "Pending"
                app = s.get("approved_by") or "Pending"
                st.markdown(f"<small>"
                           f"📝 Prep: {prep}<br/>"
                           f"👁 Review: {rev}<br/>"
                           f"✅ Approve: {app}"
                           f"</small>", unsafe_allow_html=True)
            with c4:
                if can_edit:
                    if not s.get("reviewed_by"):
                        if st.button("👁 Review",
                                      key=f"rev_{s['id']}",
                                      use_container_width=True):
                            update_signoff(s["id"], "review",
                                user.get("full_name") or user.get("username"))
                            st.success("Reviewed")
                            st.rerun()
                    elif not s.get("approved_by") and role_has_approve(user):
                        if st.button("✅ Approve",
                                      key=f"app_{s['id']}",
                                      use_container_width=True):
                            update_signoff(s["id"], "approve",
                                user.get("full_name") or user.get("username"))
                            st.success("Approved")
                            st.rerun()


def role_has_approve(user) -> bool:
    """Only admin/accounting can approve."""
    return user.get("role") in ("admin", "accounting")
