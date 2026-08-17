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
    add_cost_line, update_cost_line, delete_cost_line, lock_job_financials, unlock_job_financials,
    AP_CATEGORIES, AR_CATEGORIES,
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
    selected = a.selectbox("Job", [j["job_no"] for j in jobs], key="job_control_selector", label_visibility="collapsed")
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
    with c[0]: _card("Shipment Info", "▣", f'Job Type: <b>{_s(j.get("job_type"))}</b><br>Mode: <b>{_s(j.get("mode"))}</b><br>Cargo: <b>{_s(j.get("cargo_type"))}</b><br>Incoterm: <b>{_s(j.get("incoterm"))}</b><br>Freight: <b>{_s(j.get("freight_term"))}</b>')
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
        pol = c4.selectbox("POL", _opts("pol"), index=_idx(_opts("pol"), j.get("pol")))
        pod = c5.selectbox("POD", _opts("pod"), index=_idx(_opts("pod"), j.get("pod")))
        carrier = c6.selectbox("Carrier", _opts("carrier"), index=_idx(_opts("carrier"), j.get("carrier")))

        c7, c8, c9 = st.columns(3)
        vessel = c7.text_input("Vessel (Feeder / Ocean)", value=_s(j.get("vessel"), ""))
        voyage = c8.text_input("Voyage No.", value=_s(j.get("voyage"), ""))
        trans = c9.selectbox("Transshipment", _opts("transshipment_port"), index=_idx(_opts("transshipment_port"), j.get("transshipment_port")))

        mv1, mv2 = st.columns(2)
        mother_vessel = mv1.text_input("Mother Vessel", value=_s(j.get("mother_vessel"), ""))
        mother_voyage = mv2.text_input("Mother Voyage No.", value=_s(j.get("mother_voyage"), ""))

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
    st.caption("Documents are generated from database data. No binary document upload is required.")
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
    st.divider()
    st.write("**Related Documents**")
    st.dataframe(pd.DataFrame([{"Document": n, "Document No.": _s(v)} for n, v in [("Quotation", j.get("quotation_no")), ("Booking", j.get("booking_no")), ("Bill of Lading", j.get("bl_no")), ("Invoice", j.get("invoice_no"))]]), use_container_width=True, hide_index=True)


def _financial(j):
    st.markdown('<div class="s-section">Operation Cost & Revenue Management (Cost vs. Sell)</div>', unsafe_allow_html=True)
    st.caption("Operation team manages both Cost (AP) and Sell (AR) charges and reconciles billing coverage before handover to Accounting.")
    
    user = st.session_state.get("user", {})
    can_edit = can_write(st.session_state.get("role", "admin"), "shipment")
    is_locked = bool(j.get("financial_locked"))
    audit_data = get_cost_sell_audit_matrix(j["id"])

    # Top metrics bar
    a, b, c, d, e = st.columns(5)
    a.metric("Total Sell (Revenue)", _money(audit_data["total_sell_thb"]))
    b.metric("Total Cost (Expense)", _money(audit_data["total_cost_thb"]))
    c.metric("Gross Profit", _money(audit_data["gross_profit"]), delta=f"{audit_data['margin_pct']:.1f}% Margin")
    d.metric("Unbilled Cost Items", str(audit_data["unbilled_cost_count"]), delta_color="inverse")
    
    with e:
        st.write("**Handover Status**")
        if is_locked:
            st.success(f"🔒 Locked ({_s(j.get('handover_by'), 'Operation')})")
            if can_edit and st.button("Unlock for Revision", key=f"unlock_fin_{j['id']}", use_container_width=True):
                unlock_job_financials(j["id"], user)
                st.rerun()
        else:
            st.warning("📝 Work in Progress")
            if can_edit and st.button("🔒 Handover to Accounting", key=f"lock_fin_{j['id']}", type="primary", use_container_width=True):
                if audit_data["unbilled_cost_count"] > 0:
                    st.error(f"Cannot handover: {audit_data['unbilled_cost_count']} unbilled cost line(s) detected! Please verify customer billing.")
                else:
                    lock_job_financials(j["id"], user)
                    st.success("Financials verified & handed over to Accounting.")
                    st.rerun()

    if audit_data["unbilled_cost_count"] > 0:
        st.error(f"⚠️ **Attention Operation**: Found **{audit_data['unbilled_cost_count']} unbilled cost line(s)** totaling {_money(audit_data['unbilled_cost_amount'])}. Please review below to ensure all vendor costs are billed to customer or flagged as internal.")

    fin_tabs = st.tabs(["📊 Cost vs. Sell Audit Matrix", "💰 Cost (AP - ต้นทุนจ่าย)", "🧾 Sell (AR - รายได้เรียกเก็บ)"])

    # -------------------------------------------------------------
    # TAB 1: AUDIT MATRIX
    # -------------------------------------------------------------
    with fin_tabs[0]:
        st.markdown("##### 🔍 Reconciliation & Margin Audit")
        matrix_rows = audit_data.get("matrix_rows", [])
        if not matrix_rows:
            st.info("No cost or sell charges recorded yet. Add Cost lines and Sell lines in the respective tabs.")
        else:
            display_rows = [{
                "Audit Status": r["badge"],
                "Cost Category / Description": f"{_s(r['category'])} - {_s(r['description'])}",
                "Vendor / Supplier": _s(r["supplier"]),
                "Cost (THB)": _money(r["cost_thb"]),
                "Billable?": "Yes" if r["is_billable"] else "No (Internal)",
                "Matching Customer Item": _s(r["sell_description"]),
                "Sell (THB)": _money(r["sell_thb"]),
                "Item Profit (THB)": _money(r["profit_thb"]),
            } for r in matrix_rows]
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

    # -------------------------------------------------------------
    # TAB 2: COST (AP) ENTRY
    # -------------------------------------------------------------
    with fin_tabs[1]:
        st.markdown("##### 💰 Operational Cost Lines (Vendor / Carrier / Port / Trucking)")
        ap_lines = get_cost_lines(j["id"], cost_type="AP")
        if ap_lines:
            ap_display = [{
                "ID": r["id"],
                "Category": r.get("category"),
                "Description": r.get("description"),
                "Supplier / Vendor": r.get("supplier"),
                "Qty": r.get("quantity"),
                "Price": r.get("unit_price"),
                "Curr": r.get("currency"),
                "Amount (THB)": _money(r.get("amount_thb")),
                "Billable": "Yes" if r.get("billable_to_customer", 1) in (1, True, "1") else "No",
                "Status": r.get("cost_status"),
                "Payout": r.get("payout_status", "UNPAID"),
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
                    c1, c2, c3 = st.columns(3)
                    cat = c1.selectbox("Cost Category", AP_CATEGORIES)
                    desc = c2.text_input("Description / Charge Name", value="Ocean Freight")
                    supplier = c3.text_input("Vendor / Carrier / Transporter", value=_s(j.get("carrier"), ""))

                    c4, c5, c6, c7 = st.columns(4)
                    qty = c4.number_input("Quantity", min_value=0.01, value=1.0, step=1.0)
                    price = c5.number_input("Unit Price", min_value=0.0, value=0.0, step=100.0)
                    curr = c6.selectbox("Currency", ["THB", "USD", "EUR", "CNY"], index=0)
                    billable = c7.selectbox("Billable to Customer?", ["Yes (เรียกเก็บลูกค้า)", "No (ต้นทุนภายในบริษัท)"], index=0)

                    remark = st.text_input("Remarks / Notes")
                    save_cost = st.form_submit_button("Save Cost Line", type="primary", use_container_width=True)

                if save_cost:
                    try:
                        add_cost_line({
                            "shipment_id": j["id"],
                            "cost_type": "AP",
                            "category": cat,
                            "description": desc.strip(),
                            "supplier": supplier.strip() or None,
                            "quantity": qty,
                            "unit_price": price,
                            "amount": qty * price,
                            "currency": curr,
                            "billable_to_customer": (billable.startswith("Yes")),
                            "remark": remark.strip() or None,
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
        ar_lines = get_cost_lines(j["id"], cost_type="AR")
        if ar_lines:
            ar_display = [{
                "ID": r["id"],
                "Category": r.get("category"),
                "Description": r.get("description"),
                "Customer": r.get("supplier") or _s(j.get("customer_name")),
                "Qty": r.get("quantity"),
                "Price": r.get("unit_price"),
                "Curr": r.get("currency"),
                "Amount (THB)": _money(r.get("amount_thb")),
                "Status": r.get("cost_status"),
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
                    s1, s2, s3 = st.columns(3)
                    s_cat = s1.selectbox("Revenue Category", AR_CATEGORIES)
                    s_desc = s2.text_input("Description / Charge Name", value="Ocean Freight Revenue")
                    s_cust = s3.text_input("Customer", value=_s(j.get("customer_name"), ""))

                    s4, s5, s6 = st.columns(3)
                    s_qty = s4.number_input("Quantity", min_value=0.01, value=1.0, step=1.0, key=f"ar_qty_{j['id']}")
                    s_price = s5.number_input("Unit Price", min_value=0.0, value=0.0, step=100.0, key=f"ar_prc_{j['id']}")
                    s_curr = s6.selectbox("Currency", ["THB", "USD", "EUR", "CNY"], index=0, key=f"ar_curr_{j['id']}")

                    s_remark = st.text_input("Remarks / Notes", key=f"ar_rem_{j['id']}")
                    save_sell = st.form_submit_button("Save Customer Revenue Line", type="primary", use_container_width=True)

                if save_sell:
                    try:
                        add_cost_line({
                            "shipment_id": j["id"],
                            "cost_type": "AR",
                            "category": s_cat,
                            "description": s_desc.strip(),
                            "supplier": s_cust.strip() or None,
                            "quantity": s_qty,
                            "unit_price": s_price,
                            "amount": s_qty * s_price,
                            "currency": s_curr,
                            "billable_to_customer": True,
                            "remark": s_remark.strip() or None,
                            "created_by": user.get("username", "operation"),
                        })
                        st.success("Customer revenue line added.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to add revenue: {exc}")


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
    customers = list_customers() or []
    sales = list_sales_users() or []
    customer_options = [x.get("company_name") for x in customers if x.get("company_name")]
    sales_options = [_s(x.get("full_name"), x.get("username")) for x in sales]
    with st.form("new_job_form", clear_on_submit=True):
        a, b, c = st.columns(3)
        jt = a.selectbox("Job Type", ["EXPORT SEA", "IMPORT SEA", "EXPORT AIR", "IMPORT AIR", "CROSS BORDER"])
        mode = b.selectbox("Mode", ["SEA", "AIR", "ROAD"])
        customer = c.selectbox("Customer", customer_options or [""])
        d, e, f = st.columns(3)
        sales_person = d.selectbox("Sales", sales_options or [""])
        etd = e.date_input("ETD", date.today())
        eta = f.date_input("ETA", date.today())
        create = st.form_submit_button("Create Job", type="primary", use_container_width=True)
    if create:
        customer_id = next((x.get("id") for x in customers if x.get("company_name") == customer), None)
        try:
            no = create_shipment({"job_type": jt, "mode": mode, "customer_id": customer_id, "sales_person": sales_person, "etd": etd.isoformat(), "eta": eta.isoformat(), "status": "Proceed"})
            st.success(f"Job {no} created")
            st.session_state.pop("job_control_new", None)
            st.rerun()
        except Exception as exc:
            st.error(f"Create failed: {exc}")
