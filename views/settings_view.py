import streamlit as st
import pandas as pd
from managers.template_manager import list_templates, get_template, update_template, seed_default_templates
from managers.email_manager import list_email_logs, _get_smtp_config

def render():
    user = st.session_state.get("user", {})
    if user.get("role") != "admin":
        st.error("⚠️ Admin access only")
        return
    
    st.title("⚙️ Settings")
    
    tabs = st.tabs(["📝 Email Templates", "📨 SMTP", "🔍 Activity Log", "💾 Database Backup"])
    
    # ==== 1. TEMPLATES ====
    with tabs[0]:
        seed_default_templates()
        tpls = list_templates()
        sel_code = st.selectbox("Select Template", [t["code"] for t in tpls], format_func=lambda x: x, key="tpl_sel")
        tpl = get_template(sel_code)
        
        with st.form("edit_tpl"):
            subject = st.text_input("Subject", value=tpl.get("subject", ""))
            body = st.text_area("Body (HTML)", value=tpl.get("body", ""), height=300)
            if st.form_submit_button("💾 Save Template", type="primary"):
                update_template(sel_code, subject, body)
                st.success("Template updated successfully!")

    # ==== 2. SMTP ====
    with tabs[1]:
        cfg = _get_smtp_config()
        if cfg:
            st.success("✅ SMTP is configured")
            st.code(f"Host: {cfg.get('host')}\nFrom: {cfg.get('from_email')}")
            # ตรงนี้สามารถเพิ่มปุ่ม Send Test Email ได้
        else:
            st.warning("⚠️ SMTP not configured.")
            st.info("Check secrets.toml for [smtp] section.")

    # ==== 3. ACTIVITY LOG ====
    with tabs[2]:
        logs = list_email_logs(limit=100) # เพิ่มตัวเลือกจำกัดจำนวน
        if logs:
            df = pd.DataFrame(logs)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No logs found.")

    # ==== 4. DATABASE BACKUP ====
    with tabs[3]:
        from managers.db_persistence import get_backup_status, force_push
        status = get_backup_status()
        
        if status["configured"]:
            col1, col2, col3 = st.columns(3)
            col1.metric("Last Push", status["last_push_str"])
            col2.metric("Size", f"{status['db_size_bytes'] / 1024:.1f} KB")
            col3.metric("Pending", "Yes" if status["is_dirty"] else "No")
            
            if st.button("🚀 Force Push to GitHub"):
                with st.spinner("Pushing..."):
                    ok, msg = force_push()
                    if ok: st.success(msg)
                    else: st.error(msg)
        else:
            # ยุบรวมคู่มือไว้ใน expander เพื่อความเป็นระเบียบ
            with st.expander("📖 How to configure Auto-backup"):
                st.markdown("... [ใส่ขั้นตอน setup ของคุณที่นี่] ...")