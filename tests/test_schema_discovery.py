"""
Tests for schema discovery functionality
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.discovery.schema_discovery import SchemaDiscovery


class TestSchemaDiscovery:
    """Test cases for SchemaDiscovery class"""

    @pytest.fixture
    def schema_discovery(self):
        """Schema discovery instance"""
        return SchemaDiscovery()

    @pytest.mark.asyncio
    async def test_discover_frappe_doctypes(self, schema_discovery):
        """Test discovering Frappe doctypes"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "docs": [
                    {
                        "name": "Employee",
                        "fields": [
                            {"fieldname": "name", "fieldtype": "Data"},
                            {"fieldname": "first_name", "fieldtype": "Data"}
                        ]
                    }
                ]
            }
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            doctypes = await schema_discovery.discover_frappe_doctypes()

            assert len(doctypes) == 1
            assert "Employee" in doctypes

    @pytest.mark.asyncio
    async def test_discover_supabase_tables(self, schema_discovery):
        """Test discovering Supabase tables"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = [
                {
                    "table_name": "employees",
                    "columns": [
                        {"column_name": "id", "data_type": "uuid"},
                        {"column_name": "first_name", "data_type": "text"}
                    ]
                }
            ]
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            tables = await schema_discovery.discover_supabase_tables()

            assert len(tables) == 1
            assert "employees" in tables

    @pytest.mark.asyncio
    async def test_discover_event_related_doctypes(self, schema_discovery):
        """Test discovering event-related doctypes"""
        with patch.object(schema_discovery, 'discover_frappe_doctypes') as mock_frappe, \
             patch.object(schema_discovery, 'discover_supabase_tables') as mock_supabase:
            
            mock_frappe.return_value = {
                "Training Event": {
                    "name": "Training Event",
                    "fields": [{"fieldname": "name", "fieldtype": "Data"}]
                }
            }
            
            mock_supabase.return_value = {
                "training_events": {
                    "table_name": "training_events",
                    "columns": [{"column_name": "id", "data_type": "uuid"}]
                }
            }

            event_doctypes = await schema_discovery.discover_event_related_doctypes()

            assert "Training Event" in event_doctypes["frappe"]
            assert "training_events" in event_doctypes["supabase"]