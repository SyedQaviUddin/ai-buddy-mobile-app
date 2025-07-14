import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple

class EmailManager:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'email_config.json')
        self.config = self.load_config()
    
    def load_config(self) -> dict:
        """Load email configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Email config loading error: {e}")
            return {}
    
    def send_passkey_email(self, recipient_email: str, passkey: str, user_email: str) -> Tuple[bool, str]:
        """Send passkey email to user"""
        try:
            if not self.config:
                return False, "Email configuration not found"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config['email']
            msg['To'] = recipient_email
            msg['Subject'] = "Your Buddy AI Passkey"
            
            # Email body
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; text-align: center;">Welcome to Buddy AI!</h2>
                    
                    <p>Hello!</p>
                    
                    <p>Your account has been successfully registered with the email: <strong>{user_email}</strong></p>
                    
                    <p>Here's your secure passkey to access Buddy AI:</p>
                    
                    <div style="background-color: #f8f9fa; border: 2px solid #e9ecef; border-radius: 8px; padding: 15px; margin: 20px 0; text-align: center;">
                        <h3 style="color: #495057; margin: 0; font-family: 'Courier New', monospace; font-size: 18px; letter-spacing: 2px;">
                            {passkey}
                        </h3>
                    </div>
                    
                    <p><strong>Important:</strong></p>
                    <ul>
                        <li>Keep this passkey secure and don't share it with anyone</li>
                        <li>Use this passkey to log into Buddy AI</li>
                        <li>If you lose your passkey, you can log in with your email and password</li>
                    </ul>
                    
                    <p>If you didn't register for Buddy AI, please ignore this email.</p>
                    
                    <hr style="border: none; border-top: 1px solid #e9ecef; margin: 30px 0;">
                    
                    <p style="text-align: center; color: #6c757d; font-size: 14px;">
                        This is an automated message from Buddy AI. Please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            
            if self.config.get('use_tls', True):
                server.starttls()
            
            server.login(self.config['email'], self.config['password'])
            text = msg.as_string()
            server.sendmail(self.config['email'], recipient_email, text)
            server.quit()
            
            return True, "Passkey email sent successfully"
            
        except Exception as e:
            print(f"Email sending error: {e}")
            return False, f"Failed to send email: {str(e)}"
    
    def send_welcome_email(self, recipient_email: str, user_email: str) -> Tuple[bool, str]:
        """Send welcome email to user"""
        try:
            if not self.config:
                return False, "Email configuration not found"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config['email']
            msg['To'] = recipient_email
            msg['Subject'] = "Welcome to Buddy AI!"
            
            # Email body
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; text-align: center;">Welcome to Buddy AI!</h2>
                    
                    <p>Hello!</p>
                    
                    <p>Welcome to Buddy AI! Your account has been successfully created with the email: <strong>{user_email}</strong></p>
                    
                    <p>You can now:</p>
                    <ul>
                        <li>Use voice commands to control your computer</li>
                        <li>Send emails and WhatsApp messages</li>
                        <li>Get weather updates</li>
                        <li>Open applications and websites</li>
                        <li>And much more!</li>
                    </ul>
                    
                    <p>If you have any questions or need support, feel free to reach out.</p>
                    
                    <p>Enjoy using Buddy AI!</p>
                    
                    <hr style="border: none; border-top: 1px solid #e9ecef; margin: 30px 0;">
                    
                    <p style="text-align: center; color: #6c757d; font-size: 14px;">
                        This is an automated message from Buddy AI. Please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            
            if self.config.get('use_tls', True):
                server.starttls()
            
            server.login(self.config['email'], self.config['password'])
            text = msg.as_string()
            server.sendmail(self.config['email'], recipient_email, text)
            server.quit()
            
            return True, "Welcome email sent successfully"
            
        except Exception as e:
            print(f"Welcome email sending error: {e}")
            return False, f"Failed to send welcome email: {str(e)}" 