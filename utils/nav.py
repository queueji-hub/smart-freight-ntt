"""Shared navigation helper — sidebar always visible + mobile responsive."""
import streamlit as st


def setup_sidebar():
    """Inject CSS so the sidebar is always visible with a working toggle button.
    Call at the top of every page."""
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
        position: fixed !important;
        top: 0.5rem !important;
        left: 0.5rem !important;
    }

    /* =========================================
       2. SIDEBAR — visible by default
       ========================================= */
    section[data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        min-width: 14rem !important;
    }
    [data-testid="stSidebarNav"] {
        display: block !important;
        visibility: visible !important;
    }
    [data-testid="stSidebarNav"] ul {
        display: block !important;
    }
    [data-testid="stSidebarNav"] ul li {
        display: list-item !important;
        visibility: visible !important;
        height: auto !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebarNav"] ul li a {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
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
