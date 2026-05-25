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