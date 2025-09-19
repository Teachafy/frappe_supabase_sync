#!/usr/bin/env python3
"""
Quick setup script for the sync service
"""
import os
import sys
import subprocess
import json

def check_service_running():
    """Check if the sync service is running"""
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_service():
    """Start the sync service"""
    print("🚀 Starting Sync Service...")
    
    if check_service_running():
        print("✅ Service is already running!")
        return True
    
    try:
        # Start the service in background
        subprocess.Popen([sys.executable, "main.py"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        # Wait a moment for service to start
        import time
        time.sleep(3)
        
        if check_service_running():
            print("✅ Service started successfully!")
            return True
        else:
            print("❌ Failed to start service")
            return False
            
    except Exception as e:
        print(f"❌ Error starting service: {e}")
        return False

def generate_webhook_secret():
    """Generate a secure webhook secret"""
    import secrets
    secret = secrets.token_urlsafe(32)
    print(f"🔑 Generated webhook secret: {secret}")
    return secret

def update_env_file(webhook_secret):
    """Update .env file with webhook secret"""
    env_file = ".env"
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update webhook secret
        if "WEBHOOK_SECRET=" in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith("WEBHOOK_SECRET="):
                    lines[i] = f"WEBHOOK_SECRET={webhook_secret}"
                    break
            content = '\n'.join(lines)
        else:
            content += f"\nWEBHOOK_SECRET={webhook_secret}\n"
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated .env file with webhook secret")
    else:
        print(f"❌ .env file not found")

def show_webhook_config():
    """Show webhook configuration details"""
    print(f"\n📋 Webhook Configuration Details")
    print(f"=" * 50)
    
    print(f"\n🔗 Frappe Webhook Setup:")
    print(f"   URL: http://localhost:8000/webhooks/frappe")
    print(f"   Method: POST")
    print(f"   Events: Employee (Insert, Update, Delete)")
    print(f"   Events: Task (Insert, Update, Delete)")
    print(f"   Headers: Content-Type: application/json")
    print(f"   Headers: X-Webhook-Secret: [your_secret]")
    
    print(f"\n🔗 Supabase Webhook Setup:")
    print(f"   URL: http://localhost:8000/webhooks/supabase")
    print(f"   Method: POST")
    print(f"   Events: users (Insert, Update, Delete)")
    print(f"   Events: tasks (Insert, Update, Delete)")
    print(f"   Headers: Content-Type: application/json")
    print(f"   Headers: X-Webhook-Secret: [your_secret]")
    
    print(f"\n📊 Service Endpoints:")
    print(f"   Health Check: http://localhost:8000/health")
    print(f"   Sync Status: http://localhost:8000/sync/status")
    print(f"   Manual Sync: POST http://localhost:8000/sync/manual")
    print(f"   Schema Discovery: http://localhost:8000/api/schema/discover")

def test_endpoints():
    """Test the service endpoints"""
    print(f"\n🧪 Testing Service Endpoints...")
    
    try:
        import requests
        
        # Test health
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
        
        # Test sync status
        response = requests.get("http://localhost:8000/sync/status", timeout=5)
        if response.status_code == 200:
            print("✅ Sync status endpoint working")
        else:
            print(f"❌ Sync status endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")

def main():
    """Main setup function"""
    print("🚀 Frappe-Supabase Sync Service Setup")
    print("=" * 60)
    
    # Generate webhook secret
    webhook_secret = generate_webhook_secret()
    
    # Update .env file
    update_env_file(webhook_secret)
    
    # Start service
    if start_service():
        # Test endpoints
        test_endpoints()
        
        # Show configuration
        show_webhook_config()
        
        print(f"\n🎉 Setup Complete!")
        print(f"\n📋 Next Steps:")
        print(f"   1. Configure webhooks in Frappe and Supabase")
        print(f"   2. Use the URLs and secret shown above")
        print(f"   3. Test with: python test_webhooks.py")
        print(f"   4. Monitor with: python final_verification.py")
        
    else:
        print(f"\n❌ Setup failed. Please check the service manually.")

if __name__ == "__main__":
    main()
