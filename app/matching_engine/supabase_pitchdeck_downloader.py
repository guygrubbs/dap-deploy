import os
import pymupdf
import openai
from supabase import create_client, Client
from google.cloud import aiplatform_v1

# If you have the embedding_preprocessor from earlier code, 
# you can import specific functions or re-use them here.
# from app.matching_engine.embedding_preprocessor import generate_embedding, upsert_embedding_to_vertex

def init_supabase() -> Client:
    """
    Initializes and returns a Supabase Client using environment variables:
    - SUPABASE_URL
    - SUPABASE_KEY
    """
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL / SUPABASE_SERVICE_KEY env variables not set.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def download_pdf_from_supabase(file_name: str, bucket_name: str = "pitchdecks") -> str:
    """
    Downloads a PDF file from a Supabase storage bucket and saves it locally.
    Returns the local file path for further processing.
    """
    supabase = init_supabase()
    response = supabase.storage.from_(bucket_name).download(file_name)
    if not response:
        raise FileNotFoundError(f"File {file_name} not found in bucket {bucket_name}.")

    local_path = os.path.join("/tmp", file_name)  # or another temp path
    with open(local_path, "wb") as f:
        f.write(response)
    return local_path

def extract_pdf_text(pdf_path: str):
    """
    Extract text from each page of a PDF using PyMuPDF.
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
    embedding_vector = response["data"][0]["embedding"]
    return embedding_vector

def upsert_embedding_to_vertex(index_resource_name: str, data_id: str, embedding: list):
    """
    Upserts a single embedding vector to the specified Vertex AI Matching Engine index.
    """
    index_client = aiplatform_v1.IndexServiceClient()
    datapoint = aiplatform_v1.IndexDatapoint(
        datapoint_id=data_id,
        feature_vector=embedding
    )
    request = aiplatform_v1.UpsertDatapointsRequest(
        index=index_resource_name,
        datapoints=[datapoint]
    )
    index_client.upsert_datapoints(request=request)
    print(f"Upserted {data_id} into index {index_resource_name}.")


def process_pitch_deck(file_name: str, index_resource_name: str):
    """
    1. Downloads the pitch deck (PDF) from Supabase.
    2. Extracts text from its pages.
    3. Generates embeddings for each page.
    4. Upserts embeddings to Vertex AI Matching Engine.
    """
    pdf_path = download_pdf_from_supabase(file_name)
    print(f"Downloaded pitch deck to: {pdf_path}")

    # Extract text
    pages = extract_pdf_text(pdf_path)
    print(f"Found {len(pages)} non-empty pages in {file_name}.")

    # Generate embeddings & upsert each page
    for page_number, text_content in pages:
        embedding_vector = generate_embedding(text_content)
        data_id = f"{file_name}_page{page_number}"
        upsert_embedding_to_vertex(index_resource_name, data_id, embedding_vector)

    print(f"Completed processing for pitch deck: {file_name}")

if __name__ == "__main__":
    # Example usage:
    # Suppose you have your environment variables set for:
    # - OPENAI_API_KEY
    # - SUPABASE_URL
    # - SUPABASE_SERVICE_KEY
    # - GOOGLE_APPLICATION_CREDENTIALS
    # - etc.
    import argparse

    parser = argparse.ArgumentParser(description="Download & process a pitch deck from Supabase.")
    parser.add_argument("--file_name", type=str, required=True,
                        help="Name of the PDF file in the Supabase bucket.")
    parser.add_argument("--index", type=str, required=True,
                        help="Vertex AI Matching Engine index resource name, e.g. 'projects/PROJECT_ID/locations/us-central1/indexes/INDEX_ID'")
    parser.add_argument("--bucket", type=str, default="pitchdecks",
                        help="Supabase bucket name (default: 'pitchdecks').")

    args = parser.parse_args()

    # Initialize OpenAI key from env
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY not set. Please export or assign it before running.")

    process_pitch_deck(args.file_name, args.index)
