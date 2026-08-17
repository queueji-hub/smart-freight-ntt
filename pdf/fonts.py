"""Centralized Thai-compatible font registration for all PDFs."""
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from config import BASE_DIR

_REGISTERED = None


def register_thai_fonts() -> tuple:
    global _REGISTERED
    if _REGISTERED is not None:
        return _REGISTERED
    base = Path(BASE_DIR) / "assets" / "fonts"
    candidates = [
        (base / "Sarabun-Regular.ttf", base / "Sarabun-Bold.ttf", "Sarabun"),
        (Path("C:/Windows/Fonts/tahoma.ttf"), Path("C:/Windows/Fonts/tahomabd.ttf"), "Tahoma"),
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"), "DejaVuSans"),
    ]
    for regular, bold, name in candidates:
        if not regular.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, str(regular)))
            bold_name = name
            if bold.exists() and bold != regular:
                pdfmetrics.registerFont(TTFont(f"{name}-Bold", str(bold)))
                bold_name = f"{name}-Bold"
                try:
                    pdfmetrics.registerFontFamily(name, normal=name, bold=bold_name, italic=name, boldItalic=bold_name)
                    pdfmetrics.registerFontFamily(bold_name, normal=bold_name, bold=bold_name, italic=bold_name, boldItalic=bold_name)
                except Exception:
                    pass
            _REGISTERED = (name, bold_name)
            return _REGISTERED
        except Exception:
            continue
    _REGISTERED = ("Helvetica", "Helvetica-Bold")
    return _REGISTERED


THAI_FONT, THAI_FONT_BOLD = register_thai_fonts()
