import os
import markdown
from weasyprint import HTML, CSS
from datetime import datetime
from typing import Union
import base64

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
    # Replace emoji indicators to HTML spans for consistent rendering
    markdown_text = markdown_text.replace("🟢", '<span class="indicator green"></span>')
    markdown_text = markdown_text.replace("🟡", '<span class="indicator yellow"></span>')
    markdown_text = markdown_text.replace("⚠️", '<span class="warning-symbol"></span>')
    markdown_text = markdown_text.replace("✅", '<span class="check-symbol"></span>')
    
    # Convert markdown to HTML
    html = markdown.markdown(
        markdown_text, 
        extensions=[
            "tables", 
            "fenced_code",
            "nl2br",  # Convert newlines to <br>
            "sane_lists",  # Better list handling
        ]
    )
    
    # Convert standard lists to special lists when needed
    if "<!-- warning-list -->" in html:
        html = html.replace("<ul><!-- warning-list -->", '<ul class="warning-list">')
    if "<!-- check-list -->" in html:
        html = html.replace("<ul><!-- check-list -->", '<ul class="check-list">')
    
    # Replace highlight boxes placeholders
    html = html.replace("[highlight]", '<span class="highlight-box">')
    html = html.replace("[/highlight]", '</span>')
    
    return html

def generate_pdf(
    report_id: int, 
    report_title: str, 
    tier2_sections: list, 
    founder_name: str = "Founder Name", 
    company_name: str = "Founder Company",
    company_type: str = "Company Type",
    company_description: str = "What company provides",
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
        company_type (str): Type of company (e.g., "SaaS Platform").
        company_description (str): Brief description of what the company provides.
        prepared_by (str): Name and affiliation of the report preparer.
        output_path (str, optional): File path to save the PDF. If None, returns a bytes object.

    Returns:
        Union[bytes, str]: If output_path is given, returns file path. Otherwise, returns a bytes object.
    """
    # Read HTML template and styles
    template_html = read_file(TEMPLATE_HTML_PATH)
    css_content = read_file(STYLESHEET_PATH)

    # Generate table of contents
    toc_html = '<div class="toc">\n<h2>Table of Contents:</h2>\n'
    
    # Main section entries
    for i, section in enumerate(tier2_sections, start=1):
        page_num = i + 2  # +2 because first content page starts at page 3
        toc_html += f'<div class="toc-item">\n'
        toc_html += f'<span>Section {i}: {section["title"]}</span>\n'
        toc_html += f'<span class="toc-leader"></span>\n'
        toc_html += f'<span>{page_num}</span>\n'
        toc_html += f'</div>\n'
        
        # Add subsections if available (from H2 in markdown)
        if "subsections" in section and section["subsections"]:
            for subsection in section["subsections"]:
                toc_html += f'<div class="toc-item" style="padding-left: 20px;">\n'
                toc_html += f'<span>{subsection["title"]}</span>\n'
                toc_html += f'<span class="toc-leader"></span>\n'
                toc_html += f'<span>{page_num}</span>\n'
                toc_html += f'</div>\n'
                
    toc_html += '</div>'
    
    # Convert sections to HTML with page breaks
    sections_html = ""
    for i, section in enumerate(tier2_sections, start=1):
        page_num = i + 2  # +2 because first content page starts at page 3
        
        section_html = f'<div class="page">\n'
        section_html += f'<div class="page-background"></div>\n'
        section_html += f'<div class="page-content">\n'
        section_html += f'<h2>Section {i}: {section["title"]}</h2>\n'
        
        # Convert markdown content to HTML
        section_content = section["content"]
        content_html = convert_markdown_to_html(section_content)
        
        # Replace placeholders in the content
        content_html = content_html.replace("{company_name}", company_name)
        content_html = content_html.replace("{company_type}", company_type)
        content_html = content_html.replace("{company_description}", company_description)
        content_html = content_html.replace("{founder_name}", founder_name)
        
        section_html += content_html
        section_html += f'</div>\n'
        section_html += f'<div class="page-number">{page_num}</div>\n'
        section_html += f'</div>\n'
        sections_html += section_html
    
    # Prepare dynamic content replacements
    date_str = datetime.now().strftime("%b %d, %Y")
    
    # Populate the HTML template with dynamic values
    filled_html = template_html.format(
        report_id=report_id,
        report_title=report_title,
        founder_name=founder_name,
        company_name=company_name,
        company_type=company_type,
        company_description=company_description,
        prepared_by=prepared_by,
        date=date_str,
        toc=toc_html,
        content=sections_html
    )

    # Ensure the reports directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Save HTML for debugging if needed
    debug_html_path = os.path.join(OUTPUT_DIR, "debug_output.html")
    with open(debug_html_path, "w", encoding="utf-8") as html_file:
        html_file.write(filled_html)

    # Generate PDF using WeasyPrint
    pdf_bytes = HTML(string=filled_html, base_url=BASE_DIR).write_pdf(stylesheets=[CSS(string=css_content)])

    if output_path:
        with open(output_path, "wb") as pdf_file:
            pdf_file.write(pdf_bytes)
        return output_path  # Return file path like FPDF version
    else:
        return pdf_bytes  # Return bytes object if no output path given

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Example input values
    report_id = 1
    report_title = "Investment Readiness Report"
    founder_name = "John Smith"
    company_name = "TechSolutions Inc."
    company_type = "SaaS Platform"
    company_description = "AI-powered customer service automation tools"
    prepared_by = "Brendan Smith, GetFresh Ventures"

    # Define sections (Example - these would be dynamically generated from content)
    from sample_sections import investment_report_sections
    
    # Generate PDF (Returns file path)
    pdf_file_path = generate_pdf(
        report_id=report_id, 
        report_title=report_title, 
        tier2_sections=investment_report_sections,
        founder_name=founder_name,
        company_name=company_name,
        company_type=company_type,
        company_description=company_description,
        prepared_by=prepared_by,
        output_path=OUTPUT_PDF_PATH
    )
    
    print(f"PDF generated successfully: {pdf_file_path}")