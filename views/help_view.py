"""Help / User Manual view - improved version."""
import streamlit as st
import time
from pathlib import Path
from datetime import datetime
from config import BASE_DIR, OUTPUT_DIR

def get_readable_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def render():
    st.title("📘 Help / User Manual")
    st.caption("Comprehensive guide for all modules.")
    
    # ===== Download PDF section =====
    col1, col2 = st.columns([1, 2])
    pdf_path = Path(OUTPUT_DIR) / "Smart_Freight_NTT_Manual.pdf"
    
    with col1:
        st.markdown("##### 📥 Download PDF")
        if st.button("🔄 Generate Latest PDF", type="primary", use_container_width=True):
            try:
                from pdf.manual_pdf import generate_manual_pdf
                with st.spinner("Generating document..."):
                    generate_manual_pdf(str(pdf_path))
                    st.toast("✅ PDF generated successfully!", icon="✅")
            except Exception as ex:
                st.error(f"PDF generation failed: {ex}")
        
        if pdf_path.exists():
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            st.download_button("📥 Download Manual PDF", pdf_data, 
                               file_name="Smart_Freight_NTT_Manual.pdf", 
                               mime="application/pdf", use_container_width=True)
            st.caption(f"📄 Size: {len(pdf_data)/1024:.1f} KB | Updated: {get_readable_time(pdf_path.stat().st_mtime)}")
        else:
            st.info("Click 'Generate' to create the manual.")
    
    with col2:
        st.markdown("##### 📚 Quick Reference")
        st.warning("⚠️ **Note:** Ensure 'Profit Sheet' is completed before marking jobs as 'Closed'.")
    
    st.markdown("---")
    
    # ===== Inline manual viewer =====
    st.markdown("##### 📖 Read Online")
    md_path = BASE_DIR / "USER_MANUAL.md"
    
    if md_path.exists():
        md_text = md_path.read_text(encoding="utf-8")
        
        # ปรับปรุงตัวเลือก Section
        sections = [line[3:].strip() for line in md_text.split("\n") if line.startswith("## ")]
        selected = st.selectbox("Jump to section:", ["(Read all)"] + sections, key="help_section")
        
        # แสดงเนื้อหาแบบสโครลได้
        with st.container(height=500):
            if selected != "(Read all)":
                lines = md_text.split("\n")
                start, end = None, len(lines)
                for i, line in enumerate(lines):
                    if line.startswith("## ") and selected in line:
                        start = i
                    elif start is not None and line.startswith("## "):
                        end = i
                        break
                st.markdown("\n".join(lines[start:end]) if start is not None else md_text)
            else:
                st.markdown(md_text)
    else:
        st.error("USER_MANUAL.md not found.")