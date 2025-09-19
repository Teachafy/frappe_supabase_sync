"""
Core sync engine for Frappe-Supabase synchronization
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog

from ..models import (
    SyncEvent, SyncOperation, SyncStatus, SyncDirection, 
    ConflictResolutionStrategy, SyncConflict
)
from ..config import settings
from ..utils.logger import SyncLogger
from ..utils.frappe_client import FrappeClient
from ..utils.supabase_client import SupabaseClient
from ..mapping.field_mapper import FieldMapper
from ..queue.sync_queue import SyncQueue

logger = SyncLogger()


class SyncEngine:
    """Core synchronization engine"""
    
    def __init__(self):
        self.frappe_client = FrappeClient()
        self.supabase_client = SupabaseClient()
        self.field_mapper = FieldMapper()
        self.sync_queue = SyncQueue()
    
    async def process_sync_event(self, event: SyncEvent) -> Dict[str, Any]:
        """Process a sync event and create sync operations"""
        try:
            logger.log_sync_start(
                event.id, 
                f"{event.source}_to_target", 
                event.doctype, 
                event.record_id
            )
            
            # Get sync mapping for this doctype
            mapping = settings.get_sync_mapping(event.doctype)
            if not mapping:
                return {"status": "skipped", "reason": "no_mapping"}
            
            # Determine sync direction
            direction = self._determine_sync_direction(event, mapping)
            if not direction:
                return {"status": "skipped", "reason": "direction_not_allowed"}
            
            # Create sync operation
            operation = SyncOperation(
                id=str(uuid.uuid4()),
                event_id=event.id,
                direction=direction,
                source_system=event.source,
                target_system="supabase" if event.source == "frappe" else "frappe",
                doctype=event.doctype,
                table=mapping["supabase_table"],
                record_id=event.record_id,
                operation=event.operation,
                data=event.data
            )
            
            # Process the sync operation
            result = await self._process_sync_operation(operation, mapping)
            
            logger.log_sync_success(operation.id, 0.0)  # Duration would be calculated
            return result
            
        except Exception as e:
            logger.log_sync_error(event.id, str(e))
            return {"status": "error", "error": str(e)}
    
    def _determine_sync_direction(self, event: SyncEvent, mapping: Dict[str, str]) -> Optional[SyncDirection]:
        """Determine the sync direction based on event and mapping"""
        if event.source == "frappe":
            return SyncDirection.FRAPPE_TO_SUPABASE
        elif event.source == "supabase":
            return SyncDirection.SUPABASE_TO_FRAPPE
        return None
    
    async def _process_sync_operation(self, operation: SyncOperation, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Process a sync operation"""
        try:
            # Map fields according to configuration
            mapped_data = self.field_mapper.map_fields(
                operation.data, 
                operation.source_system, 
                operation.target_system,
                mapping
            )
            
            # Check for conflicts if updating
            if operation.operation in ["update", "create"]:
                conflict = await self._check_for_conflicts(operation, mapping)
                if conflict:
                    return await self._handle_conflict(conflict, operation, mapping)
            
            # Execute the sync operation
            if operation.direction == SyncDirection.FRAPPE_TO_SUPABASE:
                return await self._sync_to_supabase(operation, mapped_data, mapping)
            elif operation.direction == SyncDirection.SUPABASE_TO_FRAPPE:
                return await self._sync_to_frappe(operation, mapped_data, mapping)
            
        except Exception as e:
            logger.log_sync_error(operation.id, str(e))
            operation.status = SyncStatus.FAILED
            operation.error_message = str(e)
            return {"status": "error", "error": str(e)}
    
    async def _sync_to_supabase(self, operation: SyncOperation, mapped_data: Dict[str, Any], 
                               mapping: Dict[str, str]) -> Dict[str, Any]:
        """Sync data to Supabase"""
        try:
            if operation.operation == "create":
                result = await self.supabase_client.create_record(
                    mapping["supabase_table"], 
                    mapped_data
                )
            elif operation.operation == "update":
                result = await self.supabase_client.update_record(
                    mapping["supabase_table"],
                    operation.record_id,
                    mapped_data
                )
            elif operation.operation == "delete":
                await self.supabase_client.delete_record(
                    mapping["supabase_table"],
                    operation.record_id
                )
                result = {"deleted": True}
            
            operation.status = SyncStatus.COMPLETED
            operation.completed_at = datetime.utcnow()
            
            return {"status": "success", "result": result}
            
        except Exception as e:
            logger.log_sync_error(operation.id, str(e))
            operation.status = SyncStatus.FAILED
            operation.error_message = str(e)
            return {"status": "error", "error": str(e)}
    
    async def _sync_to_frappe(self, operation: SyncOperation, mapped_data: Dict[str, Any], 
                             mapping: Dict[str, str]) -> Dict[str, Any]:
        """Sync data to Frappe"""
        try:
            if operation.operation == "create":
                result = await self.frappe_client.create_document(
                    operation.doctype,
                    mapped_data
                )
            elif operation.operation == "update":
                result = await self.frappe_client.update_document(
                    operation.doctype,
                    operation.record_id,
                    mapped_data
                )
            elif operation.operation == "delete":
                await self.frappe_client.delete_document(
                    operation.doctype,
                    operation.record_id
                )
                result = {"deleted": True}
            
            operation.status = SyncStatus.COMPLETED
            operation.completed_at = datetime.utcnow()
            
            return {"status": "success", "result": result}
            
        except Exception as e:
            logger.log_sync_error(operation.id, str(e))
            operation.status = SyncStatus.FAILED
            operation.error_message = str(e)
            return {"status": "error", "error": str(e)}
    
    async def _check_for_conflicts(self, operation: SyncOperation, mapping: Dict[str, str]) -> Optional[SyncConflict]:
        """Check for conflicts between source and target data"""
        try:
            if operation.direction == SyncDirection.FRAPPE_TO_SUPABASE:
                # Get current Supabase data
                current_data = await self.supabase_client.get_record(
                    mapping["supabase_table"],
                    operation.record_id
                )
            else:
                # Get current Frappe data
                current_data = await self.frappe_client.get_document(
                    operation.doctype,
                    operation.record_id
                )
            
            if not current_data:
                return None  # No conflict if target doesn't exist
            
            # Check for field conflicts
            conflict_fields = self._find_conflict_fields(operation.data, current_data, mapping)
            
            if conflict_fields:
                return SyncConflict(
                    id=str(uuid.uuid4()),
                    operation_id=operation.id,
                    doctype=operation.doctype,
                    table=mapping["supabase_table"],
                    record_id=operation.record_id,
                    frappe_data=operation.data if operation.source_system == "frappe" else current_data,
                    supabase_data=operation.data if operation.source_system == "supabase" else current_data,
                    conflict_fields=conflict_fields,
                    resolution_strategy=ConflictResolutionStrategy(mapping.get("conflict_resolution", "last_modified_wins"))
                )
            
            return None
            
        except Exception as e:
            logger.log_sync_error(operation.id, f"Conflict check failed: {str(e)}")
            return None
    
    def _find_conflict_fields(self, source_data: Dict[str, Any], target_data: Dict[str, Any], 
                             mapping: Dict[str, str]) -> List[str]:
        """Find fields that have conflicts between source and target"""
        conflict_fields = []
        
        for field in mapping.get("sync_fields", []):
            source_value = source_data.get(field)
            target_value = target_data.get(field)
            
            if source_value != target_value and source_value is not None and target_value is not None:
                conflict_fields.append(field)
        
        return conflict_fields
    
    async def _handle_conflict(self, conflict: SyncConflict, operation: SyncOperation, 
                              mapping: Dict[str, str]) -> Dict[str, Any]:
        """Handle sync conflicts"""
        logger.log_conflict_detected(operation.id, conflict.conflict_fields)
        
        if conflict.resolution_strategy == ConflictResolutionStrategy.LAST_MODIFIED_WINS:
            # Use the most recently modified record
            resolved_data = self._resolve_by_last_modified(conflict)
        elif conflict.resolution_strategy == ConflictResolutionStrategy.FRAPPE_WINS:
            # Always use Frappe data
            resolved_data = conflict.frappe_data
        elif conflict.resolution_strategy == ConflictResolutionStrategy.SUPABASE_WINS:
            # Always use Supabase data
            resolved_data = conflict.supabase_data
        else:
            # Manual resolution required
            return {"status": "conflict", "conflict_id": conflict.id, "requires_manual_resolution": True}
        
        # Update the operation with resolved data
        operation.data = resolved_data
        conflict.resolved_data = resolved_data
        conflict.status = SyncStatus.COMPLETED
        conflict.resolved_at = datetime.utcnow()
        
        # Continue with the sync operation
        return await self._process_sync_operation(operation, mapping)
    
    def _resolve_by_last_modified(self, conflict: SyncConflict) -> Dict[str, Any]:
        """Resolve conflict by using the most recently modified record"""
        frappe_modified = conflict.frappe_data.get("modified")
        supabase_modified = conflict.supabase_data.get("updated_at")
        
        if frappe_modified and supabase_modified:
            if frappe_modified > supabase_modified:
                return conflict.frappe_data
            else:
                return conflict.supabase_data
        elif frappe_modified:
            return conflict.frappe_data
        else:
            return conflict.supabase_data
    
    async def get_sync_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a sync operation"""
        # This would typically query a database or cache
        # For now, return a basic structure
        return {
            "operation_id": operation_id,
            "status": "completed",  # Would be actual status
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    async def retry_failed_operations(self) -> Dict[str, Any]:
        """Retry failed sync operations"""
        # This would query for failed operations and retry them
        return {"status": "success", "retried_operations": 0}
