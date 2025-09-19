#!/usr/bin/env python3
"""
Test script for Frappe-Supabase Sync API endpoints
"""
import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/schema"

def test_endpoint(method, endpoint, data=None, expected_status=200):
    """Test an API endpoint"""
    url = f"{API_BASE}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        if response.status_code == expected_status:
            print(f"✅ {method} {endpoint} - Status: {response.status_code}")
            return response.json() if response.content else {}
        else:
            print(f"❌ {method} {endpoint} - Status: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ {method} {endpoint} - Connection failed (is the service running?)")
        return None
    except Exception as e:
        print(f"❌ {method} {endpoint} - Error: {e}")
        return None

def test_basic_endpoints():
    """Test basic service endpoints"""
    print("🔍 Testing Basic Service Endpoints")
    print("=" * 50)
    
    # Test root endpoint
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        print("✅ Root endpoint - Service is running")
    else:
        print("❌ Root endpoint - Service not responding")
        return False
    
    # Test health endpoint
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        health_data = response.json()
        print(f"✅ Health check - Status: {health_data.get('overall_status', 'unknown')}")
    else:
        print("❌ Health check - Service unhealthy")
        return False
    
    # Test sync status
    response = requests.get(f"{BASE_URL}/sync/status")
    if response.status_code == 200:
        status_data = response.json()
        print(f"✅ Sync status - Mappings: {status_data.get('sync_mappings', 0)}")
    else:
        print("❌ Sync status - Failed to get status")
        return False
    
    return True

def test_schema_discovery():
    """Test schema discovery endpoints"""
    print("\n🔍 Testing Schema Discovery Endpoints")
    print("=" * 50)
    
    # Test full schema discovery
    print("1. Testing full schema discovery...")
    result = test_endpoint("POST", "/discover")
    if result:
        print(f"   📊 Discovered {result.get('result', {}).get('total_doctypes', 0)} Frappe doctypes")
        print(f"   📊 Discovered {result.get('result', {}).get('total_tables', 0)} Supabase tables")
        print(f"   📊 Created {result.get('result', {}).get('total_mappings', 0)} mappings")
    
    # Test Frappe schemas
    print("\n2. Testing Frappe schema discovery...")
    result = test_endpoint("GET", "/frappe")
    if result:
        print(f"   📋 Found {result.get('count', 0)} Frappe schemas")
        for doctype in list(result.get('schemas', {}).keys())[:5]:
            print(f"   📋 {doctype}")
    
    # Test Supabase schemas
    print("\n3. Testing Supabase schema discovery...")
    result = test_endpoint("GET", "/supabase")
    if result:
        print(f"   📊 Found {result.get('count', 0)} Supabase schemas")
        for table in list(result.get('schemas', {}).keys())[:5]:
            print(f"   📊 {table}")
    
    # Test intelligent mappings
    print("\n4. Testing intelligent mappings...")
    result = test_endpoint("GET", "/mappings")
    if result:
        print(f"   🔗 Found {result.get('count', 0)} intelligent mappings")
        for mapping_name in list(result.get('mappings', {}).keys())[:5]:
            print(f"   🔗 {mapping_name}")
    
    # Test schema summary
    print("\n5. Testing schema summary...")
    result = test_endpoint("GET", "/summary")
    if result:
        summary = result.get('summary', {})
        print(f"   📊 Total doctypes: {summary.get('total_doctypes', 0)}")
        print(f"   📊 Total tables: {summary.get('total_tables', 0)}")
        print(f"   📊 Total mappings: {summary.get('total_mappings', 0)}")
    
    return True

def test_individual_schemas():
    """Test individual schema endpoints"""
    print("\n🔍 Testing Individual Schema Endpoints")
    print("=" * 50)
    
    # Test specific Frappe doctype
    print("1. Testing Frappe Employee doctype...")
    result = test_endpoint("GET", "/frappe/Employee")
    if result:
        schema = result.get('schema', {})
        print(f"   📋 Employee doctype: {schema.get('total_fields', 0)} fields")
        print(f"   📋 Module: {schema.get('module', 'unknown')}")
    
    # Test specific Supabase table
    print("\n2. Testing Supabase employees table...")
    result = test_endpoint("GET", "/supabase/employees")
    if result:
        schema = result.get('schema', {})
        print(f"   📊 employees table: {schema.get('total_fields', 0)} fields")
    
    # Test schema comparison
    print("\n3. Testing schema comparison...")
    result = test_endpoint("GET", "/compare/Employee/employees")
    if result:
        comparison = result.get('comparison', {})
        print(f"   🔍 Frappe fields: {comparison.get('frappe_fields', 0)}")
        print(f"   🔍 Supabase fields: {comparison.get('supabase_fields', 0)}")
        print(f"   🔍 Potential mappings: {len(comparison.get('potential_mappings', []))}")
        print(f"   🔍 Unmapped Frappe fields: {len(comparison.get('unmapped_frappe_fields', []))}")
        print(f"   🔍 Unmapped Supabase fields: {len(comparison.get('unmapped_supabase_fields', []))}")
    
    return True

def test_mapping_management():
    """Test mapping management endpoints"""
    print("\n🔍 Testing Mapping Management Endpoints")
    print("=" * 50)
    
    # Test mapping validation
    print("1. Testing mapping validation...")
    test_mapping = {
        "frappe_doctype": "Employee",
        "supabase_table": "employees",
        "field_mappings": {
            "name": "id",
            "employee_name": "full_name",
            "email": "email"
        },
        "sync_fields": ["name", "employee_name", "email"]
    }
    
    result = test_endpoint("POST", "/mappings/validate", test_mapping)
    if result:
        print("   ✅ Mapping validation passed")
    
    # Test mapping application
    print("\n2. Testing mapping application...")
    test_mappings = {
        "Employee_employees": test_mapping
    }
    
    result = test_endpoint("POST", "/mappings/apply", test_mappings)
    if result:
        print("   ✅ Mappings applied successfully")
        print(f"   📋 Applied mappings: {result.get('applied_mappings', [])}")
    
    return True

def test_webhook_endpoints():
    """Test webhook endpoints"""
    print("\n🔍 Testing Webhook Endpoints")
    print("=" * 50)
    
    # Test Frappe webhook
    print("1. Testing Frappe webhook...")
    frappe_payload = {
        "doctype": "Employee",
        "name": "EMP-001",
        "operation": "after_insert",
        "doc": {
            "name": "EMP-001",
            "employee_name": "John Doe",
            "email": "john.doe@example.com"
        }
    }
    
    result = test_endpoint("POST", "/webhook/frappe", frappe_payload)
    if result:
        print("   ✅ Frappe webhook processed")
    
    # Test Supabase webhook
    print("\n2. Testing Supabase webhook...")
    supabase_payload = {
        "table": "employees",
        "operation": "INSERT",
        "record": {
            "id": "1",
            "full_name": "Jane Doe",
            "email": "jane.doe@example.com"
        }
    }
    
    result = test_endpoint("POST", "/webhook/supabase", supabase_payload)
    if result:
        print("   ✅ Supabase webhook processed")
    
    return True

def main():
    """Main test function"""
    print("🚀 Frappe-Supabase Sync API Test Suite")
    print("=" * 60)
    
    # Check if service is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print("❌ Service is not running. Please start the service first:")
            print("   python main.py")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to service. Please start the service first:")
        print("   python main.py")
        return
    
    print("✅ Service is running. Starting tests...\n")
    
    # Run tests
    tests = [
        ("Basic Endpoints", test_basic_endpoints),
        ("Schema Discovery", test_schema_discovery),
        ("Individual Schemas", test_individual_schemas),
        ("Mapping Management", test_mapping_management),
        ("Webhook Endpoints", test_webhook_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The sync service is working correctly.")
        print("\n📋 Next Steps:")
        print("   1. Review the discovered schemas and mappings")
        print("   2. Apply the mappings to start synchronization")
        print("   3. Configure webhooks in Frappe and Supabase")
        print("   4. Monitor the sync operations")
    else:
        print("❌ Some tests failed. Please check the service logs and configuration.")

if __name__ == "__main__":
    main()
