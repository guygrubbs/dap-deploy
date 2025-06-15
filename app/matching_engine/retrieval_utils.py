"""
retrieval_utils.py

Provides utility functions for querying the Vertex AI Matching Engine index
to find the most relevant text chunks given a query. Typically used to
augment GPT prompts with context from pitch decks, maturity models, etc.
"""

import os
import openai
from google.cloud import aiplatform_v1
import logging

logger = logging.getLogger(__name__)

# (Optional) A simple local store mapping 'datapoint_id' -> 'text' to demonstrate retrieving text.
# In production, you might replace this with a database or Supabase call.
DATASTORE = {}

def set_datastore(mapping: dict):
    """
    Allows external code to load or inject a dictionary of {datapoint_id: text_content}.
    So after indexing, you can keep track of the text for each ID to retrieve it post-match.
    """
    global DATASTORE
    DATASTORE = mapping


def generate_query_embedding(query_text: str) -> list:
    """
    Generate an embedding vector for the user query using OpenAI's text-embedding-ada-002 model.
    Make sure OPENAI_API_KEY is set.
    """
    response = openai.Embedding.create(
        input=[query_text],
        model="text-embedding-ada-002"
    )
    return response["data"][0]["embedding"]


def retrieve_relevant_chunks(
    query_text: str,
    endpoint_resource_name: str,
    deployed_index_id: str,
    top_k: int = 5
) -> list:
    """
    1) Embeds the user query text.
    2) Calls Vertex AI Matching Engine to find the most similar embeddings in the index.
    3) Returns a list of (datapoint_id, text_content, distance).

    Args:
        query_text: The user question or text. We'll convert it to an embedding.
        endpoint_resource_name: The full resource name of your index endpoint,
            e.g. 'projects/PROJECT_ID/locations/us-central1/indexEndpoints/ENDPOINT_ID'
        deployed_index_id: The ID you gave when deploying the index,
            e.g. 'my_vector_index_deployed'.
        top_k: How many neighbors to retrieve.
    """
    # 1) Generate embedding for the query
    query_vector = generate_query_embedding(query_text)

    # 2) Call Vertex AI IndexEndpoint to perform approximate nearest neighbor search
    client = aiplatform_v1.MatchServiceClient()
    request = aiplatform_v1.MatchRequest(
        index_endpoint=endpoint_resource_name,
        deployed_index_id=deployed_index_id,
        queries=[query_vector],
        num_neighbors=top_k
    )

    response = client.match(request=request)
    # response is a list of MatchResponses (one per query). We used a single query, so response[0]
    if not response:
        logger.warning("No match response returned from Vertex AI.")
        return []

    # 3) Build list of (datapoint_id, text_content, distance)
    # Each neighbor has an 'id' (datapoint_id) and 'distance'
    matched_neighbors = response[0].neighbors
    results = []
    for neighbor in matched_neighbors:
        dp_id = neighbor.datapoint_id  # The ID we stored at upsert time
        distance = neighbor.distance
        # Retrieve the original text from DATASTORE or a DB
        text_content = DATASTORE.get(dp_id, f"[No text found for ID: {dp_id}]")

        results.append((dp_id, text_content, distance))

    return results


def build_context_from_matches(matches: list) -> str:
    """
    Given a list of (datapoint_id, text, distance), builds a text snippet to insert
    into your GPT prompt. Example: combines top matches with a header.

    Args:
        matches: List of (datapoint_id, text_content, distance).
    Returns:
        A combined multiline string that can be appended to a prompt.
    """
    context_strs = []
    for dp_id, text_content, dist in matches:
        snippet = f"ID: {dp_id}\nDistance: {dist}\nContent:\n{text_content}\n"
        context_strs.append(snippet)

    # Optionally, you can limit or format the text to avoid token overload
    context_block = "\n---\n".join(context_strs)
    return f"Relevant Context:\n{context_block}"


if __name__ == "__main__":
    """
    Example usage:
      1) python retrieval_utils.py --endpoint ... --deployed_index ... --query "Find info about ACME's financials"
      2) It prints the top matches along with the text.

    Make sure to set the 'DATASTORE' dict or implement a DB lookup
    for retrieving text based on the datapoint_id returned by Vertex AI.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Test retrieval from Vertex AI index.")
    parser.add_argument("--endpoint", required=True,
                        help="Resource name of Vertex Matching Engine index endpoint, e.g. 'projects/.../locations/us-central1/indexEndpoints/...'.")
    parser.add_argument("--deployed_index", required=True,
                        help="Deployed index ID, e.g. 'my_vector_index_deployed'.")
    parser.add_argument("--query", required=True,
                        help="Text query to find relevant doc chunks.")
    parser.add_argument("--top_k", type=int, default=5, help="Number of neighbors to retrieve.")
    args = parser.parse_args()

    # For a real system, we'd load text from a DB or JSON. For demo, let's do a sample:
    set_datastore({
        "doc1_page0": "This is the introduction page about ACME's finances.",
        "doc1_page1": "ACME had a 20% revenue growth last year. Their main competitor is ABC Corp.",
        # ...
    })

    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set. Please export it before running.")

    # Perform retrieval
    matched_results = retrieve_relevant_chunks(
        query_text=args.query,
        endpoint_resource_name=args.endpoint,
        deployed_index_id=args.deployed_index,
        top_k=args.top_k
    )

    # Show results
    combined_context = build_context_from_matches(matched_results)
    print("=== Retrieved Context ===")
    print(combined_context)
