def setup_sidebar():
    st.markdown("""
    <style>
    /* 1. ซ่อนปุ่มระบบ แต่ไม่ยุ่งกับ Sidebar Nav */
    div[data-testid="stManageAppButton"] { display: none !important; }
    #MainMenu, header { visibility: hidden !important; }

    /* 2. บังคับ Sidebar ให้แสดงผลชื่อหน้าตามปกติ */
    [data-testid="stSidebarNav"] {
        visibility: visible !important;
    }

    /* 3. จัดการเรื่องการเปลี่ยนชื่อเมนู โดยใช้ CSS แบบเจาะจง */
    [data-testid="stSidebarNav"] ul li:first-child a span:first-child {
        font-size: 0 !important;
    }
    [data-testid="stSidebarNav"] ul li:first-child a span:first-child::after {
        content: "📊 Dashboard" !important;
        font-size: 14px !important;
        visibility: visible !important;
    }

    /* 4. [ส่วน Mobile] เก็บไว้เหมือนเดิม */
    @media (max-width: 768px) {
        .block-container { padding: 0.75rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)