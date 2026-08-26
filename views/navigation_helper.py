"""
Central Navigation Helper for Streamlit Views.
Provides safe tab redirection and active tab resolution before widget instantiation,
preventing StreamlitAPIException: st.session_state.<key> cannot be modified after widget is instantiated.
"""
from typing import List, Any
import streamlit as st


def get_active_tab(nav_key: str, tab_options: List[str], default_idx: int = 0) -> str:
    """
    Consumes any queued redirection signal and safely initializes the session state
    BEFORE st.radio, st.selectbox, or st.segmented_control widget is instantiated.
    """
    redirect_key = f"_nav_redirect_{nav_key}"
    if redirect_key in st.session_state:
        target = st.session_state.pop(redirect_key)
        if target in tab_options:
            st.session_state[nav_key] = target
        elif isinstance(target, int) and 0 <= target < len(tab_options):
            st.session_state[nav_key] = tab_options[target]
        else:
            st.session_state[nav_key] = target

    if nav_key not in st.session_state or st.session_state[nav_key] not in tab_options:
        st.session_state[nav_key] = tab_options[default_idx]

    return st.session_state[nav_key]


def redirect_to_tab(nav_key: str, target_tab: Any) -> None:
    """
    Queues a safe tab redirect to be applied at the beginning of the next script run
    before the navigation widget is rendered.
    """
    st.session_state[f"_nav_redirect_{nav_key}"] = target_tab
