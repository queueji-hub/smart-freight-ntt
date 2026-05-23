"""Email notification system - SMTP-based."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from database.connection import get_connection

try:
    import streamlit as st
except ImportError:
    st = None


def _ensure_email_table():
    """Create email_log table."""
    with get_connection() as conn:
        # 🟢 แก้ไข: ใช้ SERIAL แทน AUTOINCREMENT
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_log (
                id SERIAL PRIMARY KEY,
                to_email TEXT NOT NULL,
                cc TEXT,
                subject TEXT,
                body TEXT,
                attachments TEXT,
                status TEXT DEFAULT 'pending',
                error TEXT,
                sent_at TIMESTAMP,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def _get_smtp_config() -> Optional[Dict[str, Any]]:
    """Read SMTP config from Streamlit secrets."""
    if st is None:
        return None
    try:
        cfg = dict(st.secrets["smtp"])
        if not cfg.get("host"):
            return None
        return cfg
    except Exception:
        return None


def send_email(to: str,
               subject: str,
               body: str,
               cc: Optional[str] = None,
               attachments: Optional[List[str]] = None,
               from_user: Optional[str] = None) -> Dict[str, Any]:
    """Send email via SMTP. If SMTP is not configured, log as draft."""
    _ensure_email_table()
    cfg = _get_smtp_config()
    attach_str = ",".join(attachments) if attachments else None
    
    if not cfg:
        with get_connection() as conn:
            # 🟢 แก้ไข: เปลี่ยน ? เป็น %s
            conn.execute(
                "INSERT INTO email_log (to_email, cc, subject, body, "
                "attachments, status, error, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (to, cc, subject, body, attach_str, "draft", "SMTP not configured", from_user)
            )
        return {"ok": False, "status": "draft", "message": "SMTP not configured."}
    
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{cfg.get('from_name','Smart Freight NTT')} <{cfg['from_email']}>"
        msg["To"] = to
        if cc:
            msg["Cc"] = cc
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))
        
        if attachments:
            for fp in attachments:
                if not Path(fp).exists():
                    continue
                with open(fp, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={Path(fp).name}")
                msg.attach(part)
        
        recipients = [to] + ([c.strip() for c in cc.split(",")] if cc else [])
        
        with smtplib.SMTP(cfg["host"], cfg.get("port", 587)) as server:
            server.starttls()
            server.login(cfg["username"], cfg["password"])
            server.send_message(msg, to_addrs=recipients)
        
        with get_connection() as conn:
            # 🟢 แก้ไข: เปลี่ยน ? เป็น %s
            conn.execute(
                "INSERT INTO email_log (to_email, cc, subject, body, "
                "attachments, status, sent_at, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (to, cc, subject, body, attach_str, "sent", datetime.now(), from_user)
            )
        return {"ok": True, "status": "sent", "message": "Email sent"}
    
    except Exception as ex:
        with get_connection() as conn:
            # 🟢 แก้ไข: เปลี่ยน ? เป็น %s
            conn.execute(
                "INSERT INTO email_log (to_email, cc, subject, body, "
                "attachments, status, error, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (to, cc, subject, body, attach_str, "failed", str(ex), from_user)
            )
        return {"ok": False, "status": "failed", "message": str(ex)}


def list_email_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """List email logs."""
    _ensure_email_table()
    with get_connection() as conn:
        # 🟢 แก้ไข: เปลี่ยน ? เป็น %s
        rows = conn.execute(
            "SELECT * FROM email_log ORDER BY created_at DESC LIMIT %s",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]