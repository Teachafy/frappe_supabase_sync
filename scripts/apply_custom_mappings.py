#!/usr/bin/env python3
"""
Apply custom mappings to the sync service
"""
import requests
import json
import sys

def apply_custom_mappings():
    """Apply custom mappings to the sync service"""
    try:
        # Load custom mappings
        with open("custom_mappings.json", "r") as f:
            custom_mappings = json.load(f)
        
        print("🔧 Applying Custom Mappings")
        print("=" * 50)
        
        # Apply mappings via API
        response = requests.post(
            "http://localhost:8000/api/schema/mappings/apply",
            json=custom_mappings,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Custom mappings applied successfully!")
            print(f"📋 Applied mappings: {result.get('applied_mappings', [])}")
            
            # Verify mappings were applied
            verify_response = requests.get("http://localhost:8000/sync/mappings")
            if verify_response.status_code == 200:
                verify_result = verify_response.json()
                print(f"📊 Total mappings in system: {len(verify_result.get('mappings', {}))}")
                
                # Show specific mappings
                for mapping_name in custom_mappings.keys():
                    if mapping_name in verify_result.get('mappings', {}):
                        print(f"   ✅ {mapping_name}: Applied")
                    else:
                        print(f"   ❌ {mapping_name}: Not found")
            
            return True
        else:
            print(f"❌ Failed to apply mappings: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except FileNotFoundError:
        print("❌ custom_mappings.json not found")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to sync service. Please start the service first:")
        print("   python main.py")
        return False
    except Exception as e:
        print(f"❌ Error applying mappings: {e}")
        return False

def test_mappings():
    """Test the applied mappings"""
    try:
        print("\n🧪 Testing Applied Mappings")
        print("=" * 50)
        
        # Test sync status
        response = requests.get("http://localhost:8000/sync/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Sync service status: {status.get('status', 'unknown')}")
            print(f"📊 Enabled mappings: {status.get('enabled_mappings', 0)}")
        
        # Test specific mappings
        mappings_response = requests.get("http://localhost:8000/sync/mappings")
        if mappings_response.status_code == 200:
            mappings = mappings_response.json()
            print(f"📋 Total mappings: {len(mappings.get('mappings', {}))}")
            
            # Check for our custom mappings
            custom_mapping_names = ["tasks_Task", "users_User"]
            for mapping_name in custom_mapping_names:
                if mapping_name in mappings.get('mappings', {}):
                    mapping = mappings['mappings'][mapping_name]
                    print(f"   ✅ {mapping_name}:")
                    print(f"      Frappe: {mapping.get('frappe_doctype')}")
                    print(f"      Supabase: {mapping.get('supabase_table')}")
                    print(f"      Fields: {len(mapping.get('field_mappings', {}))}")
                else:
                    print(f"   ❌ {mapping_name}: Not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing mappings: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Custom Mappings Application Script")
    print("=" * 60)
    
    # Apply mappings
    success1 = apply_custom_mappings()
    
    if success1:
        # Test mappings
        success2 = test_mappings()
        
        if success2:
            print("\n🎉 Custom mappings applied and tested successfully!")
            print("\n📋 Next Steps:")
            print("   1. Test the mappings with real data")
            print("   2. Set up webhooks in Frappe and Supabase")
            print("   3. Monitor sync operations")
            print("   4. Add more mappings as needed")
        else:
            print("\n❌ Mapping test failed")
    else:
        print("\n❌ Failed to apply custom mappings")

if __name__ == "__main__":
    main()
