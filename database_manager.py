import mysql.connector
import json
import os
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Tuple

class DatabaseManager:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'database_config.json')
        self.connection = None
        self.setup_database()
    
    def get_connection(self):
        """Get database connection"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            return mysql.connector.connect(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                port=config['port']
            )
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    def setup_database(self):
        """Create database and tables if they don't exist"""
        try:
            # First connect without database to create it
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            temp_conn = mysql.connector.connect(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                port=config['port']
            )
            
            cursor = temp_conn.cursor()
            
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']}")
            cursor.execute(f"USE {config['database']}")
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    passkey VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            temp_conn.commit()
            cursor.close()
            temp_conn.close()
            
        except Exception as e:
            print(f"Database setup error: {e}")
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def generate_passkey(self) -> str:
        """Generate a secure passkey"""
        return secrets.token_urlsafe(32)
    
    def register_user(self, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """Register a new user and return (success, message, passkey)"""
        try:
            conn = self.get_connection()
            if not conn:
                return False, "Database connection failed", None
            
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return False, "User with this email already exists", None
            
            # Hash password and generate passkey
            password_hash = self.hash_password(password)
            passkey = self.generate_passkey()
            
            # Insert new user
            cursor.execute("""
                INSERT INTO users (email, password_hash, passkey)
                VALUES (%s, %s, %s)
            """, (email, password_hash, passkey))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True, "Registration successful", passkey
            
        except Exception as e:
            print(f"Registration error: {e}")
            return False, f"Registration failed: {str(e)}", None
    
    def verify_passkey(self, passkey: str) -> Tuple[bool, Optional[str]]:
        """Verify passkey and return (success, email)"""
        try:
            conn = self.get_connection()
            if not conn:
                return False, None
            
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT email FROM users 
                WHERE passkey = %s AND is_active = TRUE
            """, (passkey,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                # Update last login
                self.update_last_login(passkey)
                return True, result[0]
            else:
                return False, None
                
        except Exception as e:
            print(f"Passkey verification error: {e}")
            return False, None
    
    def verify_email_password(self, email: str, password: str) -> Tuple[bool, Optional[str]]:
        """Verify email and password, return (success, passkey)"""
        try:
            conn = self.get_connection()
            if not conn:
                return False, None
            
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            cursor.execute("""
                SELECT passkey FROM users 
                WHERE email = %s AND password_hash = %s AND is_active = TRUE
            """, (email, password_hash))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                # Update last login
                self.update_last_login(result[0])
                return True, result[0]
            else:
                return False, None
                
        except Exception as e:
            print(f"Email/password verification error: {e}")
            return False, None
    
    def update_last_login(self, passkey: str):
        """Update last login timestamp"""
        try:
            conn = self.get_connection()
            if not conn:
                return
            
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP 
                WHERE passkey = %s
            """, (passkey,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Update last login error: {e}")
    
    def get_user_info(self, passkey: str) -> Optional[dict]:
        """Get user information by passkey"""
        try:
            conn = self.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id, email, created_at, last_login 
                FROM users WHERE passkey = %s AND is_active = TRUE
            """, (passkey,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return result
            
        except Exception as e:
            print(f"Get user info error: {e}")
            return None 