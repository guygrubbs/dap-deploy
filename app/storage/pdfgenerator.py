import os
import markdown
import uuid
from weasyprint import HTML, CSS
from datetime import datetime
from typing import Union, Optional
import base64
import re

# ----------------------------------------------------------------------------- 
# Directory Configuration (Adjust Paths Relative to `app/storage/`)
# ----------------------------------------------------------------------------- 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # e.g. `app/storage/`
TEMPLATE_HTML_PATH = os.path.join(BASE_DIR, "template.html")   # Main HTML template
STYLESHEET_PATH = os.path.join(BASE_DIR, "styles.css")         # CSS file
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")                 # Where PDFs are saved
OUTPUT_PDF_PATH = os.path.join(OUTPUT_DIR, "Investment_Readiness_Report.pdf")

# Font and Asset Paths
FONTS_DIR = os.path.join(BASE_DIR, "fonts")   # Fonts directory (if using custom fonts)
ASSETS_DIR = os.path.join(BASE_DIR, "assets") # Assets directory (for images/logos)
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")  # Example logo path

# ----------------------------------------------------------------------------- 
# Helper Functions
# ----------------------------------------------------------------------------- 
def read_file(file_path):
    """
    Reads and returns the entire content of a file as a string.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def convert_markdown_to_html(markdown_text, section_number=1, section_title=None):
    """
    Converts Markdown text into HTML while preserving tables and basic formatting.

    Args:
        markdown_text (str): The raw markdown text to convert.
        section_number (int): Used to add custom classes to <table> tags for styling.
        section_title (str, optional): The section title, used to remove repeated headings.

    Returns:
        str: The converted HTML string.
    """
    # 1) Strip code block delimiters if the content starts with ```markdown
    if markdown_text.strip().startswith("```markdown"):
        pattern = r"```markdown\n(.*?)```"
        match = re.search(pattern, markdown_text, re.DOTALL)
        if match:
            markdown_text = match.group(1)

    # 2) Remove the section title if it appears at the beginning of the content
    if section_title:
        escaped_title = re.escape(section_title)
        escaped_num   = re.escape(str(section_number))
        # ------------------------------------------------------------------
        # Generic regex pattern to match a heading that consists of "Section X: [Title]" 
        # at the start of the content. This covers any heading level and bold/italic markdown.
        # ------------------------------------------------------------------
        generic = rf"""
            ^\s*                             # start of text, allow leading whitespace
            \#{{1,6}}\s*                     # heading markdown (one to six # and a space)
            (?P<BOLD>\*{{0,2}})?             # optional opening bold/italic markers
            (Section\s+{escaped_num}:\s+)?   # optional "Section X:" prefix
            {escaped_title}                  # the section title text (escaped)
            (?P=BOLD)?                       # optional closing bold/italic markers (if opened)
            \s*(\{{\#.*?\}})?\s*$            # optional anchor ID in braces and end-of-line
        """
        markdown_text = re.sub(
            generic, "", markdown_text,
            flags=re.IGNORECASE | re.MULTILINE | re.VERBOSE
        )

    # 3) Replace special emoji indicators with HTML elements for consistent rendering
    markdown_text = markdown_text.replace("🟢", '<span class="indicator green"></span>')
    markdown_text = markdown_text.replace("🟡", '<span class="indicator yellow"></span>')
    markdown_text = markdown_text.replace("🔴", '<span class="indicator red"></span>')
    markdown_text = markdown_text.replace("⚠️", '<span class="warning-symbol"></span>')
    markdown_text = markdown_text.replace("✅", '<span class="check-symbol"></span>')

    # 4) Use Python-Markdown to convert the markdown to HTML (with extensions for tables, code, etc.)
    html = markdown.markdown(
        markdown_text,
        extensions=[
            "tables",
            "fenced_code",
            "nl2br",
            "sane_lists",
        ]
    )

    # 5) Add a custom class to each table for styling based on section number
    html = html.replace("<table>", f'<table class="section-{section_number}">')

    # 6) Handle special placeholders for custom list styles and highlights
    if "<!-- warning-list -->" in html:
        html = html.replace("<ul><!-- warning-list -->", '<ul class="warning-list">')
    if "<!-- check-list -->" in html:
        html = html.replace("<ul><!-- check-list -->", '<ul class="check-list">')
    html = html.replace("[highlight]", '<span class="highlight-box">')
    html = html.replace("[/highlight]", '</span>')

    return html

def extract_subsections(content):
    """
    Extracts subsections from the markdown content based on '##' level headings.
    Returns a list of dicts with 'title' and 'id' for each subsection discovered.
    """
    subsections = []
    pattern = r'^## (\d+\)\s*)?(.+?)(\s*\{#.*?\})?$'
    matches = re.finditer(pattern, content, re.MULTILINE)
    for match in matches:
        subsections.append({
            "title": match.group(2).strip(),
            "id": f"subsection-{len(subsections) + 1}"
        })
    return subsections

def clean_title(title):
    """
    Cleans a section or subsection title by removing duplicate phrases and numbering.
    Also strips out any anchor IDs (e.g., {#anchor}) and numeric prefixes (like '1)').
    """
    # Remove any markdown anchor IDs in braces
    title = re.sub(r'\s*\{#.*?\}', '', title)
    # Remove numeric prefixes like "1) " at the start of the title
    title = re.sub(r'^\d+\)\s*', '', title)

    # Handle repeated "Section X: Section X:" patterns (remove the redundant part)
    pattern_dup = r'^Section \d+:\s*Section \d+:\s*(.+)$'
    match = re.match(pattern_dup, title)
    if match:
        return match.group(1)

    # If there's a single "Section X:" prefix, remove it for cleanliness
    pattern_single = r'^Section \d+:\s*(.+)$'
    match = re.match(pattern_single, title)
    if match:
        return match.group(1)

    return title

def estimate_content_height(content, subsections_count):
    """
    Roughly estimates the 'height' of a section's content for pagination purposes.
    Considers length of text, number of tables, code blocks, and subsections.
    """
    base_height = len(content) * 0.05
    table_count = content.count('|---')
    table_height = table_count * 50
    subsection_height = subsections_count * 80

    complex_elements = 0
    complex_elements += content.count('```')  # code blocks
    complex_elements += content.count('<!-- warning-list -->')
    complex_elements += content.count('<!-- check-list -->')
    complex_element_height = complex_elements * 60

    return base_height + table_height + subsection_height + complex_element_height

def generate_pdf(
    report_id: Union[str, uuid.UUID],
    report_title: str,
    tier2_sections: list,
    founder_name: str = "Founder Name",
    founder_company: str = "Founder Company",
    founder_type: str = "Founder Type",
    prepared_by: Optional[str] = None,
    output_path: str = None
) -> Union[bytes, str]:
    """
    Generates a PDF from structured Markdown content for each section.

    The resulting PDF includes:
    - A cover page (from the HTML template).
    - A dynamic Table of Contents referencing each section and subsection.
    - Content sections with appropriate pagination.
    - Replaces placeholders (founder_name, founder_company, etc.) with provided data.

    If 'output_path' is specified, the PDF is written to that file path.
    Otherwise, the function returns a bytes object containing the PDF data.
    """
    # 1) Read the main HTML template and the CSS stylesheet
    template_html = read_file(TEMPLATE_HTML_PATH)
    css_content = read_file(STYLESHEET_PATH)

    # 2) Pagination setup
    max_content_height_per_page = 1000  # Rough threshold for content height per page
    section_start_page = 3             # First content page number (after cover and TOC)
    current_page = section_start_page
    current_page_content_height = 0

    # 3) Preprocess each section for subsections and pagination
    for i, section in enumerate(tier2_sections):
        section["clean_title"] = clean_title(section["title"])
        # Ensure subsections are extracted and have IDs
        if "subsections" not in section or not section["subsections"]:
            section["subsections"] = extract_subsections(section["content"])
        for j, subsection in enumerate(section["subsections"]):
            if "id" not in subsection:
                subsection["id"] = f"section-{i+1}-subsection-{j+1}"
            subsection["title"] = clean_title(subsection["title"])

        # Estimate the content height to determine page count
        content_height = estimate_content_height(section["content"], len(section["subsections"]))

        # Start each new main section on a new page (skip increment for the very first section)
        if i > 0:
            current_page += 1
            current_page_content_height = 0

        section["page_number"] = current_page  # record the starting page number of this section
        current_page_content_height += content_height

        # If content exceeds one page, increment page count accordingly
        if current_page_content_height > max_content_height_per_page:
            additional_pages = int(current_page_content_height / max_content_height_per_page)
            current_page += additional_pages
            current_page_content_height = current_page_content_height % max_content_height_per_page

    # 4) Build the Table of Contents HTML
    toc_html = '<div class="toc">\n<h2>Table of Contents:</h2>\n'
    for i, section in enumerate(tier2_sections, start=1):
        section_id = f"section-{i}"
        toc_html += (
            f'<div class="toc-item">\n'
            f'  <span><a href="#{section_id}">Section {i}: {section["clean_title"]}</a></span>\n'
            f'  <span class="toc-leader"></span>\n'
            f'</div>\n'
        )
        # Include subsections in TOC with indent
        if section.get("subsections"):
            for subsection in section["subsections"]:
                sub_title = clean_title(subsection["title"])
                toc_html += (
                    f'<div class="toc-item" style="padding-left: 20px;">\n'
                    f'  <span><a href="#{subsection["id"]}">{sub_title}</a></span>\n'
                    f'  <span class="toc-leader"></span>\n'
                    f'</div>\n'
                )
    toc_html += '</div>'

    # 5) Convert each section's Markdown content to HTML and assemble content pages
    sections_html = ""
    for i, section in enumerate(tier2_sections, start=1):
        section_id = f"section-{i}"
        # Begin a new page for the section content
        section_html = '<div class="page">\n'
        section_html += '<div class="page-background"></div>\n'
        section_html += '<div class="page-content">\n'
        section_html += f'<h2 id="{section_id}">Section {i}: {section["clean_title"]}</h2>\n'

        # Convert markdown to HTML for this section
        content_html = convert_markdown_to_html(
            section["content"],
            section_number=i,
            section_title=section["clean_title"]
        )

        # Inject IDs into subsection headings (supports both <h2> and <h3> levels)
        for j, subsection in enumerate(section["subsections"]):
            subsection_id    = subsection["id"]
            subsection_title = clean_title(subsection["title"])
            subsection_title_pattern = re.escape(subsection_title)
            # Replace occurrences of the subsection title in an <h2> or <h3> tag with an anchored version
            for heading_level in ("h2", "h3"):
                heading_pattern = rf'<{heading_level}>(\d+\)\s*)?{subsection_title_pattern}</{heading_level}>'
                replacement = rf'<{heading_level} id="{subsection_id}">\1{subsection_title}</{heading_level}>'
                content_html = re.sub(heading_pattern, replacement, content_html)

        # Replace placeholders in content with actual values
        content_html = content_html.replace("{founder_name}", founder_name)
        content_html = content_html.replace("{founder_company}", founder_company)
        content_html = content_html.replace("{founder_type}", founder_type)
        # Note: {company_description} placeholder has been removed as it is not used

        section_html += content_html
        section_html += '</div>\n'
        section_html += f'<div class="page-number">{section["page_number"]}</div>\n'
        section_html += '</div>\n'
        sections_html += section_html

    # 6) Fill the HTML template with dynamic fields and generated content
    date_str = datetime.now().strftime("%b %d, %Y")
    final_prepared_by = prepared_by or "Diraj Goel, Get Fresh Ventures"  # default if not provided
    filled_html = template_html.format(
        report_id=report_id,
        report_title=report_title,
        founder_name=founder_name,
        founder_company=founder_company,
        founder_type=founder_type,
        prepared_by=final_prepared_by,
        date=date_str,
        toc=toc_html,
        content=sections_html,
        assets_dir=ASSETS_DIR
    )

    # 7) Ensure the output directory exists and save a debug HTML (for inspection if needed)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    debug_html_path = os.path.join(OUTPUT_DIR, "debug_output.html")
    with open(debug_html_path, "w", encoding="utf-8") as html_file:
        html_file.write(filled_html)

    # 8) Generate the PDF using WeasyPrint
    pdf_bytes = HTML(string=filled_html, base_url=BASE_DIR).write_pdf(
        stylesheets=[CSS(string=css_content)]
    )

    # 9) Return or save the PDF file
    if output_path:
        with open(output_path, "wb") as pdf_file:
            pdf_file.write(pdf_bytes)
        return output_path
    else:
        return pdf_bytes

# ----------------------------------------------------------------------------- 
# Main Execution (Example Usage)
# ----------------------------------------------------------------------------- 
if __name__ == "__main__":
    # Example usage with dummy data
    report_id = str(uuid.uuid4())  # unique report identifier
    report_title = "Investment Readiness Report"
    founder_name = "John Smith"
    founder_company = "TechSolutions Inc."
    founder_type = "SaaS Platform"

    # Import or define `investment_report_sections` structure containing sections and content
    try:
        from sample_sections import investment_report_sections  # Example reference if available
    except ImportError:
        investment_report_sections = []  # Fallback to empty or predefined sections

    # Generate the PDF
    pdf_file_path = generate_pdf(
        report_id=report_id,
        report_title=report_title,
        tier2_sections=investment_report_sections,
        founder_name=founder_name,
        founder_company=founder_company,
        founder_type=founder_type,
        output_path=OUTPUT_PDF_PATH
    )
    print(f"PDF generated at: {pdf_file_path}")
