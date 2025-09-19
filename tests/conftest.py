"""
Pytest configuration and fixtures for the sync engine tests
"""
import pytest
import asyncio
import json
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Add the src directory to the path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.config import Settings
from src.models import SyncEvent, SyncOperation, FrappeWebhookPayload, SupabaseWebhookPayload
from src.engine.sync_engine import SyncEngine
from src.handlers.frappe_webhook import FrappeWebhookHandler
from src.handlers.supabase_webhook import SupabaseWebhookHandler
from src.mapping.field_mapper import FieldMapper
from src.mapping.complex_mapper import ComplexMapper
from src.discovery.schema_discovery import SchemaDiscovery


@pytest.fixture
def test_settings():
    """Test settings configuration"""
    return Settings(
        frappe_url="http://test-frappe.com",
        frappe_api_key="test_key",
        frappe_api_secret="test_secret",
        supabase_url="https://test-supabase.com",
        supabase_anon_key="test_anon_key",
        supabase_service_role_key="test_service_key",
        webhook_secret="test_webhook_secret",
        frappe_webhook_token="HAPPY",
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/1",  # Use different DB for tests
        sync_batch_size=10,
        sync_retry_attempts=2,
        sync_retry_delay=1,
        conflict_resolution_strategy="last_modified_wins",
        log_level="DEBUG",
        enable_metrics=False
    )


@pytest.fixture
def sample_frappe_employee_data():
    """Sample Frappe Employee data"""
    return {
        "name": "HR-EMP-00001",
        "first_name": "John",
        "last_name": "Doe",
        "employee": "HR-EMP-00001",
        "cell_number": "+1234567890",
        "personal_email": "john.doe@personal.com",
        "company_email": "john.doe@company.com",
        "preferred_contact_email": "john.doe@preferred.com",
        "company": "Test Company",
        "status": "Active",
        "designation": "Software Engineer",
        "department": "Engineering",
        "user_id": "admin",
        "creation": "2025-01-27 10:00:00",
        "modified": "2025-01-27 10:00:00"
    }


@pytest.fixture
def sample_frappe_task_data():
    """Sample Frappe Task data"""
    return {
        "name": "TASK-2025-0001",
        "subject": "Implement new feature",
        "status": "Open",
        "project": "PROJ-001",
        "act_start_date": "2025-01-27",
        "act_end_date": "2025-01-30",
        "type": "Development",
        "description": "Implement the new authentication feature",
        "progress": 0,
        "is_milestone": False,
        "creation": "2025-01-27 10:00:00",
        "modified": "2025-01-27 10:00:00",
        "owner": "admin",
        "_assign": ["user1", "user2"]
    }


@pytest.fixture
def sample_supabase_user_data():
    """Sample Supabase user data"""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "first_name": "John",
        "last_name": "Doe",
        "name": "john.doe",
        "phone_number": "+1234567890",
        "email": "john.doe@example.com",
        "organization": "Test Organization",
        "verified": True,
        "designation": "Software Engineer",
        "department": "Engineering",
        "created_by": "550e8400-e29b-41d4-a716-446655440001",
        "created_at": "2025-01-27T10:00:00Z",
        "updated_at": "2025-01-27T10:00:00Z"
    }


@pytest.fixture
def sample_supabase_task_data():
    """Sample Supabase task data"""
    return {
        "id": 1,
        "task_name": "Implement new feature",
        "status": "Open",
        "project": 1,
        "start_date": "2025-01-27T00:00:00Z",
        "end_date": "2025-01-30T00:00:00Z",
        "task_category": ["Development"],
        "page_content": "Implement the new authentication feature",
        "progress": 0,
        "needs_submission": False,
        "created_at": "2025-01-27T10:00:00Z",
        "updated_at": "2025-01-27T10:00:00Z",
        "created_by": "550e8400-e29b-41d4-a716-446655440001",
        "assigned_to": ["550e8400-e29b-41d4-a716-446655440002", "550e8400-e29b-41d4-a716-446655440003"]
    }


@pytest.fixture
def custom_mappings():
    """Load custom mappings from file"""
    mapping_file = os.path.join(os.path.dirname(__file__), '..', 'custom_mappings.json')
    with open(mapping_file, 'r') as f:
        return json.load(f)


@pytest.fixture
def mock_frappe_client():
    """Mock Frappe client"""
    client = Mock()
    client.get_doctype_meta = AsyncMock(return_value={
        "fields": [
            {"fieldname": "name", "fieldtype": "Data"},
            {"fieldname": "first_name", "fieldtype": "Data"},
            {"fieldname": "last_name", "fieldtype": "Data"},
            {"fieldname": "email", "fieldtype": "Data"},
            {"fieldname": "status", "fieldtype": "Select"},
            {"fieldname": "creation", "fieldtype": "Datetime"},
            {"fieldname": "modified", "fieldtype": "Datetime"}
        ],
        "module": "HR",
        "total_fields": 7
    })
    client.get_list = AsyncMock(return_value=[])
    client.get_doc = AsyncMock(return_value={})
    client.insert = AsyncMock(return_value={"name": "TEST-001"})
    client.update = AsyncMock(return_value={"name": "TEST-001"})
    client.delete = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    client = Mock()
    client.table.return_value.select.return_value.execute.return_value = Mock(data=[])
    client.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": 1}])
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(data=[{"id": 1}])
    client.table.return_value.delete.return_value.eq.return_value.execute.return_value = Mock(data=[])
    client.rpc.return_value.execute.return_value = Mock(data=[])
    return client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    client = Mock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=True)
    client.exists = AsyncMock(return_value=False)
    client.lpush = AsyncMock(return_value=1)
    client.rpop = AsyncMock(return_value=None)
    client.llen = AsyncMock(return_value=0)
    return client


@pytest.fixture
def sync_engine(test_settings, mock_frappe_client, mock_supabase_client, mock_redis_client):
    """Sync engine with mocked dependencies"""
    with patch('src.engine.sync_engine.FrappeClient', return_value=mock_frappe_client), \
         patch('src.engine.sync_engine.SupabaseClient', return_value=mock_supabase_client), \
         patch('src.engine.sync_engine.Redis', return_value=mock_redis_client):
        return SyncEngine()


@pytest.fixture
def frappe_webhook_handler(sync_engine):
    """Frappe webhook handler"""
    return FrappeWebhookHandler()


@pytest.fixture
def supabase_webhook_handler(sync_engine):
    """Supabase webhook handler"""
    return SupabaseWebhookHandler()


@pytest.fixture
def field_mapper():
    """Field mapper instance"""
    return FieldMapper()


@pytest.fixture
def complex_mapper():
    """Complex mapper instance"""
    return ComplexMapper()


@pytest.fixture
def schema_discovery(test_settings, mock_frappe_client, mock_supabase_client):
    """Schema discovery with mocked clients"""
    with patch('src.discovery.schema_discovery.FrappeClient', return_value=mock_frappe_client), \
         patch('src.discovery.schema_discovery.SupabaseClient', return_value=mock_supabase_client):
        return SchemaDiscovery()


@pytest.fixture
def sample_sync_events():
    """Sample sync events for testing"""
    return [
        SyncEvent(
            id="test_event_1",
            source="frappe",
            doctype="Employee",
            record_id="HR-EMP-00001",
            operation="create",
            data={"name": "HR-EMP-00001", "first_name": "John"},
            webhook_id="test_webhook_1"
        ),
        SyncEvent(
            id="test_event_2",
            source="supabase",
            doctype="Employee",
            record_id="550e8400-e29b-41d4-a716-446655440000",
            operation="update",
            data={"id": "550e8400-e29b-41d4-a716-446655440000", "first_name": "Jane"},
            webhook_id="test_webhook_2"
        )
    ]


@pytest.fixture
def sample_webhook_payloads():
    """Sample webhook payloads"""
    return {
        "frappe_employee_insert": {
            "doctype": "Employee",
            "name": "HR-EMP-00001",
            "operation": "after_insert",
            "doc": {
                "name": "HR-EMP-00001",
                "first_name": "John",
                "last_name": "Doe",
                "personal_email": "john.doe@example.com"
            }
        },
        "supabase_user_insert": {
            "table": "users",
            "operation": "INSERT",
            "record": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com"
            }
        }
    }


# Async test support
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test data factories
class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_frappe_employee(**kwargs):
        """Create Frappe employee data with defaults"""
        defaults = {
            "name": "HR-EMP-00001",
            "first_name": "John",
            "last_name": "Doe",
            "personal_email": "john.doe@example.com",
            "status": "Active",
            "creation": "2025-01-27 10:00:00",
            "modified": "2025-01-27 10:00:00"
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_supabase_user(**kwargs):
        """Create Supabase user data with defaults"""
        defaults = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "verified": True,
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z"
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_sync_event(**kwargs):
        """Create sync event with defaults"""
        defaults = {
            "id": "test_event_1",
            "source": "frappe",
            "doctype": "Employee",
            "record_id": "HR-EMP-00001",
            "operation": "create",
            "data": {"name": "HR-EMP-00001"},
            "webhook_id": "test_webhook_1"
        }
        defaults.update(kwargs)
        return SyncEvent(**defaults)


@pytest.fixture
def data_factory():
    """Test data factory fixture"""
    return TestDataFactory()
