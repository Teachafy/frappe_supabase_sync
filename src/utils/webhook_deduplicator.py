"""
Webhook deduplication service to prevent infinite sync loops
"""
import time
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
import structlog

from ..config import settings
from .logger import get_logger

logger = get_logger(__name__)

class WebhookDeduplicator:
    """
    Prevents duplicate webhook processing based on record identifiers
    """
    
    def __init__(self):
        self.processed_webhooks: Dict[str, float] = {}
        self.successful_syncs: Dict[str, float] = {}  # Track successful syncs by identifier
        self.timeout_ms = settings.webhook_deduplication_timeout
        self.enabled = settings.enable_webhook_deduplication
        
    def _get_record_identifier(self, source: str, doctype: str, data: dict) -> Optional[str]:
        """
        Generate a unique identifier for a record based on its content
        
        For Employee records: use phone number (last 10 digits) or email
        For Task records: use subject/task_name
        For other records: use name field
        """
        try:
            if doctype.lower() in ["employee", "users"]:
                # For Employee/Users: prioritize phone number, fallback to email
                from .phone_normalizer import extract_phone_from_data, get_phone_lookup_fields, get_email_lookup_fields
                
                # Try phone number first
                phone_fields = get_phone_lookup_fields(source, "any")
                phone = extract_phone_from_data(data, phone_fields)
                if phone:
                    return f"phone:{phone}"
                
                # Fallback to email
                email_fields = get_email_lookup_fields(source, "any")
                for field in email_fields:
                    if field in data and data[field]:
                        return f"email:{data[field]}"
                        
            elif doctype.lower() in ["task", "tasks"]:
                # For Task records: use subject/task_name + description/page_content for better deduplication
                subject = data.get("subject") or data.get("task_name") or data.get("name")
                description = data.get("description") or data.get("page_content") or ""
                
                if subject:
                    # Use subject + first 50 chars of description for better uniqueness
                    desc_snippet = description[:50].replace("\n", " ").strip() if description else ""
                    identifier = f"subject:{subject}"
                    if desc_snippet:
                        identifier += f"_desc:{desc_snippet}"
                    return identifier
                    
            else:
                # For other records: use name field
                name = data.get("name") or data.get("title") or data.get("subject")
                if name:
                    return f"name:{name}"
                    
        except Exception as e:
            logger.error("Failed to generate record identifier", error=str(e), doctype=doctype)
            
        return None
    
    def is_duplicate(self, source: str, doctype: str, data: dict) -> bool:
        """
        Check if this webhook is a duplicate that should be ignored
        
        Args:
            source: Source system (frappe/supabase)
            doctype: Document type
            data: Record data
            
        Returns:
            True if this is a duplicate webhook that should be ignored
        """
        if not self.enabled:
            return False
            
        try:
            # Generate record identifier
            record_id = self._get_record_identifier(source, doctype, data)
            if not record_id:
                return False
                
            # Create unique key for this webhook
            webhook_key = f"{source}:{doctype}:{record_id}"
            current_time = time.time() * 1000  # Convert to milliseconds
            
            # Check if we've seen this webhook recently
            if webhook_key in self.processed_webhooks:
                last_processed = self.processed_webhooks[webhook_key]
                time_diff = current_time - last_processed
                
                if time_diff < self.timeout_ms:
                    logger.info(
                        "Duplicate webhook detected, ignoring",
                        webhook_key=webhook_key,
                        time_diff_ms=time_diff,
                        timeout_ms=self.timeout_ms
                    )
                    return True
                else:
                    # Timeout expired, remove old entry
                    del self.processed_webhooks[webhook_key]
            
            # Record this webhook
            self.processed_webhooks[webhook_key] = current_time
            
            # Clean up old entries (older than 2x timeout)
            self._cleanup_old_entries(current_time)
            
            return False
            
        except Exception as e:
            logger.error("Error in webhook deduplication", error=str(e))
            return False
    
    def _cleanup_old_entries(self, current_time: float):
        """Clean up old webhook entries to prevent memory leaks"""
        try:
            cutoff_time = current_time - (self.timeout_ms * 2)
            old_keys = [
                key for key, timestamp in self.processed_webhooks.items()
                if timestamp < cutoff_time
            ]
            for key in old_keys:
                del self.processed_webhooks[key]
        except Exception as e:
            logger.error("Error cleaning up old webhook entries", error=str(e))
    
    def record_successful_sync(self, source: str, doctype: str, data: dict):
        """Record a successful sync to prevent opposite service webhooks"""
        try:
            record_id = self._get_record_identifier(source, doctype, data)
            if record_id:
                # Create identifier for the same service (not opposite)
                sync_key = f"{source}:{doctype}:{record_id}"
                current_time = time.time() * 1000
                
                self.successful_syncs[sync_key] = current_time
                logger.info(
                    "Recorded successful sync to prevent opposite service webhook",
                    sync_key=sync_key,
                    source=source
                )
        except Exception as e:
            logger.error("Error recording successful sync", error=str(e))
    
    def is_opposite_service_webhook(self, source: str, doctype: str, data: dict) -> bool:
        """Check if this is a webhook from the opposite service after a recent successful sync"""
        if not self.enabled:
            return False
            
        try:
            record_id = self._get_record_identifier(source, doctype, data)
            if not record_id:
                return False
                
            # Determine the opposite service
            opposite_source = "supabase" if source == "frappe" else "frappe"
            
            # Check for successful sync from the OPPOSITE service
            opposite_webhook_key = f"{opposite_source}:{doctype}:{record_id}"
            current_time = time.time() * 1000
            
            # Check if we have a recent successful sync from the opposite service
            if opposite_webhook_key in self.successful_syncs:
                last_sync = self.successful_syncs[opposite_webhook_key]
                time_diff = current_time - last_sync
                
                if time_diff < self.timeout_ms:
                    logger.info(
                        "Skipping opposite service webhook after recent successful sync",
                        webhook_key=f"{source}:{doctype}:{record_id}",
                        opposite_webhook_key=opposite_webhook_key,
                        time_diff_ms=time_diff,
                        timeout_ms=self.timeout_ms
                    )
                    return True
                else:
                    # Timeout expired, remove old entry
                    del self.successful_syncs[opposite_webhook_key]
            
            return False
            
        except Exception as e:
            logger.error("Error checking opposite service webhook", error=str(e))
            return False
    
    def get_stats(self) -> dict:
        """Get deduplication statistics"""
        return {
            "enabled": self.enabled,
            "timeout_ms": self.timeout_ms,
            "active_webhooks": len(self.processed_webhooks),
            "successful_syncs": len(self.successful_syncs),
            "processed_webhooks": list(self.processed_webhooks.keys()),
            "successful_syncs_keys": list(self.successful_syncs.keys())
        }

# Global instance
webhook_deduplicator = WebhookDeduplicator()
