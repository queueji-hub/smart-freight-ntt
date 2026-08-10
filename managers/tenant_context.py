import streamlit as st

def get_current_tenant_id() -> str:
    """
    Returns the authenticated tenant ID from the session state.
    Defaults to 'default' if the session is not yet initialized or in a non-SaaS dev context.
    """
    if hasattr(st, 'session_state') and hasattr(st.session_state, 'user') and isinstance(st.session_state.user, dict):
        return st.session_state.user.get('tenant_id', 'default')
    
    # Fallback to default for legacy/testing purposes
    return 'default'
