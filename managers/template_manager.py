import re
from typing import Dict, List, Any, Optional
from database.connection import get_connection
from config import COMPANY

def render_template(code: str, context: Dict[str, Any]) -> Dict[str, str]:
    """Render template using Regex for high-performance substitution."""
    tpl = get_template(code)
    if not tpl:
        return {"subject": "", "body": ""}
    
    # รวม context พื้นฐานจากบริษัทเข้ากับข้อมูลที่ส่งมา
    full_context = {
        "company_name": COMPANY.get("name", ""),
        "signer_name": COMPANY.get("signer_name", ""),
        "signer_title": COMPANY.get("signer_title", ""),
        **{k: (str(v) if v is not None else "") for k, v in context.items()},
    }

    def replace_match(match):
        key = match.group(1)
        return full_context.get(key, match.group(0)) # คืนค่าเดิมหากหา key ไม่เจอ

    # ใช้ Regex ค้นหา {{key}} ทั้งหมดแล้วแทนที่
    pattern = re.compile(r"\{\{(\w+)\}\}")
    subject = pattern.sub(replace_match, tpl["subject"] or "")
    body = pattern.sub(replace_match, tpl["body"] or "")
    
    return {"subject": subject, "body": body}

def update_template(code: str, subject: str, body: str) -> bool:
    """Update template and commit changes."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE email_templates SET subject=%s, body=%s, updated_at=CURRENT_TIMESTAMP WHERE code=%s",
            (subject, body, code)
        )
        conn.commit()
    return True