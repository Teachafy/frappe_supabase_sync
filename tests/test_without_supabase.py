#!/usr/bin/env python3
"""
Test the sync service without Supabase client for development
"""
import json
import sys
import os
import asyncio

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_mappings_without_supabase():
    """Test mappings without Supabase client"""
    print("🔍 Testing Mappings Without Supabase Client")
    print("=" * 50)
    
    try:
        # Load custom mappings
        with open("custom_mappings.json", "r") as f:
            custom_mappings = json.load(f)
        
        print(f"✅ Loaded {len(custom_mappings)} custom mappings")
        
        # Test tasks mapping
        tasks_mapping = custom_mappings["tasks_Task"]
        print(f"\n📋 Tasks Mapping:")
        print(f"   Frappe: {tasks_mapping['frappe_doctype']}")
        print(f"   Supabase: {tasks_mapping['supabase_table']}")
        
        # Test field transformations
        test_data = {
            "name": "TASK-2025-0001",
            "subject": "Test Task",
            "status": "Open",
            "project": "PROJ-001",
            "exp_start_date": "2025-01-15",
            "exp_end_date": "2025-01-20",
            "type": "Development",
            "description": "This is a test task"
        }
        
        print(f"\n📊 Test Data: {test_data}")
        
        # Simulate field mapping
        field_mappings = tasks_mapping["field_mappings"]
        mapped_data = {}
        for frappe_field, supabase_field in field_mappings.items():
            if frappe_field in test_data:
                mapped_data[supabase_field] = test_data[frappe_field]
        
        print(f"📊 Mapped Data: {mapped_data}")
        
        # Test complex transformations
        print(f"\n🔧 Complex Transformations:")
        
        # Task ID transformation
        frappe_id = test_data["name"]
        if frappe_id.startswith("TASK-"):
            parts = frappe_id.split("-")
            if len(parts) >= 3:
                try:
                    supabase_id = int(parts[2])
                    print(f"   Task ID: {frappe_id} → {supabase_id}")
                except ValueError:
                    print(f"   ❌ Could not extract ID from {frappe_id}")
        
        # Project ID transformation
        frappe_project = test_data["project"]
        if frappe_project.startswith("PROJ-"):
            numeric_part = frappe_project.replace("PROJ-", "")
            try:
                supabase_project = int(numeric_part)
                print(f"   Project ID: {frappe_project} → {supabase_project}")
            except ValueError:
                print(f"   ❌ Could not extract project ID from {frappe_project}")
        
        # Test users mapping
        users_mapping = custom_mappings["users_User"]
        print(f"\n📋 Users Mapping:")
        print(f"   Frappe: {users_mapping['frappe_doctype']}")
        print(f"   Supabase: {users_mapping['supabase_table']}")
        
        test_user = {
            "name": "john.doe",
            "first_name": "John",
            "last_name": "Doe",
            "personal_email": "john.doe@personal.com",
            "company_email": "john.doe@company.com",
            "preferred_email": "john.doe@preferred.com",
            "mobile_no": "+1234567890",
            "company": "ACME Corp"
        }
        
        print(f"\n📊 Test User: {test_user}")
        
        # Simulate user field mapping
        user_field_mappings = users_mapping["field_mappings"]
        mapped_user = {}
        for frappe_field, supabase_field in user_field_mappings.items():
            if frappe_field in test_user:
                mapped_user[supabase_field] = test_user[frappe_field]
        
        print(f"📊 Mapped User: {mapped_user}")
        
        # Test email priority
        email_priority = ["personal_email", "company_email", "preferred_email"]
        selected_email = None
        for field in email_priority:
            if field in test_user and test_user[field]:
                selected_email = test_user[field]
                break
        
        print(f"📧 Selected Email: {selected_email}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Testing Mappings Without Supabase Client")
    print("=" * 60)
    
    success = asyncio.run(test_mappings_without_supabase())
    
    if success:
        print("\n🎉 All tests passed!")
        print("\n📋 Next Steps:")
        print("1. Get your Supabase service role key:")
        print("   python get_supabase_keys.py")
        print("2. Update the .env file with your service role key")
        print("3. Reinstall Supabase client:")
        print("   pip install supabase==2.0.0")
        print("4. Test the full service:")
        print("   python main.py")
    else:
        print("\n❌ Tests failed")

if __name__ == "__main__":
    main()
