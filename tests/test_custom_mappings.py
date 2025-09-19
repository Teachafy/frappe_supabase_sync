#!/usr/bin/env python3
"""
Test script for custom mappings (tasks and users)
"""
import asyncio
import sys
import os
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.discovery.schema_discovery import SchemaDiscovery
from src.mapping.field_mapper import FieldMapper
from src.mapping.complex_mapper import ComplexMapper
from src.config import settings

async def test_custom_mappings():
    """Test the custom mappings for tasks and users"""
    print("🔍 Testing Custom Mappings (Tasks & Users)")
    print("=" * 50)
    
    try:
        # Load custom mappings
        with open("custom_mappings.json", "r") as f:
            custom_mappings = json.load(f)
        
        print(f"✅ Loaded {len(custom_mappings)} custom mappings")
        
        # Test each mapping
        for mapping_name, mapping_config in custom_mappings.items():
            print(f"\n📋 Testing {mapping_name}...")
            
            # Test field mapping
            field_mapper = FieldMapper()
            
            # Create sample data
            if "Task" in mapping_name:
                sample_data = {
                    "name": "TASK-2025-0001",
                    "subject": "Test Task",
                    "status": "Open",
                    "project": "PROJ-001",
                    "exp_start_date": "2025-01-27",
                    "exp_end_date": "2025-01-30",
                    "type": "Development",
                    "description": "This is a test task"
                }
            else:  # User
                sample_data = {
                    "name": "user1",
                    "first_name": "John",
                    "last_name": "Doe",
                    "personal_email": "john.doe@example.com",
                    "mobile_no": "+1234567890",
                    "company": "Test Company"
                }
            
            print(f"   📊 Sample data: {sample_data}")
            
            # Test Frappe to Supabase mapping
            print("   🔄 Testing Frappe → Supabase mapping...")
            try:
                mapped_data = await field_mapper.map_fields(
                    sample_data, 
                    "frappe", 
                    "supabase", 
                    mapping_config
                )
                print(f"   ✅ Mapped data: {mapped_data}")
            except Exception as e:
                print(f"   ❌ Mapping failed: {e}")
            
            # Test Supabase to Frappe mapping
            print("   🔄 Testing Supabase → Frappe mapping...")
            try:
                # Create reverse sample data
                reverse_data = {}
                reverse_mappings = mapping_config.get("reverse_mappings", {})
                for supabase_field, frappe_field in reverse_mappings.items():
                    if supabase_field in sample_data:
                        reverse_data[supabase_field] = sample_data[frappe_field]
                
                reverse_mapped_data = await field_mapper.map_fields(
                    reverse_data,
                    "supabase",
                    "frappe",
                    mapping_config
                )
                print(f"   ✅ Reverse mapped data: {reverse_mapped_data}")
            except Exception as e:
                print(f"   ❌ Reverse mapping failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Custom mapping test failed: {e}")
        return False

async def test_complex_mappings():
    """Test complex mapping logic"""
    print("\n🔍 Testing Complex Mapping Logic")
    print("=" * 50)
    
    try:
        complex_mapper = ComplexMapper()
        
        # Test Task ID transformation
        print("1. Testing Task ID transformation...")
        
        # Frappe to Supabase
        frappe_task_id = "TASK-2025-0001"
        supabase_task_id = await complex_mapper.map_task_id(frappe_task_id, "frappe_to_supabase")
        print(f"   Frappe ID: {frappe_task_id} → Supabase ID: {supabase_task_id}")
        
        # Supabase to Frappe
        supabase_task_id = 1
        frappe_task_id = await complex_mapper.map_task_id(supabase_task_id, "supabase_to_frappe")
        print(f"   Supabase ID: {supabase_task_id} → Frappe ID: {frappe_task_id}")
        
        # Test Project ID transformation
        print("\n2. Testing Project ID transformation...")
        
        # Frappe to Supabase
        frappe_project_id = "PROJ-001"
        supabase_project_id = await complex_mapper.map_task_project(frappe_project_id, "frappe_to_supabase")
        print(f"   Frappe Project: {frappe_project_id} → Supabase Project: {supabase_project_id}")
        
        # Supabase to Frappe
        supabase_project_id = 1
        frappe_project_id = await complex_mapper.map_task_project(supabase_project_id, "supabase_to_frappe")
        print(f"   Supabase Project: {supabase_project_id} → Frappe Project: {frappe_project_id}")
        
        # Test email priority mapping
        print("\n3. Testing email priority mapping...")
        
        # Frappe to Supabase
        frappe_user_data = {
            "personal_email": "john.doe@personal.com",
            "company_email": "john.doe@company.com",
            "preferred_email": "john.doe@preferred.com"
        }
        
        email_priority_config = {
            "email_priority": ["personal_email", "company_email", "preferred_email"]
        }
        
        supabase_email = await complex_mapper._handle_email_priority(
            frappe_user_data, email_priority_config, "frappe_to_supabase"
        )
        print(f"   Frappe emails: {frappe_user_data} → Supabase email: {supabase_email}")
        
        # Supabase to Frappe
        supabase_email = "john.doe@example.com"
        frappe_emails = await complex_mapper._handle_email_priority(
            supabase_email, email_priority_config, "supabase_to_frappe"
        )
        print(f"   Supabase email: {supabase_email} → Frappe emails: {frappe_emails}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complex mapping test failed: {e}")
        return False

async def test_schema_discovery_with_custom_mappings():
    """Test schema discovery with custom mappings"""
    print("\n🔍 Testing Schema Discovery with Custom Mappings")
    print("=" * 50)
    
    try:
        discovery = SchemaDiscovery()
        
        # Test Frappe schema discovery
        print("1. Testing Frappe schema discovery...")
        frappe_schemas = await discovery.discover_frappe_schemas()
        
        # Check if Task and User doctypes are discovered
        if "Task" in frappe_schemas:
            task_schema = frappe_schemas["Task"]
            print(f"   ✅ Task doctype discovered: {task_schema.get('total_fields', 0)} fields")
            print(f"   📋 Key fields: {[f['fieldname'] for f in task_schema.get('fields', [])[:10]]}")
        else:
            print("   ❌ Task doctype not found")
        
        if "User" in frappe_schemas:
            user_schema = frappe_schemas["User"]
            print(f"   ✅ User doctype discovered: {user_schema.get('total_fields', 0)} fields")
            print(f"   📋 Key fields: {[f['fieldname'] for f in user_schema.get('fields', [])[:10]]}")
        else:
            print("   ❌ User doctype not found")
        
        # Test Supabase schema discovery
        print("\n2. Testing Supabase schema discovery...")
        supabase_schemas = await discovery.discover_supabase_schemas()
        
        # Check if tasks and users tables are discovered
        if "tasks" in supabase_schemas:
            tasks_schema = supabase_schemas["tasks"]
            print(f"   ✅ tasks table discovered: {tasks_schema.get('total_fields', 0)} fields")
            print(f"   📊 Key fields: {[f['fieldname'] for f in tasks_schema.get('fields', [])[:10]]}")
        else:
            print("   ❌ tasks table not found")
        
        if "users" in supabase_schemas:
            users_schema = supabase_schemas["users"]
            print(f"   ✅ users table discovered: {users_schema.get('total_fields', 0)} fields")
            print(f"   📊 Key fields: {[f['fieldname'] for f in users_schema.get('fields', [])[:10]]}")
        else:
            print("   ❌ users table not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema discovery test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Custom Mappings Test Suite")
    print("=" * 60)
    
    # Test configuration
    print("📋 Configuration Check:")
    print(f"   Frappe URL: {settings.frappe_url}")
    print(f"   Supabase URL: {settings.supabase_url}")
    print()
    
    # Run tests
    success1 = await test_custom_mappings()
    success2 = await test_complex_mappings()
    success3 = await test_schema_discovery_with_custom_mappings()
    
    if success1 and success2 and success3:
        print("\n🎉 All custom mapping tests passed!")
        print("\n📋 Next Steps:")
        print("   1. Apply the custom mappings to your sync configuration")
        print("   2. Test the mappings with real data")
        print("   3. Set up webhooks for real-time synchronization")
        print("   4. Monitor sync operations")
    else:
        print("\n❌ Some tests failed. Please check the configuration and try again.")

if __name__ == "__main__":
    asyncio.run(main())
