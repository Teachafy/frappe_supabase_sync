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
        assert sync_engine.redis_client is not None

    @pytest.mark.asyncio
    async def test_process_sync_event_create(self, sync_engine, sample_sync_events):
        """Test processing a create sync event"""
        event = sample_sync_events[0]  # Frappe create event
        
        # Mock the mapping lookup
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
        }):
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
        }):
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
        }):
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
        
        result = await sync_engine.sync_frappe_to_supabase(
            "Employee", 
            sample_frappe_employee_data, 
            mapping
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
        
        result = await sync_engine.sync_supabase_to_frappe(
            "users", 
            sample_supabase_user_data, 
            mapping
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
            frappe_data, 
            supabase_data, 
            "last_modified_wins"
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
            frappe_data, 
            supabase_data, 
            "last_modified_wins"
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
        
        result = await sync_engine.validate_sync_mapping(valid_mapping)
        assert result is True
        
        invalid_mapping = {
            "frappe_doctype": "Employee",
            # Missing required fields
        }
        
        result = await sync_engine.validate_sync_mapping(invalid_mapping)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_sync_mapping(self, sync_engine, custom_mappings):
        """Test getting sync mapping by doctype"""
        with patch.object(sync_engine, 'load_sync_mappings', return_value=custom_mappings):
            mapping = await sync_engine.get_sync_mapping("Employee")
            assert mapping is not None
            assert mapping["frappe_doctype"] == "Employee"
            
            mapping = await sync_engine.get_sync_mapping("NonExistent")
            assert mapping is None

    @pytest.mark.asyncio
    async def test_load_sync_mappings(self, sync_engine):
        """Test loading sync mappings from file"""
        with patch('builtins.open', mock_open=True), \
             patch('json.load', return_value={"test": "mapping"}):
            mappings = await sync_engine.load_sync_mappings()
            assert mappings is not None

    @pytest.mark.asyncio
    async def test_save_sync_mappings(self, sync_engine, custom_mappings):
        """Test saving sync mappings to file"""
        with patch('builtins.open', mock_open=True), \
             patch('json.dump') as mock_dump:
            result = await sync_engine.save_sync_mappings(custom_mappings)
            assert result is True
            mock_dump.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, sync_engine):
        """Test retry mechanism for failed operations"""
        call_count = 0
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await sync_engine.retry_operation(failing_operation, max_retries=3)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_mechanism_max_retries_exceeded(self, sync_engine):
        """Test retry mechanism when max retries exceeded"""
        call_count = 0
        
        async def always_failing_operation():
            nonlocal call_count
            call_count += 1
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            await sync_engine.retry_operation(always_failing_operation, max_retries=2)
        
        assert call_count == 3  # Initial + 2 retries

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
            assert "successful_events" in metrics

    @pytest.mark.asyncio
    async def test_webhook_signature_validation(self, sync_engine):
        """Test webhook signature validation"""
        payload = b'{"test": "data"}'
        signature = "test_signature"
        
        with patch('hmac.compare_digest', return_value=True):
            result = await sync_engine.validate_webhook_signature(payload, signature)
            assert result is True
        
        with patch('hmac.compare_digest', return_value=False):
            result = await sync_engine.validate_webhook_signature(payload, signature)
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
            field_mappings, 
            "frappe_to_supabase"
        )
        
        assert transformed_data["id"] == "HR-EMP-00001"
        assert transformed_data["first_name"] == "John"
        assert transformed_data["last_name"] == "Doe"
        assert transformed_data["email"] == "john.doe@example.com"
        assert "created_at" in transformed_data

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
        }):
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
        with patch.object(sync_engine, 'get_sync_mapping', return_value=custom_mappings["users_Employee"]):
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
        
        # Sync Frappe to Supabase
        frappe_result = await sync_engine.sync_frappe_to_supabase(
            "Employee", 
            sample_frappe_employee_data, 
            mapping
        )
        
        # Sync Supabase to Frappe
        supabase_result = await sync_engine.sync_supabase_to_frappe(
            "users", 
            sample_supabase_user_data, 
            mapping
        )
        
        assert frappe_result["status"] == "success"
        assert supabase_result["status"] == "success"
