"""Shared navigation helper — mobile responsive CSS only."""
import streamlit as st


def setup_sidebar():
    """Inject CSS for mobile responsiveness and clean UI.
    Call at the top of every page."""
    st.markdown("""
    <style>
    /* =========================================
       1. KEEP SIDEBAR TOGGLE BUTTON VISIBLE
       ========================================= */
    /* Hide the deploy/share button only, keep header for sidebar toggle */
    div[data-testid="stManageAppButton"] { display: none !important; }
    #MainMenu { visibility: hidden !important; }

    /* Make header transparent but keep it functional for sidebar toggle */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: auto !important;
        z-index: 999 !important;
    }

    /* Ensure the sidebar collapse/expand button is always visible */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    button[kind="header"],
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 9999 !important;
    }

    /* =========================================
       2. SIDEBAR — ensure all nav items visible when open
       ========================================= */
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
            padding-top: 0.5rem !important;
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
