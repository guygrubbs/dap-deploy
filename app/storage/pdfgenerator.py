import os
import re
from fpdf import FPDF, HTMLMixin
from io import BytesIO
from typing import Union, Dict, Any, List

# -----------------------------------------------------------------------------
# 1. Font paths — adjust as needed
# -----------------------------------------------------------------------------
FONTS_DIR = "fonts"
NOTO_SANS_REGULAR = os.path.join(FONTS_DIR, "NotoSans-Regular.ttf")
NOTO_SANS_BOLD    = os.path.join(FONTS_DIR, "NotoSans-Bold.ttf")
# Optional color-emoji font (won't actually display *in color* for most PDF readers):
NOTO_COLOR_EMOJI  = os.path.join(FONTS_DIR, "NotoColorEmoji-Regular.ttf")

# -----------------------------------------------------------------------------
# 2. Sanitization function
# -----------------------------------------------------------------------------
def _sanitize_text(text: str) -> str:
    """
    Replaces known problematic punctuation (e.g., curly quotes, em dashes)
    with ASCII equivalents. Leaves other Unicode symbols (including color emojis)
    intact so that we can handle them separately.
    """
    replacements = {
        "\u2014": "-",    # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote / apostrophe
        "\u201C": '"',    # left double quote
        "\u201D": '"',    # right double quote
        "\u2026": "...",  # ellipsis
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text

# -----------------------------------------------------------------------------
# 3. Replace color emojis with colored text via HTML
# -----------------------------------------------------------------------------
def _replace_color_emojis_with_html(text: str) -> str:
    """
    Detects common colored circle emojis and replaces them
    with a <span style="color: rgb(...);">COLOR</span> snippet.
    Example: "🟢" -> <span style="color: rgb(0,255,0);">Green</span>
    """
    color_emoji_map = {
        "🟢": ("Green",  "0,255,0"),
        "🔴": ("Red",    "255,0,0"),
        "🟡": ("Yellow", "255,255,0"),
        "🔵": ("Blue",   "0,0,255"),
        "🟠": ("Orange", "255,165,0"),
        "🟣": ("Purple", "128,0,128"),
        "⚫":  ("Black",  "0,0,0"),
        "⚪":  ("White",  "255,255,255"),
        "🟤": ("Brown",  "139,69,19"),
        # Add more if needed
    }

    pattern = "|".join(re.escape(k) for k in color_emoji_map.keys())
    regex = re.compile(pattern)

    def replacer(match):
        emoji = match.group(0)
        color_name, rgb_vals = color_emoji_map[emoji]
        # Return an HTML span that sets font color
        return f'<span style="color: rgb({rgb_vals});">{color_name}</span>'

    return regex.sub(replacer, text)

# -----------------------------------------------------------------------------
# 4. Custom PDF class with HTML support
# -----------------------------------------------------------------------------
class PDFGenerator(FPDF, HTMLMixin):
    """
    Custom PDF class using FPDF + HTMLMixin to allow partial color changes
    via <span style="color:..."></span> for replaced emojis.
    """

    def __init__(self, orientation="P", unit="mm", format="A4"):
        super().__init__(orientation=orientation, unit=unit, format=format)

        # Register Noto Sans
        self.add_font("NotoSans", "", NOTO_SANS_REGULAR, uni=True)
        self.add_font("NotoSans", "B", NOTO_SANS_BOLD,    uni=True)

        # Register Noto Color Emoji (though actual color rendering in PDFs is limited)
        if os.path.exists(NOTO_COLOR_EMOJI):
            self.add_font("NotoEmoji", "", NOTO_COLOR_EMOJI, uni=True)

        # Set our default font (NotoSans regular, size 12)
        self.set_font("NotoSans", "", 12)

        # Enable auto page break
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """
        Defines the header that appears at the top of each page.
        """
        self.set_font("NotoSans", "B", 12)
        self.cell(0, 10, "GFV Investment Readiness Report", border=False, ln=1, align="C")
        self.ln(5)
        self.set_font("NotoSans", "", 12)

    def footer(self):
        """
        Adds a footer with page numbering at the bottom of each page.
        """
        self.set_y(-15)
        self.set_font("NotoSans", "", 8)
        page_text = f"Page {self.page_no()}"
        page_text = _sanitize_text(page_text)  # just in case
        self.cell(0, 10, page_text, 0, 0, "C")

# -----------------------------------------------------------------------------
# 5. Generate PDF function
# -----------------------------------------------------------------------------
def generate_pdf(
    report_id: int,
    report_title: str,
    tier2_sections: List[Dict[str, Any]],
    output_path: str = None
) -> Union[bytes, str]:
    """
    Generates a PDF from a structured Tier-2 report using FPDF2 + HTMLMixin.

    Steps:
      1. Sanitize punctuation (fancy quotes, etc.).
      2. Replace color circle emojis with <span> HTML for partial color text.
      3. Insert into PDF using write_html() for each section.

    Args:
        report_id (int): The report's ID.
        report_title (str): The title or main heading for the report.
        tier2_sections (List[Dict[str, Any]]): A list of sections, e.g.:
            [
              {"id": "section_1",
               "title": "Executive Summary",
               "content": "We are at a 🟢 stage..."}
            ]
        output_path (str, optional): If provided, saves PDF to disk at this path
            and returns the path; otherwise returns PDF bytes.

    Returns:
        Union[bytes, str]:
            - If output_path is None, returns a bytes object of the generated PDF.
            - If output_path is provided, returns that file path as a string.
    """
    pdf = PDFGenerator(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    # Sanitize the main title, then handle color emojis (if any)
    safe_title = _sanitize_text(report_title)
    safe_title = _replace_color_emojis_with_html(safe_title)

    # Use a bolder/larger font for the main title
    pdf.set_font("NotoSans", "B", 16)
    pdf.write_html(f"<center><b>Report #{report_id}: {safe_title}</b></center><br><br>")
    pdf.set_font("NotoSans", "", 12)

    # Now iterate over Tier-2 sections
    for section in tier2_sections:
        raw_title = section.get("title", "Untitled Section")
        raw_content = section.get("content", "No content available.")

        # 1) Sanitize text punctuation
        section_title = _sanitize_text(raw_title)
        section_content = _sanitize_text(raw_content)

        # 2) Replace color emojis with colored text spans
        section_title_html = _replace_color_emojis_with_html(section_title)
        section_content_html = _replace_color_emojis_with_html(section_content)

        # Section header (bold, slightly larger)
        pdf.set_font("NotoSans", "B", 14)
        pdf.write_html(f"<b>{section_title_html}</b><br>")
        pdf.ln(2)

        # Section body
        pdf.set_font("NotoSans", "", 12)
        pdf.write_html(section_content_html + "<br><br>")

    # Output the PDF
    if output_path:
        pdf.output(output_path)
        return output_path
    else:
        return pdf.output(dest="S")  # returns a bytes object
