"""Settings - Email templates, company info, email log."""
import streamlit as st
import pandas as pd
from managers.template_manager import (
    list_templates, get_template, update_template, seed_default_templates,
)
from managers.email_manager import list_email_logs, _get_smtp_config


def render():
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    if role != "admin":
        st.error("⚠️ Admin only")
        return
    
    st.title("⚙️ Settings")
    st.caption("Email templates · SMTP config · Activity logs")
    
    tab_t, tab_s, tab_l, tab_b = st.tabs([
        "📝 Email Templates", "📨 SMTP & Email Log",
        "🔍 Activity Log", "💾 Database Backup",
    ])
    
    # ==== TEMPLATES ====
    with tab_t:
        seed_default_templates()
        tpls = list_templates()
        if not tpls:
            st.info("No templates.")
        else:
            options = {t["code"]: f"{t['name']} ({t['code']})" for t in tpls}
            sel_code = st.selectbox("Template", list(options.keys()),
                                      format_func=lambda c: options[c],
                                      key="tpl_sel")
            tpl = get_template(sel_code)
            
            with st.form("edit_tpl"):
                subject = st.text_input("Subject", value=tpl["subject"] or "")
                body = st.text_area("Body (HTML)",
                    value=tpl["body"] or "", height=350)
                
                st.caption("Available variables (use {{variable_name}}):")
                st.code("""
Common: {{company_name}} {{signer_name}} {{signer_title}}
Customer: {{customer_name}}
Quotation: {{quotation_no}} {{quotation_date}} {{validity_date}}
Booking: {{booking_no}} {{pol}} {{pod}} {{etd}} {{eta}} {{carrier}} {{m_vessel}}
Shipment: {{job_no}} {{status}} {{container_no}}
Invoice: {{doc_no}} {{currency}} {{total_amount}} {{outstanding}} {{due_date}}
                """, language="text")
                
                if st.form_submit_button("💾 Save Template", type="primary"):
                    update_template(sel_code, subject, body)
                    st.success("Template updated")
    
    # ==== SMTP ====
    with tab_s:
        cfg = _get_smtp_config()
        if cfg:
            st.success("✅ SMTP configured")
            st.code(f"""
Host: {cfg.get('host')}
Port: {cfg.get('port', 587)}
From: {cfg.get('from_email')}
            """, language="text")
        else:
            st.warning("⚠️ SMTP not configured — emails will be saved as drafts")
            st.markdown("""
            **To enable email sending**, add to `.streamlit/secrets.toml`:
            ```toml
            [smtp]
            host = "smtp.gmail.com"
            port = 587
            username = "you@example.com"
            password = "your-app-password"
            from_email = "you@example.com"
            from_name = "Smart Freight NTT"
            ```
            For Gmail: create an [App Password](https://myaccount.google.com/apppasswords).
            For Streamlit Cloud: add via app settings → Secrets.
            """)
        
        st.markdown("---")
        st.markdown("##### 📬 Recent Email Activity")
        logs = list_email_logs(limit=50)
        if logs:
            df = pd.DataFrame(logs)
            cols = ["created_at", "to_email", "subject", "status", "created_by"]
            cols = [c for c in cols if c in df.columns]
            st.dataframe(df[cols], use_container_width=True,
                          hide_index=True, height=300)
        else:
            st.info("No emails sent yet.")
    
    # ==== ACTIVITY LOG ====
    with tab_l:
        from database.connection import get_connection
        with get_connection() as conn:
            try:
                rows = conn.execute(
                    "SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 200"
                ).fetchall()
                logs = [dict(r) for r in rows]
            except Exception:
                logs = []
        
        if logs:
            df = pd.DataFrame(logs)
            cols = ["created_at", "username", "action", "entity_type",
                    "entity_id", "details"]
            cols = [c for c in cols if c in df.columns]
            st.dataframe(df[cols], use_container_width=True,
                          hide_index=True, height=400)
        else:
            st.info("No activity logged yet.")
    
    # ==== DATABASE BACKUP (Auto-persist to GitHub) ====
    with tab_b:
        from managers.db_persistence import (
            get_backup_status, force_push, is_github_configured,
        )
        
        status = get_backup_status()
        
        if status["configured"]:
            st.success(f"✅ Auto-backup configured · Repo: `{status['repo']}`")
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Last Push", status["last_push_str"])
            with c2:
                st.metric("Initial Pull",
                    "✅ Done" if status["initial_pull_done"] else "Pending")
            
            st.markdown("##### 🔄 Manual Backup")
            st.markdown(
                "ระบบจะ auto-backup ทุก 30 วินาทีหลังบันทึกข้อมูล "
                "(หากต้องการ backup ทันที ให้กดปุ่มด้านล่าง)"
            )
            if st.button("💾 Backup Now (Push to GitHub)",
                          type="primary", use_container_width=True):
                with st.spinner("Pushing to GitHub..."):
                    ok = force_push()
                if ok:
                    st.success("✅ Database pushed to GitHub")
                    st.rerun()
                else:
                    st.error("❌ Push failed - check secrets config")
        else:
            st.warning("⚠️ Auto-backup NOT configured")
            st.markdown("""
            ### 📋 Setup Auto-backup ใน 4 ขั้นตอน
            
            **1. สร้าง GitHub Personal Access Token (PAT):**
            
            - ไปที่ https://github.com/settings/tokens
            - คลิก **"Generate new token (classic)"**
            - ตั้งชื่อ: `streamlit-db-backup`
            - เลือก scope: ✅ **`repo`** (full control)
            - กด **Generate token** → copy token (ขึ้นต้น `ghp_...`)
            
            **2. ใน Streamlit Cloud → app settings → Secrets → paste:**
            
            ```toml
            [github]
            token = "ghp_paste_your_token_here"
            repo = "queueji-hub/smart-freight-ntt"
            branch = "main"
            author_name = "Smart Freight Bot"
            author_email = "bot@nattayaraat.com"
            db_path = "data/smart_freight.db"
            ```
            
            **3. กด Save secrets**
            
            **4. Reboot app**
            
            หลังจากนั้น:
            - 📥 ทุกครั้งที่เปิด app ระบบจะ pull DB ล่าสุดจาก GitHub
            - 📤 ทุกครั้งที่บันทึกข้อมูลในระบบ ระบบจะ auto-push DB ขึ้น GitHub (debounce 30 วินาที)
            - ✅ ข้อมูลจะคงอยู่แม้ Reboot/Redeploy
            """)
            
            with st.expander("⚠️ ข้อจำกัดที่ควรทราบ"):
                st.markdown("""
                - **อย่าใช้ระบบพร้อมกันหลายคนบันทึกในเวลาเดียวกัน** อาจเกิด race condition
                - การ push บ่อยๆ อาจถูก GitHub rate limit (ปกติไม่เกิน 5,000 ครั้ง/ชม.)
                - DB file ควรไม่เกิน 100MB (limit ของ GitHub)
                - ทุกการเปลี่ยนแปลงจะปรากฏใน GitHub commit history
                """)
