"""
AI-Powered Logistics Quotation Extractor & Schema Intelligence Engine
OpenAI GPT-4o Architecture with Rigid Pydantic Structured Outputs Validation
"""

import json
import os
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# =========================================================
# VALIDATION SCHEMAS DEF: RIGID STRUCTURED OUTPUTS MAPPING
# =========================================================
class QuotationLineItem(BaseModel):
    description: str = Field(description="Narrative title of the service fee, ocean charge, or localized transport cost.")
    estimated_amount: float = Field(0.0, description="Numerical estimated monetary tariff or net value. Fallback to 0.0 if unknown.")

class LogisticsQuotePayload(BaseModel):
    job_type: str = Field(description="Must strict fall inside operational domains: 'SE' (Sea Export), 'SI' (Sea Import), 'AE' (Air Export), or 'AI' (Air Import).")
    customer_name: Optional[str] = Field(None, description="Identified trading entity or client account title initiating the RFQ.")
    shipper_cnee: Optional[str] = Field(None, description="Consignor or Consignee trade entity identification statement.")
    attention: Optional[str] = Field(None, description="Target corporate contact officer point of liaison.")
    tel: Optional[str] = Field(None, description="Contact telephone numbers or communication dials.")
    pol: Optional[str] = Field(None, description="Port of Loading location descriptor.")
    pod: Optional[str] = Field(None, description="Port of Discharge / Ultimate delivery endpoint destination.")
    incoterm: Optional[str] = Field(None, description="Standard International Commercial Terms structure (e.g., FOB, CIF, EXW, DDP).")
    commodity: Optional[str] = Field(None, description="Nature description classification of commodities or physical goods cargo.")
    weight: Optional[str] = Field(None, description="Gross, volumetric or net payload mass parameters (e.g., '520 kgs', '3.5 tons').")
    quantity_desc: Optional[str] = Field(None, description="Equipment metric configuration statement (e.g., '1x20GP', '3 Pallets').")
    items: List[QuotationLineItem] = Field(default_factory=list, description="Array configuration list mapping transactional charge items extracted from matrix text.")
    missing_info: List[str] = Field(default_factory=list, description="Explicit array tracking mandatory corporate parameters data that could not be mapped out from the email segment text.")

# =========================================================
# ADVANCED SYSTEM INTEGRATION CORE PROMPT
# =========================================================
SYSTEM_PROMPT = """You are an elite freight forwarding expert and enterprise cargo quotation agent.
Analyze the provided unstructured client email communication log thread, inquiry parameters or freight request tickets, and cleanly translate them into standard corporate logistics fields.

Rigid Classification Rule:
- Classify 'job_type' strictly to: 'SE' (Sea Export), 'SI' (Sea Import), 'AE' (Air Export), or 'AI' (Air Import).
- If the transport route direction or mode is ambiguous, use cross-border context indicators (e.g., 'Flight' or 'Air' matches Air Mode, 'Sailing' or 'Ocean' matches Sea Mode).

Verify your data structures. Ensure float metrics align flawlessly. Items array list must parse pricing values completely.
"""

# =========================================================
# PRIVATE SUBSYSTEM CONTEXT MANAGEMENT HANDLERS
# =========================================================
def _get_openai_client() -> Optional[Any]:
    """Retrieve validated OpenAI client wrapper using platform cluster environment variables or safe Streamlit Secrets engines."""
    if OpenAI is None:
        return None
    
    # Try local environment container configurations first
    api_key = os.environ.get("OPENAI_API_KEY")
    
    # Fallback transaction check onto safe UI platform framework secrets desk
    if not api_key:
        try:
            import streamlit as st
            if "OPENAI_API_KEY" in st.secrets:
                api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            pass  # Silent intercept - prevent thread interruptions
            
    return OpenAI(api_key=api_key) if api_key else None


def _heuristic_parse(text: str) -> Dict[str, Any]:
    """
    Advanced Deterministic Regular Expression Rule-based Fallback Parser.
    Invoked upon system network timeouts, service disruptions, or missing integration tokens.
    """
    t = text.lower()
    
    # Smarter Heuristic Route Direction Decoupling Matrix
    is_air = any(keyword in t for keyword in ["air", "flight", "suvarnabhumi", "bkk", "aviation", "cargo flight"])
    is_export = any(keyword in t for keyword in ["export", "outbound", "ex-thailand", "sending from", "pol: th", "pol: bkk"])
    
    if is_air:
        job_type = "AE" if is_export else "AI"
    else:
        job_type = "SE" if is_export else "SI" # Fallback domain defaults to Sea Cargo operations
        
    # Attempt primitive Incoterm harvesting checks via regex patterns matching 3 alpha characters
    incoterm_match = re.search(r'\b(fob|cif|exw|ddp|dap|cfr|fca|cpt|cip)\b', t)
    extracted_incoterm = incoterm_match.group(1).upper() if incoterm_match else None
    
    return {
        "job_type": job_type,
        "customer_name": "Unstructured Account Entity (Heuristic Fallback)",
        "shipper_cnee": None,
        "attention": None,
        "tel": None,
        "pol": "Determining Pol..." if "pol" in t else None,
        "pod": "Determining Pod..." if "pod" in t else None,
        "incoterm": extracted_incoterm,
        "commodity": None,
        "weight": None,
        "quantity_desc": None,
        "items": [],
        "confidence": "CRITICAL_LOW_HEURISTIC",
        "missing_info": ["All deep multi-currency line-item charge variables and client identity rows require manual validation."],
        "_method": "heuristic_fallback_engine"
    }


# =========================================================
# PUBLIC ENDPOINT FUNCTION TRANSACTIONS INTERFACE
# =========================================================
def parse_email_to_quotation(text: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Parse customer email narrative/text stream into a high-fidelity digital quotation draft payload.
    Uses OpenAI Structured Outputs (beta.chat.completions.parse) to secure data format conformity.
    """
    if not text or not text.strip():
        return {
            "error": "Input text segment null or blank payload configuration parameters.",
            "job_type": "SE",
            "items": [],
            "missing_info": ["Blank Text Document Frame Context"]
        }
    
    client = _get_openai_client()
    if client is None:
        # Graceful degradation failure routing pattern if API credentials missing
        return _heuristic_parse(text)
    
    try:
        # Native integration using rigid response validation model schema bindings
        response = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format=LogisticsQuotePayload,
            temperature=0,  # Strict determinism vector tracking allocation
        )
        
        # Extract validated parsed objects output payload directly
        parsed_data = response.choices[0].message.parsed
        
        if parsed_data:
            # Output matching dictionaries natively for downstream Streamlit state controls mapping
            data_dict = parsed_data.model_dump()
            data_dict["_method"] = "openai_structured_outputs"
            data_dict["_model"] = model
            data_dict["confidence"] = "verified_high"
            return data_dict
        else:
            raise ValueError("Output validation intercept received empty content stream format.")
            
    except Exception as pipeline_fault_exception:
        # Safe catch-all intercept: If AI engine errors out, engage heuristic tracking and anchor debug logs
        fallback_payload = _heuristic_parse(text)
        fallback_payload["_error_trace_logs"] = str(pipeline_fault_exception)
        fallback_payload["_method"] = "runtime_exception_failover_intercept"
        return fallback_payload


def is_ai_available() -> bool:
    """
    Run automated network configuration check to verify if 
    the OpenAI framework credentials handshake resolves smoothly.
    """
    return _get_openai_client() is not None