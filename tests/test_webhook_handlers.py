"""
Comprehensive tests for webhook handlers
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, HTTPException

from src.handlers.frappe_webhook import FrappeWebhookHandler
from src.handlers.supabase_webhook import SupabaseWebhookHandler
from src.models import FrappeWebhookPayload, SupabaseWebhookPayload


class TestFrappeWebhookHandler:
    """Test cases for FrappeWebhookHandler"""

    @pytest.mark.asyncio
    async def test_webhook_handler_initialization(self, frappe_webhook_handler):
        """Test webhook handler initialization"""
        assert frappe_webhook_handler is not None
        assert frappe_webhook_handler.sync_engine is not None

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_valid(self, frappe_webhook_handler):
        """Test valid webhook signature verification"""
        request = Mock()
        request.headers = {"X-Frappe-Signature": "valid_signature"}
        payload = b'{"test": "data"}'
        
        with patch('hmac.compare_digest', return_value=True):
            result = frappe_webhook_handler.verify_webhook_signature(request, payload)
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_invalid(self, frappe_webhook_handler):
        """Test invalid webhook signature verification"""
        request = Mock()
        request.headers = {"X-Frappe-Signature": "invalid_signature"}
        payload = b'{"test": "data"}'
        
        with patch('hmac.compare_digest', return_value=False):
            result = frappe_webhook_handler.verify_webhook_signature(request, payload)
            assert result is False

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_missing(self, frappe_webhook_handler):
        """Test webhook signature verification with missing signature"""
        request = Mock()
        request.headers = {}
        payload = b'{"test": "data"}'
        
        result = frappe_webhook_handler.verify_webhook_signature(request, payload)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_webhook_success(self, frappe_webhook_handler, sample_webhook_payloads):
        """Test successful webhook processing"""
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.headers = {"X-Frappe-Signature": "valid_signature"}
        
        payload = sample_webhook_payloads["frappe_employee_insert"]
        
        with patch.object(frappe_webhook_handler, 'verify_webhook_signature', return_value=True), \
             patch.object(frappe_webhook_handler.sync_engine, 'process_sync_event', 
                         return_value={"status": "success", "event_id": "test_event"}):
            
            result = await frappe_webhook_handler.process_webhook(request, payload)
            
            assert result is not None
            assert result["status"] == "success"
            assert "event_id" in result

    @pytest.mark.asyncio
    async def test_process_webhook_invalid_signature(self, frappe_webhook_handler, sample_webhook_payloads):
        """Test webhook processing with invalid signature"""
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.headers = {"X-Frappe-Signature": "invalid_signature"}
        
        payload = sample_webhook_payloads["frappe_employee_insert"]
        
        with patch.object(frappe_webhook_handler, 'verify_webhook_signature', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await frappe_webhook_handler.process_webhook(request, payload)
            
            assert exc_info.value.status_code == 401
            assert "Invalid webhook signature" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_process_webhook_doctype_not_configured(self, frappe_webhook_handler, sample_webhook_payloads):
        """Test webhook processing for unconfigured doctype"""
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.headers = {"X-Frappe-Signature": "valid_signature"}
        
        payload = sample_webhook_payloads["frappe_employee_insert"]
        
        with patch.object(frappe_webhook_handler, 'verify_webhook_signature', return_value=True), \
             patch.object(frappe_webhook_handler.sync_engine, 'get_sync_mapping', return_value=None):
            
            result = await frappe_webhook_handler.process_webhook(request, payload)
            
            assert result is not None
            assert result["status"] == "skipped"
            assert result["reason"] == "doctype_not_configured"

    @pytest.mark.asyncio
    async def test_process_webhook_error_handling(self, frappe_webhook_handler, sample_webhook_payloads):
        """Test webhook processing error handling"""
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.headers = {"X-Frappe-Signature": "valid_signature"}
        
        payload = sample_webhook_payloads["frappe_employee_insert"]
        
        with patch.object(frappe_webhook_handler, 'verify_webhook_signature', return_value=True), \
             patch.object(frappe_webhook_handler.sync_engine, 'process_sync_event', 
                         side_effect=Exception("Test error")):
            
            with pytest.raises(HTTPException) as exc_info:
                await frappe_webhook_handler.process_webhook(request, payload)
            
            assert exc_info.value.status_code == 500
            assert "Webhook processing failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_document_created(self, frappe_webhook_handler):
        """Test handling document creation event"""
        doctype = "Employee"
        doc = {"name": "HR-EMP-00001", "first_name": "John"}
        
        with patch.object(frappe_webhook_handler.sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users"
        }), \
        patch.object(frappe_webhook_handler.sync_engine, 'process_sync_event', 
                    return_value={"status": "success"}):
            
            result = await frappe_webhook_handler.handle_document_created(doctype, doc)
            
            assert result is not None
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_handle_document_updated(self, frappe_webhook_handler):
        """Test handling document update event"""
        doctype = "Employee"
        doc = {"name": "HR-EMP-00001", "first_name": "Jane"}
        
        with patch.object(frappe_webhook_handler.sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users"
        }), \
        patch.object(frappe_webhook_handler.sync_engine, 'process_sync_event', 
                    return_value={"status": "success"}):
            
            result = await frappe_webhook_handler.handle_document_updated(doctype, doc)
            
            assert result is not None
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_handle_document_deleted(self, frappe_webhook_handler):
        """Test handling document deletion event"""
        doctype = "Employee"
        doc_name = "HR-EMP-00001"
        
        with patch.object(frappe_webhook_handler.sync_engine, 'get_sync_mapping', return_value={
            "frappe_doctype": "Employee",
            "supabase_table": "users"
        }), \
        patch.object(frappe_webhook_handler.sync_engine, 'process_sync_event', 
                    return_value={"status": "success"}):
            
            result = await frappe_webhook_handler.handle_document_deleted(doctype, doc_name)
            
            assert result is not None
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_map_frappe_operation(self, frappe_webhook_handler):
        """Test Frappe operation mapping"""
        assert frappe_webhook_handler._map_frappe_operation("after_insert") == "create"
        assert frappe_webhook_handler._map_frappe_operation("after_update") == "update"
        assert frappe_webhook_handler._map_frappe_operation("after_delete") == "delete"
        assert frappe_webhook_handler._map_frappe_operation("unknown") == "update"  # default

    @pytest.mark.asyncio
    async def test_webhook_payload_validation(self, frappe_webhook_handler):
        """Test webhook payload validation"""
        # Valid payload
        valid_payload = {
            "doctype": "Employee",
            "name": "HR-EMP-00001",
            "operation": "after_insert",
            "doc": {"name": "HR-EMP-00001", "first_name": "John"}
        }
        
        try:
            FrappeWebhookPayload(**valid_payload)
            assert True
        except Exception:
            assert False, "Valid payload should not raise exception"
        
        # Invalid payload (missing required fields)
        invalid_payload = {
            "doctype": "Employee",
            # Missing name, operation, doc
        }
        
        with pytest.raises(Exception):
            FrappeWebhookPayload(**invalid_payload)


class TestSupabaseWebhookHandler:
    """Test cases for SupabaseWebhookHandler"""

    @pytest.mark.asyncio
    async def test_webhook_handler_initialization(self, supabase_webhook_handler):
        """Test webhook handler initialization"""
        assert supabase_webhook_handler is not None
        assert supabase_webhook_handler.sync_engine is not None

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_valid(self, supabase_webhook_handler):
        """Test valid webhook signature verification"""
        request = Mock()
        request.headers = {"X-Supabase-Signature": "valid_signature"}
        payload = b'{"test": "data"}'
        
        with patch('hmac.compare_digest', return_value=True):
            result = supabase_webhook_handler.verify_webhook_signature(request, payload)
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_invalid(self, supabase_webhook_handler):
        """Test invalid webhook signature verification"""
        request = Mock()
        request.headers = {"X-Supabase-Signature": "invalid_signature"}
        payload = b'{"test": "data"}'
        
        with patch('hmac.compare_digest', return_value=False):
            result = supabase_webhook_handler.verify_webhook_signature(request, payload)
            assert result is False

    @pytest.mark.asyncio
    async def test_process_webhook_success(self, supabase_webhook_handler, sample_webhook_payloads):
        """Test successful webhook processing"""
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.headers = {"X-Supabase-Signature": "valid_signature"}
        
        payload = sample_webhook_payloads["supabase_user_insert"]
        
        with patch.object(supabase_webhook_handler, 'verify_webhook_signature', return_value=True), \
             patch.object(supabase_webhook_handler, '_find_mapping_by_table', return_value={
                 "frappe_doctype": "Employee",
                 "supabase_table": "users"
             }), \
             patch.object(supabase_webhook_handler.sync_engine, 'process_sync_event', 
                         return_value={"status": "success", "event_id": "test_event"}):
            
            result = await supabase_webhook_handler.process_webhook(request, payload)
            
            assert result is not None
            assert result["status"] == "success"
            assert "event_id" in result

    @pytest.mark.asyncio
    async def test_process_webhook_table_not_configured(self, supabase_webhook_handler, sample_webhook_payloads):
        """Test webhook processing for unconfigured table"""
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.headers = {"X-Supabase-Signature": "valid_signature"}
        
        payload = sample_webhook_payloads["supabase_user_insert"]
        
        with patch.object(supabase_webhook_handler, 'verify_webhook_signature', return_value=True), \
             patch.object(supabase_webhook_handler, '_find_mapping_by_table', return_value=None):
            
            result = await supabase_webhook_handler.process_webhook(request, payload)
            
            assert result is not None
            assert result["status"] == "skipped"
            assert result["reason"] == "table_not_configured"

    @pytest.mark.asyncio
    async def test_find_mapping_by_table(self, supabase_webhook_handler, custom_mappings):
        """Test finding mapping by table name"""
        with patch.object(supabase_webhook_handler.sync_engine, 'load_sync_mappings', 
                         return_value=custom_mappings):
            
            mapping = await supabase_webhook_handler._find_mapping_by_table("users")
            assert mapping is not None
            assert mapping["supabase_table"] == "users"
            
            mapping = await supabase_webhook_handler._find_mapping_by_table("nonexistent")
            assert mapping is None

    @pytest.mark.asyncio
    async def test_map_supabase_operation(self, supabase_webhook_handler):
        """Test Supabase operation mapping"""
        assert supabase_webhook_handler._map_supabase_operation("INSERT") == "create"
        assert supabase_webhook_handler._map_supabase_operation("UPDATE") == "update"
        assert supabase_webhook_handler._map_supabase_operation("DELETE") == "delete"
        assert supabase_webhook_handler._map_supabase_operation("unknown") == "update"  # default

    @pytest.mark.asyncio
    async def test_webhook_payload_validation(self, supabase_webhook_handler):
        """Test webhook payload validation"""
        # Valid payload
        valid_payload = {
            "table": "users",
            "operation": "INSERT",
            "record": {"id": "1", "name": "John"}
        }
        
        try:
            SupabaseWebhookPayload(**valid_payload)
            assert True
        except Exception:
            assert False, "Valid payload should not raise exception"
        
        # Invalid payload (missing required fields)
        invalid_payload = {
            "table": "users",
            # Missing operation, record
        }
        
        with pytest.raises(Exception):
            SupabaseWebhookPayload(**invalid_payload)


class TestWebhookIntegration:
    """Integration tests for webhook handlers"""

    @pytest.mark.asyncio
    async def test_frappe_webhook_end_to_end(self, frappe_webhook_handler, sample_webhook_payloads):
        """Test complete Frappe webhook flow"""
        request = Mock()
        request.body = AsyncMock(return_value=json.dumps(sample_webhook_payloads["frappe_employee_insert"]).encode())
        request.headers = {"X-Frappe-Signature": "valid_signature"}
        
        payload = sample_webhook_payloads["frappe_employee_insert"]
        
        with patch.object(frappe_webhook_handler, 'verify_webhook_signature', return_value=True), \
             patch.object(frappe_webhook_handler.sync_engine, 'get_sync_mapping', return_value={
                 "frappe_doctype": "Employee",
                 "supabase_table": "users",
                 "field_mappings": {"name": "id", "first_name": "first_name"}
             }), \
             patch.object(frappe_webhook_handler.sync_engine, 'process_sync_event', 
                         return_value={"status": "success", "event_id": "test_event"}):
            
            result = await frappe_webhook_handler.process_webhook(request, payload)
            
            assert result is not None
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_supabase_webhook_end_to_end(self, supabase_webhook_handler, sample_webhook_payloads):
        """Test complete Supabase webhook flow"""
        request = Mock()
        request.body = AsyncMock(return_value=json.dumps(sample_webhook_payloads["supabase_user_insert"]).encode())
        request.headers = {"X-Supabase-Signature": "valid_signature"}
        
        payload = sample_webhook_payloads["supabase_user_insert"]
        
        with patch.object(supabase_webhook_handler, 'verify_webhook_signature', return_value=True), \
             patch.object(supabase_webhook_handler, '_find_mapping_by_table', return_value={
                 "frappe_doctype": "Employee",
                 "supabase_table": "users",
                 "reverse_mappings": {"id": "name", "first_name": "first_name"}
             }), \
             patch.object(supabase_webhook_handler.sync_engine, 'process_sync_event', 
                         return_value={"status": "success", "event_id": "test_event"}):
            
            result = await supabase_webhook_handler.process_webhook(request, payload)
            
            assert result is not None
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_webhook_error_recovery(self, frappe_webhook_handler, sample_webhook_payloads):
        """Test webhook error recovery mechanisms"""
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.headers = {"X-Frappe-Signature": "valid_signature"}
        
        payload = sample_webhook_payloads["frappe_employee_insert"]
        
        # Test with temporary failure that recovers
        call_count = 0
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            return {"status": "success", "event_id": "test_event"}
        
        with patch.object(frappe_webhook_handler, 'verify_webhook_signature', return_value=True), \
             patch.object(frappe_webhook_handler.sync_engine, 'process_sync_event', 
                         side_effect=failing_then_success()):
            
            with pytest.raises(HTTPException):
                await frappe_webhook_handler.process_webhook(request, payload)

    @pytest.mark.asyncio
    async def test_webhook_rate_limiting(self, frappe_webhook_handler, sample_webhook_payloads):
        """Test webhook rate limiting"""
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.headers = {"X-Frappe-Signature": "valid_signature"}
        
        payload = sample_webhook_payloads["frappe_employee_insert"]
        
        # Simulate rate limiting by making process_sync_event take time
        async def slow_process_sync_event(event):
            await asyncio.sleep(0.1)  # Simulate processing time
            return {"status": "success", "event_id": "test_event"}
        
        with patch.object(frappe_webhook_handler, 'verify_webhook_signature', return_value=True), \
             patch.object(frappe_webhook_handler.sync_engine, 'process_sync_event', 
                         side_effect=slow_process_sync_event):
            
            # Process multiple webhooks concurrently
            tasks = [
                frappe_webhook_handler.process_webhook(request, payload)
                for _ in range(5)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete (rate limiting handled internally)
            assert len(results) == 5
