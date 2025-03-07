import os
from fpdf import FPDF
from io import BytesIO
from typing import Union, Dict, Any, List

def _sanitize_text(text: str) -> str:
    """
    Replaces characters that are not supported by the default FPDF fonts
    (Latin-1 encoding). Converts “fancy quotes”, ellipses, and em dashes
    to simple ASCII alternatives. Expand/modify as needed.
    """
    # Mapping of problematic Unicode chars to ASCII replacements
    replacements = {
        "\u2014": "-",    # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote / apostrophe
        "\u201C": '"',    # left double quote
        "\u201D": '"',    # right double quote
        "\u2026": "...",  # ellipsis
    }

    # Apply each replacement in turn
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)

    return text

class PDFGenerator(FPDF):
    """
    Custom PDF class using FPDF to create a nicely formatted report.
    """

    def header(self):
        """
        Defines the header that appears at the top of each page.
        You can customize fonts, colors, or add logos as needed.
        """
        # Remember to sanitize any text you place here, if needed.
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "GFV Investment Readiness Report", border=False, ln=1, align="C")
        self.ln(5)

    def footer(self):
        """
        Adds a footer with page numbering at the bottom of each page.
        """
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        page_text = f"Page {self.page_no()}"
        page_text = _sanitize_text(page_text)  # Just in case of unexpected chars
        self.cell(0, 10, page_text, 0, 0, "C")


def generate_pdf(
    report_id: int,
    report_title: str,
    tier2_sections: List[Dict[str, Any]],
    output_path: str = None
) -> Union[bytes, str]:
    """
    Generates a PDF from a structured Tier‑2 report using FPDF.

    Args:
        report_id (int): The report's ID.
        report_title (str): The title or main heading for the report.
        tier2_sections (List[Dict[str, Any]]): A list of sections. Each item should have:
            {
              "id": "section_1",
              "title": "Executive Summary & Investment Rationale",
              "content": "Text content for this section..."
            }
        output_path (str, optional): A path to save the generated PDF file.
            - If provided, the file is saved to disk, returning the file path.
            - If omitted, a bytes object containing the PDF data is returned.

    Returns:
        bytes or str:
            - If output_path is None, returns a bytes object of the generated PDF.
            - If output_path is provided, returns that file path as a string.
    """
    pdf = PDFGenerator(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)

    # Sanitize the main title
    safe_title = _sanitize_text(report_title)

    # Main Title
    pdf.cell(0, 10, f"Report #{report_id}: {safe_title}", ln=1, align="C")
    pdf.ln(10)

    # Now iterate over Tier‑2 sections
    for section in tier2_sections:
        # Safely retrieve text fields
        raw_title = section.get("title", "Untitled Section")
        raw_content = section.get("content", "No content available.")

        # Sanitize them
        section_title = _sanitize_text(raw_title)
        section_content = _sanitize_text(raw_content)

        # Section header
        pdf.set_font("Arial", "B", 14)
        pdf.multi_cell(0, 8, section_title)
        pdf.ln(2)

        # Section body
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 7, section_content)
        pdf.ln(5)

    # Output the PDF
    if output_path:
        pdf.output(output_path)
        return output_path
    else:
        # Use "S" to output as a bytes string
        pdf_bytes = pdf.output(dest="S")
        return pdf_bytes