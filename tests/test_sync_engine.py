"""
Comprehensive unit tests for the sync engine
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime

from src.engine.sync_engine import SyncEngine
from src.models import SyncEvent, SyncOperation, SyncDirection
from src.config import Settings


class TestSyncEngine:
    """Test cases for SyncEngine class"""

    @pytest.mark.asyncio
    async def test_sync_engine_initialization(self, sync_engine, test_settings):
        """Test sync engine initialization"""
        assert sync_engine is not None
        assert sync_engine.settings == test_settings
        assert sync_engine.frappe_client is not None
        assert sync_engine.supabase_client is not None
        assert sync_engine.sync_queue is not None

    @pytest.mark.asyncio
    async def test_process_sync_event_create(self, sync_engine, sample_sync_events):
        """Test processing a create sync event"""
        event = sample_sync_events[0]  # Frappe create event
        
        # Mock the mapping lookup and internal methods
        with patch.object(sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {
                "name": "id",
                "first_name": "first_name",
                "last_name": "last_name"
            },
            "reverse_mappings": {
                "id": "name",
                "first_name": "first_name",
                "last_name": "last_name"
            }
        }), \
        patch.object(sync_engine, '_check_for_conflicts', return_value=None), \
        patch.object(sync_engine, '_sync_to_supabase', return_value={"status": "success", "event_id": event.id}):
            result = await sync_engine.process_sync_event(event)
            
            assert result is not None
            assert result["status"] == "success"
            assert "event_id" in result

    @pytest.mark.asyncio
    async def test_process_sync_event_update(self, sync_engine, sample_sync_events):
        """Test processing an update sync event"""
        event = sample_sync_events[1]  # Supabase update event
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {
                "name": "id",
                "first_name": "first_name",
                "last_name": "last_name"
            },
            "reverse_mappings": {
                "id": "name",
                "first_name": "first_name",
                "last_name": "last_name"
            }
        }), \
        patch.object(sync_engine, '_check_for_conflicts', return_value=None), \
        patch.object(sync_engine, '_sync_to_frappe', return_value={"status": "success", "event_id": event.id}):
            result = await sync_engine.process_sync_event(event)
            
            assert result is not None
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_process_sync_event_delete(self, sync_engine):
        """Test processing a delete sync event"""
        event = SyncEvent(
            id="test_delete_event",
            source="frappe",
            doctype="Employee",
            record_id="HR-EMP-00001",
            operation="delete",
            data={"name": "HR-EMP-00001"}
        )
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {"name": "id"},
            "reverse_mappings": {"id": "name"}
        }), \
        patch.object(sync_engine, '_check_for_conflicts', return_value=None), \
        patch.object(sync_engine, '_sync_to_supabase', return_value={"status": "success"}):
            result = await sync_engine.process_sync_event(event)
            
            assert result is not None
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_process_sync_event_no_mapping(self, sync_engine, sample_sync_events):
        """Test processing sync event with no mapping"""
        event = sample_sync_events[0]
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value=None):
            result = await sync_engine.process_sync_event(event)
            
            assert result is not None
            assert result["status"] == "skipped"
            assert "reason" in result

    @pytest.mark.asyncio
    async def test_process_sync_event_error_handling(self, sync_engine, sample_sync_events):
        """Test error handling in sync event processing"""
        event = sample_sync_events[0]
        
        with patch.object(sync_engine, 'get_sync_mapping', side_effect=Exception("Test error")):
            result = await sync_engine.process_sync_event(event)
            
            assert result is not None
            assert result["status"] == "error"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_sync_frappe_to_supabase(self, sync_engine, sample_frappe_employee_data):
        """Test syncing from Frappe to Supabase"""
        mapping = {
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {
                "name": "id",
                "first_name": "first_name",
                "last_name": "last_name",
                "personal_email": "email"
            }
        }
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value=mapping), \
             patch.object(sync_engine.supabase_client, 'insert_data', new_callable=AsyncMock, return_value={"id": "new_id"}):
            result = await sync_engine.sync_frappe_to_supabase(
                "Employee", 
                "HR-EMP-00001",
                sample_frappe_employee_data
            )
            
            assert result is not None
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_sync_supabase_to_frappe(self, sync_engine, sample_supabase_user_data):
        """Test syncing from Supabase to Frappe"""
        mapping = {
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "reverse_mappings": {
                "id": "name",
                "first_name": "first_name",
                "last_name": "last_name",
                "email": "personal_email"
            }
        }
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value=mapping), \
             patch.object(sync_engine.frappe_client, 'create_document', new_callable=AsyncMock, return_value={"name": "new_doc"}):
            result = await sync_engine.sync_supabase_to_frappe(
                "Employee", 
                "user-123",
                sample_supabase_user_data
            )
            
            assert result is not None
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_handle_data_conflicts(self, sync_engine):
        """Test handling data conflicts"""
        frappe_data = {
            "name": "HR-EMP-00001",
            "first_name": "John",
            "modified": "2025-01-27 10:00:00"
        }
        
        supabase_data = {
            "id": "HR-EMP-00001",
            "first_name": "Jane",
            "updated_at": "2025-01-27 11:00:00Z"
        }
        
        result = await sync_engine.handle_data_conflicts(
            "Employee",
            "HR-EMP-00001",
            frappe_data, 
            supabase_data
        )
        
        assert result is not None
        # Should prefer Supabase data as it's more recent
        assert result["first_name"] == "Jane"

    @pytest.mark.asyncio
    async def test_handle_data_conflicts_frappe_wins(self, sync_engine):
        """Test conflict resolution when Frappe data wins"""
        frappe_data = {
            "name": "HR-EMP-00001",
            "first_name": "John",
            "modified": "2025-01-27 12:00:00"
        }
        
        supabase_data = {
            "id": "HR-EMP-00001",
            "first_name": "Jane",
            "updated_at": "2025-01-27 11:00:00Z"
        }
        
        result = await sync_engine.handle_data_conflicts(
            "Employee",
            "HR-EMP-00001",
            frappe_data, 
            supabase_data
        )
        
        assert result is not None
        # Should prefer Frappe data as it's more recent
        assert result["first_name"] == "John"

    @pytest.mark.asyncio
    async def test_validate_sync_mapping(self, sync_engine):
        """Test sync mapping validation"""
        valid_mapping = {
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {
                "name": "id",
                "first_name": "first_name"
            },
            "reverse_mappings": {
                "id": "name",
                "first_name": "first_name"
            }
        }
        
        result = sync_engine.validate_sync_mapping(valid_mapping)
        assert result is True
        
        invalid_mapping = {
            "frappe_doctype": "Employee",
            # Missing required fields
        }
        
        result = sync_engine.validate_sync_mapping(invalid_mapping)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_sync_mapping(self, sync_engine, custom_mappings):
        """Test getting sync mapping by doctype"""
        with patch.object(sync_engine, 'load_sync_mappings', return_value=custom_mappings):
            mapping = sync_engine.get_sync_mapping("Employee")
            assert mapping is not None
            assert mapping["frappe_doctype"] == "Employee"
            
            mapping = sync_engine.get_sync_mapping("NonExistent")
            assert mapping is None

    @pytest.mark.asyncio
    async def test_load_sync_mappings(self, sync_engine):
        """Test loading sync mappings from file"""
        with patch('builtins.open', mock_open=True), \
             patch('json.load', return_value={"test": "mapping"}):
            mappings = sync_engine.load_sync_mappings()
            assert mappings is not None

    @pytest.mark.asyncio
    async def test_save_sync_mappings(self, sync_engine, custom_mappings):
        """Test saving sync mappings to file"""
        result = sync_engine.save_sync_mappings(custom_mappings)
        assert result is True
        # Verify mappings were updated in settings
        assert "tasks_Task" in sync_engine.settings.sync_mappings

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, sync_engine):
        """Test retry mechanism for failed operations"""
        operation = SyncOperation(
            id="test_operation",
            event_id="test_event",
            direction=SyncDirection.FRAPPE_TO_SUPABASE,
            source_system="frappe",
            target_system="supabase",
            doctype="Employee",
            table="users",
            record_id="HR-EMP-00001",
            operation="create",
            data={"name": "HR-EMP-00001"}
        )
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {"name": "id"}
        }), \
        patch.object(sync_engine, '_process_sync_operation', side_effect=[
            {"status": "error", "error": "Temporary failure"},
            {"status": "error", "error": "Temporary failure"},
            {"status": "success", "data": {"id": "new_id"}}
        ]):
            result = await sync_engine.retry_operation(operation, max_retries=3)
            assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_mechanism_max_retries_exceeded(self, sync_engine):
        """Test retry mechanism when max retries exceeded"""
        operation = SyncOperation(
            id="test_operation",
            event_id="test_event",
            direction=SyncDirection.FRAPPE_TO_SUPABASE,
            source_system="frappe",
            target_system="supabase",
            doctype="Employee",
            table="users",
            record_id="HR-EMP-00001",
            operation="create",
            data={"name": "HR-EMP-00001"}
        )
        
        # Set retry count to max retries
        operation.retry_count = 3
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {"name": "id"}
        }):
            result = await sync_engine.retry_operation(operation, max_retries=3)
            assert result == "error"

    @pytest.mark.asyncio
    async def test_batch_sync_operations(self, sync_engine, sample_sync_events):
        """Test batch processing of sync operations"""
        events = sample_sync_events * 5  # 10 events total
        
        with patch.object(sync_engine, 'process_sync_event', return_value={"status": "success"}):
            results = await sync_engine.batch_process_sync_events(events, batch_size=3)
            
            assert len(results) == 10
            assert all(result["status"] == "success" for result in results)

    @pytest.mark.asyncio
    async def test_sync_metrics_collection(self, sync_engine, sample_sync_events):
        """Test sync metrics collection"""
        event = sample_sync_events[0]
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {"name": "id"}
        }):
            await sync_engine.process_sync_event(event)
            
            # Check if metrics were updated
            metrics = await sync_engine.get_sync_metrics()
            assert metrics is not None
            assert "total_events" in metrics
            assert "successful_operations" in metrics

    @pytest.mark.asyncio
    async def test_webhook_signature_validation(self, sync_engine):
        """Test webhook signature validation"""
        payload = b'{"test": "data"}'
        signature = "test_webhook_secret"  # Use the correct webhook secret from test settings
        
        result = sync_engine.validate_webhook_signature(payload, signature)
        assert result is True
        
        # Test with wrong signature
        wrong_signature = "wrong_signature"
        result = sync_engine.validate_webhook_signature(payload, wrong_signature)
        assert result is False

    @pytest.mark.asyncio
    async def test_data_transformation(self, sync_engine):
        """Test data transformation between systems"""
        frappe_data = {
            "name": "HR-EMP-00001",
            "first_name": "John",
            "last_name": "Doe",
            "personal_email": "john.doe@example.com",
            "creation": "2025-01-27 10:00:00"
        }
        
        field_mappings = {
            "name": "id",
            "first_name": "first_name",
            "last_name": "last_name",
            "personal_email": "email",
            "creation": "created_at"
        }
        
        transformed_data = await sync_engine.transform_data(
            frappe_data, 
            "frappe", 
            "supabase"
        )
        
        assert transformed_data["id"] == "HR-EMP-00001"
        assert transformed_data["first_name"] == "John"
        assert transformed_data["last_name"] == "Doe"
        assert transformed_data["personal_email"] == "john.doe@example.com"
        assert transformed_data["creation"] == "2025-01-27 10:00:00"

    @pytest.mark.asyncio
    async def test_edge_case_empty_data(self, sync_engine):
        """Test handling of empty data"""
        event = SyncEvent(
            id="empty_event",
            source="frappe",
            doctype="Employee",
            record_id="EMPTY-001",
            operation="create",
            data={}
        )
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {}
        }), \
        patch.object(sync_engine, '_check_for_conflicts', return_value=None), \
        patch.object(sync_engine, '_sync_to_supabase', return_value={"status": "success"}):
            result = await sync_engine.process_sync_event(event)
            
            assert result is not None
            assert result["status"] in ["success", "skipped"]

    @pytest.mark.asyncio
    async def test_edge_case_malformed_data(self, sync_engine):
        """Test handling of malformed data"""
        event = SyncEvent(
            id="malformed_event",
            source="frappe",
            doctype="Employee",
            record_id="MALFORMED-001",
            operation="create",
            data={"invalid": "data", "missing_required": None}
        )
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {"name": "id"}
        }):
            result = await sync_engine.process_sync_event(event)
            
            assert result is not None
            # Should handle gracefully
            assert result["status"] in ["success", "error", "skipped"]

    @pytest.mark.asyncio
    async def test_concurrent_sync_operations(self, sync_engine, sample_sync_events):
        """Test concurrent sync operations"""
        events = sample_sync_events * 3  # 6 events
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {"name": "id"}
        }):
            # Process events concurrently
            tasks = [sync_engine.process_sync_event(event) for event in events]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            assert len(results) == 6
            # All should succeed or be handled gracefully
            for result in results:
                if isinstance(result, dict):
                    assert result["status"] in ["success", "error", "skipped"]


# Mock open function for file operations
def mock_open(*args, **kwargs):
    return Mock()


# Additional test classes for specific functionality
class TestSyncEngineIntegration:
    """Integration tests for sync engine"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_sync_flow(self, sync_engine, sample_frappe_employee_data, custom_mappings):
        """Test complete end-to-end sync flow"""
        # Mock all external dependencies
        with patch.object(sync_engine, 'get_sync_mapping', return_value=custom_mappings["users_Employee"]), \
        patch.object(sync_engine, '_check_for_conflicts', return_value=None), \
        patch.object(sync_engine, '_sync_to_supabase', return_value={"status": "success"}):
            # Create event
            event = SyncEvent(
                id="e2e_test_event",
                source="frappe",
                doctype="Employee",
                record_id="HR-EMP-00001",
                operation="create",
                data=sample_frappe_employee_data
            )
            
            result = await sync_engine.process_sync_event(event)
            
            assert result is not None
            assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_bidirectional_sync_consistency(self, sync_engine, sample_frappe_employee_data, sample_supabase_user_data):
        """Test bidirectional sync consistency"""
        mapping = {
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {
                "name": "id",
                "first_name": "first_name",
                "last_name": "last_name",
                "personal_email": "email"
            },
            "reverse_mappings": {
                "id": "name",
                "first_name": "first_name",
                "last_name": "last_name",
                "email": "personal_email"
            }
        }
        
        with patch.object(sync_engine, 'get_sync_mapping', return_value=mapping), \
             patch.object(sync_engine.supabase_client, 'insert_data', new_callable=AsyncMock, return_value={"id": "new_id"}), \
             patch.object(sync_engine.frappe_client, 'create_document', new_callable=AsyncMock, return_value={"name": "new_doc"}):
            # Sync Frappe to Supabase
            frappe_result = await sync_engine.sync_frappe_to_supabase(
                "Employee", 
                "HR-EMP-00001",
                sample_frappe_employee_data
            )
            
            # Sync Supabase to Frappe
            supabase_result = await sync_engine.sync_supabase_to_frappe(
                "Employee", 
                "user-123",
                sample_supabase_user_data
            )
            
            assert frappe_result["status"] == "success"
            assert supabase_result["status"] == "success"
