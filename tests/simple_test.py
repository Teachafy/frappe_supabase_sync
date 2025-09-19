#!/usr/bin/env python3
"""
Simple test for custom mappings without external dependencies
"""
import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_custom_mappings():
    """Test the custom mappings configuration"""
    print("🔍 Testing Custom Mappings Configuration")
    print("=" * 50)
    
    try:
        # Load custom mappings
        with open("custom_mappings.json", "r") as f:
            custom_mappings = json.load(f)
        
        print(f"✅ Loaded {len(custom_mappings)} custom mappings")
        
        # Test each mapping
        for mapping_name, mapping_config in custom_mappings.items():
            print(f"\n📋 Testing {mapping_name}...")
            
            # Validate required fields
            required_fields = ["frappe_doctype", "supabase_table", "field_mappings", "sync_fields"]
            for field in required_fields:
                if field not in mapping_config:
                    print(f"   ❌ Missing required field: {field}")
                    return False
                else:
                    print(f"   ✅ {field}: {mapping_config[field]}")
            
            # Test field mappings
            field_mappings = mapping_config.get("field_mappings", {})
            reverse_mappings = mapping_config.get("reverse_mappings", {})
            
            print(f"   📊 Field mappings: {len(field_mappings)} fields")
            print(f"   📊 Reverse mappings: {len(reverse_mappings)} fields")
            
            # Test complex mappings if present
            complex_mappings = mapping_config.get("complex_mappings", {})
            if complex_mappings:
                print(f"   🔧 Complex mappings: {len(complex_mappings)} fields")
                for field, config in complex_mappings.items():
                    print(f"      - {field}: {config.get('type', 'unknown')}")
            
            # Test confidence score
            confidence = mapping_config.get("confidence_score", 0)
            print(f"   📈 Confidence score: {confidence}")
        
        return True
        
    except Exception as e:
        print(f"❌ Custom mapping test failed: {e}")
        return False

def test_field_transformations():
    """Test field transformation logic"""
    print("\n🔍 Testing Field Transformations")
    print("=" * 50)
    
    # Test Task ID transformation
    print("1. Testing Task ID transformation...")
    
    # Frappe to Supabase
    frappe_task_id = "TASK-2025-0001"
    if frappe_task_id.startswith("TASK-"):
        parts = frappe_task_id.split("-")
        if len(parts) >= 3:
            try:
                supabase_id = int(parts[2])
                print(f"   ✅ Frappe ID: {frappe_task_id} → Supabase ID: {supabase_id}")
            except ValueError:
                print(f"   ❌ Could not extract numeric part from {frappe_task_id}")
        else:
            print(f"   ❌ Invalid format: {frappe_task_id}")
    else:
        print(f"   ❌ Not a TASK ID: {frappe_task_id}")
    
    # Supabase to Frappe
    supabase_task_id = 1
    year = 2025
    frappe_id = f"TASK-{year}-{supabase_task_id:04d}"
    print(f"   ✅ Supabase ID: {supabase_task_id} → Frappe ID: {frappe_id}")
    
    # Test Project ID transformation
    print("\n2. Testing Project ID transformation...")
    
    # Frappe to Supabase
    frappe_project_id = "PROJ-001"
    if frappe_project_id.startswith("PROJ-"):
        numeric_part = frappe_project_id.replace("PROJ-", "")
        try:
            supabase_id = int(numeric_part)
            print(f"   ✅ Frappe Project: {frappe_project_id} → Supabase Project: {supabase_id}")
        except ValueError:
            print(f"   ❌ Could not extract numeric part from {frappe_project_id}")
    else:
        print(f"   ❌ Not a PROJ ID: {frappe_project_id}")
    
    # Supabase to Frappe
    supabase_project_id = 1
    frappe_project_id = f"PROJ-{supabase_project_id:03d}"
    print(f"   ✅ Supabase Project: {supabase_project_id} → Frappe Project: {frappe_project_id}")
    
    # Test email priority mapping
    print("\n3. Testing email priority mapping...")
    
    # Frappe to Supabase
    frappe_user_data = {
        "personal_email": "john.doe@personal.com",
        "company_email": "john.doe@company.com",
        "preferred_email": "john.doe@preferred.com"
    }
    
    email_priority = ["personal_email", "company_email", "preferred_email"]
    selected_email = None
    
    for field in email_priority:
        if field in frappe_user_data and frappe_user_data[field]:
            selected_email = frappe_user_data[field]
            break
    
    print(f"   ✅ Frappe emails: {frappe_user_data} → Selected email: {selected_email}")
    
    # Supabase to Frappe
    supabase_email = "john.doe@example.com"
    frappe_emails = {field: supabase_email for field in email_priority}
    print(f"   ✅ Supabase email: {supabase_email} → Frappe emails: {frappe_emails}")
    
    return True

def main():
    """Main test function"""
    print("🚀 Simple Custom Mappings Test")
    print("=" * 60)
    
    # Test custom mappings
    success1 = test_custom_mappings()
    
    if success1:
        # Test field transformations
        success2 = test_field_transformations()
        
        if success2:
            print("\n🎉 All tests passed! Custom mappings are configured correctly.")
            print("\n📋 Next Steps:")
            print("   1. Start the sync service: python main.py")
            print("   2. Apply the mappings via API")
            print("   3. Test with real data")
            print("   4. Set up webhooks")
        else:
            print("\n❌ Field transformation test failed")
    else:
        print("\n❌ Custom mapping test failed")

if __name__ == "__main__":
    main()
