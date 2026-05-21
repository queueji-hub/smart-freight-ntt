"""Shared navigation helper — sidebar always visible + mobile responsive.

Note: This app uses single-file architecture with custom sidebar buttons,
so we hide Streamlit's auto-generated nav (stSidebarNav).
"""
import streamlit as st


def setup_sidebar():
    """Inject CSS for sidebar visibility and mobile responsiveness."""
    st.markdown("""
    <style>
    /* =========================================
       1. KEEP HEADER (with toggle button) VISIBLE
       ========================================= */
    div[data-testid="stManageAppButton"] { display: none !important; }
    #MainMenu { visibility: hidden !important; }

    header[data-testid="stHeader"] {
        background: rgba(14,16,21,0.6) !important;
        backdrop-filter: blur(8px);
        height: 2.5rem !important;
        z-index: 999999 !important;
        display: block !important;
        visibility: visible !important;
    }

    /* Sidebar toggle button — always visible, top-left */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    button[kind="header"],
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 9999999 !important;
    }

    /* =========================================
       2. HIDE Streamlit's auto-generated nav (we use custom buttons)
       ========================================= */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    section[data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        min-width: 14rem !important;
    }

    /* =========================================
       3. MOBILE RESPONSIVE
       ========================================= */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
            padding-top: 2.5rem !important;
        }
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0.5rem !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 0 !important;
        }
        .kpi-strip {
            flex-wrap: wrap !important;
            gap: 12px !important;
            padding: 8px 12px !important;
            font-size: 0.8rem !important;
        }
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.15rem !important; }
        h3 { font-size: 1rem !important; }
        .stButton button { width: 100% !important; }
        .stDataFrame, [data-testid="stTable"] {
            font-size: 0.75rem !important;
            overflow-x: auto !important;
        }
        .stTextInput input, .stSelectbox div, .stTextArea textarea {
            font-size: 16px !important;
        }
        .mobile-hide { display: none !important; }
        .status-pill {
            font-size: 0.65rem !important;
            padding: 1px 6px !important;
        }
        [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
        }
    }
    @media (max-width: 480px) {
        .kpi-item {
            font-size: 0.75rem !important;
            flex: 1 1 calc(50% - 6px) !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
