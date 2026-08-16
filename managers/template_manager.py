from managers.tenant_context import get_current_tenant_id
import re
from typing import Dict, List, Any, Optional
from database.connection import get_connection

_templates_table_ensured = False

def ensure_templates_table():
    """Ensure that the email_templates table exists in the database."""
    global _templates_table_ensured
    if _templates_table_ensured:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS email_templates (
                        code VARCHAR(50) PRIMARY KEY,
                        subject VARCHAR(255) NOT NULL,
                        body TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                _templates_table_ensured = True
            except Exception:
                conn.rollback()

def seed_default_templates():
    """Seeds the default system templates if they don't already exist."""
    ensure_templates_table()
    defaults = {
        "BOOKING_CONF": (
            "Booking Confirmation - {{booking_no}}",
            "Dear {{customer_name}},\n\nYour booking {{booking_no}} has been confirmed. Details:\nPOL: {{pol}}\nPOD: {{pod}}\nETD: {{etd}}\nETA: {{eta}}\n\nBest regards,\n{{signer_name}}\n{{signer_title}}\n{{company_name}}"
        ),
        "ARRIVAL_NOTICE": (
            "Arrival Notice - {{job_no}}",
            "Dear {{customer_name}},\n\nYour shipment {{job_no}} is arriving at {{pod}} on {{eta}}.\n\nBest regards,\n{{signer_name}}\n{{signer_title}}\n{{company_name}}"
        ),
        "INVOICE_TRANSMIT": (
            "Invoice {{doc_no}} Transmittal",
            "Dear {{customer_name}},\n\nPlease find attached invoice {{doc_no}} for shipment {{job_no}}.\nOutstanding: {{outstanding}} {{currency}}.\n\nBest regards,\n{{signer_name}}\n{{signer_title}}\n{{company_name}}"
        )
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            for code, (subj, body) in defaults.items():
                try:
                    cur.execute("SELECT code FROM email_templates WHERE code = %s", (code,))
                    if not cur.fetchone():
                        cur.execute("""
                            INSERT INTO email_templates (code, subject, body)
                            VALUES (%s, %s, %s)
                        """, (code, subj, body))
                except Exception:
                    pass
            conn.commit()

def list_templates() -> List[Dict[str, Any]]:
    """Returns a list of all email templates."""
    ensure_templates_table()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT code, subject, body FROM email_templates ORDER BY code")
            rows = cur.fetchall()
            return [dict(r) for r in rows]

def get_template(code: str) -> Optional[Dict[str, Any]]:
    """Fetches a single email template by code."""
    ensure_templates_table()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT code, subject, body FROM email_templates WHERE code = %s", (code,))
            row = cur.fetchone()
            return dict(row) if row else None

def update_template(code: str, subject: str, body: str) -> bool:
    """Updates an email template's subject and body."""
    ensure_templates_table()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE email_templates
                SET subject = %s, body = %s, updated_at = CURRENT_TIMESTAMP
                WHERE code = %s
            """, (subject, body, code))
            conn.commit()
    return True

def render_template(code: str, context: Dict[str, Any]) -> Dict[str, str]:
    """Renders a template by substituting variables."""
    from config import COMPANY
    tpl = get_template(code)
    if not tpl:
        return {"subject": "", "body": ""}
    
    full_context = {
        "company_name": COMPANY.get("name", ""),
        "signer_name": COMPANY.get("signer_name", ""),
        "signer_title": COMPANY.get("signer_title", ""),
        **{k: (str(v) if v is not None else "") for k, v in context.items()},
    }

    def replace_match(match):
        key = match.group(1)
        return full_context.get(key, match.group(0))

    pattern = re.compile(r"\{\{(\w+)\}\}")
    subject = pattern.sub(replace_match, tpl["subject"] or "")
    body = pattern.sub(replace_match, tpl["body"] or "")
    
    return {"subject": subject, "body": body}