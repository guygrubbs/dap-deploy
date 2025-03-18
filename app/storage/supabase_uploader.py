"""
Legacy module that re-exports the refactored Supabase storage functionality.
This module is maintained for backward compatibility.
"""

# Re-export the refactored functionality
from app.storage.supabase import (
    supabase,
    initialize_supabase,
    upload_pdf_to_supabase,
    sync_report_to_supabase
)

# For backward compatibility, ensure the client is available directly
import os
import logging
from supabase import Client

logger = logging.getLogger(__name__)

# Re-define these constants for backward compatibility
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Warning about missing credentials, for backward compatibility
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("Supabase URL or Service Role Key is not set. Supabase uploads will fail.")