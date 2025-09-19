#!/usr/bin/env python3
"""
Helper script to guide you through getting Supabase keys
"""
import webbrowser
import os

def main():
    print("🔑 Supabase Keys Setup Guide")
    print("=" * 50)
    
    print("\n📋 To get your Supabase Service Role Key:")
    print("1. Go to your Supabase project dashboard")
    print("2. Click on 'Settings' in the left sidebar")
    print("3. Click on 'API' in the settings menu")
    print("4. You'll see two keys:")
    print("   - 'anon' key (public key)")
    print("   - 'service_role' key (secret key)")
    print("5. Copy the 'service_role' key")
    
    print("\n🌐 Opening Supabase Dashboard...")
    try:
        webbrowser.open("https://supabase.com/dashboard")
        print("✅ Opened Supabase dashboard in your browser")
    except:
        print("❌ Could not open browser automatically")
        print("   Please go to: https://supabase.com/dashboard")
    
    print("\n📝 Once you have the service role key:")
    print("1. Open the .env file in this directory")
    print("2. Find the line: SUPABASE_SERVICE_ROLE_KEY=your_key_here")
    print("3. Replace 'your_key_here' with your actual service role key")
    print("4. Save the file")
    
    print("\n🔍 Current .env file location:")
    env_path = os.path.join(os.getcwd(), ".env")
    print(f"   {env_path}")
    
    print("\n⚠️  Security Note:")
    print("   - Never commit the service role key to version control")
    print("   - Keep it secure and private")
    print("   - Only use it in server-side applications")
    
    print("\n✅ After updating the .env file, run:")
    print("   python test_mappings_standalone.py")

if __name__ == "__main__":
    main()
