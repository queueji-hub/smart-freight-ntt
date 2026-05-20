"""Shared navigation helper — rename 'app' to 'Dashboard' in sidebar + mobile responsive."""
import streamlit as st


def setup_sidebar():
    """Inject CSS for sidebar rename + mobile responsiveness.
    Call at the top of every page."""
    st.markdown("""
    <style>
    /* =========================================
       1. CORE SYSTEM UI FIXES (ซ่อนปุ่มขยะของระบบ)
       ========================================= */
    div[data-testid="stManageAppButton"] { display: none !important; }
    #MainMenu, header { visibility: hidden !important; display: none !important; }

    /* =========================================
       2. SIDEBAR MENU FIXES (แก้เมนูหายและเปลี่ยนชื่อ)
       ========================================= */
    /* บังคับให้เมนูทุกตัวแสดงผลเสมอ ไม่ว่าจะอยู่หน้าไหน */
    [data-testid="stSidebarNav"] ul li {
        display: list-item !important;
        visibility: visible !important;
        height: auto !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebarNav"] ul li a,
    [data-testid="stSidebarNav"] ul li a[aria-current="page"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }

    /* เปลี่ยนชื่อเมนูแรกสุดให้เป็น '📊 Dashboard' เสมอ ทุกหน้า */
    [data-testid="stSidebarNav"] ul li:first-child {
        display: block !important;
    }
    [data-testid="stSidebarNav"] ul li:first-child a span:first-child {
        font-size: 0 !important;
    }
    [data-testid="stSidebarNav"] ul li:first-child a span:first-child::after {
        content: "📊 Dashboard" !important;
        font-size: 14px !important;
        visibility: visible !important;
    }

    /* (ทางเลือก) บังคับ Sidebar ให้โชว์ตลอดเวลา ห้ามพับเก็บ */
    [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] {
        width: 16rem !important;
        min-width: 16rem !important;
        transform: none !important;
        visibility: visible !important;
        position: relative !important;
    }
    .stApp { margin-left: 0px !important; }


    /* =========================================
       3. MOBILE RESPONSIVE
       ========================================= */
    @media (max-width: 768px) {
        /* Reduce main container padding on mobile */
        .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
            padding-top: 0.5rem !important;
        }
        
        /* Force columns to stack vertically on mobile */
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0.5rem !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 0 !important;
        }
        
        /* KPI strip — make it wrap */
        .kpi-strip {
            flex-wrap: wrap !important;
            gap: 12px !important;
            padding: 8px 12px !important;
            font-size: 0.8rem !important;
        }
        
        /* Smaller headings */
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.15rem !important; }
        h3 { font-size: 1rem !important; }
        
        /* Make buttons full width */
        .stButton button {
            width: 100% !important;
        }
        
        /* Tables: smaller font and allow horizontal scroll */
        .stDataFrame, [data-testid="stTable"] {
            font-size: 0.75rem !important;
            overflow-x: auto !important;
        }
        
        /* Form inputs: bigger touch targets */
        .stTextInput input, .stSelectbox div, .stTextArea textarea {
            font-size: 16px !important; /* prevents iOS zoom */
        }
        
        /* Hide hint captions on mobile (save space) */
        .mobile-hide {
            display: none !important;
        }
        
        /* Status pills: smaller */
        .status-pill {
            font-size: 0.65rem !important;
            padding: 1px 6px !important;
        }
        
        /* Tabs: scroll horizontally if needed */
        [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
        }
    }
    
    /* On very small screens, even more compact */
    @media (max-width: 480px) {
        .kpi-item {
            font-size: 0.75rem !important;
            flex: 1 1 calc(50% - 6px) !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)