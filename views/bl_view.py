"""
Bill of Lading (B/L) Control Center & Document Workspace
Phase J5 Complete — Full Ledger, Multi-Tab Workspace, Container Manifest & PDF Engine
"""

import os
import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.bl_manager import (
    create_bl, get_bl, list_bls as list_bl, update_bl, delete_bl,
    update_bl_status, list_bl_containers, add_bl_container, remove_bl_container,
    BL_STATUS_FLOW, LOCKED_STATUSES, EDITABLE_STATUSES, BL_TYPES, _s, _f, _i
)
from managers.shipment_manager import list_shipments, list_job_containers
from pdf.bl_pdf import generate_bl_pdf


def render():
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    can_edit = can_write(role, "bl")

    st.markdown(
        "<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Document Management Engine</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>📜 Bill of Lading Control Center</h2>",
        unsafe_allow_html=True,
    )
    st.caption("Centralised HBL/MBL Document Control, Container Manifest Linkage & ReportLab PDF Compilation.")

    tabs = st.tabs([
        "📋 B/L Document Ledger",
        "✏️ B/L Detail Workspace & Manifest",
        "➕ Construct New B/L Entry",
    ])

    with tabs[0]:
        _render_bl_ledger(can_edit)

    with tabs[1]:
        _render_bl_workspace(can_edit)

    with tabs[2]:
        _render_bl_create(user, can_edit)


# =========================================================
# TAB 0: B/L LEDGER & PDF COMPILER (LANDING SCREEN)
# =========================================================
def _render_bl_ledger(can_edit):
    st.markdown(
        "<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>📋 Bill of Lading Master Document Ledger</h4>",
        unsafe_allow_html=True,
    )

    # Filter Row
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        type_filter = st.selectbox("B/L Type Filter", options=["All Types"] + list(BL_TYPES), key="bl_ledger_type_filt")
    with f2:
        status_filter = st.selectbox(
            "Status Filter",
            options=["All Statuses", "Draft", "Submitted", "Approved", "Issued", "Surrendered", "Cancelled"],
            key="bl_ledger_stat_filt"
        )
    with f3:
        search_query = st.text_input("Search (No / Job / Shipper / Ports)", placeholder="e.g. HBL2608 or Customer", key="bl_ledger_search")
    with f4:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Ledger", use_container_width=True, key="bl_ledger_refresh"):
            st.rerun()

    # Load data
    try:
        filt_stat = None if status_filter == "All Statuses" else status_filter
        bl_rows = list_bl(status=filt_stat) or []
    except Exception as e:
        st.error(f"Failed to fetch B/L records: {e}")
        bl_rows = []

    if type_filter != "All Types":
        bl_rows = [r for r in bl_rows if r.get("bl_type") == type_filter]

    if search_query and search_query.strip():
        q_lower = search_query.strip().lower()
        filtered = []
        for r in bl_rows:
            haystack = f"{r.get('bl_no','')} {r.get('job_no','')} {r.get('shipper','')} {r.get('consignee','')} {r.get('port_of_loading','')} {r.get('port_of_discharge','')}".lower()
            if q_lower in haystack:
                filtered.append(r)
        bl_rows = filtered

    if not bl_rows:
        st.info("ℹ️ No Bill of Lading records match the selected filter criteria.")
        return

    # Render Dataframe
    display_list = []
    for r in bl_rows:
        display_list.append({
            "B/L No": _s(r.get("bl_no")),
            "Type": _s(r.get("bl_type")),
            "Status": _s(r.get("status")),
            "Job No": _s(r.get("job_no")),
            "Shipper": _s(r.get("shipper"), "—"),
            "Consignee": _s(r.get("consignee"), "—"),
            "POL": _s(r.get("port_of_loading") or r.get("pol"), "—"),
            "POD": _s(r.get("port_of_discharge") or r.get("pod"), "—"),
            "Vessel / Voy": f"{_s(r.get('vessel'))} {_s(r.get('voyage'))}".strip() or "—",
            "Pkgs": _s(r.get("package_qty") or r.get("package_quantity"), "—"),
            "Gross Weight": f"{_f(r.get('gross_weight')):,.2f} KG" if r.get("gross_weight") else "—",
            "CBM": f"{_f(r.get('measurement_cbm')):,.3f} CBM" if r.get("measurement_cbm") else "—",
        })

    st.dataframe(pd.DataFrame(display_list), use_container_width=True, hide_index=True)

    # Instant Action & PDF Compiler
    st.markdown("---")
    st.markdown("<h5 style='font-size:14px; color:#F1F5F9; font-weight:700;'>⚡ Instant Action & PDF Compiler</h5>", unsafe_allow_html=True)

    col_sel, col_btn1, col_btn2 = st.columns([3, 1.5, 1.5])
    bl_ids = [r["id"] for r in bl_rows if "id" in r]
    bl_labels = {r["id"]: f"{r.get('bl_no')} [{r.get('bl_type')}] — {r.get('status')}" for r in bl_rows if "id" in r}

    with col_sel:
        target_id = st.selectbox(
            "Select Target B/L",
            options=bl_ids,
            format_func=lambda x: bl_labels.get(x, str(x)),
            key="bl_ledger_target_sel",
            label_visibility="collapsed"
        )

    if target_id:
        target_rec = next((r for r in bl_rows if r["id"] == target_id), None)
        with col_btn1:
            if st.button("👁️ Open Workspace", use_container_width=True, key="bl_open_ws_btn"):
                st.session_state["selected_bl_id"] = target_id
                st.toast(f"Loaded B/L id={target_id} in Workspace tab", icon="📜")
                st.rerun()

        with col_btn2:
            if target_rec:
                try:
                    pdf_path = generate_bl_pdf(target_id)
                    if pdf_path and os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label="📥 Download B/L PDF",
                                data=f.read(),
                                file_name=os.path.basename(pdf_path),
                                mime="application/pdf",
                                key=f"dl_bl_pdf_ledger_{target_id}",
                                use_container_width=True,
                                type="primary",
                            )
                except Exception as pdf_err:
                    st.error(f"PDF Compile Error: {pdf_err}")


# =========================================================
# TAB 1: B/L DETAIL WORKSPACE & MANIFEST
# =========================================================
def _render_bl_workspace(can_edit):
    st.markdown(
        "<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>✏️ B/L Detail Workspace & Manifest Linkage</h4>",
        unsafe_allow_html=True,
    )

    try:
        bl_all = list_bl() or []
    except Exception as e:
        st.error(f"Failed to fetch B/L records: {e}")
        return

    if not bl_all:
        st.info("ℹ️ No Bill of Lading records exist in database.")
        return

    bl_options = {r["id"]: f"{_s(r.get('bl_no'))} [{_s(r.get('bl_type'))}] — Job: {_s(r.get('job_no'))} ({_s(r.get('status'))})" for r in bl_all}
    
    default_idx = 0
    if "selected_bl_id" in st.session_state and st.session_state["selected_bl_id"] in bl_options:
        default_idx = list(bl_options.keys()).index(st.session_state["selected_bl_id"])

    selected_id = st.selectbox(
        "Select B/L Record to Inspect / Edit",
        options=list(bl_options.keys()),
        index=default_idx,
        format_func=lambda x: bl_options[x],
        key="bl_ws_selector"
    )

    bl = get_bl(selected_id)
    if not bl:
        st.error("Could not load B/L details.")
        return

    bl_status = _s(bl.get("status"), "Draft")
    bl_locked = bl_status in LOCKED_STATUSES
    allow_full_edit = can_edit and not bl_locked
    job_no = bl.get("job_no", "")

    # Top Header Card & Actions Bar
    st.markdown(
        f"""
        <div style="padding: 16px; border: 1px solid #334155; background-color: #0F172A; border-radius:10px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size:18px; font-weight:800; color:#F8FAFC;">Document: {bl.get('bl_no')}</span>
                    <span style="margin-left: 12px; background: #1E293B; border: 1px solid #475569; padding: 2px 10px; border-radius: 12px; font-size:12px; font-weight:700; color:#38BDF8;">{bl.get('bl_type')}</span>
                    <span style="margin-left: 8px; color: #94A3B8; font-size: 13px;">Job: {job_no}</span>
                </div>
                <div>
                    <span style="font-size:14px; font-weight:700; color:#F1F5F9;">Status: <b>{bl_status}</b></span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top Action Bar: Status Transitions & PDF
    a1, a2 = st.columns([3, 1])

    with a1:
        next_statuses = BL_STATUS_FLOW.get(bl_status, [])
        if can_edit and next_statuses:
            st.markdown("**Status Transition Actions:**")
            st_cols = st.columns(len(next_statuses))
            for idx, ns in enumerate(next_statuses):
                with st_cols[idx]:
                    if st.button(f"→ Transition to {ns}", key=f"ws_st_btn_{selected_id}_{ns}", type="primary" if ns in ("Approved", "Issued") else "secondary"):
                        try:
                            update_bl_status(selected_id, ns)
                            st.success(f"Status updated to {ns}")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
        elif bl_locked:
            st.caption(f"🔒 Document is locked in status '{bl_status}'")

    with a2:
        try:
            pdf_path = generate_bl_pdf(selected_id)
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📄 Compile & Download PDF",
                        data=f.read(),
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf",
                        key=f"dl_bl_pdf_ws_{selected_id}",
                        use_container_width=True,
                        type="primary"
                    )
        except Exception as pdf_e:
            st.error(f"PDF Compiler Error: {pdf_e}")

    st.markdown("---")

    # Multi-tab Workspace Form
    t1, t2, t3, t4, t5, t6 = st.tabs([
        "1. Parties & Header",
        "2. Routing & Transport",
        "3. Cargo & Commercial",
        "4. Container Manifest",
        "5. Remarks & Legal Terms",
        "6. 📎 Documents"
    ])

    with st.form(f"bl_ws_form_{selected_id}"):
        with t1:
            st.markdown("#### Parties & Issuance Details")
            d1, d2, d3 = st.columns(3)
            bl_date = d1.date_input("B/L Date", value=_s(bl.get("bl_date")), disabled=not allow_full_edit)
            place_issue = d2.text_input("Place of Issue", value=_s(bl.get("place_of_issue"), "BANGKOK, THAILAND"), disabled=not allow_full_edit)
            num_orig = d3.text_input("No. of Originals", value=_s(bl.get("number_of_originals"), "THREE (3)"), disabled=not allow_full_edit)

            shipper = st.text_area("Shipper / Exporter", value=_s(bl.get("shipper")), disabled=not allow_full_edit)
            consignee = st.text_area("Consignee", value=_s(bl.get("consignee")), disabled=not allow_full_edit)
            notify = st.text_area("Notify Party", value=_s(bl.get("notify_party")), disabled=not allow_full_edit)

        with t2:
            st.markdown("#### Routing & Vessel Information")
            r1, r2, r3 = st.columns(3)
            por = r1.text_input("Place of Receipt (POR)", value=_s(bl.get("place_of_receipt") or bl.get("por")), disabled=not allow_full_edit)
            pol = r2.text_input("Port of Loading (POL) *", value=_s(bl.get("port_of_loading") or bl.get("pol")), disabled=not allow_full_edit)
            tranship = r3.text_input("Transhipment Port", value=_s(bl.get("transshipment_port")), disabled=not allow_full_edit)

            r4, r5 = st.columns(2)
            pod = r4.text_input("Port of Discharge (POD) *", value=_s(bl.get("port_of_discharge") or bl.get("pod")), disabled=not allow_full_edit)
            pde = r5.text_input("Place of Delivery / Final Destination", value=_s(bl.get("place_of_delivery") or bl.get("final_destination")), disabled=not allow_full_edit)

            v1, v2, v3 = st.columns(3)
            vessel = v1.text_input("Vessel", value=_s(bl.get("vessel")), disabled=not allow_full_edit)
            voyage = v2.text_input("Voyage", value=_s(bl.get("voyage")), disabled=not allow_full_edit)
            carrier = v3.text_input("Carrier / Liner", value=_s(bl.get("carrier")), disabled=not allow_full_edit)

        with t3:
            st.markdown("#### Cargo Specifications & Freight Terms")
            f1, f2 = st.columns(2)
            freight_term = f1.selectbox("Freight Term", ["PREPAID", "COLLECT"], index=0 if _s(bl.get("freight_term")) == "PREPAID" else 1, disabled=not allow_full_edit)
            freight_payable = f2.text_input("Freight Payable At", value=_s(bl.get("freight_payable_at")), disabled=not allow_full_edit)

            c1, c2, c3, c4 = st.columns(4)
            pkg_qty = c1.number_input("Package Qty", value=_i(bl.get("package_qty") or bl.get("package_quantity")), step=1, disabled=not allow_full_edit)
            pkg_type = c2.text_input("Package Unit", value=_s(bl.get("package_type"), "PKGS"), disabled=not allow_full_edit)
            gross_wt = c3.number_input("Gross Weight (KG)", value=_f(bl.get("gross_weight")), step=0.01, disabled=not allow_full_edit)
            cbm_val = c4.number_input("Measurement (CBM)", value=_f(bl.get("measurement_cbm")), step=0.001, disabled=not allow_full_edit)

            goods_desc = st.text_area("Description of Goods & Cargo *", value=_s(bl.get("description_of_goods")), disabled=not allow_full_edit)
            m1, m2 = st.columns(2)
            marks = m1.text_area("Marks & Numbers", value=_s(bl.get("marks_numbers"), "N/M"), disabled=not allow_full_edit)
            hs_code = m2.text_input("HS Code", value=_s(bl.get("hs_code")), disabled=not allow_full_edit)

        with t5:
            st.markdown("#### Remarks & Special Instructions")
            remarks = st.text_area("Remarks", value=_s(bl.get("remarks")), disabled=not allow_full_edit)
            special = st.text_area("Special Instructions", value=_s(bl.get("special_instructions")), disabled=not allow_full_edit)

        save_submitted = st.form_submit_button("💾 Save B/L Workspace Changes", type="primary", use_container_width=True, disabled=not allow_full_edit)

    if save_submitted:
        try:
            update_bl(selected_id, {
                "bl_date": bl_date.isoformat() if bl_date else None,
                "place_of_issue": place_issue.strip() if place_issue else None,
                "number_of_originals": num_orig.strip() if num_orig else None,
                "shipper": shipper.strip() if shipper else None,
                "consignee": consignee.strip() if consignee else None,
                "notify_party": notify.strip() if notify else None,
                "place_of_receipt": por.strip() if por else None,
                "port_of_loading": pol.strip() if pol else None,
                "port_of_discharge": pod.strip() if pod else None,
                "place_of_delivery": pde.strip() if pde else None,
                "vessel": vessel.strip() if vessel else None,
                "voyage": voyage.strip() if voyage else None,
                "carrier": carrier.strip() if carrier else None,
                "freight_term": freight_term,
                "freight_payable_at": freight_payable.strip() if freight_payable else None,
                "package_qty": int(pkg_qty) if pkg_qty else None,
                "package_type": pkg_type.strip() if pkg_type else None,
                "gross_weight": float(gross_wt) if gross_wt else None,
                "measurement_cbm": float(cbm_val) if cbm_val else None,
                "description_of_goods": goods_desc.strip() if goods_desc else None,
                "marks_numbers": marks.strip() if marks else None,
                "hs_code": hs_code.strip() if hs_code else None,
                "remarks": remarks.strip() if remarks else None,
                "special_instructions": special.strip() if special else None,
            })
            st.success("✅ B/L updates saved successfully!")
            st.rerun()
        except Exception as err:
            st.error(f"Save failed: {err}")

    # Tab 4: Container Manifest Mapping
    with t4:
        st.markdown("#### Container Manifest Junction Mapping")
        st.caption("Links physical Job containers to this B/L document. Unlinking removes the manifest association without deleting the container.")
        
        linked_ctrs = list_bl_containers(selected_id) or []
        linked_ids = {c["id"] for c in linked_ctrs}

        if linked_ctrs:
            st.markdown("**Linked Containers Manifest:**")
            df_ctrs = pd.DataFrame([{
                "Container No": _s(c.get("container_no")),
                "Size": _s(c.get("container_size")),
                "Type": _s(c.get("container_type")),
                "Seal No": _s(c.get("seal_no"), "—"),
                "Tare (KG)": _f(c.get("tare_weight")),
                "VGM (KG)": _f(c.get("vgm_kg")),
                "Gross (KG)": _f(c.get("gross_weight")),
            } for c in linked_ctrs])
            st.dataframe(df_ctrs, use_container_width=True, hide_index=True)

            if allow_full_edit:
                unl_col1, unl_col2 = st.columns([3, 1])
                with unl_col1:
                    unlink_target = st.selectbox(
                        "Select Container to Unlink",
                        options=[c["id"] for c in linked_ctrs],
                        format_func=lambda x: next((_s(c.get("container_no")) for c in linked_ctrs if c["id"] == x), str(x)),
                        key=f"ws_unl_sel_{selected_id}"
                    )
                with unl_col2:
                    st.write("")
                    st.write("")
                    if st.button("Unlink Container", key=f"ws_unl_btn_{selected_id}"):
                        try:
                            remove_bl_container(selected_id, unlink_target)
                            st.success("Container unlinked.")
                            st.rerun()
                        except Exception as ex:
                            st.error(str(ex))
        else:
            st.info("No physical containers linked to this B/L document manifest yet.")

        if allow_full_edit and job_no:
            job_all_ctrs = list_job_containers(job_no) or []
            avail_ctrs = [c for c in job_all_ctrs if c["id"] not in linked_ids]
            if avail_ctrs:
                st.markdown("---")
                st.markdown("**Available Job Containers to Link:**")
                lnk_col1, lnk_col2 = st.columns([3, 1])
                with lnk_col1:
                    link_target = st.selectbox(
                        "Select Job Container to Link",
                        options=[c["id"] for c in avail_ctrs],
                        format_func=lambda x: next((f"{_s(c.get('container_no'))} ({_s(c.get('container_size'))} {_s(c.get('container_type'))})" for c in avail_ctrs if c["id"] == x), str(x)),
                        key=f"ws_lnk_sel_{selected_id}"
                    )
                with lnk_col2:
                    st.write("")
                    st.write("")
                    if st.button("Link to B/L Manifest", type="primary", key=f"ws_lnk_btn_{selected_id}"):
                        try:
                            add_bl_container(selected_id, link_target)
                            st.success("Container linked to B/L manifest!")
                            st.rerun()
                        except Exception as ex:
                            st.error(str(ex))

    with t6:
        from views.document_ui import render_document_section
        st.subheader("📎 Documents")
        render_document_section("HBL" if _s(bl.get("bl_type")) == "HBL" else "MBL", selected_id)


# =========================================================
# TAB 2: CONSTRUCT NEW B/L ENTRY
# =========================================================
def _render_bl_create(user, can_edit):
    st.markdown(
        "<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>➕ Construct New B/L Document Entry</h4>",
        unsafe_allow_html=True,
    )

    if not can_edit:
        st.error("🔒 Access Denied: Your account role does not have permission to create Bill of Lading records.")
        return

    try:
        shipments = list_shipments() or []
        job_options = [s["job_no"] for s in shipments if "job_no" in s]
    except Exception as e:
        st.warning(f"Unable to read shipments: {e}")
        job_options = []

    if not job_options:
        st.warning("⚠️ No active Jobs found in system. Create or convert a Booking to a Job first.")
        return

    with st.form("bl_create_form"):
        c1, c2 = st.columns(2)
        target_job = c1.selectbox("Target Operational Job No *", options=job_options, key="bl_cr_job_sel")
        bl_type = c2.selectbox("B/L Document Type *", options=list(BL_TYPES), key="bl_cr_type_sel")

        st.caption("Creating a B/L automatically prefills Shipper, Consignee, Notify, Routing, and Cargo details from the target Job.")
        submit_create = st.form_submit_button("🚀 Create B/L & Auto-Prefill from Job", type="primary", use_container_width=True)

    if submit_create:
        try:
            new_id = create_bl(target_job, bl_type, user)
            st.success(f"✅ B/L created successfully (ID: {new_id}) for Job '{target_job}'!")
            st.session_state["selected_bl_id"] = new_id
            st.rerun()
        except Exception as ex:
            st.error(f"Creation failed: {ex}")