import os
import json
import markdown
from weasyprint import HTML, CSS
from datetime import datetime
from typing import Union, List, Dict, Any
from jinja2 import Environment, FileSystemLoader

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

def generate_pdf(
    report_id: int,
    report_title: str,
    tier2_sections: List[Dict[str, str]],
    founder_name: str = "Founder Name",
    company_name: str = "Founder Company",
    prepared_by: str = "Brendan Smith, GetFresh Ventures",
    output_path: str = None
) -> Union[bytes, str]:
    """
    Generates a PDF from structured Markdown content.

    Args:
        report_id (int): Unique ID of the report.
        report_title (str): Title of the report.
        tier2_sections (list): List of section dictionaries containing "title" and "content".
        founder_name (str): Name of the founder.
        company_name (str): Name of the company.
        prepared_by (str): Name of the report preparer.
        output_path (str, optional): File path to save the PDF. If None, returns a bytes object.

    Returns:
        Union[bytes, str]: If output_path is given, returns file path. Otherwise, returns a bytes object.
    """
    # Ensure the reports directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Set up Jinja2 environment and template
    env = Environment(loader=FileSystemLoader(BASE_DIR))
    template = env.get_template(os.path.basename(TEMPLATE_HTML_PATH))

    # Convert sections to HTML content
    sections_html = ""
    for i, section in enumerate(tier2_sections, start=1):
        section_id = f"section-{i}"
        section_title = section.get("title", "Untitled Section")
        section_content_md = section.get("content", "No content available.")
        section_content_html = convert_markdown_to_html(section_content_md)
        sections_html += f'{section_title}\n\n{section_content_html}\n'

    # Create metadata structure
    metadata = {
        "companyName": company_name,
        "preparedFor": founder_name,
        "preparedBy": prepared_by,
        "reportDate": datetime.now().strftime("%b %d, %Y"),
        "reportTitle": report_title,
        "reportId": report_id
    }

    # Prepare context for template rendering
    context = {
        'metadata': json.dumps(metadata),
        'markdown_content': sections_html
    }

    # Render the HTML template with context
    html_content = template.render(**context)

    # Create a temporary file for debugging if needed
    temp_html_path = os.path.join(OUTPUT_DIR, 'temp_report.html')
    with open(temp_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Generate PDF using WeasyPrint
    html = HTML(string=html_content, base_url=BASE_DIR)
    css = [CSS(filename=STYLESHEET_PATH)]

    # Generate the PDF
    pdf_bytes = html.write_pdf(stylesheets=css)

    if output_path:
        with open(output_path, "wb") as pdf_file:
            pdf_file.write(pdf_bytes)
        return output_path  # Return file path like FPDF version
    else:
        return pdf_bytes  # Return bytes object if no output path given

def convert_to_pdf(markdown_file, output_pdf, template_dir=None):
    """Backward compatibility function for the old conversion method."""
    # Read markdown file
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse metadata and content
    metadata, markdown_content = parse_metadata(content)

    # Extract or use default values
    company_name = metadata.get('companyName', 'Company Name')
    prepared_for = metadata.get('preparedFor', 'Client Name')
    prepared_by = metadata.get('preparedBy', 'Consultant Name')
    report_title = "Investment Readiness Report"

    # Create a single section containing all content
    tier2_sections = [{"title": "Report Content", "content": markdown_content}]

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_pdf)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate the PDF
    return generate_pdf(
        report_id=1,
        report_title=report_title,
        tier2_sections=tier2_sections,
        founder_name=prepared_for,
        company_name=company_name,
        prepared_by=prepared_by,
        output_path=output_pdf
    )

def parse_metadata(markdown_content):
    """Extract metadata from markdown file if available."""
    metadata = {
        "companyName": "Company Name",
        "preparedFor": "Client Name",
        "preparedBy": "Consultant Name",
        "reportDate": datetime.now().strftime("%b %d, %Y")
    }

    # Look for YAML-like frontmatter
    if markdown_content.startswith('---'):
        end_delimiter = markdown_content.find('---', 3)
        if end_delimiter > 0:
            frontmatter = markdown_content[3:end_delimiter].strip()
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    # Map the keys to our metadata structure
                    if key.lower() in ['company', 'company_name', 'companyname']:
                        metadata['companyName'] = value
                    elif key.lower() in ['client', 'prepared_for', 'preparedfor']:
                        metadata['preparedFor'] = value
                    elif key.lower() in ['author', 'prepared_by', 'preparedby']:
                        metadata['preparedBy'] = value
                    elif key.lower() in ['date', 'report_date', 'reportdate']:
                        metadata['reportDate'] = value

            # Remove frontmatter from content
            markdown_content = markdown_content[end_delimiter+3:].strip()

    return metadata, markdown_content

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
