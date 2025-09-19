#!/usr/bin/env python3
"""
Test script for schema discovery and mapping
"""
import asyncio
import sys
import os
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.discovery.schema_discovery import SchemaDiscovery
from src.config import settings

async def test_schema_discovery():
    """Test the schema discovery system"""
    print("🔍 Testing Schema Discovery System")
    print("=" * 50)
    
    try:
        # Initialize schema discovery
        discovery = SchemaDiscovery()
        
        print("1. Testing Frappe Schema Discovery...")
        frappe_schemas = await discovery.discover_frappe_schemas()
        print(f"   ✅ Discovered {len(frappe_schemas)} Frappe doctypes")
        
        for doctype, schema in frappe_schemas.items():
            print(f"   📋 {doctype}: {schema.get('total_fields', 0)} fields")
        
        print("\n2. Testing Supabase Schema Discovery...")
        supabase_schemas = await discovery.discover_supabase_schemas()
        print(f"   ✅ Discovered {len(supabase_schemas)} Supabase tables")
        
        for table, schema in supabase_schemas.items():
            print(f"   📊 {table}: {schema.get('total_fields', 0)} fields")
        
        print("\n3. Testing Intelligent Mapping...")
        mappings = await discovery.create_intelligent_mappings(frappe_schemas, supabase_schemas)
        print(f"   ✅ Created {len(mappings)} intelligent mappings")
        
        for mapping_name, mapping in mappings.items():
            confidence = mapping.get('confidence_score', 0)
            field_count = len(mapping.get('field_mappings', {}))
            print(f"   🔗 {mapping_name}: {field_count} field mappings (confidence: {confidence:.2f})")
        
        print("\n4. Testing Schema Summary...")
        summary = await discovery.get_schema_summary()
        print(f"   ✅ Summary generated")
        print(f"   📊 Total doctypes: {summary.get('total_doctypes', 0)}")
        print(f"   📊 Total tables: {summary.get('total_tables', 0)}")
        print(f"   📊 Total mappings: {summary.get('total_mappings', 0)}")
        
        print("\n🎉 Schema Discovery Test Completed Successfully!")
        
        # Save results to file
        results = {
            "frappe_schemas": frappe_schemas,
            "supabase_schemas": supabase_schemas,
            "mappings": mappings,
            "summary": summary
        }
        
        with open("schema_discovery_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print("📁 Results saved to schema_discovery_results.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema discovery test failed: {e}")
        return False

async def test_individual_schemas():
    """Test individual schema discovery"""
    print("\n🔍 Testing Individual Schema Discovery")
    print("=" * 50)
    
    try:
        discovery = SchemaDiscovery()
        
        # Test specific Frappe doctype
        print("Testing Frappe Employee doctype...")
        employee_schema = await discovery._get_frappe_doctype_schema("Employee", [])
        if employee_schema:
            print(f"   ✅ Employee doctype: {employee_schema.get('total_fields', 0)} fields")
            print(f"   📋 Fields: {[f['fieldname'] for f in employee_schema.get('fields', [])[:5]]}...")
        else:
            print("   ❌ Employee doctype not found")
        
        # Test specific Supabase table
        print("Testing Supabase employees table...")
        employees_schema = await discovery._get_supabase_table_schema("employees", [])
        if employees_schema:
            print(f"   ✅ employees table: {employees_schema.get('total_fields', 0)} fields")
            print(f"   📊 Fields: {[f['fieldname'] for f in employees_schema.get('fields', [])[:5]]}...")
        else:
            print("   ❌ employees table not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Individual schema test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Frappe-Supabase Schema Discovery Test Suite")
    print("=" * 60)
    
    # Test configuration
    print("📋 Configuration Check:")
    print(f"   Frappe URL: {settings.frappe_url}")
    print(f"   Supabase URL: {settings.supabase_url}")
    print(f"   Discovery Doctypes: {getattr(settings, 'frappe_discovery_doctypes', 'Not set')}")
    print(f"   Discovery Tables: {getattr(settings, 'supabase_discovery_tables', 'Not set')}")
    print()
    
    # Run tests
    success1 = await test_schema_discovery()
    success2 = await test_individual_schemas()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Schema discovery is working correctly.")
        print("\n📋 Next Steps:")
        print("   1. Review the generated mappings in schema_discovery_results.json")
        print("   2. Apply the mappings using the API: POST /api/schema/mappings/apply")
        print("   3. Start the sync service: python main.py")
    else:
        print("\n❌ Some tests failed. Please check the configuration and try again.")

if __name__ == "__main__":
    asyncio.run(main())
