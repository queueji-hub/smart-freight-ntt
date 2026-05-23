import streamlit as st
import pandas as pd

from managers.bl_manager import create_bl, list_bl
from managers.container_manager import add_container, list_containers


def render():

    st.title("📄 Bill of Lading & Container System")

    tabs = st.tabs(["➕ Create BL", "📦 Containers", "📋 BL List"])

    # =========================
    # CREATE BL
    # =========================
    with tabs[0]:
        job_no = st.text_input("Job No")
        bl_no = st.text_input("BL No")

        shipper = st.text_input("Shipper")
        consignee = st.text_input("Consignee")

        pol = st.text_input("POL")
        pod = st.text_input("POD")

        vessel = st.text_input("Vessel")
        voyage = st.text_input("Voyage")

        if st.button("Create BL"):
            create_bl({
                "job_no": job_no,
                "bl_no": bl_no,
                "shipper": shipper,
                "consignee": consignee,
                "pol": pol,
                "pod": pod,
                "vessel": vessel,
                "voyage": voyage
            })
            st.success("BL Created")

    # =========================
    # CONTAINERS
    # =========================
    with tabs[1]:
        job_no = st.text_input("Job No (for container)")
        bl_no = st.text_input("BL No (for container)")

        container_no = st.text_input("Container No")
        size = st.selectbox("Size", ["20GP", "40GP", "40HQ"])
        ctype = st.selectbox("Type", ["FCL", "LCL", "OT", "FR"])
        seal = st.text_input("Seal No")

        if st.button("Add Container"):
            add_container({
                "job_no": job_no,
                "bl_no": bl_no,
                "container_no": container_no,
                "container_size": size,
                "container_type": ctype,
                "seal_no": seal
            })
            st.success("Container Added")

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