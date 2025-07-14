import json
import os
import hashlib
import secrets
from typing import Optional, Tuple
from email_manager import EmailManager
import time

class SimpleAuthManager:
    def __init__(self):
        self.users_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.json')
        self.users = self.load_users()
        self.email_manager = EmailManager()
        self.login_attempts = {}  # Track failed login attempts
        self.locked_users = {}    # Track locked users and lockout time
        self.lockout_threshold = 5  # 5 failed attempts
        self.lockout_duration = 300  # 5 minutes in seconds
    
    def load_users(self) -> dict:
        """Load users from JSON file"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading users: {e}")
        return {}
    
    def save_users(self):
        """Save users to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
        except Exception as e:
            print(f"Error saving users: {e}")
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def generate_passkey(self) -> str:
        """Generate a secure passkey"""
        return secrets.token_urlsafe(32)
    
    def register_user(self, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """Register a new user and return (success, message, passkey)"""
        try:
            # Check if user already exists
            if email in self.users:
                return False, "User with this email already exists", None
            
            # Hash password and generate passkey
            password_hash = self.hash_password(password)
            passkey = self.generate_passkey()
            
            # Store user
            self.users[email] = {
                "password_hash": password_hash,
                "passkey": passkey,
                "created_at": str(os.path.getctime(self.users_file)) if os.path.exists(self.users_file) else "now",
                "is_active": True
            }
            
            self.save_users()
            return True, "Registration successful", passkey
            
        except Exception as e:
            print(f"Registration error: {e}")
            return False, f"Registration failed: {str(e)}", None
    
    def verify_passkey(self, passkey: str) -> Tuple[bool, Optional[str]]:
        """Verify passkey and return (success, email)"""
        try:
            for email, user_data in self.users.items():
                if user_data.get('passkey') == passkey and user_data.get('is_active', True):
                    return True, email
            return False, None
                
        except Exception as e:
            print(f"Passkey verification error: {e}")
            return False, None
    
    def verify_email_password(self, email: str, password: str) -> Tuple[bool, Optional[str]]:
        """Verify email and password, return (success, passkey) with lockout and attempt tracking"""
        try:
            # Check lockout
            if email in self.locked_users:
                lock_time = self.locked_users[email]
                if time.time() - lock_time < self.lockout_duration:
                    return False, f"Account locked. Try again in {int(self.lockout_duration - (time.time() - lock_time))} seconds."
                else:
                    del self.locked_users[email]
                    self.login_attempts[email] = 0
            if email in self.users:
                user_data = self.users[email]
                password_hash = self.hash_password(password)
                if user_data.get('password_hash') == password_hash and user_data.get('is_active', True):
                    self.login_attempts[email] = 0  # Reset on success
                    return True, user_data.get('passkey')
                else:
                    # Track failed attempts
                    self.login_attempts[email] = self.login_attempts.get(email, 0) + 1
                    if self.login_attempts[email] >= self.lockout_threshold:
                        self.locked_users[email] = time.time()
                        return False, "Account locked due to too many failed attempts. Try again later."
            return False, None
        except Exception as e:
            print(f"Email/password verification error: {e}")
            return False, None
    
    def get_user_info(self, passkey: str) -> Optional[dict]:
        """Get user information by passkey"""
        try:
            for email, user_data in self.users.items():
                if user_data.get('passkey') == passkey and user_data.get('is_active', True):
                    return {
                        'email': email,
                        'created_at': user_data.get('created_at', 'unknown'),
                        'is_active': user_data.get('is_active', True)
                    }
            return None
            
        except Exception as e:
            print(f"Get user info error: {e}")
            return None
    
    def reset_password(self, email: str) -> Tuple[bool, str]:
        """Stub for password reset (to be implemented with email verification)"""
        if email not in self.users:
            return False, "Email not registered."
        # In a real system, send a reset link or code via email
        return True, "Password reset link sent to your email (feature coming soon)." 