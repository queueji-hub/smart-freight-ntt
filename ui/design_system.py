"""Shared UI design primitives for Smart Freight NTT.

Keep this module presentation-only. It must not access database, managers, or business logic.
"""
import streamlit as st

PAGE_TITLES = {
    "dashboard": "Home",
    "crm": "Customers",
    "quotation": "Quotations",
    "booking": "Bookings",
    "shipment": "Jobs",
    "bl": "Bills of Lading",
    "document": "Documents",
    "billing": "Finance",
    "ap": "Payables",
    "profit": "Profitability",
    "reports": "Reports",
    "regulatory": "Compliance",
    "users": "Users",
    "settings": "Settings",
}

PAGE_SUBTITLES = {
    "dashboard": "Ask about operations, customers and finance.",
    "crm": "Manage customer master data and commercial terms.",
    "quotation": "Create and manage freight quotations.",
    "booking": "Manage carrier bookings and shipment instructions.",
    "shipment": "Manage jobs, execution, documents and financials.",
    "bl": "Create and manage bills of lading from job data.",
    "document": "Access operational and financial documents.",
    "billing": "Manage receivables, billing and tax documents.",
    "ap": "Manage vendor payables and payment workflow.",
    "profit": "Review revenue, cost, profit and margin by job.",
    "reports": "Monitor operational and financial performance.",
    "regulatory": "Manage compliance and regulatory workflows.",
    "users": "Manage users and access roles.",
    "settings": "Manage system preferences and configuration.",
}


def apply_theme() -> None:
    """Apply one lightweight visual system across the app."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Sarabun:wght@400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&family=Material+Icons&family=Material+Icons+Outlined&family=Material+Icons+Round&family=Material+Icons+Sharp&display=swap');

        @font-face {
            font-family: 'Material Symbols Rounded';
            font-style: normal;
            font-weight: 100 700;
            src: url(https://fonts.gstatic.com/s/materialsymbolsrounded/v217/syKg-zpnAoQgL0kmAzMrEQBu4deNPoK5470puED74V0.woff2) format('woff2');
        }

        :root {
            --sf-navy: #0f172a;
            --sf-blue: #2563eb;
            --sf-bg: #f8fafc;
            --sf-card: #ffffff;
            --sf-border: #e2e8f0;
            --sf-text: #0f172a;
            --sf-muted: #64748b;
            --sf-success: #16a34a;
            --sf-warning: #d97706;
            --sf-danger: #dc2626;
        }

        html, body {
            font-family: 'Inter', 'Sarabun', -apple-system, BlinkMacSystemFont, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }

        /* Standard text elements font */
        p, input, textarea, select, label, h1, h2, h3, h4, h5, h6 {
            font-family: 'Inter', 'Sarabun', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* =========================================================
           BULLETPROOF ICONS & ZERO LIGATURE TEXT LEAKS
        ========================================================= */

        /* 1. SIDEBAR COLLAPSE / EXPAND TOGGLE */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarHeaderCollapseButton"],
        [data-testid="collapsedControl"],
        div[data-testid="collapsedControl"] button,
        button[data-testid="baseButton-headerNoPadding"],
        button[data-testid="baseButton-header"] {
            position: relative !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        [data-testid="stSidebarCollapseButton"] span,
        [data-testid="stSidebarHeaderCollapseButton"] span,
        [data-testid="collapsedControl"] span,
        div[data-testid="collapsedControl"] button span {
            font-size: 0px !important;
            line-height: 0 !important;
            color: transparent !important;
            text-indent: -9999px !important;
            width: 24px !important;
            height: 24px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            overflow: hidden !important;
            position: relative !important;
        }

        /* Sidebar open -> close button (arrow pointing left ◀) */
        section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] span::after,
        section[data-testid="stSidebar"] [data-testid="stSidebarHeaderCollapseButton"] span::after,
        section[data-testid="stSidebar"] button[data-testid="baseButton-headerNoPadding"] span::after {
            content: "◀" !important;
            font-size: 13px !important;
            color: #64748b !important;
            text-indent: 0 !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            position: absolute !important;
            top: 0; left: 0; right: 0; bottom: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }

        /* Sidebar closed -> open button (arrow pointing right ▶) */
        [data-testid="collapsedControl"] span::after,
        div[data-testid="collapsedControl"] button span::after {
            content: "▶" !important;
            font-size: 13px !important;
            color: #2563eb !important;
            text-indent: 0 !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            position: absolute !important;
            top: 0; left: 0; right: 0; bottom: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }

        /* 2. PASSWORD VISIBILITY TOGGLE EYE */
        div[data-testid="stTextInput"] button,
        div[data-testid="stPasswordInput"] button,
        div[data-testid="stTextInput"] button[aria-label*="password" i],
        div[data-testid="stTextInput"] button[aria-label*="Password" i] {
            position: relative !important;
        }

        div[data-testid="stTextInput"] button span,
        div[data-testid="stPasswordInput"] button span,
        div[data-testid="stTextInput"] button[aria-label*="password" i] span,
        div[data-testid="stTextInput"] button[aria-label*="Password" i] span {
            font-size: 0px !important;
            line-height: 0 !important;
            color: transparent !important;
            text-indent: -9999px !important;
            width: 20px !important;
            height: 20px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            overflow: hidden !important;
            position: relative !important;
        }

        div[data-testid="stTextInput"] button span::after,
        div[data-testid="stPasswordInput"] button span::after,
        div[data-testid="stTextInput"] button[aria-label*="password" i] span::after,
        div[data-testid="stTextInput"] button[aria-label*="Password" i] span::after {
            content: "👁" !important;
            font-size: 14px !important;
            color: #64748b !important;
            text-indent: 0 !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            position: absolute !important;
            top: 0; left: 0; right: 0; bottom: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }

        /* 3. EXPANDER DROPDOWN CHEVRON */
        [data-testid="stExpanderToggleIcon"],
        details[data-testid="stExpander"] summary span:first-child,
        [data-testid="stExpander"] summary span:first-child,
        details summary span:first-child {
            font-size: 0px !important;
            line-height: 0 !important;
            color: transparent !important;
            text-indent: -9999px !important;
            width: 18px !important;
            height: 18px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            overflow: hidden !important;
            position: relative !important;
        }

        [data-testid="stExpanderToggleIcon"]::after,
        details[data-testid="stExpander"] summary span:first-child::after,
        [data-testid="stExpander"] summary span:first-child::after,
        details summary span:first-child::after {
            content: "▼" !important;
            font-size: 10px !important;
            color: #64748b !important;
            text-indent: 0 !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            position: absolute !important;
            top: 0; left: 0; right: 0; bottom: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            transition: transform 0.15s ease !important;
        }

        details[data-testid="stExpander"][open] summary [data-testid="stExpanderToggleIcon"]::after,
        details[data-testid="stExpander"][open] summary span:first-child::after,
        details[open] summary span:first-child::after {
            content: "▲" !important;
        }

        /* 4. SELECTBOX DROPDOWN ARROW */
        [data-testid="stSelectbox"] [data-baseweb="select"] span[class*="material"],
        [data-testid="stSelectbox"] [data-baseweb="select"] div[role="button"] span,
        [data-baseweb="select"] span[class*="material"] {
            font-size: 0px !important;
            line-height: 0 !important;
            color: transparent !important;
            text-indent: -9999px !important;
            width: 16px !important;
            height: 16px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            overflow: hidden !important;
            position: relative !important;
        }

        [data-testid="stSelectbox"] [data-baseweb="select"] span[class*="material"]::after,
        [data-testid="stSelectbox"] [data-baseweb="select"] div[role="button"] span::after,
        [data-baseweb="select"] span[class*="material"]::after {
            content: "▼" !important;
            font-size: 9px !important;
            color: #64748b !important;
            text-indent: 0 !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            position: absolute !important;
            top: 0; left: 0; right: 0; bottom: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }

        /* 5. GENERAL MATERIAL SYMBOLS FALLBACK */
        .stIconMaterial,
        [data-testid="stIconMaterial"],
        .material-symbols-rounded,
        .material-symbols-outlined,
        .material-icons {
            font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
            letter-spacing: normal !important;
            text-transform: none !important;
            direction: ltr !important;
            -webkit-font-feature-settings: 'liga' 1 !important;
            font-feature-settings: 'liga' 1 !important;
            -webkit-font-smoothing: antialiased !important;
        }

        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 1560px;
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid var(--sf-border);
        }

        /* Metric cards - Adaptive typography and zero clipping */
        div[data-testid="stMetric"] {
            background: var(--sf-card);
            border: 1px solid var(--sf-border);
            border-radius: 12px;
            padding: 0.85rem 1rem;
            box-shadow: 0 2px 8px rgba(15,23,42,.05);
            min-width: 0 !important;
            overflow: visible !important;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        div[data-testid="stMetric"]:hover {
            box-shadow: 0 4px 12px rgba(15,23,42,.08);
        }
        div[data-testid="stMetric"] label {
            color: var(--sf-muted) !important;
            font-size: 0.76rem !important;
            font-weight: 600 !important;
            white-space: normal !important;
            word-break: break-word !important;
            line-height: 1.25 !important;
        }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            color: var(--sf-text) !important;
            font-size: clamp(0.95rem, 1.35vw, 1.35rem) !important;
            font-weight: 750 !important;
            white-space: normal !important;
            word-break: break-word !important;
            overflow-wrap: anywhere !important;
            text-overflow: clip !important;
            line-height: 1.25 !important;
            letter-spacing: -0.01em !important;
        }

        .sf-page-title {
            margin: 0;
            color: var(--sf-text);
            font-size: 1.55rem;
            font-weight: 750;
            letter-spacing: -.02em;
        }
        .sf-page-subtitle {
            margin: .2rem 0 0;
            color: var(--sf-muted);
            font-size: .86rem;
        }
        .sf-section {
            margin: 1rem 0 .55rem;
            color: var(--sf-text);
            font-size: 1rem;
            font-weight: 700;
        }
        .sf-card {
            background: var(--sf-card);
            border: 1px solid var(--sf-border);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            box-shadow: 0 2px 8px rgba(15,23,42,.04);
        }

        /* Fully visible dataframes & tables */
        .stDataFrame, div[data-testid="stTable"] {
            width: 100% !important;
        }

        /* Refined primary action buttons */
        button[kind="primary"] {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 6px rgba(37,99,235,0.2) !important;
        }
        button[kind="primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
        }
        button[kind="secondary"] {
            border-radius: 8px !important;
            transition: all 0.15s ease !important;
        }

        /* High-contrast alert boxes */
        div[data-testid="stAlert"] {
            border-radius: 10px !important;
            padding: 0.75rem 1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(page_id: str, status_text: str | None = None) -> None:
    # Deduplicate header within a single render execution
    render_key = f"_rendered_hdr_{page_id}"
    if st.session_state.get(render_key):
        return
    st.session_state[render_key] = True

    title = PAGE_TITLES.get(page_id, page_id.replace("_", " ").title())
    subtitle = PAGE_SUBTITLES.get(page_id, "").strip()
    badge = f"<span class='sf-card' style='padding:.3rem .65rem;border-radius:999px;font-size:.72rem;color:#166534;background:#f0fdf4;border-color:#bbf7d0'>{status_text}</span>" if status_text else ""
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;margin-bottom:.9rem'><div><div class='sf-page-title'>{title}</div><div class='sf-page-subtitle'>{subtitle}</div></div>{badge}</div>",
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(f"<div class='sf-section'>{title}</div>", unsafe_allow_html=True)
