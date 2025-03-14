# pdfgenerator.py
import os
from datetime import datetime
from weasyprint import HTML, CSS
import markdown
from supabase import create_client

# Input markdown content (this could be passed in or read from a file)
# For demonstration, we assume markdown_text is provided or loaded prior.
markdown_text = """# Executive Summary & Investment Rationale
...
"""
# Note: In practice, you'd populate markdown_text with the actual content of the report.

# Convert Markdown to HTML (using tables extension for Markdown tables)
content_html = markdown.markdown(markdown_text, extensions=['tables'])

# Prepare dynamic data for template
founder_name = "Founder Name"
company_name = "Founder Company"
prepared_by = "Brendan Smith, GetFresh Ventures"
date_str = datetime.now().strftime("%b %d, %Y")

# Load HTML template
with open("template.html", "r", encoding="utf-8") as f:
    template_html = f.read()

# Insert dynamic content into the template
filled_html = template_html.format(
    founder_name=founder_name,
    company_name=company_name,
    prepared_by=prepared_by,
    date=date_str,
    content=content_html
)

# Generate PDF using WeasyPrint
# Set base_url to current directory so that relative paths (CSS, images) are resolved
HTML(string=filled_html, base_url=os.getcwd()).write_pdf("report.pdf", stylesheets=[CSS("styles.css")])
print("PDF generated successfully as report.pdf")

# Upload PDF to Supabase Storage (optional, if SUPABASE_URL/KEY are provided)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    bucket_name = "reports"  # replace with your Supabase Storage bucket name
    # Define storage file path (e.g., in a "reports" folder with a unique name)
    storage_file_path = f"reports/{company_name}_Investment_Readiness_Report.pdf"
    # Upload the PDF file
    with open("report.pdf", "rb") as pdf_file:
        res = supabase.storage.from_(bucket_name).upload(
            path=storage_file_path,
            file=pdf_file,
            file_options={"contentType": "application/pdf", "upsert": True}
        )
    if res.get("error"):
        print(f"Error uploading to Supabase: {res['error']}")
    else:
        print(f"PDF uploaded to Supabase Storage at path: {storage_file_path}")
