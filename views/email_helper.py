"""Reusable email-with-attachment dialog."""
import streamlit as st
import re
from managers.email_manager import send_email
from managers.template_manager import render_template

def is_valid_email(email):
    # ตรวจสอบรูปแบบอีเมลเบื้องต้น
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def email_form(template_code: str, context: dict,
                attachment_path: str = None,
                default_to: str = "",
                default_cc: str = "",
                key_prefix: str = "em") -> bool:
    
    # ดึงค่า Template 1 ครั้ง
    rendered = render_template(template_code, context)
    
    with st.expander("✉️ Compose Email", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            to = st.text_input("To *", value=default_to, key=f"{key_prefix}_to")
        with col2:
            cc = st.text_input("Cc (comma-separated)", value=default_cc, key=f"{key_prefix}_cc")
        
        subject = st.text_input("Subject", value=rendered["subject"], key=f"{key_prefix}_sub")
        body = st.text_area("Body (HTML allowed)", value=rendered["body"], height=250, key=f"{key_prefix}_body")
        
        if attachment_path:
            st.caption(f"📎 Attachment: {attachment_path.split('/')[-1]}")
        
        # Action Buttons
        cols = st.columns([1, 1])
        send_btn = cols[0].button("📨 Send Email", type="primary", use_container_width=True)
        
        if send_btn:
            if not to.strip() or not is_valid_email(to.strip()):
                st.error("Please enter a valid 'To' email address.")
                return False
            
            with st.spinner("Sending email..."):
                user = st.session_state.get("user", {})
                result = send_email(
                    to=to.strip(), subject=subject, body=body,
                    cc=cc.strip() if cc.strip() else None,
                    attachments=[attachment_path] if attachment_path else None,
                    from_user=user.get("username"),
                )
                
                if result["ok"]:
                    st.success(f"✅ {result['message']}")
                    # Clear session keys เพื่อ Reset Form
                    for k in [f"{key_prefix}_to", f"{key_prefix}_cc", f"{key_prefix}_sub", f"{key_prefix}_body"]:
                        st.session_state[k] = ""
                    return True
                else:
                    st.error(f"❌ {result['message']}")
                    return False
    return False