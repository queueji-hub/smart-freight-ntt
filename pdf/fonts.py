"""Centralized Thai-compatible font registration for ALL PDFs.

Call register_thai_fonts() once at module top to ensure Thai chars render
correctly in any reportlab PDF.

Returns (regular, bold) font names that can be used in ParagraphStyle.fontName.
"""
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import BASE_DIR


_REGISTERED = None


def register_thai_fonts() -> tuple:
    """Register Thai-supporting Unicode fonts. Cached after first call.
    
    Returns (regular_font_name, bold_font_name).
    """
    global _REGISTERED
    if _REGISTERED is not None:
        return _REGISTERED
    
    # Priority list: bundled → system fonts → fallback
    candidates = [
        # Bundled Sarabun (Thai-optimized, OFL license)
        (BASE_DIR / "assets" / "fonts" / "Sarabun-Regular.ttf",
         BASE_DIR / "assets" / "fonts" / "Sarabun-Bold.ttf",
         "Sarabun"),
        # Linux (Streamlit Cloud has DejaVu installed by default)
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
         Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
         "DejaVuSans"),
        # macOS
        (Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
         Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
         "ArialUnicode"),
        # Windows (dev only)
        (Path("C:/Windows/Fonts/tahoma.ttf"),
         Path("C:/Windows/Fonts/tahomabd.ttf"),
         "Tahoma"),
    ]
    
    for reg_path, bold_path, name in candidates:
        try:
            if not reg_path.exists():
                continue
            
            pdfmetrics.registerFont(TTFont(name, str(reg_path)))
            
            bold_name = f"{name}-Bold"
            if bold_path.exists() and bold_path != reg_path:
                pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
            else:
                bold_name = name  # fallback to same font
            
            # Register family for easy use
            try:
                from reportlab.pdfbase.pdfmetrics import registerFontFamily
                registerFontFamily(name, normal=name, bold=bold_name,
                                    italic=name, boldItalic=bold_name)
            except Exception:
                pass
            
            _REGISTERED = (name, bold_name)
            return _REGISTERED
        except Exception:
            continue
    
    # Last resort - built-in Helvetica (won't render Thai but won't crash)
    _REGISTERED = ("Helvetica", "Helvetica-Bold")
    return _REGISTERED


# Auto-register on import
THAI_FONT, THAI_FONT_BOLD = register_thai_fonts()
