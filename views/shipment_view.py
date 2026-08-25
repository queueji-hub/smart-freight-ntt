"""Smart Freight NTT — Job Control / Job 360 workspace."""
from datetime import date
import os
import pandas as pd
import streamlit as st
from managers.auth_manager import can_write
from managers.customer_manager import list_customers
from managers.master_data_manager import list_distinct_job_values, list_sales_users
from managers.shipment_manager import (
    STATUS_FLOW, add_job_container, create_shipment, get_shipment,
    list_job_containers, list_milestones, list_shipments, update_shipment,
)
from managers.profit_manager import (
    get_profit_summary, get_cost_sell_audit_matrix, get_cost_lines,
    get_unified_job_ledger, get_job_document_audit,
    add_cost_line, update_cost_line, delete_cost_line, lock_job_financials, unlock_job_financials,
    AP_CATEGORIES, AR_CATEGORIES, TAX_TYPES, WHT_TYPES,
)
from core.audit import list_audit_logs, log_action


def _s(v, fb="—"):
    if v is None:
        return fb
    x = str(v).strip()
    return fb if not x or x.lower() in {"none", "nan", "nat"} else x


def _money(v):
    try:
        return f"฿ {float(v or 0):,.2f}"
    except (TypeError, ValueError):
        return "฿ 0.00"


def _dt(v):
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def _idx(opts, value):
    value = _s(value, "")
    return opts.index(value) if value in opts else 0


def _opts(column):
    try:
        return [""] + list_distinct_job_values(column)
    except Exception:
        return [""]


def _css():
    st.markdown("""<style>
    .s-card{background:#fff;border:1px solid #e8edf4;border-radius:14px;padding:16px 18px;min-height:150px;box-shadow:0 3px 14px rgba(15,23,42,.055);margin-bottom:14px}
    .s-title{font-weight:750;color:#162033;font-size:15px}.s-body{color:#536174;font-size:13px;line-height:1.85;margin-top:8px}
    .s-label{color:#718096;font-size:10px;text-transform:uppercase;letter-spacing:.04em}.s-val{color:#172033;font-weight:650}
    .s-job{color:#0b63e5;font-size:21px;font-weight:800}.s-status{display:inline-block;padding:3px 9px;border-radius:999px;background:#e9f9ef;color:#16803a;font-size:11px;font-weight:750}
    .s-section{color:#162033;font-size:17px;font-weight:800;margin:12px 0 8px}
    </style>""", unsafe_allow_html=True)


def _card(title, icon, body):
    st.markdown(f'<div class="s-card"><div class="s-title"><span style="display:inline-flex;width:25px;height:25px;align-items:center;justify-content:center;border-radius:8px;background:#eef5ff;color:#1769e0;margin-right:8px">{icon}</span>{title}</div><div class="s-body">{body}</div></div>', unsafe_allow_html=True)


def render():
    _css()
    st.markdown("# Job Control")
    st.caption("Operational center for shipment execution, documents and job profitability.")
    jobs = list_shipments(limit=200) or []
    if st.session_state.get("job_control_new") or not jobs:
        _new_job()
        if jobs and st.button("Cancel", key="cancel_new_job"):
            st.session_state.pop("job_control_new", None)
            st.rerun()
        return

    a, b = st.columns([5, 1])
    job_nos = [j["job_no"] for j in jobs]
    target_job = st.session_state.get("target_job_no")
    default_job_idx = 0
    if target_job and target_job in job_nos:
        default_job_idx = job_nos.index(target_job)
    selected = a.selectbox("Job", job_nos, index=default_job_idx, key="job_view_selector", label_visibility="collapsed")
    if b.button("＋ New Job", use_container_width=True):
        st.session_state["job_control_new"] = True
        st.rerun()
    job = get_shipment(selected)
    if not job:
        st.error("Unable to load the selected job from the database.")
        return

    _summary(job)
    tabs = st.tabs(["Overview", "Operations", "Cargo & Containers", "Milestones", "Documents", "Financial", "History"])
    with tabs[0]: _overview(job)
    with tabs[1]: _operations(job)
    with tabs[2]: _containers(job)
    with tabs[3]: _milestones(job)
    with tabs[4]: _documents(job)
    with tabs[5]: _financial(job)
    with tabs[6]: _history(job)


def _summary(j):
    p = get_profit_summary(j.get("id")) or {}
    gp = p.get("actual_net_profit", p.get("net_profit", 0))
    margin = p.get("actual_margin_pct", p.get("profit_margin", 0))
    mother = j.get("mother_vessel") or j.get("m_vessel") or j.get("vessel")
    customer = j.get("customer_name") or j.get("customer") or j.get("customer_id")
    st.markdown(f'''<div style="background:#fff;border:1px solid #e7edf5;border-radius:15px;padding:18px 20px;box-shadow:0 4px 18px rgba(15,23,42,.06);margin:4px 0 18px"><div style="display:flex;justify-content:space-between;gap:18px;align-items:flex-start;flex-wrap:wrap"><div><div class="s-label">Job No.</div><div class="s-job">{_s(j.get('job_no'),'NEW JOB')}</div></div><div><div class="s-label">Customer</div><div class="s-val">{_s(customer)}</div></div><div><div class="s-label">Service</div><div class="s-val">{_s(j.get('mode'))} · {_s(j.get('service_type'))}</div></div><div><div class="s-label">POL / POD</div><div class="s-val">{_s(j.get('pol'))} / {_s(j.get('pod'))}</div></div><div><div class="s-label">ETD / ETA</div><div class="s-val">{_s(j.get('etd'))} / {_s(j.get('eta'))}</div></div><div><div class="s-label">Mother Vessel</div><div class="s-val">{_s(mother)}</div></div><div><div class="s-label">Gross Profit</div><div class="s-val" style="color:#169447">{_money(gp)}</div><div style="color:#718096">Margin {float(margin or 0):.2f}%</div></div><div><span class="s-status">{_s(j.get('status'),'Proceed')}</span></div></div></div>''', unsafe_allow_html=True)


def _overview(j):
    c = st.columns(4)
    v_str = f"{_s(j.get('vessel'))} {_s(j.get('voyage'))}".strip() or "—"
    mv_str = f"{_s(j.get('mother_vessel'))} {_s(j.get('mother_voyage'))}".strip() or "—"
    mbl_str = _s(j.get('mbl_no'), '—')
    hbl_str = _s(j.get('hbl_no'), '—')
    booking_str = _s(j.get('booking_no'), '—')
    with c[0]: _card("Shipment Info", "▣", f'Job Type: <b>{_s(j.get("job_type"))}</b><br>Mode: <b>{_s(j.get("mode"))}</b><br>Carrier MBL: <b>{mbl_str}</b><br>HBL: <b>{hbl_str}</b><br>Booking: <b>{booking_str}</b>')
    with c[1]: _card("Route Info", "⌖", f'POL: <b>{_s(j.get("pol"))}</b><br>Transshipment: <b>{_s(j.get("transshipment_port"))}</b><br>POD: <b>{_s(j.get("pod"))}</b><br>Vessel / Voy: <b>{v_str}</b><br>Mother Vessel / Voy: <b>{mv_str}</b>')
    with c[2]: _card("Parties", "▤", f'Shipper: <b>{_s(j.get("shipper"))}</b><br>Consignee: <b>{_s(j.get("consignee"))}</b><br>Notify: <b>{_s(j.get("notify_party"))}</b><br>Sales: <b>{_s(j.get("sales_person"))}</b>')
    p = get_profit_summary(j.get("id")) or {}
    with c[3]: _card("Financial Overview", "฿", f'Revenue: <b>{_money(p.get("ar_actual"))}</b><br>Cost: <b>{_money(p.get("ap_actual"))}</b><br>Profit: <b style="color:#169447">{_money(p.get("actual_net_profit"))}</b><br>Margin: <b>{float(p.get("actual_margin_pct") or 0):.2f}%</b>')


def _operations(j):
    st.markdown('<div class="s-section">Operations</div>', unsafe_allow_html=True)
    if not can_write(st.session_state.get("role", "admin"), "shipment"):
        st.info("Read-only access")
        return
    customers = list_customers() or []
    sales = list_sales_users() or []
    customer_options = [x.get("company_name") for x in customers if x.get("company_name")]
    sales_options = [_s(x.get("full_name"), x.get("username")) for x in sales]
    current_customer = j.get("customer_name") or j.get("customer")
    with st.form(f'ops_{j["job_no"]}', clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        customer = c1.selectbox("Customer", customer_options or [""], index=_idx(customer_options, current_customer))
        sales_person = c2.selectbox("Sales", sales_options or [""], index=_idx(sales_options, j.get("sales_person")))
        status = c3.selectbox("Status", STATUS_FLOW, index=_idx(STATUS_FLOW, j.get("status")))
        c4, c5, c6 = st.columns(3)
        pol = c4.text_input("POL (Port of Loading)", value=_s(j.get("pol")))
        pod = c5.text_input("POD (Port of Discharge)", value=_s(j.get("pod")))
        carrier = c6.text_input("Carrier / Liner", value=_s(j.get("carrier")))

        c7, c8, c9 = st.columns(3)
        vessel = c7.text_input("Vessel (Feeder / Ocean)", value=_s(j.get("vessel"), ""))
        voyage = c8.text_input("Voyage No.", value=_s(j.get("voyage"), ""))
        trans = c9.text_input("Transshipment Port", value=_s(j.get("transshipment_port"), ""))

        mv1, mv2 = st.columns(2)
        mother_vessel = mv1.text_input("Mother Vessel", value=_s(j.get("mother_vessel"), ""))
        mother_voyage = mv2.text_input("Mother Voyage No.", value=_s(j.get("mother_voyage"), ""))

        b1, b2, b3 = st.columns(3)
        mbl_no = b1.text_input("Carrier MBL No. (Master B/L)", value=_s(j.get("mbl_no"), ""))
        hbl_no = b2.text_input("Company HBL No.", value=_s(j.get("hbl_no"), ""))
        booking_no = b3.text_input("Booking No.", value=_s(j.get("booking_no"), ""))

        c10, c11, c12, c13 = st.columns(4)
        etd = c10.date_input("ETD", value=_dt(j.get("etd")) or date.today())
        eta = c11.date_input("ETA", value=_dt(j.get("eta")) or date.today())
        actual_dep = c12.date_input("Actual Departure", value=_dt(j.get("actual_departure")), help="Required for In Transit")
        actual_arr = c13.date_input("Actual Arrival", value=_dt(j.get("actual_arrival")), help="Required for Arrived / Finished / Closed")
        remarks = st.text_area("Remarks", value=_s(j.get("remark"), ""), height=80)
        save = st.form_submit_button("Save Changes", type="primary", use_container_width=True)

    if save:
        customer_id = next((x.get("id") for x in customers if x.get("company_name") == customer), j.get("customer_id"))
        try:
            payload = {
                "customer_id": customer_id,
                "sales_person": sales_person,
                "status": status,
                "pol": pol or None,
                "pod": pod or None,
                "carrier": carrier or None,
                "vessel": vessel.strip() or None,
                "voyage": voyage.strip() or None,
                "mother_vessel": mother_vessel.strip() or None,
                "mother_voyage": mother_voyage.strip() or None,
                "mbl_no": mbl_no.strip() or None,
                "hbl_no": hbl_no.strip() or None,
                "booking_no": booking_no.strip() or None,
                "transshipment_port": trans or None,
                "etd": etd.isoformat(),
                "eta": eta.isoformat(),
                "actual_departure": actual_dep.isoformat() if actual_dep else None,
                "actual_arrival": actual_arr.isoformat() if actual_arr else None,
                "remark": remarks,
            }
            update_shipment(j["job_no"], payload)
            log_action(user_id=st.session_state.get("user_id", 1), tenant_id=st.session_state.get("tenant_id", "ntt"), entity="shipment", entity_id=j["job_no"], action="UPDATE", details="Job Control updated")
            st.success("Job updated")
            st.rerun()
        except Exception as exc:
            st.error(f"Update failed: {exc}")


def _containers(j):
    st.markdown('<div class="s-section">Cargo & Containers</div>', unsafe_allow_html=True)
    handling = _s(j.get("service_type"), "").upper()
    mode = _s(j.get("mode"), "").upper()
    if mode == "AIR":
        st.caption("Air shipment — cargo handling is Loose. CY/CFS fields are not applicable.")
    elif handling in {"CY/CY", "CY-CY"}:
        st.caption("CY/CY selected — CFS fields are intentionally hidden.")
    elif handling in {"CFS/CFS", "CFS-CFS"}:
        st.caption("CFS/CFS selected — CY fields are intentionally hidden.")
    with st.form(f'container_{j["job_no"]}', clear_on_submit=True):
        a, b, c = st.columns(3)
        no = a.text_input("Container No.")
        size = b.selectbox("Size", ["20GP", "40GP", "40HC", "45HC"])
        seal = c.text_input("Seal No.")
        if st.form_submit_button("Add Container", use_container_width=True):
            try:
                add_job_container({"job_no": j["job_no"], "container_no": no, "container_size": size, "seal_no": seal, "gross_weight": 0.0})
                st.success("Container added")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    rows = list_job_containers(j["job_no"]) or []
    if rows:
        df = pd.DataFrame(rows)
        cols = [x for x in ["container_no", "container_size", "seal_no", "gross_weight", "volume_cbm", "status"] if x in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
    else:
        st.info("No containers attached to this job.")


def _milestones(j):
    st.markdown('<div class="s-section">Milestones</div>', unsafe_allow_html=True)
    rows = list_milestones(j["job_no"]) or []
    if not rows:
        st.info("No milestones recorded.")
        return
    df = pd.DataFrame(rows)
    cols = [x for x in ["milestone_name", "planned_date", "actual_date", "status", "location", "remark"] if x in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)


def _documents(j):
    st.markdown('<div class="s-section">Documents & Workflow</div>', unsafe_allow_html=True)
    st.caption("Documents are generated from authoritative database data without requiring file uploads.")
    
    # 1. Job Sheet
    a, b = st.columns([5, 1])
    a.write(f'**Job Sheet** · `{j["job_no"]}`')
    if b.button("PDF", key=f"prepare_job_pdf_{j['id']}", use_container_width=True, type="primary"):
        try:
            from pdf.report_generator import generate_job_sheet_pdf
            p = get_profit_summary(j["id"]) or {}
            path = generate_job_sheet_pdf(j, p, list_milestones(j["job_no"]) or [], approval_status=j.get("approval_status", "Draft"))
            if path and os.path.exists(path):
                with open(path, "rb") as handle:
                    st.download_button("Download PDF", handle.read(), file_name=os.path.basename(path), mime="application/pdf", key=f"job_pdf_download_{j['id']}", use_container_width=True)
        except Exception as exc:
            st.error(f"PDF unavailable: {exc}")

    # 2. House Bill of Lading / Air Waybill / Truck Waybill
    st.markdown("---")
    from managers.bl_workflow_service import list_job_bls, create_bl_from_job, detect_transport_mode
    from managers.booking_manager import get_booking

    bk_data = get_booking(j.get("booking_no")) if j.get("booking_no") else {}
    t_mode, d_type, d_title = detect_transport_mode(job=j, booking=bk_data)
    mode_emoji = "✈️" if t_mode == "AIR" else "🚚" if t_mode == "TRUCK" else "🚢"
    
    st.markdown(f"##### {mode_emoji} Company {d_title.title()} ({t_mode} Freight)")
    
    job_bls = list_job_bls(j["job_no"]) or []
    if job_bls:
        for bl in job_bls:
            b_col1, b_col2, b_col3 = st.columns([4, 1, 1])
            bl_no = _s(bl.get("bl_no"))
            bl_status = _s(bl.get("approval_status"), "Draft")
            b_col1.write(f"**{mode_emoji} {d_title.title()}** · `{bl_no}` · Status: `{bl_status}` (#{bl.get('consol_seq', 1)})")
            with b_col2:
                if st.button("Workspace", key=f"open_bl_{bl['id']}", use_container_width=True):
                    st.session_state["target_job_no"] = j["job_no"]
                    st.session_state["bl_v2_selected"] = bl["id"]
                    st.session_state["current_navigation"] = "bl"
                    st.query_params["page"] = "bl"
                    st.rerun()
            with b_col3:
                if st.button("PDF", key=f"pdf_bl_{bl['id']}", type="primary", use_container_width=True):
                    try:
                        from pdf.bl_pdf import generate_bl_pdf
                        pdf_file = generate_bl_pdf(bl["id"])
                        if pdf_file and os.path.exists(pdf_file):
                            with open(pdf_file, "rb") as fh:
                                st.download_button(
                                    "Download PDF",
                                    fh.read(),
                                    file_name=os.path.basename(pdf_file),
                                    mime="application/pdf",
                                    key=f"dl_bl_{bl['id']}",
                                    use_container_width=True
                                )
                    except Exception as e:
                        st.error(f"PDF failed: {e}")
        
        if can_write(st.session_state.get("role", "admin"), "bl"):
            if st.button(f"＋ Issue Another {d_title.title()} (Consolidation)", key=f"add_consol_bl_{j['id']}"):
                try:
                    user = st.session_state.get("user", {})
                    new_bid = create_bl_from_job(j["job_no"], user)
                    st.session_state["bl_v2_selected"] = new_bid
                    st.session_state["current_navigation"] = "bl"
                    st.query_params["page"] = "bl"
                    st.success(f"New {d_title.title()} created.")
                    st.rerun()
                except Exception as ex:
                    st.error(str(ex))
    else:
        st.info(f"No {d_title.title()} has been issued for this Job yet.")
        if can_write(st.session_state.get("role", "admin"), "bl"):
            if st.button(f"🚀 Issue {d_title.title()} for this Job", key=f"issue_first_bl_{j['id']}", type="primary"):
                try:
                    user = st.session_state.get("user", {})
                    new_bid = create_bl_from_job(j["job_no"], user)
                    st.session_state["bl_v2_selected"] = new_bid
                    st.session_state["current_navigation"] = "bl"
                    st.query_params["page"] = "bl"
                    st.success(f"{d_title.title()} issued successfully!")
                    st.rerun()
                except Exception as ex:
                    st.error(str(ex))
    si_mode = "hbl" if "Agent B/L" in si_mode_choice else "direct"

    from managers.si_service import assemble_si_payload
    try:
        si_data = assemble_si_payload(j["job_no"], si_mode=si_mode)
        with si_c2:
            st.caption(f"**Shipper:** {_s(si_data.get('shipper')).splitlines()[0]}<br/>**Consignee:** {_s(si_data.get('consignee')).splitlines()[0]}<br/>**Notify:** {_s(si_data.get('notify_party'))}", unsafe_allow_html=True)
        
        sa, sb = st.columns([5, 1])
        sa.write(f"**Shipping Instruction (S/I)** · `{j['job_no']}` · `{si_data['si_mode_label']}` · Carrier: `{_s(si_data.get('carrier'))}`")
        if sb.button("PDF", key=f"si_btn_{j['id']}_{si_mode}", type="primary", use_container_width=True):
            try:
                from pdf.si_pdf import generate_si_pdf
                si_pdf_path = generate_si_pdf(si_data)
                if si_pdf_path and os.path.exists(si_pdf_path):
                    with open(si_pdf_path, "rb") as h:
                        st.download_button(
                            "Download S/I",
                            h.read(),
                            file_name=os.path.basename(si_pdf_path),
                            mime="application/pdf",
                            key=f"si_dl_{j['id']}_{si_mode}",
                            use_container_width=True
                        )
            except Exception as e:
                st.error(f"S/I PDF generation failed: {e}")
    except Exception as exc:
        st.error(f"Unable to assemble S/I: {exc}")

    st.divider()
    st.write("**Related Documents**")
    st.dataframe(pd.DataFrame([{"Document": n, "Document No.": _s(v)} for n, v in [("Quotation", j.get("quotation_no")), ("Booking", j.get("booking_no")), ("Bill of Lading", j.get("bl_no")), ("Invoice", j.get("invoice_no"))]]), use_container_width=True, hide_index=True)


def _financial(j):
    st.markdown('<div class="s-section">Operation Cost & Revenue Management (Unified AP / AR Ledger)</div>', unsafe_allow_html=True)
    st.caption("Operation team manages both Cost (AP) and Sell (AR) charges and reconciles billing coverage before handover to Accounting.")
    
    user = st.session_state.get("user", {})
    can_edit = can_write(st.session_state.get("role", "admin"), "shipment")
    is_locked = bool(j.get("financial_locked"))
    ledger = get_unified_job_ledger(j["id"])
    summary = ledger["summary"]
    matrix_rows = ledger["matrix_rows"]

    # Top metrics bar
    a, b, c, d, e = st.columns(5)
    a.metric("Total Sell (AR)", _money(summary["total_ar_amount"]))
    b.metric("Total Cost (AP)", _money(summary["total_ap_amount"]))
    gp = summary["gross_profit"]
    margin = summary["margin_pct"]
    c.metric("Gross Profit", _money(gp), delta=f"{margin:.1f}% Margin")
    d.metric("Net Cashflow Expected", _money(summary["total_ar_net"] - summary["total_ap_net"]))
    
    with e:
        if st.button("🚀 Open AP/AR & P&L Center", key=f"open_full_profit_{j['id']}", type="primary", use_container_width=True):
            st.session_state["target_job_no"] = j["job_no"]
            st.session_state["current_navigation"] = "profit"
            st.query_params["page"] = "profit"
            st.rerun()
        if is_locked:
            st.caption(f"🔒 Locked ({_s(j.get('handover_by'), 'Operation')})")
        else:
            st.caption("🔓 Financial Open")

    # Load charge master options for streamlined entry
    std_charges = []
    try:
        from managers.charge_master_manager import list_charges
        std_charges = list_charges(active_only=True) or []
    except Exception:
        std_charges = []
    std_charge_opts = ["— Custom / Freeform —"] + [f"{c['charge_code']} - {c['description']} ({c.get('category','Other')})" for c in std_charges]

    fin_tabs = st.tabs([
        "📊 Unified AP / AR Matrix & Margin",
        "💰 Cost (AP - ต้นทุนจ่าย)",
        "🧾 Sell (AR - รายได้เรียกเก็บ)",
        "📜 Document Audit (ประวัติเอกสาร)"
    ])

    # -------------------------------------------------------------
    # TAB 1: UNIFIED AUDIT MATRIX
    # -------------------------------------------------------------
    with fin_tabs[0]:
        st.markdown("##### 🔍 Unified Side-by-Side AP / AR Reconciliation & Margins")
        if not matrix_rows:
            st.info("No cost or sell charges recorded yet. Add Cost lines and Sell lines in the respective tabs.")
        else:
            table_data = []
            for r in matrix_rows:
                table_data.append({
                    "No.": r["line_no"],
                    "AP Description": r["ap_description"],
                    "Payee": r["ap_supplier"],
                    "AP Rate": f"{r['ap_unit_price']:,.2f} {r['ap_currency']}" if r["ap_id"] else "—",
                    "AP Qty": f"{r['ap_quantity']:g} {r['ap_unit']}" if r["ap_id"] else "—",
                    "AP Amount (฿)": f"{r['ap_amount_thb']:,.2f}" if r["ap_id"] else "—",
                    "AP Tax": r["ap_tax_type"] if r["ap_id"] else "—",
                    "AP Status": f"{r['ap_payout_status']} ({r['ap_voucher_no']})" if r["ap_id"] else "—",
                    "Link": "➔" if r["is_matched"] else ("✦ Pure AR" if not r["ap_id"] else "✦ Unbilled AP"),
                    "AR Description": r["ar_description"],
                    "AR Rate": f"{r['ar_unit_price']:,.2f} {r['ar_currency']}" if r["ar_id"] else "—",
                    "AR Qty": f"{r['ar_quantity']:g} {r['ar_unit']}" if r["ar_id"] else "—",
                    "AR Amount (฿)": f"{r['ar_amount_thb']:,.2f}" if r["ar_id"] else "—",
                    "AR Tax": r["ar_tax_type"] if r["ar_id"] else "—",
                    "AR Status": f"{r['ar_billing_status']} ({r['ar_invoice_no']})" if r["ar_id"] else "—",
                    "Profit (฿)": f"{r['line_profit_thb']:,.2f}",
                    "Margin %": f"{r['line_margin_pct']:.1f}%",
                })
            st.dataframe(pd.DataFrame(table_data), hide_index=True, width="stretch")

    # -------------------------------------------------------------
    # TAB 2: COST (AP) ENTRY
    # -------------------------------------------------------------
    with fin_tabs[1]:
        st.markdown("##### 💰 Operational Cost Lines (Vendor / Carrier / Port / Trucking)")
        ap_lines = ledger["ap_lines"]
        if ap_lines:
            ap_display = [{
                "ID": r["id"],
                "Category": r.get("category"),
                "Description": r.get("description"),
                "Payee / Supplier": r.get("supplier"),
                "Qty": f"{r.get('quantity', 1):g} {r.get('unit', 'UNIT')}",
                "Unit Rate": f"{float(r.get('unit_price',0)):,.2f} {r.get('currency','THB')}",
                "Amount (THB)": _money(r.get("amount_thb")),
                "Tax / WHT": f"{r.get('tax_type', 'VAT 7%')} / {r.get('wht_type', 'None')}",
                "Net Payable": _money(r.get("net_amount")),
                "Payout Status": f"{r.get('payout_status', 'UNPAID')} ({_s(r.get('voucher_no'))})",
            } for r in ap_lines]
            st.dataframe(pd.DataFrame(ap_display), use_container_width=True, hide_index=True)

            if can_edit and not is_locked:
                del_col1, del_col2 = st.columns([4, 1])
                del_id = del_col1.selectbox("Delete Cost Line", [r["id"] for r in ap_lines], format_func=lambda x: f"Cost #{x}: {next((r['description'] for r in ap_lines if r['id']==x), '')}", key=f"del_cost_sel_{j['id']}")
                if del_col2.button("Delete Line", key=f"del_cost_btn_{j['id']}", use_container_width=True):
                    delete_cost_line(del_id)
                    st.rerun()
        else:
            st.info("No cost lines recorded.")

        if can_edit and not is_locked:
            with st.expander("＋ Add Operational Cost Line", expanded=(len(ap_lines) == 0)):
                with st.form(f"add_cost_form_{j['id']}", clear_on_submit=True):
                    c0, c1, c2, c3 = st.columns([2, 2, 2, 2])
                    charge_pick = c0.selectbox("Standard Charge", std_charge_opts, key=f"ap_std_{j['id']}")
                    cat = c1.selectbox("Cost Category", AP_CATEGORIES)
                    desc = c2.text_input("Description / Charge Name", value="Ocean Freight")
                    supplier = c3.text_input("Vendor / Carrier / Transporter", value=_s(j.get("carrier"), ""))

                    c4, c5, c6, c7 = st.columns(4)
                    qty = c4.number_input("Quantity", min_value=0.001, value=1.0, step=0.01, format="%.2f")
                    unit = c5.selectbox("Unit", ["BL", "CTR", "CBM", "TRIP", "SHPT", "LOT", "SET", "KG"], index=0)
                    price = c6.number_input("Unit Price", min_value=0.0, value=0.0, step=500.0, format="%.2f")
                    curr = c7.selectbox("Currency", ["THB", "USD", "EUR", "CNY", "JPY", "SGD"], index=0)

                    t1, t2, t3 = st.columns(3)
                    ex = t1.number_input("Ex.Rate to THB", min_value=0.001, value=1.0 if curr == "THB" else 35.5, step=0.1)
                    tax_type = t2.selectbox("Tax Type", TAX_TYPES, index=0)
                    wht_type = t3.selectbox("WHT Type", WHT_TYPES, index=0)

                    vinv = st.text_input("Vendor Invoice / Ref No.", placeholder="e.g. ONE-12345")
                    save_cost = st.form_submit_button("Save Cost Line", type="primary", use_container_width=True)

                if save_cost:
                    try:
                        matched_code = None
                        final_desc = desc.strip()
                        if charge_pick and not charge_pick.startswith("—"):
                            matched_code = charge_pick.split(" - ")[0].strip()
                            if not final_desc or final_desc == "Ocean Freight":
                                final_desc = charge_pick.split(" - ")[1].split(" (")[0].strip()

                        add_cost_line({
                            "shipment_id": j["id"],
                            "cost_type": "AP",
                            "category": cat,
                            "description": final_desc or "Operational Cost",
                            "supplier": supplier.strip() or None,
                            "quantity": qty,
                            "unit": unit,
                            "unit_price": price,
                            "currency": curr,
                            "exchange_rate": ex,
                            "tax_type": tax_type,
                            "wht_type": wht_type,
                            "matched_charge_code": matched_code,
                            "vendor_invoice_no": vinv.strip() or None,
                            "created_by": user.get("username", "operation"),
                        })
                        st.success("Cost line added.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to add cost: {exc}")

    # -------------------------------------------------------------
    # TAB 3: SELL (AR) ENTRY
    # -------------------------------------------------------------
    with fin_tabs[2]:
        st.markdown("##### 🧾 Customer Revenue Lines (Freight / Handling / Clearance / DOC)")
        ar_lines = ledger["ar_lines"]
        if ar_lines:
            ar_display = [{
                "ID": r["id"],
                "Category": r.get("category"),
                "Description": r.get("description"),
                "Customer": r.get("supplier") or _s(j.get("customer_name")),
                "Qty": f"{r.get('quantity', 1):g} {r.get('unit', 'UNIT')}",
                "Selling Rate": f"{float(r.get('unit_price',0)):,.2f} {r.get('currency','THB')}",
                "Amount (THB)": _money(r.get("amount_thb")),
                "Tax / WHT": f"{r.get('tax_type', 'VAT 7%')} / {r.get('wht_type', 'None')}",
                "Net Receivable": _money(r.get("net_amount")),
                "Billing Status": f"{r.get('billing_status', 'UNBILLED')} ({_s(r.get('invoice_no'))})",
            } for r in ar_lines]
            st.dataframe(pd.DataFrame(ar_display), use_container_width=True, hide_index=True)

            if can_edit and not is_locked:
                del_ar_col1, del_ar_col2 = st.columns([4, 1])
                del_ar_id = del_ar_col1.selectbox("Delete Revenue Line", [r["id"] for r in ar_lines], format_func=lambda x: f"Sell #{x}: {next((r['description'] for r in ar_lines if r['id']==x), '')}", key=f"del_sell_sel_{j['id']}")
                if del_ar_col2.button("Delete Line", key=f"del_sell_btn_{j['id']}", use_container_width=True):
                    delete_cost_line(del_ar_id)
                    st.rerun()
        else:
            st.info("No customer revenue lines recorded.")

        if can_edit and not is_locked:
            with st.expander("＋ Add Customer Revenue Line", expanded=(len(ar_lines) == 0)):
                with st.form(f"add_sell_form_{j['id']}", clear_on_submit=True):
                    s0, s1, s2, s3 = st.columns([2, 2, 2, 2])
                    s_charge_pick = s0.selectbox("Standard Charge", std_charge_opts, key=f"ar_std_{j['id']}")
                    s_cat = s1.selectbox("Revenue Category", AR_CATEGORIES)
                    s_desc = s2.text_input("Description / Charge Name", value="Ocean Freight Revenue")
                    s_cust = s3.text_input("Customer", value=_s(j.get("customer_name"), ""))

                    s4, s5, s6, s7 = st.columns(4)
                    s_qty = s4.number_input("Quantity", min_value=0.001, value=1.0, step=0.01, format="%.2f", key=f"ar_qty_{j['id']}")
                    s_unit = s5.selectbox("Unit", ["BL", "CTR", "CBM", "TRIP", "SHPT", "LOT", "SET", "KG"], index=0, key=f"ar_unit_{j['id']}")
                    s_price = s6.number_input("Unit Price Rate", min_value=0.0, value=0.0, step=500.0, format="%.2f", key=f"ar_prc_{j['id']}")
                    s_curr = s7.selectbox("Currency", ["THB", "USD", "EUR", "CNY", "JPY", "SGD"], index=0, key=f"ar_curr_{j['id']}")

                    t1, t2, t3 = st.columns(3)
                    s_ex = t1.number_input("Ex.Rate to THB", min_value=0.001, value=1.0 if s_curr == "THB" else 35.5, step=0.1, key=f"ar_ex_{j['id']}")
                    s_tax = t2.selectbox("Tax Type", TAX_TYPES, index=0, key=f"ar_tax_{j['id']}")
                    s_wht = t3.selectbox("WHT Type", WHT_TYPES, index=0, key=f"ar_wht_{j['id']}")

                    save_sell = st.form_submit_button("Save Customer Revenue Line", type="primary", use_container_width=True)

                if save_sell:
                    try:
                        s_matched_code = None
                        final_s_desc = s_desc.strip()
                        if s_charge_pick and not s_charge_pick.startswith("—"):
                            s_matched_code = s_charge_pick.split(" - ")[0].strip()
                            if not final_s_desc or final_s_desc == "Ocean Freight Revenue":
                                final_s_desc = s_charge_pick.split(" - ")[1].split(" (")[0].strip()

                        add_cost_line({
                            "shipment_id": j["id"],
                            "cost_type": "AR",
                            "category": s_cat,
                            "description": final_s_desc or "Customer Revenue",
                            "supplier": s_cust.strip() or None,
                            "quantity": s_qty,
                            "unit": s_unit,
                            "unit_price": s_price,
                            "currency": s_curr,
                            "exchange_rate": s_ex,
                            "tax_type": s_tax,
                            "wht_type": s_wht,
                            "matched_charge_code": s_matched_code,
                            "created_by": user.get("username", "operation"),
                        })
                        st.success("Customer revenue line added.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to add revenue: {exc}")

    # -------------------------------------------------------------
    # TAB 4: DOCUMENT AUDIT TRACEABILITY
    # -------------------------------------------------------------
    with fin_tabs[3]:
        st.markdown("##### 📜 Linked Documents Audit & Traceability")
        doc_audit = get_job_document_audit(j["id"])
        vouchers = doc_audit["payment_vouchers"]
        invoices = doc_audit["invoices"]

        d1, d2 = st.columns(2)
        with d1:
            st.markdown(f"**📑 AP Payment Vouchers ({len(vouchers)})**")
            if not vouchers:
                st.caption("No Payment Vouchers generated yet.")
            else:
                for v in vouchers:
                    st.write(f"• **{v.get('voucher_no')}** — {v.get('payee_name')} | {_money(v.get('total'))} [{v.get('status')}]")
        with d2:
            st.markdown(f"**🧾 AR Customer Invoices ({len(invoices)})**")
            if not invoices:
                st.caption("No Invoices generated yet.")
            else:
                for inv in invoices:
                    st.write(f"• **{inv.get('doc_no')}** — {inv.get('customer_name')} | {_money(inv.get('grand_total'))} [{inv.get('status')}]")


def _history(j):
    st.markdown('<div class="s-section">Activity History</div>', unsafe_allow_html=True)
    rows = list_audit_logs(entity="shipment", search=j["job_no"]) or []
    if not rows:
        st.info("No audit events recorded.")
        return
    df = pd.DataFrame(rows)
    cols = [x for x in ["username", "action", "details", "timestamp"] if x in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)


def _new_job():
    st.markdown('<div class="s-section">Create Job</div>', unsafe_allow_html=True)
    from managers.master_data_crud_manager import list_parties
    from managers.salesperson_manager import list_salespersons
    
    parties_cust = list_parties("CUSTOMER", active_only=True) or []
    legacy_cust = list_customers() or []
    customer_dict = {}
    for r in parties_cust:
        cid = int(r["id"])
        cname = r.get("display_name") or r.get("legal_name") or str(cid)
        customer_dict[cid] = f"{r.get('party_code')} — {cname}"
    for r in legacy_cust:
        cid = int(r["id"])
        if cid not in customer_dict:
            cname = r.get("display_name") or r.get("company_name") or str(cid)
            customer_dict[cid] = f"{r.get('customer_code', '')} — {cname}".strip(" —")

    sales_list = list_salespersons(active_only=True) or []
    sales_options = [f"{s.get('sales_code')} — {s.get('name')}".strip(" —") for s in sales_list if s.get("name")]
    if not sales_options:
        sales_options = ["Unassigned"]

    cust_ids = list(customer_dict)
    with st.form("new_job_form", clear_on_submit=True):
        a, b, c = st.columns(3)
        jt = a.selectbox("Job Type", ["EXPORT SEA", "IMPORT SEA", "EXPORT AIR", "IMPORT AIR", "CROSS BORDER"])
        mode = b.selectbox("Mode", ["SEA", "AIR", "ROAD", "RAIL"])
        customer_id = c.selectbox("Customer", cust_ids, format_func=lambda x: customer_dict[x]) if cust_ids else None
        d, e, f = st.columns(3)
        sales_person = d.selectbox("Sales", sales_options)
        etd = e.date_input("ETD", date.today())
        eta = f.date_input("ETA", date.today())
        g, h, i = st.columns(3)
        pol_input = g.text_input("POL (Port of Loading)", placeholder="e.g. THBKK — Bangkok Port")
        pod_input = h.text_input("POD (Port of Discharge)", placeholder="e.g. SGSIN — Singapore")
        carrier_input = i.text_input("Carrier / Liner", placeholder="e.g. ONE, Evergreen, Maersk")
        j1, j2 = st.columns(2)
        mbl_input = j1.text_input("Carrier MBL No. (Master B/L)")
        booking_input = j2.text_input("Booking No.")
        create = st.form_submit_button("Create Job", type="primary", use_container_width=True)
    if create:
        try:
            no = create_shipment({
                "job_type": jt,
                "mode": mode,
                "customer_id": customer_id,
                "customer_name": customer_dict.get(customer_id, "") if customer_id else None,
                "sales_person": sales_person,
                "etd": etd.isoformat(),
                "eta": eta.isoformat(),
                "pol": pol_input.strip() or None,
                "pod": pod_input.strip() or None,
                "carrier": carrier_input.strip() or None,
                "mbl_no": mbl_input.strip() or None,
                "booking_no": booking_input.strip() or None,
                "status": "Proceed"
            })
            st.success(f"Job {no} created")
            st.session_state.pop("job_control_new", None)
            st.session_state["target_job_no"] = no
            st.rerun()
        except Exception as exc:
            st.error(f"Create failed: {exc}")
