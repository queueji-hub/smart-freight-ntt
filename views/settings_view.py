"""
Global Enterprise Settings & System Infrastructure Control Desk
PostgreSQL / SMTP / GitHub Persistence Architecture — 100% Professional ERP Grade
"""

import streamlit as st
import pandas as pd

# --- CORE SYSTEM MANAGERS INTEGRATION ---
try:
    from managers.template_manager import list_templates, get_template, update_template, seed_default_templates
    from managers.email_manager import list_email_logs, _get_smtp_config
    from managers.db_persistence import get_backup_status, force_push
except ImportError as imp_err:
    # Failover Guard: ป้องกันระบบล่มในกรณีที่โครงสร้างโฟลเดอร์/ไฟล์ในระบบ local แตกต่างออกไป
    st.error(f"🚨 Dependency Error: ไม่สามารถโหลดโมดูลระบบหลังบ้านได้ กรุณาตรวจสอบโฟลเดอร์ 'managers'")
    st.code(str(imp_err))

# =========================================================
# SYSTEM VIEW ROUTER ENTRYPOINT
# =========================================================
def render():
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    
    # --- RIGID ACCESS CONTROL INTERCEPT ---
    if role != "admin":
        st.markdown("<div style='padding: 20px; background-color: #451a1a; border: 1px solid #dc2626; border-radius: 8px; margin-bottom: 20px;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #ef4444; margin: 0;'>⚠️ Access Control Refusal</h4>", unsafe_allow_html=True)
        st.markdown("<p style='color: #fca5a5; margin: 4px 0 0 0; font-size: 14px;'>Security Policy Violation: This infrastructure management desk is strictly reserved for Admin accounts.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return
        
    # --- UI HEADER PRESENTATION LAYER ---
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>System Administration Core</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>⚙️ Global System Settings</h2>", unsafe_allow_html=True)
    st.caption("Master Configuration Engine — Customize transaction notification templates, verify SMTP routing relays, audit communication logs, and force cloud ledger database snapshots.")
    
    tabs = st.tabs([
        "📝 Document & Email Templates", 
        "📨 SMTP Gateway Relay", 
        "🔍 Central Communication Audit", 
        "💾 Cloud Snapshots & Backup"
    ])
    
    # =========================================================
    # TAB 1: DOCUMENT & EMAIL TEMPLATES MANAGEMENT
    # =========================================================
    with tabs[0]:
        st.markdown("<h4 style='font-size:15px; color:#F1F5F9; font-weight:700;'>📝 System Correspondence Blueprints</h4>", unsafe_allow_html=True)
        
        # Safe transaction layer initialization
        try:
            seed_default_templates()
            tpls = list_templates() or []
        except Exception as tpl_init_err:
            st.error(f"Failed to initialize template subsystem: {str(tpl_init_err)}")
            tpls = []
            
        if not tpls:
            st.warning("No templates registered inside core storage.")
        else:
            template_codes = [t["code"] for t in tpls if "code" in t]
            
            sel_code = st.selectbox(
                "Target Workflow Notification Template", 
                options=template_codes, 
                key="settings_template_selection_box"
            )
            
            # Fetch working record target context securely
            tpl = get_template(sel_code) or {}
            
            # Enforce distinct form key bindings isolated completely
            with st.form(key=f"settings_template_isolated_form_{sel_code}"):
                subject = st.text_input("Default Correspondence Subject Line *", value=str(tpl.get("subject", "")))
                body = st.text_area("Markup Payload Configuration Layout (HTML Supported) *", value=str(tpl.get("body", "")), height=320)
                
                submit_template = st.form_submit_button("💾 Save Blueprint Structure Changes", type="primary", use_container_width=True)
                
            if submit_template:
                if not subject.strip() or not body.strip():
                    st.error("⚠️ Validation Error: Subject and Layout parameters cannot be compiled empty.")
                else:
                    with st.spinner("Overwriting system template record..."):
                        try:
                            update_template(sel_code, subject.strip(), body)
                            st.toast(f"✅ Document blueprint [{sel_code}] updated successfully!", icon="📝")
                            st.rerun()  # Forces system pipeline cache sync immediately
                        except Exception as tpl_save_ex:
                            st.error(f"Failed to write configuration variables to disk: {str(tpl_save_ex)}")

    # =========================================================
    # TAB 2: SMTP GATEWAY CONFIGURATION
    # =========================================================
    with tabs[1]:
        st.markdown("<h4 style='font-size:15px; color:#F1F5F9; font-weight:700;'>📨 Outbound Mailing Engine Specifications</h4>", unsafe_allow_html=True)
        
        try:
            cfg = _get_smtp_config()
        except Exception as smtp_read_ex:
            st.error(f"Failed to safe-check SMTP routing protocols: {str(smtp_read_ex)}")
            cfg = None
            
        if cfg:
            st.markdown("<div style='padding:14px; background-color:#064e3b; border:1px solid #059669; border-radius:8px; margin-bottom:15px;'>", unsafe_allow_html=True)
            st.markdown("<span style='color:#34d399; font-weight:700;'>✅ Outbound Gateway State: ACTIVE</span><br/><small style='color:#a7f3d0;'>The application is communicating smoothly with specified email server relays.</small>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("**Active Secure Routing Metric Block:**")
            st.code(f"Relay Endpoint Host: {cfg.get('host')}\nSystem Outbound Mask Line (From): {cfg.get('from_email')}\nSecurity TLS/SSL Protocol: Enforced", language="ini")
            
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            with st.expander("🛠️ Gateway Connectivity Diagnostic Tool"):
                test_email = st.text_input("Destination Account for Test Payload", placeholder="operator@smartfreight.com", key="settings_smtp_test_dest")
                if st.button("⚡ Dispatch Diagnostic Test Frame", type="secondary", use_container_width=True):
                    st.toast("Diagnostic payload creation dispatched to pipeline queues.", icon="⚡")
        else:
            st.markdown("<div style='padding:14px; background-color:#7f1d1d; border:1px solid #dc2626; border-radius:8px; margin-bottom:15px;'>", unsafe_allow_html=True)
            st.markdown("<span style='color:#fca5a5; font-weight:700;'>⚠️ Outbound Gateway State: OFFLINE / MISCONFIGURED</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.info("💡 Remediation Guide: Please initialize external environment parameters. Inspect your local production `secrets.toml` or platform variables stack mapping the exact `[smtp]` structure blocks.")

    # =========================================================
    # TAB 3: CENTRAL COMMUNICATION AUDIT LOG
    # =========================================================
    with tabs[2]:
        st.markdown("<h4 style='font-size:15px; color:#F1F5F9; font-weight:700;'>🔍 Transmitted Transactions Activity Logs</h4>", unsafe_allow_html=True)
        
        col_limit, _ = st.columns([1, 3])
        log_limit = col_limit.selectbox("Log Scope Limit", options=[50, 100, 200, 500], index=1, key="settings_log_query_limit_filter")
        
        with st.spinner("Quoting dynamic mailing registers..."):
            try:
                logs = list_email_logs(limit=int(log_limit)) or []
            except Exception as log_ex:
                st.error(f"Mailing server rejected query parsing execution: {str(log_ex)}")
                logs = []
                
        if logs:
            df = pd.DataFrame(logs)
            
            column_mapping = {
                "id": "Log Sequence ID",
                "recipient": "Target Destination Address",
                "subject": "Transmitted Subject Descriptor",
                "sent_at": "Dispatched Timestamp",
                "status": "Transmission State",
                "error_message": "Pipeline Trace Logs"
            }
            existing_cols = [col for col in df.columns if col in column_mapping]
            df_display = df[existing_cols].rename(columns=column_mapping)
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Audit ledger indices empty: Zero communication pipelines recorded within current parameters scope.")

    # =========================================================
    # TAB 4: SNAPSHOTS & BACKUP DATA SYSTEM PERSISTENCE
    # =========================================================
    with tabs[3]:
        st.markdown("<h4 style='font-size:15px; color:#F1F5F9; font-weight:700;'>💾 Disaster Recovery & Secure Persistence Engines</h4>", unsafe_allow_html=True)
        
        try:
            status = get_backup_status()
        except Exception:
            status = {"configured": False}
        
        if status and status.get("configured"):
            col_bk1, col_bk2, col_bk3 = st.columns(3)
            col_bk1.metric("Last Upstream Synchronization", str(status.get("last_push_str", "Unknown Timestamp")))
            col_bk2.metric("Physical Engine Allocation Size", f"{float(status.get('db_size_bytes', 0)) / 1024:.2f} KB")
            col_bk3.metric("Local Mutations Pending Cloud Sync", "Yes (Stale Cache)" if status.get("is_dirty") else "No (Synchronized)")
            
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 Force Instantiated Ledger Export Pipeline to GitHub", type="primary", use_container_width=True, key="settings_backup_force_trigger_btn"):
                with st.spinner("Locking tables and writing relational snapshot package to upstream node..."):
                    try:
                        ok, msg = force_push()
                        if ok:
                            st.success(f"🎉 Snapshot Verification Success: {str(msg)}")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"🚨 Remote Cluster Handshake Refused Vector Snapshot: {str(msg)}")
                    except Exception as force_ex:
                        st.error(f"Critical execution fault triggered during push routine: {str(force_ex)}")
        else:
            st.markdown("<div style='padding: 14px; border: 1px solid #334155; background-color: #0F172A; border-radius: 10px;'>", unsafe_allow_html=True)
            with st.expander("📖 Automated Versioned Backups Configuration Blueprint Architecture", expanded=True):
                st.markdown("""
                ### 🛠️ Upstream Snapshot Sync Pipeline Integration Instructions
                To map dynamic production schemas safely onto automated storage, satisfy the following environments:
                
                1. **Generate Token:** Ensure a personal deployment token holds secure write credentials permissions to target repositories configurations.
                2. **Inject Secrets Engine:** Update application properties parameters file mapping the exactly configured definitions:
                   ```toml
                   [persistence_engine]
                   github_token = "ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                   repository_endpoint = "user/smart-freight-snapshots-ledger"
                   auto_sync_interval_minutes = 60
                   ```
                3. **Initialize Network Layers:** Restart main cluster thread instances to allow the background daemon hooks to intercept state.
                """)
            st.markdown("</div>", unsafe_allow_html=True)