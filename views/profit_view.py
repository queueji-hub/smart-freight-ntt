"""
Job Profitability Sheet - Strategic Financial Reconciliation & Audit Workspace
AR/AP Ledger Cost Controls + Sign-off Pipeline - 100% Professional ERP Grade
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from managers.shipment_manager import list_shipments

# --- SAFE INJECTION & BACKUP FAILOVER GUARD FOR ACCOUNTING CATEGORIES ---
try:
    from managers.profit_manager import (
        add_cost_line, delete_cost_line,
        get_cost_lines, get_profit_summary,
        create_profit_sheet, list_profit_sheets, update_signoff,
    )
    # พยายามโหลดหมวดหมู่ หากโหลดไม่ได้จะไปทำที่บล็อก exceptด้านล่าง
    from managers.profit_manager import AR_CATEGORIES, AP_CATEGORIES
except ImportError:
    # Local Failover Memory Array Injections ในกรณีที่หลังบ้านไม่ได้ประกาศตัวแปรไว้
    AR_CATEGORIES = ["Ocean Freight Revenue", "Local Terminal Charges (AR)", "Customs Clearance Service", "Inland Trucking Revenue", "Warehousing", "Miscellaneous Revenue"]
    AP_CATEGORIES = ["Ocean Freight Cost", "Port Terminal Cost", "Customs Duty Paid", "Inland Carrier Expenses", "Agent Handling Fee", "Miscellaneous Cost"]
    
    # ดึงฟังก์ชันที่เหลือมาทำงานต่อเพื่อไม่ให้ระบบหยุดทำงาน
    from managers.profit_manager import (
        add_cost_line, delete_cost_line,
        get_cost_lines, get_profit_summary,
        create_profit_sheet, list_profit_sheets, update_signoff,
    )

from managers.fx_manager import SUPPORTED_CURRENCIES
from managers.auth_manager import can_write

def role_has_approve(user) -> bool:
    return str(user.get("role", "")).lower() in ("admin", "accounting")

# =========================================================
# SYSTEM VIEW ROUTER ENTRYPOINT
# =========================================================
def render():
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    can_edit = can_write(role, "shipment") or can_write(role, "billing")
    
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Financial Audit Infrastructure</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>📊 Job Profitability Sheet</h2>", unsafe_allow_html=True)
    st.caption("P&L Financial Ledger — Audit real-time accounts receivable (AR) vs payable (AP) lines, evaluate gross operating margins, and generate sign-off profiles.")
    
    # Initialize multi-session track states safely
    if "prev_shipment" not in st.session_state:
        st.session_state.prev_shipment = None
    
    # --- 1. SELECT FREIGHT WORKSPACE PROFILE ---
    with st.spinner("Extracting master logistics records..."):
        try:
            ships = list_shipments() or []
        except Exception as e:
            st.error(f"Master ledger extraction blocked at interface layers: {str(e)}")
            return
            
    if not ships:
        st.info("ℹ️ No active corporate shipments logged to compile profitability metrics.")
        return
    
    # Cap parsing at index bounds safely
    options = {f"🚢 {s['job_no']} — {s.get('customer_name','Internal Account')} ({s.get('container_no','-')})": s for s in ships[:200]}
    sel_label = st.selectbox("Target Freight Reference Operation *", list(options.keys()), key="profit_sheet_target_selector")
    ship = options[sel_label]
    
    # --- AUTOMATED CACHE PURGE UPON JOB SWITCH ---
    if st.session_state.prev_shipment != ship["id"]:
        st.session_state.pop("latest_ps_pdf", None)
        st.session_state.prev_shipment = ship["id"]
    
    # --- 2. EXECUTIVE CORE HEAD METRICS GRID ---
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Job Tracking Identifier", str(ship["job_no"]))
    c2.metric("Corporate Debtor Title", str(ship.get("customer_name") or "—"))
    c3.metric("Freight Life Status", str(ship.get("status", "Proceed")))
    c4.metric("Intermodal Unit Equipment", str(ship.get("container_no") or "—"))
    
    st.markdown("---")
    
    # --- 3. OPERATIONAL P&L GAUGE METRICS ---
    try:
        summary = get_profit_summary(ship["id"]) or {"total_ar": 0, "total_ap": 0, "net_profit": 0, "profit_margin": 0}
    except Exception as sum_err:
        st.error(f"Failed to sum local table records variables: {str(sum_err)}")
        summary = {"total_ar": 0, "total_ap": 0, "net_profit": 0, "profit_margin": 0}

    net = summary.get("net_profit", 0)
    margin = summary.get("profit_margin", 0)
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Gross Revenue Allocation (AR)", f"฿ {summary.get('total_ar', 0):,.2f}")
    s2.metric("Total Operational Cost (AP)", f"฿ {summary.get('total_ap', 0):,.2f}")
    s3.metric("Net Job Yield Margin", f"฿ {net:,.2f}", delta=f"{margin:.1f}% Margin Ratio")
    
    if net >= 0:
        s4.markdown("<div style='padding: 8px 14px; background-color: #064e3b; border-radius: 8px; text-align: center; border: 1px solid #059669; margin-top:10px;'><span style='color: #34d399; font-weight:800; font-size:16px;'>🟢 YIELD PROFITABLE</span></div>", unsafe_allow_html=True)
    else:
        s4.markdown("<div style='padding: 8px 14px; background-color: #7f1d1d; border-radius: 8px; text-align: center; border: 1px solid #dc2626; margin-top:10px;'><span style='color: #fca5a5; font-weight:800; font-size:16px;'>🔴 REVENUE LOSS</span></div>", unsafe_allow_html=True)
        
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    
    # --- 4. DATA TABLES LEDGER INTERACTION TABS ---
    tab_ar, tab_ap, tab_sheets = st.tabs(["💰 Accounts Receivable (AR)", "💸 Accounts Payable (AP)", "📋 Signed P&L Ledger Archive"])
    
    with tab_ar:
        _render_cost_section(ship, "AR", AR_CATEGORIES, can_edit, user)
    with tab_ap:
        _render_cost_section(ship, "AP", AP_CATEGORIES, can_edit, user)
    with tab_sheets:
        _render_sheets_section(ship, summary, can_edit, role, user)


# =========================================================
# SUB-ROUTINE: COST SECTION RENDER ENGINE
# =========================================================
def _render_cost_section(ship, cost_type, categories, can_edit, user):
    st.markdown(f"##### Integrated {cost_type} Transaction Statements")
    
    try:
        lines = get_cost_lines(ship["id"], cost_type) or []
    except Exception as read_ex:
        st.error(f"Failed to load ledger lines: {str(read_ex)}")
        lines = []

    # Insert Data Form Segment
    if can_edit:
        with st.expander(f"➕ Append New Dynamic Line Item into {cost_type} Matrix"):
            with st.form(f"profit_form_add_line_{cost_type}_{ship['id']}"):
                c_form1, c_form2 = st.columns(2)
                cat = c_form1.selectbox("Standard Ledger Category Class *", options=categories, key=f"sel_cat_widget_{cost_type}")
                desc = c_form1.text_input("Operational Line Item Description *", placeholder="e.g., Ocean Freight Charge...", key=f"txt_desc_widget_{cost_type}")
                qty = c_form2.number_input("Transactional Volumetric Quantity *", min_value=0.01, value=1.0, step=1.0, key=f"num_qty_widget_{cost_type}")
                price = c_form2.number_input("Unit Price Rate Frame (THB) *", min_value=0.00, format="%.2f", step=500.0, key=f"num_prc_widget_{cost_type}")
                
                submit_line = st.form_submit_button(f"⚡ Append to {cost_type} Ledger", use_container_width=True)
                
            if submit_line:
                if not desc.strip():
                    st.error("⚠️ Validation Fault: Operational narrative description parameter is required.")
                else:
                    with st.spinner("Injecting vector metrics line item..."):
                        try:
                            add_cost_line({
                                "shipment_id": ship["id"], 
                                "cost_type": cost_type,
                                "category": cat, 
                                "description": desc.strip(),
                                "quantity": qty, 
                                "unit_price": price,
                                "amount": qty * price, 
                                "created_by": str(user.get("username", "billing_agent"))
                            })
                            st.toast(f"✅ Item line inserted into {cost_type} tables mapping successfully.", icon="💰" if cost_type == "AR" else "💸")
                            st.rerun()
                        except Exception as add_ex:
                            st.error(f"Database rejected cost injection sequence: {str(add_ex)}")

    if not lines:
        st.info(f"ℹ️ Zero {cost_type} financial line-items currently allocated to this shipping reference frame.")
    else:
        df = pd.DataFrame(lines)
        
        column_configs = {
            "category": st.column_config.TextColumn("Category Type", width="small"),
            "description": st.column_config.TextColumn("Line Narrative Description", width="medium"),
            "quantity": st.column_config.NumberColumn("Qty", format="%.2f"),
            "unit_price": st.column_config.NumberColumn("Unit Rate Price", format="฿%,.2f"),
            "amount": st.column_config.NumberColumn("Net Consolidated Amount", format="฿%,.2f"),
            "created_by": st.column_config.TextColumn("Author Token", width="small"),
        }
        
        display_cols = [c for c in ["category", "description", "quantity", "unit_price", "amount", "created_by"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True, column_config=column_configs)
        
        if can_edit:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            with st.form(key=f"profit_form_prune_line_{cost_type}_{ship['id']}"):
                delete_options = [(l["id"], f"🗑️ {l.get('category')} — {l.get('description','No Description')} [฿{l.get('amount',0):,.2f}]") for l in lines]
                target_del_tuple = st.selectbox(
                    f"Select Unreconciled {cost_type} Target Item to Prune", 
                    options=delete_options, 
                    format_func=lambda x: x[1],
                    key=f"profit_delete_select_box_{cost_type}"
                )
                submit_deletion = st.form_submit_button(f"Prune Selected {cost_type} Entry Line permanently", type="secondary", use_container_width=True)
                
            if submit_deletion and target_del_tuple:
                with st.spinner("Erasing database entry sequence index..."):
                    try:
                        delete_cost_line(target_del_tuple[0])
                        st.toast("Financial line item permanently pruned from workspace metrics context.", icon="🗑️")
                        st.rerun()
                    except Exception as del_ex:
                        st.error(f"Ledger mutation layer blocked structural record deletion: {str(del_ex)}")


# =========================================================
# SUB-ROUTINE: MASTER SHEETS GENERATION & EXECUTIVE SIGN-OFF
# =========================================================
def _render_sheets_section(ship, summary, can_edit, role, user):
    st.markdown("##### Consolidated P&L Report Compilation Matrix")
    
    try:
        sheets = list_profit_sheets(ship["id"]) or []
    except Exception as read_sheets_ex:
        st.error(f"Failed to recall corporate balance sheet indexes: {str(read_sheets_ex)}")
        sheets = []

    if can_edit:
        if st.button("🚀 Generate Official Job Profitability Sheet PDF Structure", type="primary", use_container_width=True):
            with st.status("Executing PDF vector compile engines...", expanded=True) as status_indicator:
                try:
                    from pdf.profit_pdf import generate_profit_pdf
                    
                    sheet = create_profit_sheet(ship["id"], prepared_by=str(user.get("full_name", user.get("username", "Operator"))))
                    ar = get_cost_lines(ship["id"], "AR") or []
                    ap = get_cost_lines(ship["id"], "AP") or []
                    
                    pdf_path = generate_profit_pdf(ship, ar, ap, summary, sheet)
                    
                    with open(pdf_path, "rb") as pdf_file_stream:
                        st.session_state["latest_ps_pdf"] = {
                            "data": pdf_file_stream.read(), 
                            "name": f"PROFIT_SHEET_{sheet.get('sheet_no', 'GEN')}_{ship['job_no']}.pdf"
                        }
                    status_indicator.update(label="✅ Snapshot Verification Success! Document buffer initialized.", state="complete")
                    st.rerun()
                except Exception as pdf_ex:
                    st.error(f"🚨 Pipeline Interruption: Compilation engine failed: {str(pdf_ex)}")

    if "latest_ps_pdf" in st.session_state:
        pdf_payload = st.session_state["latest_ps_pdf"]
        st.markdown("<div style='margin-top:10px; margin-bottom:15px;'></div>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Download Newly Compiled Audit Sheet Document Frame (PDF)", 
            data=pdf_payload["data"], 
            file_name=pdf_payload["name"], 
            mime="application/pdf",
            use_container_width=True,
            key="profit_sheet_download_trigger_btn"
        )

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown("###### Historical Document Multi-Stage Sign-off Vault")
    
    if not sheets:
        st.caption("No historical P&L sheets compiled for this operational matrix.")
    else:
        for s in sheets:
            with st.container(border=True):
                col_sh1, col_sh2, col_sh3 = st.columns([2, 1, 1])
                
                with col_sh1:
                    st.markdown(f"📄 **Document No:** `{s['sheet_no']}`")
                    st.caption(f"Prepared Authorized Token: {s.get('prepared_by', 'System Engine')}")
                    
                    rev_token = s.get('reviewed_by')
                    app_token = s.get('approved_by')
                    
                    status_badge = "<span style='color:#E2E8F0; background-color:#475569; padding:2px 8px; border-radius:4px; font-size:11px;'>STAGE 1: DRAFTED</span>"
                    if rev_token:
                        status_badge = "<span style='color:#FEE2E2; background-color:#991B1B; padding:2px 8px; border-radius:4px; font-size:11px;'>STAGE 2: AUDITED</span>"
                    if app_token:
                        status_badge = "<span style='color:#D1FAE5; background-color:#065F46; padding:2px 8px; border-radius:4px; font-size:11px;'>STAGE 3: APPROVED & RELEASED</span>"
                        
                    st.markdown(f"Workflow Authorization Vector Clearance: {status_badge}", unsafe_allow_html=True)
                
                col_sh2.metric("Declared Net Profit", f"฿ {s.get('net_profit', 0):,.2f}")
                
                with col_sh3:
                    st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
                    if can_edit:
                        if not s.get("reviewed_by"):
                            if st.button("👁️ Verify Audit Sign-off", key=f"profit_btn_review_token_{s['id']}", use_container_width=True):
                                with st.spinner("Signing record frame..."):
                                    try:
                                        update_signoff(s["id"], "review", str(user.get("full_name", user.get("username", "Auditor"))))
                                        st.toast("Document frame state successfully upgraded to AUDITED index.", icon="👁️")
                                        st.rerun()
                                    except Exception as err_rev:
                                        st.error(str(err_rev))
                                        
                        elif not s.get("approved_by") and role_has_approve(user):
                            if st.button("✅ Executive Release", key=f"profit_btn_approve_token_{s['id']}", use_container_width=True, type="primary"):
                                with st.spinner("Locking corporate records balance vector..."):
                                    try:
                                        update_signoff(s["id"], "approve", str(user.get("full_name", user.get("username", "Executive"))))
                                        st.toast("Document matrix locked and approved for liquidation distribution.", icon="✅")
                                        st.rerun()
                                    except Exception as err_app:
                                        st.error(str(err_app))
                        else:
                            st.markdown("<center style='color:#94A3B8; font-size:12px; font-style:italic; padding-top:15px;'>Verification Locked</center>", unsafe_allow_html=True)