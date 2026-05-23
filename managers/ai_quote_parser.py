"""AI-powered quotation extractor.
Reads customer emails/text and produces structured quotation drafts.
"""
import json
import os
import re
from typing import Dict, Any, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# ใช้ environment variable หรือ Streamlit secrets
def _get_openai_client() -> Optional[Any]:
    if OpenAI is None:
        return None
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            pass
            
    return OpenAI(api_key=api_key) if api_key else None

SYSTEM_PROMPT = """You are an expert freight forwarding quotation assistant.
Extract shipment details from customer emails and output JSON.
... (คงเนื้อหาเดิมไว้) ...
"""

def _heuristic_parse(text: str) -> Dict[str, Any]:
    """Fallback parser using regex + keywords."""
    result = {
        "job_type": None, "customer_name": None, "shipper_cnee": None,
        "carrier": None, "pol": None, "pod": None, "service_type": None,
        "attention": None, "tel": None, "incoterm": None, "commodity": None,
        "weight": None, "quantity_desc": None, "subject": None,
        "items": [], "confidence": "low", "missing_info": [], "_method": "heuristic"
    }
    
    t = text.lower()
    
    # Logic เดิมสำหรับดึงข้อมูล...
    if any(x in t for x in ["sea export", "se "]): result["job_type"] = "SE"
    # ... (สามารถคง Logic เดิมของคุณไว้ได้เลยครับ)
    
    return result

def parse_email_to_quotation(text: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Parse customer email/text into a quotation draft."""
    if not text or not text.strip():
        return {"error": "Empty input", "items": []}
    
    client = _get_openai_client()
    
    if client is None:
        return _heuristic_parse(text)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        parsed = json.loads(response.choices[0].message.content)
        parsed["_method"] = "ai"
        parsed["_model"] = model
        return parsed
    except Exception as ex:
        # Fallback to heuristic if AI fails
        result = _heuristic_parse(text)
        result["_error"] = str(ex)
        return result

def is_ai_available() -> bool:
    return _get_openai_client() is not None