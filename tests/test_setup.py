#!/usr/bin/env python3
"""
Test script to verify Frappe-Supabase Sync Service setup
"""
import sys
import os

def test_imports():
    """Test if all required modules can be imported"""
    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Test basic imports
        print("Testing imports...")
        
        # Test config import
        from src.config import settings
        print("✅ Config module imported successfully")
        
        # Test models import
        from src.models import SyncEvent, SyncOperation
        print("✅ Models module imported successfully")
        
        # Test utils import
        from src.utils.logger import setup_logging
        print("✅ Logger module imported successfully")
        
        print("\n🎉 All imports successful! The system is ready to run.")
        print(f"📊 Frappe URL: {settings.frappe_url}")
        print(f"📊 Supabase URL: {settings.supabase_url}")
        print(f"📊 Redis URL: {settings.redis_url}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Please install dependencies: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    try:
        from src.config import settings
        
        required_vars = [
            'frappe_url', 'frappe_api_key', 'frappe_api_secret',
            'supabase_url', 'supabase_service_role_key',
            'webhook_secret_key', 'frappe_webhook_token'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(settings, var, None):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing configuration variables: {missing_vars}")
            print("💡 Please check your .env file")
            return False
        else:
            print("✅ All required configuration variables are set")
            return True
            
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Frappe-Supabase Sync Service Setup Test")
    print("=" * 50)
    
    # Test configuration first
    config_ok = test_configuration()
    
    if config_ok:
        # Test imports
        imports_ok = test_imports()
        
        if imports_ok:
            print("\n🎉 Setup test completed successfully!")
            print("🚀 You can now run: python main.py")
        else:
            print("\n❌ Setup test failed - import issues")
    else:
        print("\n❌ Setup test failed - configuration issues")
