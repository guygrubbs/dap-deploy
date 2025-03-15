import os
import markdown
from weasyprint import HTML, CSS
from datetime import datetime
from typing import Union

# -----------------------------------------------------------------------------
# Directory Configuration (Adjust Paths Relative to `app/storage/`)
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # `app/storage/`
TEMPLATE_HTML_PATH = os.path.join(BASE_DIR, "template.html")  # Template
STYLESHEET_PATH = os.path.join(BASE_DIR, "styles.css")  # CSS file
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")  # Where PDFs are saved
OUTPUT_PDF_PATH = os.path.join(OUTPUT_DIR, "Investment_Readiness_Report.pdf")

# Font and Asset Paths
FONTS_DIR = os.path.join(BASE_DIR, "fonts")  # Fonts directory
ASSETS_DIR = os.path.join(BASE_DIR, "assets")  # Assets directory

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def read_file(file_path):
    """Reads and returns the content of a given file."""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def convert_markdown_to_html(markdown_text):
    """Converts Markdown text to HTML while preserving tables and formatting."""
    return markdown.markdown(markdown_text, extensions=["tables", "fenced_code"])

def generate_pdf(report_id: int, report_title: str, tier2_sections: list, founder_name: str = "Founder Name", company_name: str = "Founder Company", output_path: str = None) -> Union[bytes, str]:
    """
    Generates a PDF from structured Markdown content while matching FPDF output.

    Args:
        report_id (int): Unique ID of the report.
        report_title (str): Title of the report.
        tier2_sections (list): List of section dictionaries containing "title" and "content".
        output_path (str, optional): File path to save the PDF. If None, returns a bytes object.

    Returns:
        Union[bytes, str]: If output_path is given, returns file path. Otherwise, returns a bytes object.
    """
    # Read HTML template and styles
    template_html = read_file(TEMPLATE_HTML_PATH)
    css_content = read_file(STYLESHEET_PATH)

    # Convert sections to HTML content
    sections_html = ""
    for section in tier2_sections:
        section_title = section.get("title", "Untitled Section")
        section_content_md = section.get("content", "No content available.")
        section_content_html = convert_markdown_to_html(section_content_md)
        sections_html += f"<h2>{section_title}</h2>\n{section_content_html}\n"

    # Prepare dynamic content replacements
    date_str = datetime.now().strftime("%b %d, %Y")

    # Populate the HTML template with dynamic values
    filled_html = template_html.format(
        report_id=report_id,
        report_title=report_title,
        date=date_str,
        content=sections_html
    )

    # Ensure the reports directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate PDF using WeasyPrint
    pdf_bytes = HTML(string=filled_html, base_url=BASE_DIR).write_pdf(stylesheets=[CSS(string=css_content)])

    if output_path:
        with open(output_path, "wb") as pdf_file:
            pdf_file.write(pdf_bytes)
        return output_path  # Return file path like FPDF version
    else:
        return pdf_bytes  # Return bytes object if no output path given

# -----------------------------------------------------------------------------
# Execution Example
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Example input values (Replace with actual dynamic data)
    report_id = 1
    report_title = "Investment Readiness Report"
    founder_name = "Founder Name"
    company_name = "Founder Company"
    prepared_by = "Brendan Smith, GetFresh Ventures"

# Sample Tier-2 Sections (Structured data for PDF generation)
    tier2_sections = [
        {"title": "Executive Summary", "content": "We are at a 🟢 stage..."},
        {"title": "Market Overview", "content": "The total addressable market (TAM) is growing at 15% YoY."},
        {"title": "Financial Performance", "content": "Revenue has increased by 25% YoY."}
    ]

    # Generate PDF (Returns file path)
    pdf_file_path = generate_pdf(report_id, report_title, tier2_sections, output_path=OUTPUT_PDF_PATH)
