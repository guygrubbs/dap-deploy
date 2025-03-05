#!/usr/bin/env python3
"""
pdf_to_openai_jsonl.py

This script automates the process of converting PDF pitch decks into multiple .jsonl records,
with each record limited to approximately 1000 tokens of text (to avoid overly long prompts).
It also supports uploading the resulting .jsonl file to OpenAI.

Changes from previous version:
  - The create_jsonl_file() function now splits extracted text into ~1000-token chunks.
  - Each chunk is written as a separate line in the .jsonl, with a minimal placeholder for the assistant response.

Usage Examples:
  1) Local PDF -> JSONL only:
       python pdf_to_openai_jsonl.py \
         --pdf /path/to/deck.pdf \
         --jsonl output_data.jsonl

  2) Supabase PDF -> JSONL -> Upload to OpenAI:
       python pdf_to_openai_jsonl.py \
         --supabase-file some_pitch_deck.pdf \
         --bucket pitchdecks \
         --jsonl out_data.jsonl \
         --upload

Environment Variables:
  - OPENAI_API_KEY: Your OpenAI API key
  - SUPABASE_URL:   URL of your Supabase project
  - SUPABASE_SERVICE_KEY:  Service key for Supabase Storage (for download)
  - (Optional) TESSDATA_PREFIX: Path to Tesseract language data, if needed for OCR

Dependencies:
  - PyMuPDF (fitz)
  - pytesseract and Tesseract installed at system level (for OCR fallback)
  - supabase-py (if using Supabase downloads)
  - openai
  - tiktoken (for approximate token chunking)  <-- new

Key Steps:
  1) Download or read a PDF (from local filesystem or Supabase).
  2) Convert each page to text. If no text is found, apply OCR with pytesseract.
  3) Split the extracted text into ~1000-token chunks and build a .jsonl file (chat-based format).
  4) Optionally, upload that .jsonl to OpenAI using openai.File.create(purpose='fine-tune').
"""

import os
import argparse
import json

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import openai

# For token-chunking, we use tiktoken (install via `pip install tiktoken`)
try:
    import tiktoken
except ImportError:
    tiktoken = None

# If you need Supabase downloads, ensure 'supabase' installed and env vars set.
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


def init_supabase() -> "Client":
    """
    Creates and returns a Supabase client using env variables:
      - SUPABASE_URL
      - SUPABASE_SERVICE_KEY
    Raises ValueError if missing any env vars.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables.")
    return create_client(url, key)


def download_pdf_from_supabase(file_name: str, bucket: str = "pitchdecks") -> bytes:
    """
    Download a PDF file from Supabase Storage as bytes.

    :param file_name: The filename/path in the bucket (e.g. "decks/deck1.pdf")
    :param bucket: Name of the Supabase bucket (default: "pitchdecks")
    :return: The raw PDF file contents as bytes
    """
    if not SUPABASE_AVAILABLE:
        raise RuntimeError("supabase-py not installed or import failed. Cannot use Supabase feature.")

    sb = init_supabase()
    response = sb.storage.from_(bucket).download(file_name)
    if not response:
        raise FileNotFoundError(f"File '{file_name}' not found in bucket '{bucket}'.")
    return response


def extract_text_with_ocr(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF (supplied as bytes) using PyMuPDF.
    If a page has no text, fallback to OCR with pytesseract.

    :param pdf_bytes: The raw PDF data as bytes
    :return: A single string containing the entire extracted text
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_text = []

    for page_index in range(doc.page_count):
        page = doc[page_index]
        # Attempt direct extraction
        text = page.get_text("text")
        if text.strip():
            all_text.append(text)
        else:
            # OCR fallback
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ocr_result = pytesseract.image_to_string(img)
            if ocr_result.strip():
                all_text.append(ocr_result)

    return "\n".join(all_text)


def chunk_text_by_tokens(full_text: str, tokens_per_chunk: int = 1000) -> list:
    """
    Splits a string into multiple chunks (~1000 tokens each) using tiktoken
    for an approximate measure of tokens. If tiktoken is not installed,
    it falls back to a naive approach by splitting on whitespace.

    :param full_text: The text to split
    :param tokens_per_chunk: Approx tokens per chunk (default=1000)
    :return: A list of text chunks, each chunk ~1000 tokens or less
    """
    if tiktoken is None:
        # Fallback: naive approach splitting ~1000 words
        words = full_text.split()
        chunks = []
        current_chunk = []

        for word in words:
            current_chunk.append(word)
            if len(current_chunk) >= 1000:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks
    else:
        # Use tiktoken for more accurate token counting
        enc = tiktoken.get_encoding("cl100k_base")  # or your desired encoding
        tokens = enc.encode(full_text)
        chunks = []
        start = 0
        while start < len(tokens):
            end = start + tokens_per_chunk
            chunk_tokens = tokens[start:end]
            # Decode tokens back to text
            chunk_text = enc.decode(chunk_tokens)
            chunks.append(chunk_text)
            start = end
        return chunks


def create_jsonl_file(text: str, output_path: str) -> None:
    """
    Writes the extracted text to a .jsonl file in chat-based format for OpenAI fine-tuning.
    Splits the text into ~1000-token chunks. Each chunk becomes a separate record with
    an empty or placeholder assistant response.

    :param text: The full text extracted from the PDF
    :param output_path: Path to the .jsonl file to create
    """
    # 1) Split text into ~1000-token chunks
    text_chunks = chunk_text_by_tokens(text, tokens_per_chunk=1000)

    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in text_chunks:
            record = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"{chunk}"
                    },
                    {
                        "role": "assistant",
                        "content": ""  # minimal placeholder for assistant
                    }
                ]
            }
            # Write each chunk as a separate line
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Created .jsonl file with {len(text_chunks)} chunk(s) at: {output_path}")


def upload_jsonl_to_openai(jsonl_path: str, purpose: str = "fine-tune") -> str:
    """
    Upload the .jsonl file to OpenAI using openai.File.create().

    :param jsonl_path: Path to the .jsonl file
    :param purpose: Purpose for the file (usually 'fine-tune')
    :return: The OpenAI file ID
    """
    openai.api_key = os.getenv("OPENAI_API_KEY", "")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set. Cannot upload to OpenAI.")

    if not os.path.isfile(jsonl_path):
        raise FileNotFoundError(f"{jsonl_path} does not exist or is not accessible.")

    print(f"Uploading {jsonl_path} to OpenAI with purpose='{purpose}'...")
    with open(jsonl_path, "rb") as f:
        response = openai.File.create(file=f, purpose=purpose)
    file_id = response["id"]
    print(f"Upload complete. File ID: {file_id}")
    return file_id


def main():
    parser = argparse.ArgumentParser(
        description="Convert a PDF pitch deck into multiple ~1000-token JSONL records, then optionally upload to OpenAI."
    )
    parser.add_argument("--pdf", type=str, default=None,
                        help="Local path to a PDF file.")
    parser.add_argument("--supabase-file", type=str, default=None,
                        help="Name/path of the PDF in Supabase (e.g. 'deck1.pdf').")
    parser.add_argument("--bucket", type=str, default="pitchdecks",
                        help="Supabase bucket name (default='pitchdecks').")
    parser.add_argument("--jsonl", type=str, required=True,
                        help="Output path for the .jsonl file.")
    parser.add_argument("--upload", action="store_true",
                        help="If set, will upload the .jsonl to OpenAI with purpose='fine-tune'.")
    args = parser.parse_args()

    # Basic validation
    if args.pdf and args.supabase_file:
        raise ValueError("Please specify either --pdf or --supabase-file, not both.")
    if not (args.pdf or args.supabase_file):
        raise ValueError("You must specify either --pdf (local) or --supabase-file (Supabase).")

    # 1) Load PDF bytes
    pdf_bytes = None
    if args.pdf:
        if not os.path.isfile(args.pdf):
            raise FileNotFoundError(f"Local PDF file '{args.pdf}' not found.")
        with open(args.pdf, "rb") as f:
            pdf_bytes = f.read()
        print(f"Read local PDF: {args.pdf}")
    elif args.supabase_file:
        pdf_bytes = download_pdf_from_supabase(args.supabase_file, args.bucket)
        print(f"Downloaded PDF from Supabase: {args.supabase_file} (bucket: {args.bucket})")

    # 2) Extract text (with OCR fallback)
    extracted_text = extract_text_with_ocr(pdf_bytes)
    if not extracted_text.strip():
        print("Warning: No text extracted from PDF (may be empty or purely images).")

    # 3) Create .jsonl with multiple chunks (1000 tokens each)
    create_jsonl_file(extracted_text, args.jsonl)

    # 4) Optionally upload to OpenAI
    if args.upload:
        file_id = upload_jsonl_to_openai(args.jsonl, purpose="fine-tune")
        print(f"Successfully uploaded to OpenAI. File ID: {file_id}")


if __name__ == "__main__":
    main()
