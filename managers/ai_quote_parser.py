"""AI-powered quotation extractor."""
import json
import os
from typing import Dict, Any, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# ปรับปรุง System Prompt ให้เป็นมาตรฐานเดียวกัน
SYSTEM_PROMPT = """You are an expert freight forwarding quotation assistant.
Extract the following information from customer emails into a structured JSON format:
- job_type: (SE, SI, AE, AI)
- customer_name, shipper_cnee, attention, tel
- pol, pod, incoterm, commodity
- weight, quantity_desc
- items: list of items (description, estimated_amount)
- missing_info: list of fields that could not be found

Always return a valid JSON object.
"""

def _get_openai_client() -> Optional[Any]:
    """Retrieve OpenAI client using environment or Streamlit secrets."""
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

def _heuristic_parse(text: str) -> Dict[str, Any]:
    """Fallback parser using simple keyword matching."""
    t = text.lower()
    # ตรวจสอบเบื้องต้น
    job_type = "SE" if any(x in t for x in ["sea export", "se "]) else "SI"
    
    return {
        "job_type": job_type,
        "customer_name": None,
        "items": [],
        "confidence": "low",
        "missing_info": ["All detailed fields"],
        "_method": "heuristic"
    }

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
            temperature=0,
        )
        data = json.loads(response.choices[0].message.content)
        data["_method"] = "ai"
        data["_model"] = model
        return data
    except Exception as ex:
        # หาก AI มีปัญหา ให้ใช้ heuristic และแนบ Error ไปด้วย
        result = _heuristic_parse(text)
        result["_error"] = str(ex)
        result["_method"] = "heuristic_fallback"
        return result

def is_ai_available() -> bool:
    """Check if OpenAI is properly configured."""
    return _get_openai_client() is not None