import os
from fpdf import FPDF
from io import BytesIO
from typing import Union


class PDFGenerator(FPDF):
    """
    Custom PDF class using FPDF to create a nicely formatted report.
    """

    def header(self):
        """
        Defines the header that appears at the top of each page.
        You can customize fonts, colors, or add logos as needed.
        """
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "AI-Powered Report", border=False, ln=1, align="C")
        self.ln(5)

    def footer(self):
        """
        Adds a footer with page numbering at the bottom of each page.
        """
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")


def generate_pdf(report_content: dict, output_path: str = None) -> Union[bytes, str]:
    """
    Generates a PDF from a structured report (dict) using FPDF.

    Args:
        report_content (dict): A dictionary containing the report sections.
            Expected keys include 'executive_summary', 'market_analysis', 'recommendations', etc.
        output_path (str, optional): A path to save the generated PDF file.
            - If provided, the file is saved to disk, and this function returns the file path.
            - If omitted, a bytes object containing the PDF data is returned.

    Returns:
        bytes or str:
            - If output_path is None, a bytes object of the generated PDF is returned.
            - If output_path is provided, the file path is returned.
    """
    pdf = PDFGenerator(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Optional cover or title page
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Complete Report", ln=1, align="C")
    pdf.ln(10)

    # Define the order and titles for each section
    section_order = [
        ("executive_summary", "Executive Summary"),
        ("market_analysis", "Market Analysis"),
        ("recommendations", "Recommendations"),
    ]

    # Populate the PDF with content
    for key, title in section_order:
        content = report_content.get(key, "No content available.")

        # Section header
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, title, ln=1)
        pdf.ln(2)

        # Section body
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, content)
        pdf.ln(5)

    # Output the PDF to a file if output_path is specified, otherwise return bytes
    if output_path:
        pdf.output(output_path)
        return output_path
    else:
        pdf_buffer = BytesIO()
        pdf.output(pdf_buffer)  # Writes PDF content to the BytesIO buffer
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
        return pdf_bytes
