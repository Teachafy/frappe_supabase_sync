#!/usr/bin/env python3
"""
Test webhook endpoints for the sync service
"""
import requests
import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_webhook_endpoints():
    """Test the webhook endpoints"""
    print("🔍 Testing Webhook Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    webhook_secret = "your_webhook_secret"  # Update this with your actual secret
    
    # Test health endpoint
    print("1. Testing Health Endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("   ✅ Health endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health endpoint error: {e}")
    
    # Test Frappe webhook
    print("\n2. Testing Frappe Webhook...")
    frappe_payload = {
        "doctype": "Employee",
        "name": "HR-EMP-00001",
        "action": "insert",
        "data": {
            "name": "HR-EMP-00001",
            "employee_name": "Test Employee",
            "first_name": "Test",
            "last_name": "Employee",
            "personal_email": "test@example.com",
            "cell_number": "1234567890",
            "company": "Test Company",
            "status": "Active"
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/webhooks/frappe",
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Secret": webhook_secret
            },
            json=frappe_payload,
            timeout=10
        )
        if response.status_code == 200:
            print("   ✅ Frappe webhook working")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Frappe webhook failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Frappe webhook error: {e}")
    
    # Test Supabase webhook
    print("\n3. Testing Supabase Webhook...")
    supabase_payload = {
        "table": "users",
        "id": 1,
        "action": "insert",
        "data": {
            "id": 1,
            "name": "test.user",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone_number": "1234567890",
            "organization": "Test Organization"
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/webhooks/supabase",
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Secret": webhook_secret
            },
            json=supabase_payload,
            timeout=10
        )
        if response.status_code == 200:
            print("   ✅ Supabase webhook working")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Supabase webhook failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Supabase webhook error: {e}")
    
    # Test sync status
    print("\n4. Testing Sync Status...")
    try:
        response = requests.get(f"{base_url}/sync/status", timeout=10)
        if response.status_code == 200:
            print("   ✅ Sync status endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Sync status failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Sync status error: {e}")

def test_manual_sync():
    """Test manual sync trigger"""
    print("\n5. Testing Manual Sync...")
    
    base_url = "http://localhost:8000"
    
    try:
        response = requests.post(f"{base_url}/sync/manual", timeout=30)
        if response.status_code == 200:
            print("   ✅ Manual sync working")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Manual sync failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Manual sync error: {e}")

def main():
    """Main test function"""
    print("🚀 Webhook Testing Suite")
    print("=" * 60)
    
    print("⚠️  Make sure the sync service is running:")
    print("   python main.py")
    print()
    
    # Test webhook endpoints
    test_webhook_endpoints()
    
    # Test manual sync
    test_manual_sync()
    
    print(f"\n📋 Webhook Configuration Summary:")
    print(f"   Frappe Webhook URL: http://localhost:8000/webhooks/frappe")
    print(f"   Supabase Webhook URL: http://localhost:8000/webhooks/supabase")
    print(f"   Health Check URL: http://localhost:8000/health")
    print(f"   Sync Status URL: http://localhost:8000/sync/status")
    
    print(f"\n📋 Next Steps:")
    print(f"   1. Update webhook secret in this script")
    print(f"   2. Configure webhooks in Frappe and Supabase")
    print(f"   3. Test with real data changes")
    print(f"   4. Monitor sync operations")

if __name__ == "__main__":
    main()
