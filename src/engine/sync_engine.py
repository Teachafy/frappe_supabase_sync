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
from ..sync_queue_module.sync_queue import SyncQueue
from ..utils.webhook_deduplicator import webhook_deduplicator

logger = SyncLogger()


class SyncEngine:
    """Core synchronization engine"""
    
    def __init__(self):
        self.settings = settings
        self.frappe_client = FrappeClient()
        self.supabase_client = SupabaseClient()
        self.field_mapper = FieldMapper()
        self.sync_queue = SyncQueue()
    
    def get_sync_mapping(self, doctype: str) -> Optional[Dict[str, Any]]:
        """Get sync mapping configuration for a doctype"""
        return self.settings.get_sync_mapping(doctype)
    
    async def process_sync_event(self, event: SyncEvent) -> Dict[str, Any]:
        """Process a sync event and create sync operations"""
        try:
            # Check for webhook deduplication first
            if webhook_deduplicator.is_duplicate(event.source, event.doctype, event.data):
                logger.logger.info(
                    "Webhook deduplicated, skipping",
                    event_id=event.id,
                    source=event.source,
                    doctype=event.doctype
                )
                return {"status": "skipped", "reason": "duplicate_webhook"}
            
            # Check for opposite service webhook after recent successful sync
            if webhook_deduplicator.is_opposite_service_webhook(event.source, event.doctype, event.data):
                logger.logger.info(
                    "Skipping opposite service webhook after recent successful sync",
                    event_id=event.id,
                    source=event.source,
                    doctype=event.doctype
                )
                return {"status": "skipped", "reason": "opposite_service_webhook_after_sync"}
            
            logger.log_sync_start(
                event.id, 
                f"{event.source}_to_target", 
                event.doctype, 
                event.record_id
            )
            
            # Get sync mapping for this doctype
            mapping = self.get_sync_mapping(event.doctype)
            if not mapping:
                return {"status": "skipped", "reason": "no_mapping"}
            
            # Determine sync direction
            direction = self._determine_sync_direction(event, mapping)
            if not direction:
                return {"status": "skipped", "reason": "direction_not_allowed"}
            
            # Determine the correct operation type (create vs update)
            operation_type = await self._determine_operation_type(event, mapping, direction)
            
            # Create sync operation
            # Make a deep copy of the data to prevent corruption during retries
            import copy
            operation = SyncOperation(
                id=str(uuid.uuid4()),
                event_id=event.id,
                direction=direction,
                source_system=event.source,
                target_system="supabase" if event.source == "frappe" else "frappe",
                doctype=event.doctype,
                table=mapping["supabase_table"],
                record_id=event.record_id,
                operation=operation_type,
                data=copy.deepcopy(event.data)
            )
            
            # Process the sync operation with retry logic
            result_status = await self.retry_operation(operation, max_retries=3)
            
            # Only log success if the operation actually succeeded
            if result_status == "success":
                logger.log_sync_success(operation.id, 0.0)  # Duration would be calculated
                # Record successful sync to prevent opposite service webhooks
                webhook_deduplicator.record_successful_sync(event.source, event.doctype, event.data)
                return {"status": "success", "operation_id": operation.id}
            else:
                logger.log_sync_error(operation.id, "Operation failed after retries")
                return {"status": "error", "error": "Operation failed after retries"}
            
        except Exception as e:
            logger.log_sync_error(event.id, str(e))
            return {"status": "error", "error": str(e)}
    
    def _determine_sync_direction(self, event: SyncEvent, mapping: Dict[str, str]) -> Optional[SyncDirection]:
        """Determine the sync direction based on event and mapping"""
        # Determine the target direction based on source
        if event.source == "frappe" and mapping.get("supabase_table"):
            # This is a Frappe webhook, sync to Supabase
            target_direction = SyncDirection.FRAPPE_TO_SUPABASE
        elif event.source == "supabase" and mapping.get("frappe_doctype"):
            # This is a Supabase webhook, sync to Frappe
            target_direction = SyncDirection.SUPABASE_TO_FRAPPE
        else:
            return None
        
        # Check if this would create a reverse sync loop
        # A reverse sync happens when:
        # 1. The original source is different from the current source, AND
        # 2. The target direction would sync back to the original source
        if event.original_source and event.original_source != event.source:
            if (event.original_source == "frappe" and target_direction == SyncDirection.SUPABASE_TO_FRAPPE) or \
               (event.original_source == "supabase" and target_direction == SyncDirection.FRAPPE_TO_SUPABASE):
                # This is a reverse sync, skip it
                logger.logger.info(f"Skipping reverse sync from {event.source} to {event.original_source} to prevent loop", operation_id=event.id)
                return None
        
        return target_direction
    
    async def _determine_operation_type(self, event: SyncEvent, mapping: Dict[str, str], direction: SyncDirection) -> str:
        """Determine if this should be a create or update operation based on existing records"""
        try:
            # If the event operation is delete, return delete directly
            if event.operation == "delete":
                return "delete"
            
            # Map the data to get the target format
            mapped_data = await self.field_mapper.map_fields(
                event.data,
                event.source,
                "supabase" if direction == SyncDirection.FRAPPE_TO_SUPABASE else "frappe",
                mapping
            )
            
            if not mapped_data:
                return "create"  # Default to create if no mapped data
            
            # Get primary identifier for lookup
            identifier = self.field_mapper.get_primary_identifier(
                mapped_data,
                event.source,
                "supabase" if direction == SyncDirection.FRAPPE_TO_SUPABASE else "frappe"
            )
            
            if not identifier:
                return "create"  # Default to create if no identifier
            
            identifier_type, identifier_value = identifier
            
            # Check if record exists in target system
            if direction == SyncDirection.FRAPPE_TO_SUPABASE:
                # Check Supabase for existing record
                if identifier_type == "phone":
                    existing_record = await self.supabase_client.find_record_by_field(
                        mapping["supabase_table"],
                        "phone_number",
                        identifier_value
                    )
                elif identifier_type == "email":
                    existing_record = await self.supabase_client.find_record_by_field(
                        mapping["supabase_table"],
                        "email",
                        identifier_value
                    )
                elif identifier_type == "task_subject":
                    # For Tasks: look up by task_name + page_content
                    subject, desc_snippet = identifier_value.split("|", 1) if "|" in identifier_value else (identifier_value, "")
                    existing_record = await self.supabase_client.find_record_by_field(
                        mapping["supabase_table"],
                        "task_name",
                        subject
                    )
                    # Verify description matches if we have a snippet
                    if existing_record and desc_snippet:
                        existing_desc = existing_record.get("page_content", "") or ""
                        if desc_snippet not in existing_desc:
                            existing_record = None
            else:
                # Check Frappe for existing record
                if identifier_type == "phone":
                    existing_record = await self.frappe_client.find_document_by_field(
                        event.doctype,
                        "cell_number",
                        identifier_value
                    )
                elif identifier_type == "email":
                    existing_record = await self.frappe_client.find_document_by_field(
                        event.doctype,
                        "personal_email",
                        identifier_value
                    )
                elif identifier_type == "task_subject":
                    # For Tasks: look up by subject + description
                    subject, desc_snippet = identifier_value.split("|", 1) if "|" in identifier_value else (identifier_value, "")
                    existing_record = await self.frappe_client.find_document_by_field(
                        event.doctype,
                        "subject",
                        subject
                    )
                    # Verify description matches if we have a snippet
                    if existing_record and desc_snippet:
                        existing_desc = existing_record.get("description", "") or ""
                        if desc_snippet not in existing_desc:
                            existing_record = None
            
            # Return "update" if record exists, "create" if not
            return "update" if existing_record else "create"
            
        except Exception as e:
            logger.logger.error("Error determining operation type", error=str(e), event_id=event.id)
            return "create"  # Default to create on error
    
    async def _process_sync_operation(self, operation: SyncOperation, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Process a sync operation"""
        try:
            # Map fields according to configuration
            mapped_data = await self.field_mapper.map_fields(
                operation.data, 
                operation.source_system, 
                operation.target_system,
                mapping
            )
            
            # Check for conflicts if updating
            if operation.operation in ["update", "create"]:
                conflict = await self._check_for_conflicts(operation, mapping)
                if conflict:
                    conflict_result = await self._handle_conflict(conflict, operation, mapping)
                    if conflict_result.get("status") == "success" and "resolved_data" in conflict_result:
                        # Use the resolved data for the sync operation
                        mapped_data = conflict_result["resolved_data"]
                    else:
                        return conflict_result
            
            # Execute the sync operation
            if operation.direction == SyncDirection.FRAPPE_TO_SUPABASE:
                result = await self._sync_to_supabase(operation, mapped_data, mapping)
            elif operation.direction == SyncDirection.SUPABASE_TO_FRAPPE:
                result = await self._sync_to_frappe(operation, mapped_data, mapping)
            else:
                return {"status": "error", "error": "Unknown sync direction"}
            
            return result
            
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
                # For Frappe to Supabase sync, we need to find the existing record by phone or email
                # since the record_id is a Frappe document name, not a Supabase UUID
                if operation.source_system == "frappe":
                    # Get primary identifier (phone number or email)
                    identifier = self.field_mapper.get_primary_identifier(
                        mapped_data, "frappe", "supabase"
                    )
                    
                    if identifier:
                        identifier_type, identifier_value = identifier
                        
                        if identifier_type == "phone":
                            # Look up by phone number using the original phone number from mapped_data
                            # The identifier_value is normalized, but we need the original for lookup
                            original_phone = mapped_data.get("phone_number", identifier_value)
                            existing_record = await self.supabase_client.find_record_by_field(
                                mapping["supabase_table"],
                                "phone_number",
                                original_phone
                            )
                        elif identifier_type == "email":
                            # Look up by email
                            existing_record = await self.supabase_client.find_record_by_field(
                                mapping["supabase_table"],
                                "email",
                                identifier_value
                            )
                        elif identifier_type == "task_subject":
                            # For Tasks: look up by task_name + page_content
                            subject, desc_snippet = identifier_value.split("|", 1) if "|" in identifier_value else (identifier_value, "")
                            
                            # First try to find by task_name (Supabase field)
                            existing_record = await self.supabase_client.find_record_by_field(
                                mapping["supabase_table"],
                                "task_name",
                                subject
                            )
                            
                            # If found and we have description snippet, verify it matches
                            if existing_record and desc_snippet:
                                existing_desc = existing_record.get("page_content", "") or ""
                                if desc_snippet not in existing_desc:
                                    # Description doesn't match, treat as different task
                                    existing_record = None
                        
                        if existing_record:
                            # Update existing record using its UUID
                            logger.logger.info(f"Updating existing Supabase record {existing_record.get('id')} for Frappe document {operation.record_id} (found by {identifier_type})", operation_id=operation.id)
                            result = await self.supabase_client.update_record(
                                mapping["supabase_table"],
                                existing_record.get("id"),
                                mapped_data
                            )
                        else:
                            # Create new record if not found
                            logger.logger.info(f"Creating new Supabase record for Frappe document {operation.record_id} (no existing record found by {identifier_type})", operation_id=operation.id)
                            result = await self.supabase_client.create_record(
                                mapping["supabase_table"], 
                                mapped_data
                            )
                    else:
                        # No identifier, create new record
                        logger.logger.info(f"Creating new Supabase record for Frappe document {operation.record_id} (no phone or email for lookup)", operation_id=operation.id)
                        result = await self.supabase_client.create_record(
                            mapping["supabase_table"], 
                            mapped_data
                        )
                else:
                    # For other sources, use the record_id directly
                    result = await self.supabase_client.update_record(
                        mapping["supabase_table"],
                        operation.record_id,
                        mapped_data
                    )
            elif operation.operation == "delete":
                # For Frappe to Supabase sync, find by appropriate field
                if operation.source_system == "frappe":
                    existing_record = None
                    
                    if operation.doctype == "Employee":
                        # For employees, look up by email
                        email = mapped_data.get("email")
                        logger.logger.info(f"Delete operation: looking for employee record with email {email}")
                        if email:
                            existing_record = await self.supabase_client.find_record_by_field(
                                mapping["supabase_table"],
                                "email",
                                email
                            )
                        else:
                            result = {"deleted": False, "reason": "no_email_for_lookup"}
                            logger.logger.warning("No email found in mapped data for employee delete operation")
                    elif operation.doctype == "Task":
                        # For tasks, look up by task_name
                        task_name = mapped_data.get("task_name")
                        logger.logger.info(f"Delete operation: looking for task record with task_name {task_name}")
                        if task_name:
                            existing_record = await self.supabase_client.find_record_by_field(
                                mapping["supabase_table"],
                                "task_name",
                                task_name
                            )
                        else:
                            result = {"deleted": False, "reason": "no_task_name_for_lookup"}
                            logger.logger.warning("No task_name found in mapped data for task delete operation")
                    
                    if existing_record:
                        logger.logger.info(f"Found existing record: {existing_record}")
                        await self.supabase_client.delete_record(
                            mapping["supabase_table"],
                            existing_record.get("id")
                        )
                        result = {"deleted": True}
                        logger.logger.info(f"Successfully deleted record with ID {existing_record.get('id')}")
                    elif existing_record is None and result is None:
                        result = {"deleted": False, "reason": "record_not_found"}
                        logger.logger.warning(f"Record not found for delete operation")
                else:
                    await self.supabase_client.delete_record(
                        mapping["supabase_table"],
                        operation.record_id
                    )
                    result = {"deleted": True}
            else:
                # Default to create for unknown operations
                result = await self.supabase_client.create_record(
                    mapping["supabase_table"], 
                    mapped_data
                )
            
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
                # For Supabase to Frappe sync, we need to find the document by a unique field
                # since the record_id is a UUID but Frappe uses its own naming
                if operation.source_system == "supabase":
                    # Get primary identifier (phone number or email)
                    identifier = self.field_mapper.get_primary_identifier(
                        mapped_data, "supabase", "frappe"
                    )
                    
                    if identifier:
                        identifier_type, identifier_value = identifier
                        
                        if identifier_type == "phone":
                            # Look up by phone number
                            existing_doc = await self.frappe_client.find_document_by_field(
                                operation.doctype,
                                "cell_number",
                                identifier_value
                            )
                        elif identifier_type == "email":
                            # Look up by email
                            existing_doc = await self.frappe_client.find_document_by_field(
                                operation.doctype,
                                "personal_email",
                                identifier_value
                            )
                        elif identifier_type == "task_subject":
                            # For Tasks: look up by subject + description
                            subject, desc_snippet = identifier_value.split("|", 1) if "|" in identifier_value else (identifier_value, "")
                            
                            # First try to find by subject
                            existing_doc = await self.frappe_client.find_document_by_field(
                                operation.doctype,
                                "subject",
                                subject
                            )
                            
                            # If found and we have description snippet, verify it matches
                            if existing_doc and desc_snippet:
                                existing_desc = existing_doc.get("description", "") or ""
                                if desc_snippet not in existing_desc:
                                    # Description doesn't match, treat as different task
                                    existing_doc = None
                        
                        if existing_doc:
                            # Update existing document
                            logger.logger.info(f"Updating existing Frappe document {existing_doc.get('name')} for Supabase record {operation.record_id} (found by {identifier_type})", operation_id=operation.id)
                            result = await self.frappe_client.update_document(
                                operation.doctype,
                                existing_doc.get("name"),
                                mapped_data
                            )
                        else:
                            # Create new document if not found
                            logger.logger.info(f"Creating new Frappe document for Supabase record {operation.record_id} (no existing record found by {identifier_type})", operation_id=operation.id)
                            result = await self.frappe_client.create_document(
                                operation.doctype,
                                mapped_data
                            )
                    else:
                        # No identifier, create new document
                        logger.logger.info(f"Creating new Frappe document for Supabase record {operation.record_id} (no phone or email for lookup)", operation_id=operation.id)
                        result = await self.frappe_client.create_document(
                            operation.doctype,
                            mapped_data
                        )
                else:
                    # Check if document exists first
                    existing_doc = await self.frappe_client.get_document(
                        operation.doctype,
                        operation.record_id
                    )
                    
                    if existing_doc:
                        # Document exists, update it
                        result = await self.frappe_client.update_document(
                            operation.doctype,
                            operation.record_id,
                            mapped_data
                        )
                    else:
                        # Document doesn't exist, create it
                        logger.logger.info(f"Document {operation.record_id} not found, creating new document", operation_id=operation.id)
                        result = await self.frappe_client.create_document(
                            operation.doctype,
                            mapped_data
                        )
            elif operation.operation == "delete":
                # For Supabase to Frappe deletes, we need to find the Frappe record ID first
                if operation.source_system == "supabase":
                    # Find the corresponding Frappe record by looking up using mapped data
                    frappe_record = None
                    if operation.doctype == "Employee":
                        # Look up by email
                        email = mapped_data.get("personal_email")
                        if email:
                            frappe_record = await self.frappe_client.find_document_by_field(
                                operation.doctype,
                                "personal_email",
                                email
                            )
                    elif operation.doctype == "Task":
                        # Look up by subject
                        subject = mapped_data.get("subject")
                        if subject:
                            frappe_record = await self.frappe_client.find_document_by_field(
                                operation.doctype,
                                "subject",
                                subject
                            )
                    
                    if frappe_record:
                        await self.frappe_client.delete_document(
                            operation.doctype,
                            frappe_record["name"]
                        )
                        result = {"deleted": True}
                    else:
                        result = {"deleted": False, "reason": "record_not_found"}
                else:
                    # For Frappe to Supabase deletes, use the record_id directly
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
            # Get the mapped data to find the target record
            mapped_data = await self.field_mapper.map_fields(
                operation.data,
                operation.source_system,
                "supabase" if operation.direction == SyncDirection.FRAPPE_TO_SUPABASE else "frappe",
                mapping
            )
            
            if not mapped_data:
                return None  # No conflict if no mapped data
            
            # Get primary identifier for lookup
            identifier = self.field_mapper.get_primary_identifier(
                mapped_data,
                operation.source_system,
                "supabase" if operation.direction == SyncDirection.FRAPPE_TO_SUPABASE else "frappe"
            )
            
            if not identifier or len(identifier) != 2:
                return None  # No conflict if no identifier for lookup or invalid format
            
            identifier_type, identifier_value = identifier
            
            if not identifier_value or not isinstance(identifier_value, str):  # Check if identifier_value is not None or empty
                return None
            
            if operation.direction == SyncDirection.FRAPPE_TO_SUPABASE:
                # Get current Supabase data by identifier type
                if identifier_type == "phone":
                    current_data = await self.supabase_client.find_record_by_field(
                        mapping["supabase_table"],
                        "phone_number",
                        identifier_value
                    )
                elif identifier_type == "email":
                    current_data = await self.supabase_client.find_record_by_field(
                        mapping["supabase_table"],
                        "email",
                        identifier_value
                    )
                elif identifier_type == "task_subject":
                    # For Tasks: look up by task_name + page_content
                    if identifier_value and "|" in identifier_value:
                        subject, desc_snippet = identifier_value.split("|", 1)
                    else:
                        subject, desc_snippet = identifier_value or "", ""
                    
                    current_data = await self.supabase_client.find_record_by_field(
                        mapping["supabase_table"],
                        "task_name",
                        subject
                    )
                    # Verify description matches if we have a snippet
                    if current_data and desc_snippet:
                        existing_desc = current_data.get("page_content", "") or ""
                        if desc_snippet not in existing_desc:
                            current_data = None
            else:
                # Get current Frappe data by identifier type
                if identifier_type == "phone":
                    current_data = await self.frappe_client.find_document_by_field(
                        operation.doctype,
                        "cell_number",
                        identifier_value
                    )
                elif identifier_type == "email":
                    current_data = await self.frappe_client.find_document_by_field(
                        operation.doctype,
                        "personal_email",
                        identifier_value
                    )
                elif identifier_type == "task_subject":
                    # For Tasks: look up by subject + description
                    if identifier_value and "|" in identifier_value:
                        subject, desc_snippet = identifier_value.split("|", 1)
                    else:
                        subject, desc_snippet = identifier_value or "", ""
                    
                    current_data = await self.frappe_client.find_document_by_field(
                        operation.doctype,
                        "subject",
                        subject
                    )
                    # Verify description matches if we have a snippet
                    if current_data and desc_snippet:
                        existing_desc = current_data.get("description", "") or ""
                        if desc_snippet not in existing_desc:
                            current_data = None
            
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
                    supabase_data=current_data if operation.source_system == "frappe" else operation.data,
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
            # Use the most recently modified record - but map it first
            raw_resolved_data = self._resolve_by_last_modified(conflict)
            if operation.direction == SyncDirection.FRAPPE_TO_SUPABASE:
                resolved_data = await self.field_mapper.map_fields(
                    raw_resolved_data, 
                    "frappe", 
                    "supabase", 
                    mapping
                )
            else:
                resolved_data = await self.field_mapper.map_fields(
                    raw_resolved_data, 
                    "supabase", 
                    "frappe", 
                    mapping
                )
        elif conflict.resolution_strategy == ConflictResolutionStrategy.FRAPPE_WINS:
            # Always use Frappe data - but map it first
            resolved_data = await self.field_mapper.map_fields(
                conflict.frappe_data, 
                "frappe", 
                "supabase", 
                mapping
            )
        elif conflict.resolution_strategy == ConflictResolutionStrategy.SUPABASE_WINS:
            # Always use Supabase data - but map it first
            resolved_data = await self.field_mapper.map_fields(
                conflict.supabase_data, 
                "supabase", 
                "frappe", 
                mapping
            )
        else:
            # Manual resolution required
            return {"status": "conflict", "conflict_id": conflict.id, "requires_manual_resolution": True}
        
        # Update the operation with resolved data
        operation.data = resolved_data
        conflict.resolved_data = resolved_data
        conflict.status = SyncStatus.COMPLETED
        conflict.resolved_at = datetime.utcnow()
        
        # Return success with resolved data - let the calling method handle the sync
        return {"status": "success", "resolved_data": resolved_data}
    
    def _resolve_by_last_modified(self, conflict: SyncConflict) -> Dict[str, Any]:
        """Resolve conflict by using the most recently modified record"""
        logger.logger.info(f"Resolving conflict: frappe_data={conflict.frappe_data}, supabase_data={conflict.supabase_data}")
        
        if not conflict.frappe_data or not conflict.supabase_data:
            logger.logger.warning(f"Missing data in conflict: frappe_data={conflict.frappe_data is not None}, supabase_data={conflict.supabase_data is not None}")
            return conflict.frappe_data or conflict.supabase_data or {}
        
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
    
    # Additional methods required by tests
    async def sync_frappe_to_supabase(self, doctype: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync data from Frappe to Supabase"""
        try:
            mapping = self.get_sync_mapping(doctype)
            if not mapping:
                return {"status": "error", "error": "No mapping found"}
            
            mapped_data = await self.field_mapper.map_fields(data, "frappe", "supabase", mapping)
            logger.info(f"Data being sent to Supabase: {mapped_data}")
            result = await self.supabase_client.insert_data(mapping["supabase_table"], mapped_data)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def sync_supabase_to_frappe(self, doctype: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync data from Supabase to Frappe"""
        try:
            mapping = self.get_sync_mapping(doctype)
            if not mapping:
                return {"status": "error", "error": "No mapping found"}
            
            mapped_data = await self.field_mapper.map_fields(data, "supabase", "frappe", mapping)
            result = await self.frappe_client.create_document(doctype, mapped_data)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def handle_data_conflicts(self, doctype: str, record_id: str, 
                                  frappe_data: Dict[str, Any], 
                                  supabase_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data conflicts between Frappe and Supabase"""
        try:
            mapping = self.get_sync_mapping(doctype)
            if not mapping:
                return {"status": "error", "error": "No mapping found"}
            
            # Use last modified wins strategy
            frappe_modified = frappe_data.get("modified", "")
            supabase_modified = supabase_data.get("updated_at", "")
            
            if frappe_modified > supabase_modified:
                # Frappe is newer, return Frappe data
                return frappe_data
            else:
                # Supabase is newer, return Supabase data
                return supabase_data
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def validate_sync_mapping(self, mapping: Dict[str, Any]) -> bool:
        """Validate a sync mapping configuration"""
        required_fields = ["frappe_doctype", "supabase_table", "field_mappings", "reverse_mappings"]
        return all(field in mapping for field in required_fields)
    
    def load_sync_mappings(self) -> Dict[str, Any]:
        """Load sync mappings from configuration"""
        try:
            import json
            from pathlib import Path
            
            custom_mappings_file = Path("custom_mappings.json")
            if custom_mappings_file.exists():
                with open(custom_mappings_file, 'r') as f:
                    custom_mappings = json.load(f)
                return custom_mappings
        except Exception as e:
            logger.warning(f"Could not load custom mappings: {e}")
        
        # Fallback to default mappings
        return self.settings.sync_mappings
    
    def save_sync_mappings(self, mappings: Dict[str, Any]) -> bool:
        """Save sync mappings to configuration"""
        self.settings.sync_mappings.update(mappings)
        return True
    
    async def retry_operation(self, operation: SyncOperation, max_retries: int = 3) -> str:
        """Retry a failed sync operation"""
        try:
            mapping = self.get_sync_mapping(operation.doctype)
            if not mapping:
                return "error"
            
            # Initialize retry count if not present
            if not hasattr(operation, 'retry_count'):
                operation.retry_count = 0
            
            # Check if we've already exceeded max retries
            if operation.retry_count >= max_retries:
                logger.logger.error(f"Operation {operation.id} has already exceeded max retries ({max_retries})")
                return "error"
            
            # Retry loop with timeout
            import asyncio
            start_time = asyncio.get_event_loop().time()
            timeout_seconds = 30  # 30 second timeout for the entire operation
            
            for attempt in range(max_retries + 1):
                try:
                    # Check if we've exceeded the timeout
                    if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                        logger.logger.error(f"Operation {operation.id} timed out after {timeout_seconds} seconds")
                        return "error"
                    
                    logger.logger.info(f"Retry attempt {attempt + 1}/{max_retries + 1} for operation {operation.id}")
                    result = await self._process_sync_operation(operation, mapping)
                    if result.get("status") == "success":
                        logger.logger.info(f"Operation {operation.id} succeeded on attempt {attempt + 1}")
                        return "success"
                    else:
                        operation.retry_count += 1
                        logger.logger.warning(f"Operation {operation.id} failed on attempt {attempt + 1}: {result.get('error', 'Unknown error')}")
                        if attempt == max_retries:  # Last attempt failed
                            logger.logger.error(f"Operation {operation.id} failed after {max_retries + 1} attempts")
                            return "error"
                except Exception as e:
                    operation.retry_count += 1
                    logger.logger.error(f"Operation {operation.id} failed on attempt {attempt + 1} with exception: {str(e)}")
                    if attempt == max_retries:  # Last attempt failed
                        logger.logger.error(f"Operation {operation.id} failed after {max_retries + 1} attempts with exception")
                        return "error"
            
            return "error"
        except Exception as e:
            return "error"
    
    async def batch_process_sync_events(self, events: List[SyncEvent], batch_size: int = 10) -> List[Dict[str, Any]]:
        """Process multiple sync events in batches"""
        results = []
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            batch_results = []
            for event in batch:
                result = await self.process_sync_event(event)
                batch_results.append(result)
            results.extend(batch_results)
        return results
    
    async def get_sync_metrics(self) -> Dict[str, Any]:
        """Get sync operation metrics"""
        return {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "pending_operations": 0,
            "total_events": 0
        }
    
    def validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """Validate webhook signature"""
        # This would implement actual signature validation
        return signature == self.settings.webhook_secret
    
    async def transform_data(self, data: Dict[str, Any], source_system: str, target_system: str) -> Dict[str, Any]:
        """Transform data between systems"""
        try:
            # This would use field mapper for transformation
            # For now, just return the data with some basic transformation
            if source_system == "frappe" and target_system == "supabase":
                return {"id": data.get("name", ""), **data}
            return data
        except Exception as e:
            return {"error": str(e)}
