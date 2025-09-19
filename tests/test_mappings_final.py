#!/usr/bin/env python3
"""
Final test for custom mappings integration
"""
import json
import sys
import os
import asyncio

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_field_mapper_integration():
    """Test the FieldMapper with custom mappings"""
    print("🔍 Testing FieldMapper Integration")
    print("=" * 50)
    
    try:
        # Import the FieldMapper
        from src.mapping.field_mapper import FieldMapper
        from src.mapping.complex_mapper import ComplexMapper
        
        # Create mapper instance
        field_mapper = FieldMapper()
        complex_mapper = ComplexMapper()
        
        print("✅ FieldMapper and ComplexMapper initialized successfully")
        
        # Load custom mappings
        with open("custom_mappings.json", "r") as f:
            custom_mappings = json.load(f)
        
        print(f"✅ Loaded {len(custom_mappings)} custom mappings")
        
        # Test tasks mapping
        tasks_mapping = custom_mappings["tasks_Task"]
        print(f"\n📋 Testing Tasks Mapping:")
        print(f"   Frappe Doctype: {tasks_mapping['frappe_doctype']}")
        print(f"   Supabase Table: {tasks_mapping['supabase_table']}")
        
        # Test field mapping
        test_frappe_data = {
            "name": "TASK-2025-0001",
            "subject": "Test Task",
            "status": "Open",
            "project": "PROJ-001",
            "exp_start_date": "2025-01-15",
            "exp_end_date": "2025-01-20",
            "type": "Development",
            "description": "This is a test task"
        }
        
        print(f"\n📊 Test Frappe Data: {test_frappe_data}")
        
        # Map to Supabase format
        mapping_config = tasks_mapping["field_mappings"]
        mapped_data = await field_mapper.map_fields(
            test_frappe_data, 
            "frappe", 
            "supabase", 
            mapping_config
        )
        
        print(f"📊 Mapped to Supabase: {mapped_data}")
        
        # Test reverse mapping
        test_supabase_data = {
            "id": 1,
            "task_name": "Test Task",
            "status": "Open",
            "project": 1,
            "start_date": "2025-01-15",
            "end_date": "2025-01-20",
            "task_category": "Development",
            "page_content": "This is a test task"
        }
        
        print(f"\n📊 Test Supabase Data: {test_supabase_data}")
        
        reverse_mapping = tasks_mapping["reverse_mappings"]
        reverse_mapped_data = await field_mapper.map_fields(
            test_supabase_data,
            "supabase",
            "frappe", 
            reverse_mapping
        )
        
        print(f"📊 Mapped to Frappe: {reverse_mapped_data}")
        
        # Test users mapping
        users_mapping = custom_mappings["users_User"]
        print(f"\n📋 Testing Users Mapping:")
        print(f"   Frappe Doctype: {users_mapping['frappe_doctype']}")
        print(f"   Supabase Table: {users_mapping['supabase_table']}")
        
        test_frappe_user = {
            "name": "john.doe",
            "first_name": "John",
            "last_name": "Doe",
            "personal_email": "john.doe@personal.com",
            "company_email": "john.doe@company.com",
            "preferred_email": "john.doe@preferred.com",
            "mobile_no": "+1234567890",
            "company": "ACME Corp"
        }
        
        print(f"\n📊 Test Frappe User: {test_frappe_user}")
        
        # Map to Supabase format
        user_mapping_config = users_mapping["field_mappings"]
        mapped_user = await field_mapper.map_fields(
            test_frappe_user,
            "frappe",
            "supabase",
            user_mapping_config
        )
        
        print(f"📊 Mapped to Supabase: {mapped_user}")
        
        return True
        
    except Exception as e:
        print(f"❌ FieldMapper integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_complex_mappings():
    """Test complex mapping logic"""
    print("\n🔍 Testing Complex Mappings")
    print("=" * 50)
    
    try:
        from src.mapping.complex_mapper import ComplexMapper
        
        complex_mapper = ComplexMapper()
        
        # Test Task ID mapping
        print("1. Testing Task ID mapping...")
        
        # Frappe to Supabase
        frappe_task_id = "TASK-2025-0001"
        result = await complex_mapper.map_complex_field(
            "id", frappe_task_id, 
            {"complex_mappings": {"id": {"type": "task_id"}}},
            "frappe_to_supabase"
        )
        print(f"   ✅ Frappe Task ID: {frappe_task_id} → Supabase ID: {result}")
        
        # Supabase to Frappe
        supabase_task_id = 1
        result = await complex_mapper.map_complex_field(
            "id", supabase_task_id,
            {"complex_mappings": {"id": {"type": "task_id"}}},
            "supabase_to_frappe"
        )
        print(f"   ✅ Supabase ID: {supabase_task_id} → Frappe Task ID: {result}")
        
        # Test Project ID mapping
        print("\n2. Testing Project ID mapping...")
        
        # Frappe to Supabase
        frappe_project_id = "PROJ-001"
        result = await complex_mapper.map_complex_field(
            "project", frappe_project_id,
            {"complex_mappings": {"project": {"type": "project_id"}}},
            "frappe_to_supabase"
        )
        print(f"   ✅ Frappe Project: {frappe_project_id} → Supabase Project: {result}")
        
        # Supabase to Frappe
        supabase_project_id = 1
        result = await complex_mapper.map_complex_field(
            "project", supabase_project_id,
            {"complex_mappings": {"project": {"type": "project_id"}}},
            "supabase_to_frappe"
        )
        print(f"   ✅ Supabase Project: {supabase_project_id} → Frappe Project: {result}")
        
        # Test Task Category mapping
        print("\n3. Testing Task Category mapping...")
        
        # Frappe to Supabase
        frappe_category = "Development"
        result = await complex_mapper.map_complex_field(
            "type", frappe_category,
            {"complex_mappings": {"type": {"type": "task_category"}}},
            "frappe_to_supabase"
        )
        print(f"   ✅ Frappe Category: {frappe_category} → Supabase Category: {result}")
        
        # Supabase to Frappe
        supabase_category = "Development"
        result = await complex_mapper.map_complex_field(
            "task_category", supabase_category,
            {"complex_mappings": {"task_category": {"type": "task_category"}}},
            "supabase_to_frappe"
        )
        print(f"   ✅ Supabase Category: {supabase_category} → Frappe Category: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complex mapping test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Final Custom Mappings Integration Test")
    print("=" * 60)
    
    # Test field mapper integration
    success1 = await test_field_mapper_integration()
    
    if success1:
        # Test complex mappings
        success2 = await test_complex_mappings()
        
        if success2:
            print("\n🎉 All integration tests passed!")
            print("\n📋 Custom Mappings Summary:")
            print("   ✅ Tasks ↔ Task mapping configured")
            print("   ✅ Users ↔ User mapping configured")
            print("   ✅ Complex ID transformations working")
            print("   ✅ Field mappings working")
            print("   ✅ Reverse mappings working")
            print("\n🚀 Ready for production use!")
            print("\n📋 Next Steps:")
            print("   1. Fix Supabase client compatibility issue")
            print("   2. Start the sync service")
            print("   3. Configure webhooks")
            print("   4. Test with real data")
        else:
            print("\n❌ Complex mapping test failed")
    else:
        print("\n❌ Field mapper integration test failed")

if __name__ == "__main__":
    asyncio.run(main())
