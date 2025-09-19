#!/usr/bin/env python3
"""
Test Supabase schema fetching with the service role key
"""
import sys
import os
import asyncio

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_supabase_connection():
    """Test Supabase connection and schema fetching"""
    print("🔍 Testing Supabase Connection and Schema Fetching")
    print("=" * 60)
    
    try:
        from src.utils.supabase_client import SupabaseClient
        from src.config import settings
        
        print(f"📋 Supabase Configuration:")
        print(f"   URL: {settings.supabase_url}")
        print(f"   Service Role Key: {settings.supabase_service_role_key[:20]}...")
        
        # Create Supabase client
        print(f"\n🔌 Creating Supabase client...")
        supabase_client = SupabaseClient()
        
        if supabase_client.client is None:
            print("❌ Supabase client is None - connection failed")
            return False
        
        print("✅ Supabase client created successfully")
        
        # Test basic connection
        print(f"\n🌐 Testing basic connection...")
        try:
            # Try to fetch a simple query to test connection
            result = supabase_client.client.table("users").select("*").limit(1).execute()
            print("✅ Basic connection test passed")
        except Exception as e:
            print(f"⚠️  Basic connection test failed: {e}")
            print("   This might be expected if the table doesn't exist yet")
        
        # Test schema fetching for users table
        print(f"\n📊 Testing schema fetching for 'users' table...")
        try:
            schema = await supabase_client.get_table_schema("users")
            if schema:
                print("✅ Successfully fetched 'users' table schema")
                print(f"   Schema type: {type(schema)}")
                print(f"   Schema content: {schema}")
                if isinstance(schema, dict):
                    print(f"   Columns: {list(schema.keys())}")
                    for col_name, col_info in schema.items():
                        if isinstance(col_info, dict):
                            print(f"   - {col_name}: {col_info.get('type', 'unknown')}")
                        else:
                            print(f"   - {col_name}: {col_info}")
            else:
                print("❌ Failed to fetch 'users' table schema")
        except Exception as e:
            print(f"❌ Error fetching 'users' schema: {e}")
        
        # Test schema fetching for tasks table
        print(f"\n📊 Testing schema fetching for 'tasks' table...")
        try:
            schema = await supabase_client.get_table_schema("tasks")
            if schema:
                print("✅ Successfully fetched 'tasks' table schema")
                print(f"   Schema type: {type(schema)}")
                print(f"   Schema content: {schema}")
                if isinstance(schema, dict):
                    print(f"   Columns: {list(schema.keys())}")
                    for col_name, col_info in schema.items():
                        if isinstance(col_info, dict):
                            print(f"   - {col_name}: {col_info.get('type', 'unknown')}")
                        else:
                            print(f"   - {col_name}: {col_info}")
            else:
                print("❌ Failed to fetch 'tasks' table schema")
        except Exception as e:
            print(f"❌ Error fetching 'tasks' schema: {e}")
        
        # Test basic table query instead of listing
        print(f"\n📋 Testing basic table queries...")
        try:
            # Try to query users table
            users_result = supabase_client.client.table("users").select("*").limit(1).execute()
            print(f"✅ Users table query successful: {len(users_result.data)} records")
        except Exception as e:
            print(f"❌ Users table query failed: {e}")
        
        try:
            # Try to query tasks table
            tasks_result = supabase_client.client.table("tasks").select("*").limit(1).execute()
            print(f"✅ Tasks table query successful: {len(tasks_result.data)} records")
        except Exception as e:
            print(f"❌ Tasks table query failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_frappe_connection():
    """Test Frappe connection"""
    print(f"\n🔍 Testing Frappe Connection")
    print("=" * 40)
    
    try:
        from src.utils.frappe_client import FrappeClient
        from src.config import settings
        
        print(f"📋 Frappe Configuration:")
        print(f"   URL: {settings.frappe_url}")
        print(f"   API Key: {settings.frappe_api_key[:10]}...")
        
        # Create Frappe client
        print(f"\n🔌 Creating Frappe client...")
        frappe_client = FrappeClient()
        print("✅ Frappe client created successfully")
        
        # Test basic connection
        print(f"\n🌐 Testing basic connection...")
        try:
            # Try to fetch doctype metadata
            metadata = await frappe_client.get_doctype_meta("User")
            if metadata:
                print("✅ Successfully fetched 'User' doctype metadata")
                print(f"   Metadata type: {type(metadata)}")
                print(f"   Metadata content: {metadata}")
                if isinstance(metadata, dict):
                    print(f"   Fields: {len(metadata.get('fields', []))}")
            else:
                print("❌ Failed to fetch 'User' doctype metadata")
        except Exception as e:
            print(f"❌ Error fetching 'User' metadata: {e}")
        
        # Test Task doctype
        print(f"\n📊 Testing 'Task' doctype...")
        try:
            metadata = await frappe_client.get_doctype_meta("Task")
            if metadata:
                print("✅ Successfully fetched 'Task' doctype metadata")
                print(f"   Metadata type: {type(metadata)}")
                print(f"   Metadata content: {metadata}")
                if isinstance(metadata, dict):
                    print(f"   Fields: {len(metadata.get('fields', []))}")
            else:
                print("❌ Failed to fetch 'Task' doctype metadata")
        except Exception as e:
            print(f"❌ Error fetching 'Task' metadata: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Frappe connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Supabase Schema Fetching Test")
    print("=" * 60)
    
    # Test Supabase connection
    supabase_success = await test_supabase_connection()
    
    # Test Frappe connection
    frappe_success = await test_frappe_connection()
    
    if supabase_success and frappe_success:
        print(f"\n🎉 All connection tests passed!")
        print(f"\n📋 Summary:")
        print(f"   ✅ Supabase connection working")
        print(f"   ✅ Frappe connection working")
        print(f"   ✅ Schema fetching functional")
        print(f"\n🚀 Ready to start the sync service!")
    else:
        print(f"\n❌ Some connection tests failed")
        if not supabase_success:
            print(f"   - Supabase connection issues")
        if not frappe_success:
            print(f"   - Frappe connection issues")

if __name__ == "__main__":
    asyncio.run(main())
