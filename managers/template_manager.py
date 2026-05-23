"""Email & document templates with variable substitution."""
from typing import Dict, List, Any, Optional
from database.connection import get_connection

# Built-in templates with placeholders {{var}}
DEFAULT_TEMPLATES = {
    "quotation_send": {
        "name": "Send Quotation",
        "subject": "Quotation {{quotation_no}} from {{company_name}}",
        "body": """<p>Dear {{customer_name}},</p>
<p>Please find attached our quotation <b>{{quotation_no}}</b> dated {{quotation_date}}.</p>
<p>This quotation is valid until <b>{{validity_date}}</b>.</p>
<p>Should you have any questions, please feel free to contact us.</p>
<p>Best regards,<br/>
{{signer_name}}<br/>
{{signer_title}}<br/>
{{company_name}}</p>"""
    },
    "booking_confirmation": {
        "name": "Booking Confirmation",
        "subject": "Booking Confirmation {{booking_no}}",
        "body": """<p>Dear {{customer_name}},</p>
<p>This is to confirm your booking <b>{{booking_no}}</b>.</p>
<ul>
<li><b>POL:</b> {{pol}}</li>
<li><b>POD:</b> {{pod}}</li>
<li><b>Carrier:</b> {{carrier}}</li>
<li><b>Vessel:</b> {{m_vessel}}</li>
<li><b>ETD:</b> {{etd}}</li>
<li><b>ETA:</b> {{eta}}</li>
<li><b>Closing Time:</b> {{closing_time}}</li>
</ul>
<p>Please review the attached booking confirmation document.</p>
<p>Best regards,<br/>{{signer_name}}<br/>{{company_name}}</p>"""
    },
    "shipment_update": {
        "name": "Shipment Status Update",
        "subject": "Shipment Update: {{job_no}} — {{status}}",
        "body": """<p>Dear {{customer_name}},</p>
<p>This is an update for your shipment <b>{{job_no}}</b>.</p>
<ul>
<li><b>Status:</b> {{status}}</li>
<li><b>Container:</b> {{container_no}}</li>
<li><b>Route:</b> {{pol}} → {{pod}}</li>
<li><b>ETA:</b> {{eta}}</li>
</ul>
<p>Best regards,<br/>{{signer_name}}<br/>{{company_name}}</p>"""
    },
    "invoice_send": {
        "name": "Send Invoice",
        "subject": "Invoice {{doc_no}} — {{customer_name}}",
        "body": """<p>Dear {{customer_name}},</p>
<p>Please find attached invoice <b>{{doc_no}}</b> for amount <b>{{currency}} {{total_amount}}</b>.</p>
<p><b>Due date:</b> {{due_date}}</p>
<p>Kindly arrange payment per agreed terms.</p>
<p>Best regards,<br/>{{signer_name}}<br/>{{company_name}}</p>"""
    },
    "payment_reminder": {
        "name": "Payment Reminder",
        "subject": "Payment Reminder: Invoice {{doc_no}}",
        "body": """<p>Dear {{customer_name}},</p>
<p>This is a friendly reminder that invoice <b>{{doc_no}}</b> with outstanding amount of <b>{{currency}} {{outstanding}}</b> was due on <b>{{due_date}}</b>.</p>
<p>Kindly arrange payment at your earliest convenience.</p>
<p>Best regards,<br/>{{signer_name}}<br/>{{company_name}}</p>"""
    },
}

_SEED_DONE = False

def _ensure_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_templates (
                id SERIAL PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                is_default INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def seed_default_templates():
    global _SEED_DONE
    if _SEED_DONE: return
    _ensure_table()
    with get_connection() as conn:
        for code, tpl in DEFAULT_TEMPLATES.items():
            conn.execute("""
                INSERT INTO email_templates (code, name, subject, body, is_default)
                VALUES (%s, %s, %s, %s, 1)
                ON CONFLICT (code) DO NOTHING
            """, (code, tpl["name"], tpl["subject"], tpl["body"]))
    _SEED_DONE = True

def get_template(code: str) -> Optional[Dict[str, Any]]:
    seed_default_templates()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM email_templates WHERE code=%s", (code,)
        ).fetchone()
    return dict(row) if row else None

def list_templates() -> List[Dict[str, Any]]:
    seed_default_templates()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM email_templates ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]

def update_template(code: str, subject: str, body: str) -> bool:
    _ensure_table()
    with get_connection() as conn:
        conn.execute(
            "UPDATE email_templates SET subject=%s, body=%s, updated_at=CURRENT_TIMESTAMP WHERE code=%s",
            (subject, body, code)
        )
    return True

def render_template(code: str, context: Dict[str, Any]) -> Dict[str, str]:
    """Render template with {{var}} substitution."""
    tpl = get_template(code)
    if not tpl:
        return {"subject": "", "body": ""}
    
    subject = tpl["subject"] or ""
    body = tpl["body"] or ""
    
    from config import COMPANY
    full_context = {
        "company_name": COMPANY.get("name", ""),
        "signer_name": COMPANY.get("signer_name", ""),
        "signer_title": COMPANY.get("signer_title", ""),
        **{k: ("" if v is None else str(v)) for k, v in context.items()},
    }
    
    for key, val in full_context.items():
        placeholder = "{{" + key + "}}"
        subject = subject.replace(placeholder, str(val))
        body = body.replace(placeholder, str(val))
    
    return {"subject": subject, "body": body}