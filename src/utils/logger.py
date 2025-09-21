"""
Logging utilities for Frappe-Supabase Sync Service
"""

import logging
import sys
from typing import Any, Dict, Optional
import structlog
from structlog.stdlib import LoggerFactory


def setup_logging(log_level: str = "INFO") -> None:
    """Setup structured logging for the sync service"""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class SyncLogger:
    """Specialized logger for sync operations"""

    def __init__(self, name: str = "sync"):
        self.logger = get_logger(name)

    def log_sync_start(
        self, operation_id: str, direction: str, doctype: str, record_id: str
    ) -> None:
        """Log sync operation start"""
        self.logger.info(
            "Sync operation started",
            operation_id=operation_id,
            direction=direction,
            doctype=doctype,
            record_id=record_id,
        )

    def log_sync_success(self, operation_id: str, duration: float) -> None:
        """Log successful sync operation"""
        self.logger.info(
            "Sync operation completed successfully",
            operation_id=operation_id,
            duration=duration,
        )

    def log_sync_error(
        self, operation_id: str, error: str, retry_count: int = 0
    ) -> None:
        """Log sync operation error"""
        self.logger.error(
            "Sync operation failed",
            operation_id=operation_id,
            error=error,
            retry_count=retry_count,
        )

    def log_conflict_detected(self, operation_id: str, conflict_fields: list) -> None:
        """Log conflict detection"""
        self.logger.warning(
            "Sync conflict detected",
            operation_id=operation_id,
            conflict_fields=conflict_fields,
        )

    def log_webhook_received(self, source: str, doctype: str, operation: str) -> None:
        """Log webhook reception"""
        self.logger.info(
            "Webhook received", source=source, doctype=doctype, operation=operation
        )

    def log_retry_attempt(
        self, operation_id: str, attempt: int, max_attempts: int
    ) -> None:
        """Log retry attempt"""
        self.logger.warning(
            "Retrying sync operation",
            operation_id=operation_id,
            attempt=attempt,
            max_attempts=max_attempts,
        )
