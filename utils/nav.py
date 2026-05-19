"""Shared navigation helper — rename 'app' to 'Dashboard' in sidebar."""
import streamlit as st


def setup_sidebar():
    """Inject CSS to rename the first sidebar nav item from 'app' to 'Dashboard'.
    Call this at the top of every page."""
    st.markdown("""
    <style>
    [data-testid="stSidebarNav"] ul li:first-child a span:first-child {
        font-size: 0;
    }
    [data-testid="stSidebarNav"] ul li:first-child a span:first-child::after {
        content: "📊 Dashboard";
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)
