# report_sync.py (No longer needed)
import logging
logger = logging.getLogger(__name__)

def sync_report_to_supabase(
    report_id: int,
    report_data: dict,
    user_id: str = None,
    startup_id: str = None
) -> bool:
    """
    This function is now removed / no-op, since we no longer do system_settings 
    or report_requests references. 
    """
    logger.info("sync_report_to_supabase() called but no longer implemented.")
    return True
