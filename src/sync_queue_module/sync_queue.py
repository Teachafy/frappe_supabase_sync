"""
Queue system for managing sync operations
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import redis
import structlog

from ..models import SyncOperation, SyncStatus
from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SyncQueue:
    """Queue system for managing sync operations"""

    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)
        self.queue_name = "sync_operations"
        self.failed_queue_name = "failed_sync_operations"
        self.processing_queue_name = "processing_sync_operations"

    async def enqueue_operation(self, operation: SyncOperation) -> bool:
        """Add a sync operation to the queue"""
        try:
            operation_data = operation.dict()
            operation_data["enqueued_at"] = datetime.utcnow().isoformat()

            # Add to main queue
            self.redis_client.lpush(self.queue_name, json.dumps(operation_data))

            logger.info(
                "Operation enqueued", operation_id=operation.id, queue=self.queue_name
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to enqueue operation", operation_id=operation.id, error=str(e)
            )
            return False

    async def dequeue_operation(self) -> Optional[SyncOperation]:
        """Get the next sync operation from the queue"""
        try:
            # Move operation to processing queue
            operation_data = self.redis_client.rpoplpush(
                self.queue_name, self.processing_queue_name
            )

            if not operation_data:
                return None

            operation_dict = json.loads(operation_data)
            operation = SyncOperation(**operation_dict)

            logger.info("Operation dequeued", operation_id=operation.id)
            return operation

        except Exception as e:
            logger.error("Failed to dequeue operation", error=str(e))
            return None

    async def mark_operation_completed(self, operation_id: str) -> bool:
        """Mark an operation as completed and remove from processing queue"""
        try:
            # Remove from processing queue
            operations = self.redis_client.lrange(self.processing_queue_name, 0, -1)

            for operation_data in operations:
                operation_dict = json.loads(operation_data)
                if operation_dict["id"] == operation_id:
                    self.redis_client.lrem(
                        self.processing_queue_name, 1, operation_data
                    )
                    logger.info(
                        "Operation marked as completed", operation_id=operation_id
                    )
                    return True

            logger.warning(
                "Operation not found in processing queue", operation_id=operation_id
            )
            return False

        except Exception as e:
            logger.error(
                "Failed to mark operation as completed",
                operation_id=operation_id,
                error=str(e),
            )
            return False

    async def mark_operation_failed(
        self, operation_id: str, error_message: str
    ) -> bool:
        """Mark an operation as failed and move to failed queue"""
        try:
            # Get operation from processing queue
            operations = self.redis_client.lrange(self.processing_queue_name, 0, -1)

            for operation_data in operations:
                operation_dict = json.loads(operation_data)
                if operation_dict["id"] == operation_id:
                    # Update operation status
                    operation_dict["status"] = SyncStatus.FAILED
                    operation_dict["error_message"] = error_message
                    operation_dict["failed_at"] = datetime.utcnow().isoformat()

                    # Move to failed queue
                    self.redis_client.lpush(
                        self.failed_queue_name, json.dumps(operation_dict)
                    )
                    self.redis_client.lrem(
                        self.processing_queue_name, 1, operation_data
                    )

                    logger.info(
                        "Operation marked as failed",
                        operation_id=operation_id,
                        error=error_message,
                    )
                    return True

            logger.warning(
                "Operation not found in processing queue", operation_id=operation_id
            )
            return False

        except Exception as e:
            logger.error(
                "Failed to mark operation as failed",
                operation_id=operation_id,
                error=str(e),
            )
            return False

    async def retry_failed_operations(self, max_retries: int = 3) -> int:
        """Retry failed operations that haven't exceeded max retries"""
        try:
            retried_count = 0
            failed_operations = self.redis_client.lrange(self.failed_queue_name, 0, -1)

            for operation_data in failed_operations:
                operation_dict = json.loads(operation_data)
                retry_count = operation_dict.get("retry_count", 0)

                if retry_count < max_retries:
                    # Increment retry count
                    operation_dict["retry_count"] = retry_count + 1
                    operation_dict["status"] = SyncStatus.PENDING
                    operation_dict["retry_at"] = datetime.utcnow().isoformat()

                    # Move back to main queue
                    self.redis_client.lpush(self.queue_name, json.dumps(operation_dict))
                    self.redis_client.lrem(self.failed_queue_name, 1, operation_data)

                    retried_count += 1
                    logger.info(
                        "Operation retried",
                        operation_id=operation_dict["id"],
                        retry_count=retry_count + 1,
                    )

            logger.info("Failed operations retried", count=retried_count)
            return retried_count

        except Exception as e:
            logger.error("Failed to retry operations", error=str(e))
            return 0

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        try:
            main_queue_size = self.redis_client.llen(self.queue_name)
            processing_queue_size = self.redis_client.llen(self.processing_queue_name)
            failed_queue_size = self.redis_client.llen(self.failed_queue_name)

            return {
                "main_queue_size": main_queue_size,
                "processing_queue_size": processing_queue_size,
                "failed_queue_size": failed_queue_size,
                "total_operations": main_queue_size
                + processing_queue_size
                + failed_queue_size,
            }

        except Exception as e:
            logger.error("Failed to get queue status", error=str(e))
            return {
                "main_queue_size": 0,
                "processing_queue_size": 0,
                "failed_queue_size": 0,
                "total_operations": 0,
                "error": str(e),
            }

    async def clear_queue(self, queue_name: Optional[str] = None) -> bool:
        """Clear a specific queue or all queues"""
        try:
            if queue_name:
                self.redis_client.delete(queue_name)
                logger.info("Queue cleared", queue_name=queue_name)
            else:
                self.redis_client.delete(
                    self.queue_name, self.processing_queue_name, self.failed_queue_name
                )
                logger.info("All queues cleared")

            return True

        except Exception as e:
            logger.error("Failed to clear queue", queue_name=queue_name, error=str(e))
            return False

    async def get_operation_by_id(self, operation_id: str) -> Optional[SyncOperation]:
        """Get an operation by ID from any queue"""
        try:
            # Check all queues
            for queue_name in [
                self.queue_name,
                self.processing_queue_name,
                self.failed_queue_name,
            ]:
                operations = self.redis_client.lrange(queue_name, 0, -1)

                for operation_data in operations:
                    operation_dict = json.loads(operation_data)
                    if operation_dict["id"] == operation_id:
                        return SyncOperation(**operation_dict)

            return None

        except Exception as e:
            logger.error(
                "Failed to get operation by ID", operation_id=operation_id, error=str(e)
            )
            return None

    async def get_failed_operations(self, limit: int = 100) -> List[SyncOperation]:
        """Get failed operations for analysis"""
        try:
            failed_operations = []
            operations_data = self.redis_client.lrange(
                self.failed_queue_name, 0, limit - 1
            )

            for operation_data in operations_data:
                operation_dict = json.loads(operation_data)
                failed_operations.append(SyncOperation(**operation_dict))

            return failed_operations

        except Exception as e:
            logger.error("Failed to get failed operations", error=str(e))
            return []

    async def cleanup_old_operations(self, days: int = 7) -> int:
        """Clean up old completed operations"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            cleaned_count = 0

            # This would require additional tracking of operation completion times
            # For now, just return 0
            logger.info("Operation cleanup completed", cleaned_count=cleaned_count)
            return cleaned_count

        except Exception as e:
            logger.error("Failed to cleanup old operations", error=str(e))
            return 0
