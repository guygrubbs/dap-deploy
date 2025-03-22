
"""
Supabase client initialization and configuration.
"""

import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Environment variables for Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Initialize global client
supabase: Client = None

def initialize_supabase() -> Client:
    """
    Initialize the Supabase client with environment variables.
    Returns the client or None if credentials are missing.
    """
    global supabase
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase URL or Service Role Key is not set. Supabase operations will fail.")
        return None
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
        return supabase
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}", exc_info=True)
        return None

# Initialize client on module import
if SUPABASE_URL and SUPABASE_KEY:
    initialize_supabase()
else:
    logger.warning("Supabase credentials not found. Call initialize_supabase() after setting environment variables.")