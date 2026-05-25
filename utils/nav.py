import streamlit as st


def setup_sidebar():
    """Production-safe sidebar + mobile layout control"""

    st.markdown("""
    <style>

    /* ===============================
       CORE UI STABILITY FIX
    =============================== */

    #MainMenu { visibility: hidden !important; }

    header[data-testid="stHeader"] {
        background: rgba(14,16,21,0.7) !important;
        backdrop-filter: blur(8px);
        height: 2.5rem !important;
        z-index: 9999 !important;
    }

    /* Sidebar always visible */
    section[data-testid="stSidebar"] {
        min-width: 14rem !important;
        max-width: 18rem !important;
        visibility: visible !important;
    }

    /* Hide only Streamlit default nav */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* ===============================
       MOBILE RESPONSIVE FIX (SAFE)
    =============================== */
    @media (max-width: 768px) {

        .block-container {
            padding: 1rem !important;
        }

        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
        }

        [data-testid="stColumn"] {
            width: 100% !important;
        }

        .stButton button {
            width: 100% !important;
        }

        .stDataFrame {
            font-size: 0.75rem !important;
        }

        .stTextInput input,
        .stSelectbox div,
        .stTextArea textarea {
            font-size: 16px !important;
        }

        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1rem !important; }
    }

    /* ===============================
       EXTRA STABILITY FIX
    =============================== */
    [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
    }

    </style>
    """, unsafe_allow_html=True)