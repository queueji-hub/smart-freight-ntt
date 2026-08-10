import streamlit as st
import pandas as pd

from managers.bl_manager import create_bl, list_bl
from managers.container_manager import add_container, list_containers


def render():
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Document Management Engine</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>📄 Bill of Lading & Containers</h2>", unsafe_allow_html=True)
    st.caption("Centralised HBL/MBL creation and container manifest tracking.")

    tabs = st.tabs(["➕ Create BL", "📦 Containers", "📋 BL List"])

    # =========================
    # CREATE BL
    # =========================
    with tabs[0]:
        with st.form("create_bl_form"):
            st.markdown("**Create New BL**")
            c1, c2 = st.columns(2)
            job_no = c1.text_input("Job No *")
            bl_no = c2.text_input("BL No *")

            c3, c4 = st.columns(2)
            shipper = c3.text_area("Shipper")
            consignee = c4.text_area("Consignee")

            c5, c6 = st.columns(2)
            pol = c5.text_input("POL")
            pod = c6.text_input("POD")

            c7, c8 = st.columns(2)
            vessel = c7.text_input("Vessel")
            voyage = c8.text_input("Voyage")

            submitted = st.form_submit_button("🚀 Create BL", type="primary", use_container_width=True)

        if submitted:
            if not job_no.strip() or not bl_no.strip():
                st.error("⚠️ Validation Error: Job No and BL No are required.")
            else:
                try:
                    create_bl({
                        "job_no": job_no.strip(),
                        "bl_no": bl_no.strip(),
                        "shipper": shipper.strip(),
                        "consignee": consignee.strip(),
                        "pol": pol.strip(),
                        "pod": pod.strip(),
                        "vessel": vessel.strip(),
                        "voyage": voyage.strip()
                    })
                    st.success(f"✅ BL '{bl_no}' created successfully for Job '{job_no}'!")
                except Exception as e:
                    st.error(f"Failed to create BL: {e}")

    # =========================
    # CONTAINERS
    # =========================
    with tabs[1]:
        with st.form("add_container_form"):
            st.markdown("**Add Container to Manifest**")
            c1, c2 = st.columns(2)
            job_no_c = c1.text_input("Job No *")
            bl_no_c = c2.text_input("BL No")

            c3, c4 = st.columns(2)
            container_no = c3.text_input("Container No *")
            seal = c4.text_input("Seal No")

            c5, c6 = st.columns(2)
            size = c5.selectbox("Size", ["20GP", "40GP", "40HQ"])
            ctype = c6.selectbox("Type", ["FCL", "LCL", "OT", "FR"])

            submit_cont = st.form_submit_button("📦 Add Container", type="primary", use_container_width=True)

        if submit_cont:
            if not job_no_c.strip() or not container_no.strip():
                st.error("⚠️ Validation Error: Job No and Container No are required.")
            else:
                try:
                    add_container({
                        "job_no": job_no_c.strip(),
                        "bl_no": bl_no_c.strip(),
                        "container_no": container_no.strip(),
                        "container_size": size,
                        "container_type": ctype,
                        "seal_no": seal.strip()
                    })
                    st.success(f"✅ Container '{container_no}' added to Job '{job_no_c}'!")
                except Exception as e:
                    st.error(f"Failed to add container: {e}")

    # =========================
    # LIST
    # =========================
    with tabs[2]:
        bls = list_bl()
        df = pd.DataFrame(bls)

        if not df.empty:
            st.dataframe(df, use_container_width=True)

        job_filter = st.text_input("Filter Job No")
        if job_filter:
            containers = list_containers(job_no=job_filter)
            st.dataframe(pd.DataFrame(containers), use_container_width=True)