from managers.tenant_context import get_current_tenant_id
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from database.connection import get_connection

def _get_smtp_config() -> Optional[Dict[str, Any]]:
    import streamlit as st
    if not hasattr(st, "secrets") or "smtp" not in st.secrets:
        return None
    return dict(st.secrets["smtp"])

def send_email(to: str, subject: str, body: str,
               cc: Optional[str] = None, attachments: Optional[List[str]] = None,
               from_user: Optional[str] = None) -> Dict[str, Any]:
    """Send email via SMTP and log the attempt with tenant isolation."""
    cfg = _get_smtp_config()
    attach_str = ",".join(attachments) if attachments else None
    tenant_id = get_current_tenant_id()
    
    if not cfg:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO email_log (tenant_id, to_email, cc, subject, body, attachments, status, error, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, 'draft', 'SMTP not configured', %s)
                """, (tenant_id, to, cc, subject, body, attach_str, from_user))
            conn.commit()
        return {"ok": False, "status": "draft", "message": "SMTP not configured."}
    
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{cfg.get('from_name', 'FreightFlow NTT')} <{cfg['from_email']}>"
        msg["To"] = to
        if cc: msg["Cc"] = cc
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))
        
        if attachments:
            for fp in attachments:
                path = Path(fp)
                if path.exists():
                    with open(path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f"attachment; filename={path.name}")
                        msg.attach(part)
        
        with smtplib.SMTP(cfg["host"], int(cfg.get("port", 587))) as server:
            server.starttls()
            server.login(cfg["username"], cfg["password"])
            server.send_message(msg)
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO email_log (tenant_id, to_email, cc, subject, body, attachments, status, sent_at, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, 'sent', %s, %s)
                """, (tenant_id, to, cc, subject, body, attach_str, datetime.now(), from_user))
            conn.commit()
        return {"ok": True, "status": "sent", "message": "Email sent"}
    
    except Exception as ex:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO email_log (tenant_id, to_email, cc, subject, body, attachments, status, error, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, 'failed', %s, %s)
                """, (tenant_id, to, cc, subject, body, attach_str, str(ex), from_user))
            conn.commit()
        return {"ok": False, "status": "failed", "message": str(ex)}

def list_email_logs(limit: int = 100) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM email_log WHERE tenant_id = %s ORDER BY created_at DESC LIMIT %s", 
                (tenant_id, limit)
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]