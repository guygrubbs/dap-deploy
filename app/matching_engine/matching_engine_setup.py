import google.cloud.aiplatform as aiplatform

def initialize_vertex_ai(project_id: str, location: str = "us-central1"):
    """
    Initializes the global aiplatform settings (project & location).
    """
    aiplatform.init(project=project_id, location=location)

def create_and_deploy_tree_ah_index(
    display_name: str,
    index_endpoint_name: str,
    dimensions: int = 1536,
    approximate_neighbors_count: int = 100,
    leaf_node_embedding_count: int = 500,
    leaf_nodes_to_search_percent: int = 10,
    distance_measure_type: str = "COSINE",
    index_update_method: str = "STREAM_UPDATE"
):
    """
    1) Creates a tree-AH index for approximate nearest neighbor search with streaming updates.
    2) Deploys the index to a Matching Engine index endpoint.
    """

    # Create the index
    index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name=display_name,
        dimensions=dimensions,
        approximate_neighbors_count=approximate_neighbors_count,
        leaf_node_embedding_count=leaf_node_embedding_count,
        leaf_nodes_to_search_percent=leaf_nodes_to_search_percent,
        distance_measure_type=distance_measure_type,
        index_update_method=index_update_method,
    )

    print(f"Created index resource name: {index.resource_name}")

    # Create (or retrieve) an index endpoint to deploy the index
    index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=index_endpoint_name,
        public_endpoint_enabled=True
    )
    print(f"Created index endpoint resource name: {index_endpoint.resource_name}")

    # Deploy the index to the endpoint
    deployed_index_id = f"{display_name.lower().replace(' ','_')}_deployed"
    index_endpoint.deploy_index(
    index=index,
    deployed_index_id=deployed_index_id)

    print("Index deployed successfully.")
    print("Deployed Index ID:", deployed_index_id)
    print("You can now upsert datapoints in real-time with streaming updates.")


if __name__ == "__main__":
    # Example usage
    PROJECT_ID = "deal-adjudication-platform"
    LOCATION = "us-central1"

    # 1. Initialize Vertex AI
    initialize_vertex_ai(PROJECT_ID, LOCATION)

    # 2. Create & deploy the index
    create_and_deploy_tree_ah_index(
        display_name="My Vector Index",
        index_endpoint_name="My Index Endpoint",
        dimensions=1536,
        approximate_neighbors_count=100,
        leaf_node_embedding_count=500,
        leaf_nodes_to_search_percent=10,
        distance_measure_type="COSINE_DISTANCE",
        index_update_method="STREAM_UPDATE"  # enable real-time upserts
    )
