"""Reusable email-with-attachment dialog used by Quotation/Booking/Invoice views."""
import streamlit as st
from managers.email_manager import send_email
from managers.template_manager import render_template


def email_form(template_code: str, context: dict,
                attachment_path: str = None,
                default_to: str = "",
                default_cc: str = "",
                key_prefix: str = "em") -> bool:
    """Render an inline email-sending form. Returns True if sent."""
    rendered = render_template(template_code, context)
    
    st.markdown("##### ✉️ Compose Email")
    col1, col2 = st.columns(2)
    with col1:
        to = st.text_input("To *", value=default_to, key=f"{key_prefix}_to")
    with col2:
        cc = st.text_input("Cc (comma-separated)", value=default_cc,
                            key=f"{key_prefix}_cc")
    
    subject = st.text_input("Subject", value=rendered["subject"],
                              key=f"{key_prefix}_sub")
    body = st.text_area("Body (HTML allowed)", value=rendered["body"],
                          height=250, key=f"{key_prefix}_body")
    
    if attachment_path:
        st.caption(f"📎 Attachment: {attachment_path.split('/')[-1].split(chr(92))[-1]}")
    
    if st.button("📨 Send Email", type="primary",
                  use_container_width=True, key=f"{key_prefix}_send"):
        if not to.strip():
            st.error("'To' email is required")
            return False
        user = st.session_state.get("user", {})
        result = send_email(
            to=to.strip(), subject=subject, body=body,
            cc=cc.strip() if cc.strip() else None,
            attachments=[attachment_path] if attachment_path else None,
            from_user=user.get("username"),
        )
        if result["ok"]:
            st.success(f"✅ {result['message']}")
            return True
        else:
            if result["status"] == "draft":
                st.warning(f"📝 {result['message']}")
            else:
                st.error(f"❌ {result['message']}")
            return False
    return False
