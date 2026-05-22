"""Help / User Manual view - download PDF + browse online."""
import streamlit as st
from pathlib import Path
from config import BASE_DIR, OUTPUT_DIR


def render():
    st.title("📘 Help / User Manual")
    st.caption("Comprehensive guide for all modules · Download PDF or read online")
    
    # ===== Download PDF section =====
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("##### 📥 Download PDF")
        
        # Lazy generate PDF on demand
        pdf_path = Path(OUTPUT_DIR) / "Smart_Freight_NTT_Manual.pdf"
        
        if st.button("🔄 Generate Latest PDF",
                      type="primary", use_container_width=True):
            try:
                from pdf.manual_pdf import generate_manual_pdf
                with st.spinner("Generating PDF..."):
                    generate_manual_pdf(str(pdf_path))
                st.success("✅ PDF ready!")
            except Exception as ex:
                st.error(f"PDF generation failed: {ex}")
        
        # Show download button if PDF exists
        if pdf_path.exists():
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            st.download_button(
                "📥 Download Manual PDF",
                pdf_data,
                file_name="Smart_Freight_NTT_Manual.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            file_size_kb = len(pdf_data) / 1024
            st.caption(f"📄 Size: {file_size_kb:.1f} KB · "
                       f"Updated: {pdf_path.stat().st_mtime}")
        else:
            st.info("Click 'Generate Latest PDF' first")
    
    with col2:
        st.markdown("##### 📚 Quick Reference")
        st.markdown("""
        - **Login:** Demo accounts in section 1
        - **CRM:** Manage customer master data
        - **Quotation → Booking → Shipment** workflow
        - **Profit Sheet** required before "Closed" status
        - **Billing:** Invoice, BN, CN, DN, SOA with VAT/WHT
        - **FX Rates:** Multi-currency conversion to THB
        """)
    
    st.markdown("---")
    
    # ===== Inline manual viewer =====
    st.markdown("##### 📖 Read Online")
    
    md_path = BASE_DIR / "USER_MANUAL.md"
    if md_path.exists():
        md_text = md_path.read_text(encoding="utf-8")
        
        # Section navigator
        sections = []
        for line in md_text.split("\n"):
            if line.startswith("## "):
                title = line[3:].strip()
                sections.append(title)
        
        if sections:
            selected = st.selectbox("Jump to section:", ["(Read all)"] + sections,
                                      key="help_section")
            
            if selected != "(Read all)":
                # Extract just that section
                lines = md_text.split("\n")
                start = None
                end = len(lines)
                for i, line in enumerate(lines):
                    if line.startswith("## ") and selected in line:
                        start = i
                    elif start is not None and line.startswith("## "):
                        end = i
                        break
                if start is not None:
                    md_text = "\n".join(lines[start:end])
        
        # Render markdown
        with st.container(border=True):
            st.markdown(md_text)
    else:
        st.warning("USER_MANUAL.md not found in repository")
