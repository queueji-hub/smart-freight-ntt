"""Page guard — clears session_state when switching between pages.

Prevents stale UI elements and form state from one page leaking into another.
"""
import streamlit as st


# Keys that should NEVER be cleared (database connection cache, etc.)
_PROTECTED_PREFIXES = ("__",)
_PROTECTED_KEYS = set()


def enforce_page(page_id: str) -> None:
    """Call at the very top of every page (after st.set_page_config).
    
    If the current page differs from last visited page, clear ALL session state
    so each page starts fresh. This prevents widgets/forms from prior pages
    from rendering stale data.
    """
    last_page = st.session_state.get("_current_page_id")
    
    if last_page != page_id:
        # Switched pages — wipe everything except protected keys
        keys_to_clear = [
            k for k in list(st.session_state.keys())
            if not k.startswith(_PROTECTED_PREFIXES)
            and k not in _PROTECTED_KEYS
            and k != "_current_page_id"
        ]
        for k in keys_to_clear:
            try:
                del st.session_state[k]
            except KeyError:
                pass
        
        st.session_state["_current_page_id"] = page_id
