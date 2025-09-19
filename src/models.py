"""
Data models for Frappe-Supabase Sync Service
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class SyncDirection(str, Enum):
    """Direction of synchronization"""
    FRAPPE_TO_SUPABASE = "frappe_to_supabase"
    SUPABASE_TO_FRAPPE = "supabase_to_frappe"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, Enum):
    """Status of sync operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"
    SKIPPED = "skipped"


class ConflictResolutionStrategy(str, Enum):
    """Conflict resolution strategies"""
    LAST_MODIFIED_WINS = "last_modified_wins"
    FRAPPE_WINS = "frappe_wins"
    SUPABASE_WINS = "supabase_wins"
    MANUAL = "manual"


class SyncEvent(BaseModel):
    """Represents a sync event from webhook"""
    id: str = Field(..., description="Unique event ID")
    source: str = Field(..., description="Source system (frappe/supabase)")
    doctype: str = Field(..., description="Frappe doctype or Supabase table")
    record_id: str = Field(..., description="Record ID")
    operation: str = Field(..., description="Operation (create/update/delete)")
    data: Dict[str, Any] = Field(..., description="Record data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    webhook_id: Optional[str] = Field(None, description="Webhook ID for tracking")


class SyncOperation(BaseModel):
    """Represents a sync operation to be performed"""
    id: str = Field(..., description="Unique operation ID")
    event_id: str = Field(..., description="Source event ID")
    direction: SyncDirection = Field(..., description="Sync direction")
    source_system: str = Field(..., description="Source system")
    target_system: str = Field(..., description="Target system")
    doctype: str = Field(..., description="Frappe doctype")
    table: str = Field(..., description="Supabase table")
    record_id: str = Field(..., description="Record ID")
    operation: str = Field(..., description="Operation type")
    data: Dict[str, Any] = Field(..., description="Data to sync")
    status: SyncStatus = Field(default=SyncStatus.PENDING)
    retry_count: int = Field(default=0)
    error_message: Optional[str] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)


class SyncMapping(BaseModel):
    """Configuration for syncing between Frappe doctype and Supabase table"""
    frappe_doctype: str = Field(..., description="Frappe doctype name")
    supabase_table: str = Field(..., description="Supabase table name")
    primary_key: str = Field(..., description="Primary key field")
    sync_fields: List[str] = Field(..., description="Fields to sync")
    direction: SyncDirection = Field(default=SyncDirection.BIDIRECTIONAL)
    conflict_resolution: ConflictResolutionStrategy = Field(
        default=ConflictResolutionStrategy.LAST_MODIFIED_WINS
    )
    field_mappings: Dict[str, str] = Field(
        default_factory=dict, 
        description="Field name mappings between systems"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional filters for sync"
    )
    enabled: bool = Field(default=True)


class SyncConflict(BaseModel):
    """Represents a sync conflict between systems"""
    id: str = Field(..., description="Unique conflict ID")
    operation_id: str = Field(..., description="Related sync operation ID")
    doctype: str = Field(..., description="Frappe doctype")
    table: str = Field(..., description="Supabase table")
    record_id: str = Field(..., description="Record ID")
    frappe_data: Dict[str, Any] = Field(..., description="Frappe record data")
    supabase_data: Dict[str, Any] = Field(..., description="Supabase record data")
    conflict_fields: List[str] = Field(..., description="Fields with conflicts")
    resolution_strategy: ConflictResolutionStrategy = Field(...)
    status: SyncStatus = Field(default=SyncStatus.PENDING)
    resolved_data: Optional[Dict[str, Any]] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(None)


class SyncMetrics(BaseModel):
    """Sync operation metrics"""
    total_operations: int = Field(default=0)
    successful_operations: int = Field(default=0)
    failed_operations: int = Field(default=0)
    pending_operations: int = Field(default=0)
    conflict_operations: int = Field(default=0)
    last_sync_time: Optional[datetime] = Field(None)
    average_sync_time: Optional[float] = Field(None)


class WebhookPayload(BaseModel):
    """Generic webhook payload structure"""
    event_type: str = Field(..., description="Type of event")
    doctype: str = Field(..., description="Frappe doctype or Supabase table")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(..., description="Source system")


class FrappeWebhookPayload(WebhookPayload):
    """Frappe-specific webhook payload"""
    doctype: str = Field(..., description="Frappe doctype")
    name: str = Field(..., description="Document name")
    operation: str = Field(..., description="Operation (after_insert/after_update/after_delete)")
    doc: Dict[str, Any] = Field(..., description="Document data")
    source: str = Field(default="frappe")


class SupabaseWebhookPayload(WebhookPayload):
    """Supabase-specific webhook payload"""
    table: str = Field(..., description="Supabase table name")
    record: Dict[str, Any] = Field(..., description="Record data")
    old_record: Optional[Dict[str, Any]] = Field(None, description="Old record data")
    operation: str = Field(..., description="Operation (INSERT/UPDATE/DELETE)")
    source: str = Field(default="supabase")
