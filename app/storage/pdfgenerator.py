import os
import markdown
from weasyprint import HTML, CSS
from datetime import datetime
from supabase import create_client

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

# Supabase Configuration (from Environment Variables)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = "reports"  # Supabase Storage Bucket Name

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

def generate_pdf(markdown_content, founder_name, company_name, prepared_by):
    """
    Generates a PDF from Markdown content using a structured HTML template.
    """
    # Read the HTML template and styles
    template_html = read_file(TEMPLATE_HTML_PATH)
    css_content = read_file(STYLESHEET_PATH)

    # Convert Markdown to HTML
    content_html = convert_markdown_to_html(markdown_content)

    # Prepare dynamic content replacements
    date_str = datetime.now().strftime("%b %d, %Y")

    # Populate the HTML template
    filled_html = template_html.format(
        founder_name=founder_name,
        company_name=company_name,
        prepared_by=prepared_by,
        date=date_str,
        content=content_html
    )

    # Ensure the reports directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate PDF using WeasyPrint
    HTML(string=filled_html, base_url=BASE_DIR).write_pdf(
        OUTPUT_PDF_PATH, stylesheets=[CSS(string=css_content)]
    )

    print(f"PDF successfully generated: {OUTPUT_PDF_PATH}")
    return OUTPUT_PDF_PATH

def upload_to_supabase(file_path, company_name):
    """
    Uploads the generated PDF to Supabase Storage if credentials are set.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Supabase credentials not set. Skipping upload.")
        return None

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Define the storage path in Supabase
    storage_file_path = f"reports/{company_name}_Investment_Readiness_Report.pdf"

    with open(file_path, "rb") as f:
        response = supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=storage_file_path,
            file=f,
            file_options={"contentType": "application/pdf", "upsert": True}
        )

    if "error" in response:
        print(f"Error uploading to Supabase: {response['error']}")
        return None

    print(f"PDF uploaded successfully to Supabase Storage at: {storage_file_path}")
    return storage_file_path

# -----------------------------------------------------------------------------
# Execution Example
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Example input values (Replace with actual dynamic data)
    founder_name = "Founder Name"
    company_name = "Founder Company"
    prepared_by = "Brendan Smith, GetFresh Ventures"

    # Sample Markdown content
    markdown_content = """
    # Executive Summary & Investment Rationale
    This report evaluates **{company_name}** as an investment opportunity.

    ## Key Investment Considerations
    - **Scalability & Market Fit**: 🟢 Strong
    - **Revenue Growth Potential**: 🟢 Strong
    - **Financial Transparency**: 🟡 Needs Refinement
    - **Operational Scalability**: 🟡 Needs Improvement
    - **Exit Potential**: 🟢 Favorable Pathways

    ## Financial Overview
    | Metric | Performance | Industry Benchmark |
    |--------|------------|--------------------|
    | Revenue Growth | 25% YoY | 20% YoY |
    | Profitability | Positive | Mixed |

    ## Next Steps
    - Short-Term: Increase financial reporting transparency.
    - Medium-Term: Expand into new markets.
    - Long-Term: Secure Series A funding.
    """

    # Generate PDF
    pdf_file_path = generate_pdf(markdown_content, founder_name, company_name, prepared_by)

    # Upload to Supabase
    upload_to_supabase(pdf_file_path, company_name)
