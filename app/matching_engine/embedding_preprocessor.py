"""
embedding_preprocessor.py

Usage:
    python embedding_preprocessor.py --pdf path/to/document.pdf \
                                     --index projects/PROJECT_ID/locations/us-central1/indexes/INDEX_ID

Description:
    1) Extracts text from a given PDF using PyMuPDF.
    2) Generates embeddings for each non-empty page using OpenAI's text-embedding-ada-002.
    3) Upserts these vectors into your Vertex AI Matching Engine index for real-time retrieval.

Prerequisites:
    pip install pymupdf google-cloud-aiplatform openai

Environment Variables Needed:
    - OPENAI_API_KEY: Your OpenAI API key
    - GOOGLE_APPLICATION_CREDENTIALS: Path to GCP service account JSON (if not using default auth)
"""

import argparse
import os
import pymupdf
import openai
from google.cloud import aiplatform_v1


def extract_pdf_text(pdf_path: str):
    """
    Extract text from each page of a PDF using PyMuPDF (pymupdf).
    Returns a list of (page_number, text_content).
    """
    doc = pymupdf.open(pdf_path)
    extracted = []
    for page_idx, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            extracted.append((page_idx, text))
    return extracted


def generate_embedding(text: str) -> list:
    """
    Generates an embedding vector (list of floats) for the given text
    using OpenAI's 'text-embedding-ada-002' model.
    """
    response = openai.Embedding.create(
        input=[text],
        model="text-embedding-ada-002"
    )
    # The model returns a list of embeddings (one per input). We used a single input, so index [0].
    embedding_vector = response["data"][0]["embedding"]
    return embedding_vector


def upsert_embedding_to_vertex(index_resource_name: str, data_id: str, embedding: list):
    """
    Upserts a single embedding vector to the specified Vertex AI Matching Engine index.

    Args:
        index_resource_name: Full resource name of the index,
            e.g. 'projects/PROJECT_ID/locations/us-central1/indexes/INDEX_ID'
        data_id: Unique ID for this datapoint in the index (string).
        embedding: The embedding vector as a list of floats.
    """
    index_client = aiplatform_v1.IndexServiceClient()
    datapoint = aiplatform_v1.IndexDatapoint(
        datapoint_id=data_id,
        feature_vector=embedding
        # Optional: if you have restricts, crowding tag, etc., you can add them here
    )
    request = aiplatform_v1.UpsertDatapointsRequest(
        index=index_resource_name,
        datapoints=[datapoint]
    )
    index_client.upsert_datapoints(request=request)
    print(f"Upserted {data_id} into index {index_resource_name}.")


def process_pdf_and_upsert(pdf_path: str, index_resource_name: str):
    """
    Main function:
    1) Extract text from PDF pages.
    2) Generate embeddings.
    3) Upsert into Vertex AI Matching Engine index.
    """
    # 1. Extract text from PDF
    pages = extract_pdf_text(pdf_path)
    print(f"Extracted {len(pages)} non-empty pages from {pdf_path}.")

    # 2. For each page, generate embedding & upsert
    for page_number, text_content in pages:
        # Generate an embedding
        embedding_vector = generate_embedding(text_content)

        # Create a unique datapoint_id, e.g. "mydoc_page0"
        data_id = f"{os.path.basename(pdf_path)}_page{page_number}"

        # 3. Upsert to Vertex AI
        upsert_embedding_to_vertex(index_resource_name, data_id, embedding_vector)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF to Vertex AI embedding processor.")
    parser.add_argument("--pdf", type=str, required=True,
                        help="Path to the PDF file to process.")
    parser.add_argument("--index", type=str, required=True,
                        help="Vertex AI index resource name, e.g. 'projects/PROJECT_ID/locations/us-central1/indexes/INDEX_ID'")

    args = parser.parse_args()

    # Make sure you have set openai.api_key = "..." or use OPENAI_API_KEY env variable
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY not set. Please export or assign it before running.")

    pdf_path = args.pdf
    index_resource_name = args.index

    process_pdf_and_upsert(pdf_path, index_resource_name)
