import streamlit as st

def setup_sidebar() -> None:
    """
    ตั้งค่า Sidebar และ UI พื้นฐานของ Streamlit (Production-Ready)
    - ซ่อนเมนูเริ่มต้นของ Streamlit ที่ไม่จำเป็น
    - ปรับปรุงการแสดงผลบนโทรศัพท์มือถือ (Mobile Responsive)
    - ป้องกันปัญหา UI ขยับหรือล้นจอ (Overflow fixes)
    """
    
    st.markdown("""
    <style>
        /* ===============================
           1. CORE UI & STABILITY
        =============================== */
        
        /* ซ่อน Main Menu และปุ่ม Deploy ที่ไม่จำเป็นในระดับ Production */
        #MainMenu, header[data-testid="stHeader"] .stAppDeployButton { 
            visibility: hidden !important; 
            display: none !important;
        }

        /* ปรับแต่ง Header ให้โปร่งแสงและเบลอพื้นหลัง */
        header[data-testid="stHeader"] {
            background: rgba(14, 16, 21, 0.7) !important;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px); /* รองรับ Safari */
            height: 2.5rem !important;
            z-index: 9999 !important;
        }

        /* บังคับให้ Sidebar แสดงผลในขนาดที่เหมาะสมเสมอ */
        section[data-testid="stSidebar"] {
            min-width: 16rem !important;
            max-width: 20rem !important;
        }

        /* ซ่อน Sidebar Navigation เดิมของ Streamlit (เผื่อใช้ Custom Menu) */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* ป้องกันเนื้อหาล้นหน้าจอ (Horizontal Scroll) */
        [data-testid="stAppViewContainer"] {
            overflow-x: hidden !important;
        }

        /* ===============================
           1.5 MATERIAL SYMBOLS & STREAMLIT ICONS
        =============================== */
        
        /* ซ่อน Footer "Made with Streamlit" */
        footer {
            display: none !important;
        }

        /* Sidebar toggle icon */
        [data-testid="stSidebarCollapseButton"] span,
        [data-testid="stSidebarHeaderCollapseButton"] span,
        [data-testid="collapsedControl"] span {
            font-size: 0px !important;
            line-height: 0 !important;
            color: transparent !important;
            text-indent: -9999px !important;
            width: 24px !important;
            height: 24px !important;
            display: inline-flex !important;
            overflow: hidden !important;
            position: relative !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] span::after,
        section[data-testid="stSidebar"] [data-testid="stSidebarHeaderCollapseButton"] span::after {
            content: "◀" !important;
            font-size: 13px !important;
            color: #64748b !important;
            text-indent: 0 !important;
            position: absolute !important;
            top: 0; left: 0; right: 0; bottom: 0;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        [data-testid="collapsedControl"] span::after {
            content: "▶" !important;
            font-size: 13px !important;
            color: #2563eb !important;
            text-indent: 0 !important;
            position: absolute !important;
            top: 0; left: 0; right: 0; bottom: 0;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* Password eye icon */
        div[data-testid="stTextInput"] button span,
        div[data-testid="stPasswordInput"] button span {
            font-size: 0px !important;
            line-height: 0 !important;
            color: transparent !important;
            text-indent: -9999px !important;
            width: 20px !important;
            height: 20px !important;
            display: inline-flex !important;
            overflow: hidden !important;
            position: relative !important;
        }
        div[data-testid="stTextInput"] button span::after,
        div[data-testid="stPasswordInput"] button span::after {
            content: "👁" !important;
            font-size: 14px !important;
            color: #64748b !important;
            text-indent: 0 !important;
            position: absolute !important;
            top: 0; left: 0; right: 0; bottom: 0;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* Expander chevron */
        [data-testid="stExpanderToggleIcon"],
        details summary span:first-child {
            font-size: 0px !important;
            line-height: 0 !important;
            color: transparent !important;
            text-indent: -9999px !important;
            width: 18px !important;
            height: 18px !important;
            display: inline-flex !important;
            overflow: hidden !important;
            position: relative !important;
        }
        [data-testid="stExpanderToggleIcon"]::after,
        details summary span:first-child::after {
            content: "▼" !important;
            font-size: 10px !important;
            color: #64748b !important;
            text-indent: 0 !important;
            position: absolute !important;
            top: 0; left: 0; right: 0; bottom: 0;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        details[open] summary [data-testid="stExpanderToggleIcon"]::after,
        details[open] summary span:first-child::after {
            content: "▲" !important;
        }

        /* Selectbox dropdown arrow */
        [data-testid="stSelectbox"] [data-baseweb="select"] span[class*="material"],
        [data-testid="stSelectbox"] [data-baseweb="select"] div[role="button"] span {
            font-size: 0px !important;
            line-height: 0 !important;
            color: transparent !important;
            text-indent: -9999px !important;
            width: 16px !important;
            height: 16px !important;
            display: inline-flex !important;
            overflow: hidden !important;
            position: relative !important;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"] span[class*="material"]::after,
        [data-testid="stSelectbox"] [data-baseweb="select"] div[role="button"] span::after {
            content: "▼" !important;
            font-size: 9px !important;
            color: #64748b !important;
            text-indent: 0 !important;
            position: absolute !important;
            top: 0; left: 0; right: 0; bottom: 0;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* ซ่อน Toolbar ที่ไม่จำเป็น */
        [data-testid="stElementToolbar"],
        [data-testid="stHeaderActionElements"] {
            display: none !important;
        }

        /* ===============================
           2. MOBILE RESPONSIVE (MAX 768px)
        =============================== */
        
        @media screen and (max-width: 768px) {
            /* ลด Padding ด้านข้างเพื่อให้มีพื้นที่แสดงข้อมูลมากขึ้น */
            .block-container {
                padding: 1.5rem 1rem !important;
            }

            /* บังคับให้ Column เรียงซ้อนกันเป็นแนวตั้งบนมือถือ */
            [data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
                gap: 1rem !important;
            }

            [data-testid="stColumn"] {
                width: 100% !important;
            }

            /* ขยายปุ่มให้กว้างเต็มพื้นที่บนมือถือ (กดง่ายขึ้น) */
            .stButton button {
                width: 100% !important;
            }

            /* ปรับขนาดฟอนต์ของตาราง Dataframe ให้เล็กลงพอดีจอ */
            .stDataFrame {
                font-size: 0.8rem !important;
            }

            /* ป้องกัน iOS Auto-zoom เมื่อคลิก Input (บังคับให้ font-size เป็น 16px) */
            .stTextInput input,
            .stSelectbox div,
            .stTextArea textarea,
            .stNumberInput input {
                font-size: 16px !important;
            }

            /* ปรับขนาด Heading ให้เหมาะสมกับหน้าจอมือถือ */
            h1 { font-size: 1.5rem !important; }
            h2 { font-size: 1.25rem !important; }
            h3 { font-size: 1.1rem !important; }
        }
    </style>
    """, unsafe_allow_html=True)