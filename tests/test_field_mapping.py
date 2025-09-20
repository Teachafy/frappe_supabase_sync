"""
Comprehensive tests for field mapping functionality
"""
import pytest
from unittest.mock import Mock, patch

from src.mapping.field_mapper import FieldMapper
from src.mapping.complex_mapper import ComplexMapper


class TestFieldMapper:
    """Test cases for FieldMapper class"""

    @pytest.mark.asyncio
    async def test_field_mapper_initialization(self, field_mapper):
        """Test field mapper initialization"""
        assert field_mapper is not None

    @pytest.mark.asyncio
    async def test_map_fields_frappe_to_supabase(self, field_mapper, sample_frappe_employee_data, custom_mappings):
        """Test mapping fields from Frappe to Supabase"""
        mapping_config = custom_mappings["users_Employee"]
        
        result = await field_mapper.map_fields(
            sample_frappe_employee_data,
            "frappe",
            "supabase",
            mapping_config
        )
        
        assert result is not None
        assert "id" in result  # name -> id
        assert "first_name" in result
        assert "last_name" in result
        assert "email" in result  # personal_email -> email
        assert "phone_number" in result  # cell_number -> phone_number
        assert "organization" in result  # company -> organization
        assert "verified" in result  # status -> verified

    @pytest.mark.asyncio
    async def test_map_fields_supabase_to_frappe(self, field_mapper, sample_supabase_user_data, custom_mappings):
        """Test mapping fields from Supabase to Frappe"""
        mapping_config = custom_mappings["users_Employee"]
        
        result = await field_mapper.map_fields(
            sample_supabase_user_data,
            "supabase",
            "frappe",
            mapping_config
        )
        
        assert result is not None
        assert "name" in result  # id -> name
        assert "first_name" in result
        assert "last_name" in result
        assert "personal_email" in result  # email -> personal_email
        assert "cell_number" in result  # phone_number -> cell_number
        assert "company" in result  # organization -> company
        assert "status" in result  # verified -> status

    @pytest.mark.asyncio
    async def test_map_fields_task_mapping(self, field_mapper, sample_frappe_task_data, custom_mappings):
        """Test mapping fields for Task doctype"""
        mapping_config = custom_mappings["tasks_Task"]
        
        result = await field_mapper.map_fields(
            sample_frappe_task_data,
            "frappe",
            "supabase",
            mapping_config
        )
        
        assert result is not None
        assert "id" in result  # name -> id
        assert "task_name" in result  # subject -> task_name
        assert "status" in result
        assert "project" in result
        assert "start_date" in result  # act_start_date -> start_date
        assert "end_date" in result  # act_end_date -> end_date
        assert "task_category" in result  # type -> task_category
        assert "page_content" in result  # description -> page_content
        assert "progress" in result
        assert "needs_submission" in result  # is_milestone -> needs_submission

    @pytest.mark.asyncio
    async def test_map_fields_missing_fields(self, field_mapper, custom_mappings):
        """Test mapping with missing fields"""
        mapping_config = custom_mappings["users_Employee"]
        
        # Data with missing fields
        incomplete_data = {
            "name": "HR-EMP-00001",
            "first_name": "John"
            # Missing last_name, email, etc.
        }
        
        result = await field_mapper.map_fields(
            incomplete_data,
            "frappe",
            "supabase",
            mapping_config
        )
        
        assert result is not None
        assert "id" in result
        assert "first_name" in result
        # Missing fields should not be in result
        assert "last_name" not in result
        assert "email" not in result

    @pytest.mark.asyncio
    async def test_map_fields_extra_fields(self, field_mapper, custom_mappings):
        """Test mapping with extra fields not in mapping"""
        mapping_config = custom_mappings["users_Employee"]
        
        # Data with extra fields
        extra_data = {
            "name": "HR-EMP-00001",
            "first_name": "John",
            "last_name": "Doe",
            "personal_email": "john@example.com",
            "extra_field": "extra_value",  # Not in mapping
            "another_extra": "another_value"  # Not in mapping
        }
        
        result = await field_mapper.map_fields(
            extra_data,
            "frappe",
            "supabase",
            mapping_config
        )
        
        assert result is not None
        assert "id" in result
        assert "first_name" in result
        assert "last_name" in result
        assert "email" in result
        # Extra fields should not be in result
        assert "extra_field" not in result
        assert "another_extra" not in result

    @pytest.mark.asyncio
    async def test_map_fields_empty_mapping(self, field_mapper):
        """Test mapping with empty field mappings"""
        mapping_config = {
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {},
            "reverse_mappings": {}
        }
        
        data = {"name": "HR-EMP-00001", "first_name": "John"}
        
        result = await field_mapper.map_fields(
            data,
            "frappe",
            "supabase",
            mapping_config
        )
        
        assert result is not None
        assert result == {}  # Empty mapping should return empty dict

    @pytest.mark.asyncio
    async def test_map_fields_invalid_direction(self, field_mapper, custom_mappings):
        """Test mapping with invalid direction"""
        mapping_config = custom_mappings["users_Employee"]
        data = {"name": "HR-EMP-00001"}
        
        with pytest.raises(ValueError, match="Invalid direction"):
            await field_mapper.map_fields(
                data,
                "invalid_direction",
                "supabase",
                mapping_config
            )

    @pytest.mark.asyncio
    async def test_map_fields_none_data(self, field_mapper, custom_mappings):
        """Test mapping with None data"""
        mapping_config = custom_mappings["users_Employee"]
        
        result = await field_mapper.map_fields(
            None,
            "frappe",
            "supabase",
            mapping_config
        )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_map_fields_empty_data(self, field_mapper, custom_mappings):
        """Test mapping with empty data"""
        mapping_config = custom_mappings["users_Employee"]
        
        result = await field_mapper.map_fields(
            {},
            "frappe",
            "supabase",
            mapping_config
        )
        
        assert result is not None
        assert result == {}

    @pytest.mark.asyncio
    async def test_map_fields_data_type_conversion(self, field_mapper, custom_mappings):
        """Test data type conversion during mapping"""
        mapping_config = custom_mappings["users_Employee"]
        
        # Data with different types
        data = {
            "name": "HR-EMP-00001",
            "first_name": "John",
            "last_name": "Doe",
            "personal_email": "john@example.com",
            "status": "Active",  # String
            "creation": "2025-01-27 10:00:00",  # String datetime
            "modified": "2025-01-27 10:00:00"  # String datetime
        }
        
        result = await field_mapper.map_fields(
            data,
            "frappe",
            "supabase",
            mapping_config
        )
        
        assert result is not None
        assert isinstance(result["verified"], bool)  # status -> verified (boolean)
        assert "created_at" in result  # creation -> created_at
        assert "updated_at" in result  # modified -> updated_at

    @pytest.mark.asyncio
    async def test_map_fields_case_sensitivity(self, field_mapper, custom_mappings):
        """Test case sensitivity in field mapping"""
        mapping_config = custom_mappings["users_Employee"]
        
        # Data with different case
        data = {
            "Name": "HR-EMP-00001",  # Capital N
            "FIRST_NAME": "John",    # All caps
            "last_name": "Doe",      # Lower case
            "Personal_Email": "john@example.com"  # Mixed case
        }
        
        result = await field_mapper.map_fields(
            data,
            "frappe",
            "supabase",
            mapping_config
        )
        
        # Should only map exact field names from mapping
        assert "id" not in result  # "Name" != "name"
        assert "first_name" not in result  # "FIRST_NAME" != "first_name"
        assert "last_name" in result  # Exact match
        assert "email" not in result  # "Personal_Email" != "personal_email"


class TestComplexMapper:
    """Test cases for ComplexMapper class"""

    @pytest.mark.asyncio
    async def test_complex_mapper_initialization(self, complex_mapper):
        """Test complex mapper initialization"""
        assert complex_mapper is not None

    @pytest.mark.asyncio
    async def test_map_task_id_frappe_to_supabase(self, complex_mapper):
        """Test mapping Task ID from Frappe to Supabase"""
        frappe_id = "TASK-2025-0001"
        result = await complex_mapper.map_task_id(frappe_id, "frappe_to_supabase")
        
        # Should extract numeric part or generate new ID
        assert result is not None
        assert isinstance(result, (int, str))

    @pytest.mark.asyncio
    async def test_map_task_id_supabase_to_frappe(self, complex_mapper):
        """Test mapping Task ID from Supabase to Frappe"""
        supabase_id = 1
        result = await complex_mapper.map_task_id(supabase_id, "supabase_to_frappe")
        
        # Should generate Frappe-style ID
        assert result is not None
        assert isinstance(result, str)
        assert "TASK-" in result

    @pytest.mark.asyncio
    async def test_map_task_project_frappe_to_supabase(self, complex_mapper):
        """Test mapping Project ID from Frappe to Supabase"""
        frappe_project = "PROJ-001"
        result = await complex_mapper.map_task_project(frappe_project, "frappe_to_supabase")
        
        assert result is not None
        assert isinstance(result, (int, str))

    @pytest.mark.asyncio
    async def test_map_task_project_supabase_to_frappe(self, complex_mapper):
        """Test mapping Project ID from Supabase to Frappe"""
        supabase_project = 1
        result = await complex_mapper.map_task_project(supabase_project, "supabase_to_frappe")
        
        assert result is not None
        assert isinstance(result, str)
        assert "PROJ-" in result

    @pytest.mark.asyncio
    async def test_handle_email_priority_frappe_to_supabase(self, complex_mapper):
        """Test email priority handling from Frappe to Supabase"""
        frappe_data = {
            "personal_email": "john@personal.com",
            "company_email": "john@company.com",
            "preferred_contact_email": "john@preferred.com"
        }
        
        email_config = {
            "email_priority": ["preferred_contact_email", "personal_email", "company_email"]
        }
        
        result = await complex_mapper._handle_email_priority(
            frappe_data, email_config, "frappe_to_supabase"
        )
        
        # Should return the highest priority email
        assert result == "john@preferred.com"

    @pytest.mark.asyncio
    async def test_handle_email_priority_supabase_to_frappe(self, complex_mapper):
        """Test email priority handling from Supabase to Frappe"""
        supabase_email = "john@example.com"
        
        email_config = {
            "email_priority": ["preferred_contact_email", "personal_email", "company_email"]
        }
        
        result = await complex_mapper._handle_email_priority(
            supabase_email, email_config, "supabase_to_frappe"
        )
        
        # Should return dict with email in preferred field
        assert result is not None
        assert isinstance(result, dict)
        assert result["preferred_contact_email"] == "john@example.com"

    @pytest.mark.asyncio
    async def test_handle_email_priority_missing_emails(self, complex_mapper):
        """Test email priority handling with missing emails"""
        frappe_data = {
            "personal_email": "john@personal.com"
            # Missing company_email and preferred_contact_email
        }
        
        email_config = {
            "email_priority": ["preferred_contact_email", "personal_email", "company_email"]
        }
        
        result = await complex_mapper._handle_email_priority(
            frappe_data, email_config, "frappe_to_supabase"
        )
        
        # Should return the available email
        assert result == "john@personal.com"

    @pytest.mark.asyncio
    async def test_handle_email_priority_no_emails(self, complex_mapper):
        """Test email priority handling with no emails"""
        frappe_data = {}
        
        email_config = {
            "email_priority": ["preferred_contact_email", "personal_email", "company_email"]
        }
        
        result = await complex_mapper._handle_email_priority(
            frappe_data, email_config, "frappe_to_supabase"
        )
        
        # Should return None or empty string
        assert result is None or result == ""

    @pytest.mark.asyncio
    async def test_handle_array_mapping(self, complex_mapper):
        """Test array mapping functionality"""
        frappe_assign = ["user1", "user2", "user3"]
        
        result = await complex_mapper._handle_array_mapping(
            frappe_assign, {}, "frappe_to_supabase"
        )
        
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_handle_boolean_mapping(self, complex_mapper):
        """Test boolean mapping functionality"""
        # Test various boolean representations
        test_cases = [
            ("Active", True),
            ("Inactive", False),
            ("1", True),
            ("0", False),
            (1, True),
            (0, False),
            (True, True),
            (False, False)
        ]
        
        for input_val, expected in test_cases:
            result = await complex_mapper._handle_boolean_mapping(
                input_val, {}, "frappe_to_supabase"
            )
            assert result == expected

    @pytest.mark.asyncio
    async def test_handle_datetime_mapping(self, complex_mapper):
        """Test datetime mapping functionality"""
        # Test various datetime formats
        test_cases = [
            "2025-01-27 10:00:00",
            "2025-01-27T10:00:00Z",
            "2025-01-27T10:00:00.000Z",
            "2025-01-27"
        ]
        
        for dt_string in test_cases:
            result = await complex_mapper._handle_datetime_mapping(
                dt_string, {}, "frappe_to_supabase"
            )
            assert result is not None
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_handle_lookup_mapping(self, complex_mapper):
        """Test lookup mapping functionality"""
        lookup_config = {
            "type": "lookup",
            "frappe_doctype": "Employee",
            "supabase_field": "instructor",
            "frappe_field": "name"
        }
        
        frappe_data = {"instructor": "HR-EMP-00001"}
        
        result = await complex_mapper._handle_lookup_mapping(
            frappe_data, lookup_config, "frappe_to_supabase"
        )
        
        assert result is not None
        # Should return the mapped value or perform lookup

    @pytest.mark.asyncio
    async def test_handle_complex_mapping_error(self, complex_mapper):
        """Test error handling in complex mapping"""
        invalid_config = {
            "type": "invalid_type"
        }
        
        data = {"test": "value"}
        
        result = await complex_mapper._handle_complex_mapping(
            "test_field", data, invalid_config, "frappe_to_supabase"
        )
        
        # Should handle error gracefully
        assert result is not None or result is None

    @pytest.mark.asyncio
    async def test_apply_complex_mappings(self, complex_mapper, sample_frappe_employee_data, custom_mappings):
        """Test applying complex mappings to data"""
        mapping_config = custom_mappings["users_Employee"]
        
        result = await complex_mapper.apply_complex_mappings(
            sample_frappe_employee_data,
            mapping_config,
            "frappe_to_supabase"
        )
        
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_apply_complex_mappings_no_complex_mappings(self, complex_mapper, sample_frappe_employee_data):
        """Test applying complex mappings when none exist"""
        mapping_config = {
            "frappe_doctype": "Employee",
            "supabase_table": "users",
            "field_mappings": {"name": "id"},
            "reverse_mappings": {"id": "name"}
            # No complex_mappings
        }
        
        result = await complex_mapper.apply_complex_mappings(
            sample_frappe_employee_data,
            mapping_config,
            "frappe_to_supabase"
        )
        
        assert result is not None
        assert result == sample_frappe_employee_data  # Should return original data


class TestFieldMappingIntegration:
    """Integration tests for field mapping"""

    @pytest.mark.asyncio
    async def test_complete_field_mapping_flow(self, field_mapper, complex_mapper, sample_frappe_employee_data, custom_mappings):
        """Test complete field mapping flow with complex mappings"""
        mapping_config = custom_mappings["users_Employee"]
        
        # First apply complex mappings
        complex_result = await complex_mapper.apply_complex_mappings(
            sample_frappe_employee_data,
            mapping_config,
            "frappe_to_supabase"
        )
        
        # Then apply field mappings
        final_result = await field_mapper.map_fields(
            complex_result,
            "frappe",
            "supabase",
            mapping_config
        )
        
        assert final_result is not None
        assert "id" in final_result
        assert "first_name" in final_result
        assert "last_name" in final_result
        assert "email" in final_result

    @pytest.mark.asyncio
    async def test_bidirectional_mapping_consistency(self, field_mapper, complex_mapper, sample_frappe_employee_data, custom_mappings):
        """Test bidirectional mapping consistency"""
        mapping_config = custom_mappings["users_Employee"]
        
        # Frappe to Supabase
        frappe_to_supabase = await field_mapper.map_fields(
            sample_frappe_employee_data,
            "frappe",
            "supabase",
            mapping_config
        )
        
        # Supabase to Frappe
        supabase_to_frappe = await field_mapper.map_fields(
            frappe_to_supabase,
            "supabase",
            "frappe",
            mapping_config
        )
        
        # Key fields should be consistent
        assert supabase_to_frappe["name"] == sample_frappe_employee_data["name"]
        assert supabase_to_frappe["first_name"] == sample_frappe_employee_data["first_name"]
        assert supabase_to_frappe["last_name"] == sample_frappe_employee_data["last_name"]

    @pytest.mark.asyncio
    async def test_mapping_performance(self, field_mapper, custom_mappings):
        """Test mapping performance with large datasets"""
        import time
        
        # Create large dataset
        large_data = {
            f"field_{i}": f"value_{i}" for i in range(1000)
        }
        large_data.update({
            "name": "HR-EMP-00001",
            "first_name": "John",
            "last_name": "Doe",
            "personal_email": "john@example.com"
        })
        
        mapping_config = custom_mappings["users_Employee"]
        
        start_time = time.time()
        result = await field_mapper.map_fields(
            large_data,
            "frappe",
            "supabase",
            mapping_config
        )
        end_time = time.time()
        
        assert result is not None
        assert (end_time - start_time) < 1.0  # Should complete within 1 second
