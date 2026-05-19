"""AI-powered quotation extractor.
Reads customer emails/text and produces structured quotation drafts.

Usage:
    from managers.ai_quote_parser import parse_email_to_quotation
    result = parse_email_to_quotation(email_text)
    # result is a dict matching the quotation form schema
"""
import json
import os
import re
from datetime import date, timedelta
from typing import Dict, Any, List, Optional

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False


# Read API key from env or Streamlit secrets
def _get_openai_client() -> Optional["OpenAI"]:
    if not _OPENAI_AVAILABLE:
        return None
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Try Streamlit secrets
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            pass
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


SYSTEM_PROMPT = """You are an expert freight forwarding quotation assistant for a Thai freight forwarder.
Extract shipment details from customer emails or messages and produce structured JSON.

Rules:
- Always respond with valid JSON matching the schema, no markdown.
- If a field is unclear, use null. Never guess.
- For job_type: SE=Sea Export, SI=Sea Import, AE=Air Export, AI=Air Import, TE=Truck Export, TI=Truck Import.
- Detect Thai/English/Chinese in input.
- Container types: 20GP, 40GP, 40HC, 40OT, 20FR, 20OT, 40HQ.
- Common Thai POL: Laem Chabang, Bangkok Port; common POD: any global port.
- Currency: USD by default unless THB/CNY mentioned.
- Use 'OOG' / 'Project' for special cargo if mentioned.

Output JSON schema:
{
  "job_type": "SE|SI|AE|AI|TE|TI|null",
  "customer_name": "string|null",
  "shipper_cnee": "string|null",
  "carrier": "string|null",
  "pol": "string|null",
  "pod": "string|null",
  "service_type": "CY/CY|CY/CFS|CFS/CY|CFS/CFS|AIR|TRUCK|null",
  "attention": "string|null",
  "tel": "string|null",
  "incoterm": "FOB|CIF|DAP|DDP|DDU|EXW|C&F|null",
  "commodity": "string|null",
  "weight": "string|null",
  "quantity_desc": "string|null",
  "subject": "string|null",
  "items": [
    {
      "description": "string",
      "currency": "USD|THB|CNY|EUR",
      "price": number,
      "unit": "string",
      "remark": "string|null"
    }
  ],
  "confidence": "high|medium|low",
  "missing_info": ["list of missing required fields"]
}
"""


def _heuristic_parse(text: str) -> Dict[str, Any]:
    """Fallback parser when no OpenAI key — uses regex + keywords."""
    result = {
        "job_type": None,
        "customer_name": None,
        "shipper_cnee": None,
        "carrier": None,
        "pol": None,
        "pod": None,
        "service_type": None,
        "attention": None,
        "tel": None,
        "incoterm": None,
        "commodity": None,
        "weight": None,
        "quantity_desc": None,
        "subject": None,
        "items": [],
        "confidence": "low",
        "missing_info": [],
        "_method": "heuristic",
    }
    
    t = text.lower()
    
    # Detect job type
    if "sea export" in t or "se " in t.lower():
        result["job_type"] = "SE"
    elif "sea import" in t or " si " in t.lower():
        result["job_type"] = "SI"
    elif "air export" in t:
        result["job_type"] = "AE"
    elif "air import" in t:
        result["job_type"] = "AI"
    
    # Extract Tel (Thai or international)
    tel_match = re.search(
        r'(\+?\d{1,3}[\s-]?)?(\(?\d{2,3}\)?[\s-]?)?\d{3}[\s-]?\d{4}', text
    )
    if tel_match:
        result["tel"] = tel_match.group(0).strip()
    
    # Detect carrier
    carriers = ["MAERSK", "MSC", "CMA", "ONE", "EVERGREEN", "COSCO", "OOCL",
                "HAPAG", "ZIM", "SITC", "PIL", "HEUNG-A", "SINOKOR",
                "WAN HAI", "YANG MING", "HMM", "KMTC", "INTERASIA"]
    for c in carriers:
        if c.lower() in t:
            result["carrier"] = c
            break
    
    # Detect Incoterm
    incoterms = ["FOB", "CIF", "DAP", "DDP", "DDU", "EXW", "C&F"]
    for i in incoterms:
        if i.lower() in t:
            result["incoterm"] = i
            break
    
    # Detect POD
    common_ports = [
        "Laem Chabang", "Bangkok", "Singapore", "Shanghai", "Hong Kong",
        "Incheon", "Busan", "Tokyo", "Yokohama", "Jebel Ali", "New York",
        "Long Beach", "Los Angeles", "Hamburg", "Rotterdam", "Sydney",
    ]
    for p in common_ports:
        if p.lower() in t:
            if not result["pod"]:
                result["pod"] = p
            elif not result["pol"]:
                result["pol"] = p
    
    result["missing_info"] = [
        f for f, v in result.items()
        if v is None and f in ("job_type", "customer_name", "pol", "pod")
    ]
    
    return result


def parse_email_to_quotation(text: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Parse customer email/text into a quotation draft.
    
    Returns dict with all quotation fields filled (or null if not found).
    Falls back to heuristic parsing if OpenAI is not configured.
    """
    if not text or not text.strip():
        return {"error": "Empty input", "items": []}
    
    client = _get_openai_client()
    
    if client is None:
        # Fallback to heuristic
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
        content = response.choices[0].message.content
        parsed = json.loads(content)
        parsed["_method"] = "ai"
        parsed["_model"] = model
        return parsed
    except Exception as ex:
        # Graceful fallback
        result = _heuristic_parse(text)
        result["_error"] = str(ex)
        return result


def is_ai_available() -> bool:
    """Check if OpenAI is configured."""
    return _get_openai_client() is not None
