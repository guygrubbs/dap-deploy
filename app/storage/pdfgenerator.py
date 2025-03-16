import os
import markdown
from weasyprint import HTML, CSS
from datetime import datetime
from typing import Union
import base64
import re

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
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")  # Logo path

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def read_file(file_path):
    """Reads and returns the content of a given file."""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def convert_markdown_to_html(markdown_text, section_number=1, section_title=None):
    """
    Converts Markdown text to HTML while preserving tables and formatting.
    
    Args:
        markdown_text (str): The markdown text to convert
        section_number (int): The section number for table styling
        section_title (str, optional): The section title to check for and remove if duplicated
    """

    # First, strip markdown code block delimiters if present
    if markdown_text.strip().startswith("```markdown"):
        # Extract content between markdown code blocks
        pattern = r"```markdown\n(.*?)```"
        match = re.search(pattern, markdown_text, re.DOTALL)
        if match:
            markdown_text = match.group(1)
    
    # Remove section title if it appears at the beginning of the content
    if section_title:
        # Safely escape the section title for regex
        escaped_title = re.escape(section_title)
        escaped_section_number = re.escape(str(section_number))
        
        # Create patterns with escaped values to match various heading formats
        patterns = [
            rf"^### \*\*Section {escaped_section_number}: {escaped_title}\*\*.*$",
            rf"^### Section {escaped_section_number}: {escaped_title}.*$",
            rf"^## Section {escaped_section_number}: {escaped_title}.*$",
            rf"^# Section {escaped_section_number}: {escaped_title}.*$",
            rf"^#### {escaped_title}.*$",
            rf"^### {escaped_title}.*$",
            rf"^## {escaped_title}.*$",
            rf"^# {escaped_title}.*$"
        ]
        
        # Try to remove each pattern from the content
        for pattern in patterns:
            markdown_text = re.sub(pattern, "", markdown_text, flags=re.MULTILINE)
        
        # Also look for markdown heading IDs/anchors to remove
        anchor_pattern = rf" \{{#.*?\}}"
        markdown_text = re.sub(anchor_pattern, "", markdown_text, flags=re.MULTILINE)
    
    # Replace emoji indicators to HTML spans for consistent rendering
    markdown_text = markdown_text.replace("🟢", '<span class="indicator green"></span>')
    markdown_text = markdown_text.replace("🟡", '<span class="indicator yellow"></span>')
    markdown_text = markdown_text.replace("🔴", '<span class="indicator red"></span>')
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
    
    # Add section-specific class to tables for styling
    html = html.replace("<table>", f'<table class="section-{section_number}">')
    
    # Convert standard lists to special lists when needed
    if "<!-- warning-list -->" in html:
        html = html.replace("<ul><!-- warning-list -->", '<ul class="warning-list">')
    if "<!-- check-list -->" in html:
        html = html.replace("<ul><!-- check-list -->", '<ul class="check-list">')
    
    # Replace highlight boxes placeholders
    html = html.replace("[highlight]", '<span class="highlight-box">')
    html = html.replace("[/highlight]", '</span>')
    
    return html

def extract_subsections(content):
    """Extract subsections from the markdown content based on ## headings."""
    subsections = []
    pattern = r'^## (\d+\)\s*)?(.+)$'
    matches = re.finditer(pattern, content, re.MULTILINE)
    
    for match in matches:
        subsections.append({
            "title": match.group(2).strip(),
            "id": f"subsection-{len(subsections) + 1}"
        })
    
    return subsections

def clean_title(title):
    """Clean section title by removing duplicated prefixes and numeric markers."""
    # Remove any numbered prefixes like "1) "
    title = re.sub(r'^\d+\)\s*', '', title)
    
    # Clean duplicate section prefix (e.g., "Section 1: Section 1: ...")
    title_pattern = r'^Section \d+:\s*Section \d+:\s*(.+)$'
    match = re.match(title_pattern, title)
    if match:
        return match.group(1)
    
    # Remove any "Section X: " prefix if present
    section_prefix = r'^Section \d+:\s*(.+)$'
    match = re.match(section_prefix, title)
    if match:
        return match.group(1)
    
    return title

def estimate_content_height(content, subsections_count):
    """
    Estimate the height a section will take when rendered.
    This is a simplified approximation based on content length and complexity.
    
    Args:
        content (str): The markdown content
        subsections_count (int): Number of subsections which indicates complexity
    
    Returns:
        float: Estimated height in arbitrary units (used for pagination calculation)
    """
    # Base height estimate on content length
    base_height = len(content) * 0.05
    
    # Add height for tables
    table_count = content.count('|---')
    table_height = table_count * 50
    
    # Add height for subsections
    subsection_height = subsections_count * 80
    
    # Count images, charts, or other complex elements
    complex_elements = 0
    complex_elements += content.count('```')  # Code blocks
    complex_elements += content.count('<!-- warning-list -->')
    complex_elements += content.count('<!-- check-list -->')
    
    complex_element_height = complex_elements * 60
    
    return base_height + table_height + subsection_height + complex_element_height

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

    # Define content height limits and initialize page tracking
    max_content_height_per_page = 1000  # Arbitrary units for page content capacity
    section_start_page = 3  # First content starts at page 3
    current_page = section_start_page
    current_page_content_height = 0

    # Preprocess sections to extract subsections if not provided
    for i, section in enumerate(tier2_sections):
        # Extract clean section title
        section["clean_title"] = clean_title(section["title"])
        
        # Extract subsections if not provided
        if "subsections" not in section or not section["subsections"]:
            section["subsections"] = extract_subsections(section["content"])
        
        # Assign IDs to subsections for linking
        for j, subsection in enumerate(section["subsections"]):
            if "id" not in subsection:
                subsection["id"] = f"section-{i+1}-subsection-{j+1}"
        
        # Estimate content height for pagination
        content_height = estimate_content_height(section["content"], len(section["subsections"]))
        
        # Force new page for each section and update page tracking
        if i > 0:  # First section starts on page 3
            current_page += 1
            current_page_content_height = 0
        
        # Set the page number for this section
        section["page_number"] = current_page
        
        # Update current page content height
        current_page_content_height += content_height
        
        # Check if we need another page break within this section (for very long sections)
        if current_page_content_height > max_content_height_per_page:
            additional_pages = int(current_page_content_height / max_content_height_per_page)
            current_page += additional_pages
            current_page_content_height = current_page_content_height % max_content_height_per_page

    # Generate table of contents
    toc_html = '<div class="toc">\n<h2>Table of Contents:</h2>\n'
    
    # Main section entries
    for i, section in enumerate(tier2_sections, start=1):
        section_id = f"section-{i}"
        page_num = section["page_number"]
        
        toc_html += f'<div class="toc-item">\n'
        toc_html += f'<span><a href="#{section_id}">Section {i}: {section["clean_title"]}</a></span>\n'
        toc_html += f'<span class="toc-leader"></span>\n'
        toc_html += f'<span>{page_num}</span>\n'
        toc_html += f'</div>\n'
        
        # Add subsections if available
        if "subsections" in section and section["subsections"]:
            for subsection in section["subsections"]:
                sub_title = re.sub(r'^\d+\)\s*', '', subsection["title"])
                toc_html += f'<div class="toc-item" style="padding-left: 20px;">\n'
                toc_html += f'<span><a href="#{subsection["id"]}">{sub_title}</a></span>\n'
                toc_html += f'<span class="toc-leader"></span>\n'
                toc_html += f'<span>{page_num}</span>\n'
                toc_html += f'</div>\n'
                
    toc_html += '</div>'
    
    # Convert sections to HTML with page breaks
    sections_html = ""
    for i, section in enumerate(tier2_sections, start=1):
        section_id = f"section-{i}"
        
        section_html = f'<div class="page">\n'
        section_html += f'<div class="page-background"></div>\n'
        section_html += f'<div class="page-content">\n'
        section_html += f'<h2 id="{section_id}">Section {i}: {section["clean_title"]}</h2>\n'
        
        # Convert markdown content to HTML with section number for table styling
        # Pass the section title to prevent duplication in the content
        content_html = convert_markdown_to_html(
            section["content"], 
            i, 
            section["clean_title"]
        )
        
        # Add ID attributes to subsection headings
        for j, subsection in enumerate(section["subsections"]):
            subsection_id = subsection["id"]
            subsection_title_pattern = re.escape(subsection["title"])
            heading_pattern = f'<h3>(\\d+\\)\\s*)?{subsection_title_pattern}</h3>'
            replacement = f'<h3 id="{subsection_id}">\\1{subsection["title"]}</h3>'
            content_html = re.sub(heading_pattern, replacement, content_html)
        
        # Replace placeholders in the content
        content_html = content_html.replace("{company_name}", company_name)
        content_html = content_html.replace("{company_type}", company_type)
        content_html = content_html.replace("{company_description}", company_description)
        content_html = content_html.replace("{founder_name}", founder_name)
        
        section_html += content_html
        section_html += f'</div>\n'
        section_html += f'<div class="page-number">{section["page_number"]}</div>\n'
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
        content=sections_html,
        assets_dir=ASSETS_DIR
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
    
    # Define sections from external module
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