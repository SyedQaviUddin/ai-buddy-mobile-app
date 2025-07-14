#!/usr/bin/env python3
"""
Test script for Buddy AI simplified authentication system
Tests user registration, login, and email functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simple_auth import SimpleAuthManager
from email_manager import EmailManager
import json

def test_simple_auth():
    """Test simplified authentication system"""
    print("🔍 Testing simplified authentication system...")
    
    try:
        auth = SimpleAuthManager()
        
        # Test user registration
        test_email = "test@example.com"
        test_password = "testpassword123"
        
        print(f"🔍 Testing user registration for {test_email}...")
        success, message, passkey = auth.register_user(test_email, test_password)
        
        if success:
            print(f"✅ User registration successful!")
            print(f"📧 Generated passkey: {passkey}")
            
            # Test passkey verification
            print("🔍 Testing passkey verification...")
            verify_success, verify_email = auth.verify_passkey(passkey)
            
            if verify_success and verify_email == test_email:
                print("✅ Passkey verification successful!")
            else:
                print("❌ Passkey verification failed!")
                return False
            
            # Test email/password login
            print("🔍 Testing email/password login...")
            login_success, login_passkey = auth.verify_email_password(test_email, test_password)
            
            if login_success and login_passkey == passkey:
                print("✅ Email/password login successful!")
            else:
                print("❌ Email/password login failed!")
                return False
            
            # Test user info
            print("🔍 Testing user info retrieval...")
            user_info = auth.get_user_info(passkey)
            if user_info and user_info['email'] == test_email:
                print("✅ User info retrieval successful!")
            else:
                print("❌ User info retrieval failed!")
                return False
            
            return True
        else:
            print(f"❌ User registration failed: {message}")
            return False
            
    except Exception as e:
        print(f"❌ Authentication test error: {e}")
        return False

def test_email_functionality():
    """Test email functionality"""
    print("\n📧 Testing email functionality...")
    
    try:
        email_mgr = EmailManager()
        
        # Test email configuration loading
        if not email_mgr.config:
            print("❌ Email configuration not found!")
            return False
        
        print("✅ Email configuration loaded successfully!")
        print(f"📧 SMTP Server: {email_mgr.config.get('smtp_server')}")
        print(f"📧 Email: {email_mgr.config.get('email')}")
        
        # Test email sending (optional - uncomment to test)
        # test_email = "your-test-email@example.com"  # Replace with your test email
        # print(f"🔍 Testing email sending to {test_email}...")
        # success, message = email_mgr.send_welcome_email(test_email, "test@example.com")
        # if success:
        #     print("✅ Test email sent successfully!")
        # else:
        #     print(f"❌ Test email failed: {message}")
        
        return True
        
    except Exception as e:
        print(f"❌ Email test error: {e}")
        return False

def test_config_files():
    """Test configuration files"""
    print("\n⚙️ Testing configuration files...")
    
    config_files = [
        "../config/email_config.json"
    ]
    
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"✅ {config_file} loaded successfully!")
        except Exception as e:
            print(f"❌ {config_file} failed to load: {e}")
            return False
    
    return True

def main():
    """Main test function"""
    print("🚀 Buddy AI Simplified System Test")
    print("=" * 50)
    
    # Test configuration files
    if not test_config_files():
        print("\n❌ Configuration test failed!")
        return
    
    # Test authentication functionality
    if not test_simple_auth():
        print("\n❌ Authentication test failed!")
        return
    
    # Test email functionality
    if not test_email_functionality():
        print("\n❌ Email test failed!")
        return
    
    print("\n🎉 All tests passed! The system is ready to use.")
    print("\n📋 Next steps:")
    print("1. Run the main GUI: python gui.py")
    print("2. Register a new user account")
    print("3. Check your email for the passkey")
    print("4. Login with the passkey or email/password")
    print("\n💡 Note: This system uses JSON files for user storage.")
    print("   For production use, consider setting up MySQL database.")

if __name__ == "__main__":
    main() 