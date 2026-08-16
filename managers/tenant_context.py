import streamlit as st
from typing import Optional

_OVERRIDE_TENANT_ID: Optional[str] = None

def get_current_tenant_id() -> str:
    """
    Returns the authenticated tenant ID from the session state or runtime context.
    Defaults to 'default' if the session is not yet initialized or in a non-SaaS dev context.
    """
    global _OVERRIDE_TENANT_ID
    if _OVERRIDE_TENANT_ID is not None:
        return _OVERRIDE_TENANT_ID
    if hasattr(st, 'session_state') and hasattr(st.session_state, 'user') and isinstance(st.session_state.user, dict):
        return st.session_state.user.get('tenant_id', 'default')
    
    # Fallback to default for legacy/testing purposes
    return 'default'

def set_current_tenant_id(tenant_id: Optional[str]) -> None:
    """Explicitly set or clear tenant override for testing or background execution."""
    global _OVERRIDE_TENANT_ID
    _OVERRIDE_TENANT_ID = tenant_id
