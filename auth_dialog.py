import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import re
from typing import Callable, Optional
from simple_auth import SimpleAuthManager
from email_manager import EmailManager

class AuthDialog:
    def __init__(self, parent, on_success: Callable[[str], None]):
        self.parent = parent
        self.on_success = on_success
        self.auth_manager = SimpleAuthManager()
        self.email_manager = EmailManager()
        
        # Create dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Buddy AI - Authentication")
        self.dialog.geometry("500x700")
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.center_dialog()
        
        # Make dialog modal (but do not block in __init__)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Variables
        self.current_mode = tk.StringVar(value="login")
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.passkey_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()
        
        self.setup_ui()
        
        # Focus on dialog
        self.dialog.focus_set()
        # Do not call wait_window here!
    
    def center_dialog(self):
        """Center the dialog on screen"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame, 
            text="Buddy AI", 
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#2c3e50"
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ctk.CTkLabel(
            main_frame,
            text="Your AI Assistant",
            font=ctk.CTkFont(size=16),
            text_color="#7f8c8d"
        )
        subtitle_label.pack(pady=(0, 30))
        
        # Mode selector
        mode_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(0, 20))
        
        login_btn = ctk.CTkButton(
            mode_frame,
            text="Login",
            command=lambda: self.switch_mode("login"),
            width=120,
            height=35,
            fg_color="#3498db" if self.current_mode.get() == "login" else "#34495e",
            hover_color="#2980b9" if self.current_mode.get() == "login" else "#2c3e50"
        )
        login_btn.pack(side="left", padx=(0, 10))
        
        register_btn = ctk.CTkButton(
            mode_frame,
            text="Register",
            command=lambda: self.switch_mode("register"),
            width=120,
            height=35,
            fg_color="#3498db" if self.current_mode.get() == "register" else "#34495e",
            hover_color="#2980b9" if self.current_mode.get() == "register" else "#2c3e50"
        )
        register_btn.pack(side="left")
        
        # Store buttons for color updates
        self.login_btn = login_btn
        self.register_btn = register_btn
        
        # Content frame
        self.content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)
        
        # Show initial content
        self.show_login_content()
    
    def switch_mode(self, mode: str):
        """Switch between login and register modes"""
        self.current_mode.set(mode)
        
        # Update button colors
        if mode == "login":
            self.login_btn.configure(fg_color="#3498db", hover_color="#2980b9")
            self.register_btn.configure(fg_color="#34495e", hover_color="#2c3e50")
            self.show_login_content()
        else:
            self.login_btn.configure(fg_color="#34495e", hover_color="#2c3e50")
            self.register_btn.configure(fg_color="#3498db", hover_color="#2980b9")
            self.show_register_content()
    
    def show_login_content(self):
        """Show login content"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Login options
        options_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        options_frame.pack(fill="x", pady=(0, 20))
        
        # Passkey login
        passkey_frame = ctk.CTkFrame(options_frame)
        passkey_frame.pack(fill="x", pady=(0, 15))
        
        passkey_label = ctk.CTkLabel(
            passkey_frame,
            text="Login with Passkey",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2c3e50"
        )
        passkey_label.pack(pady=(15, 10))
        
        passkey_entry = ctk.CTkEntry(
            passkey_frame,
            placeholder_text="Enter your passkey",
            textvariable=self.passkey_var,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        passkey_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        passkey_login_btn = ctk.CTkButton(
            passkey_frame,
            text="Login with Passkey",
            command=self.login_with_passkey,
            height=40,
            fg_color="#27ae60",
            hover_color="#229954"
        )
        passkey_login_btn.pack(fill="x", padx=20, pady=(0, 15))
        
        # Divider
        divider = ctk.CTkFrame(options_frame, height=2, fg_color="#bdc3c7")
        divider.pack(fill="x", pady=15)
        
        # Email/Password login
        email_frame = ctk.CTkFrame(options_frame)
        email_frame.pack(fill="x")
        
        email_label = ctk.CTkLabel(
            email_frame,
            text="Login with Email & Password",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2c3e50"
        )
        email_label.pack(pady=(15, 10))
        
        email_entry = ctk.CTkEntry(
            email_frame,
            placeholder_text="Enter your email",
            textvariable=self.email_var,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        email_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        password_entry = ctk.CTkEntry(
            email_frame,
            placeholder_text="Enter your password",
            textvariable=self.password_var,
            show="*",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        password_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        email_login_btn = ctk.CTkButton(
            email_frame,
            text="Login with Email",
            command=self.login_with_email,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        email_login_btn.pack(fill="x", padx=20, pady=(0, 15))
        
        # Add password reset link
        reset_btn = ctk.CTkButton(
            email_frame,
            text="Forgot Password?",
            command=self.reset_password,
            fg_color="#e67e22",
            hover_color="#d35400",
            height=32
        )
        reset_btn.pack(fill="x", padx=20, pady=(0, 10))
    
    def show_register_content(self):
        """Show registration content"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Registration form
        form_frame = ctk.CTkFrame(self.content_frame)
        form_frame.pack(fill="x")
        
        register_label = ctk.CTkLabel(
            form_frame,
            text="Create New Account",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#2c3e50"
        )
        register_label.pack(pady=(20, 15))
        
        # Email field
        email_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Enter your email address",
            textvariable=self.email_var,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        email_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        # Password field
        password_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Create a password",
            textvariable=self.password_var,
            show="*",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        password_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        # Confirm password field
        confirm_password_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Confirm your password",
            textvariable=self.confirm_password_var,
            show="*",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        confirm_password_entry.pack(fill="x", padx=20, pady=(0, 20))
        
        # Register button
        register_btn = ctk.CTkButton(
            form_frame,
            text="Create Account",
            command=self.register_user,
            height=45,
            fg_color="#27ae60",
            hover_color="#229954",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        register_btn.pack(fill="x", padx=20, pady=(0, 20))
        
        # Info text
        info_text = ctk.CTkLabel(
            form_frame,
            text="A secure passkey will be sent to your email address",
            font=ctk.CTkFont(size=12),
            text_color="#7f8c8d"
        )
        info_text.pack(pady=(0, 20))
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_password(self, password: str) -> bool:
        """Validate password strength"""
        return len(password) >= 6
    
    def login_with_passkey(self):
        print("[DEBUG] Login with passkey button pressed")
        passkey = self.passkey_var.get().strip()
        if not passkey:
            print("[DEBUG] No passkey entered")
            messagebox.showerror("Error", "Please enter your passkey")
            return
        threading.Thread(target=self._login_with_passkey_thread, args=(passkey,), daemon=True).start()

    def _login_with_passkey_thread(self, passkey: str):
        print(f"[DEBUG] Thread started for passkey: {passkey}")
        try:
            success, email = self.auth_manager.verify_passkey(passkey)
            print(f"[DEBUG] Thread result: success={success}, email={email}")
            self.dialog.after(0, lambda: self._handle_login_result(success, passkey, email))
        except Exception as e:
            print(f"[DEBUG] Exception in passkey thread: {e}")
            self.dialog.after(0, lambda: messagebox.showerror("Error", f"Login failed: {str(e)}"))

    def _handle_login_result(self, success, passkey, email):
        print(f"[DEBUG] Handle login result: success={success}, passkey={passkey}, email={email}")
        if success:
            self._login_success(passkey, email)
        else:
            messagebox.showerror("Error", "Invalid passkey")

    def login_with_email(self):
        print("[DEBUG] Login with email button pressed")
        email = self.email_var.get().strip()
        password = self.password_var.get()
        if not email or not password:
            print("[DEBUG] Email or password not entered")
            messagebox.showerror("Error", "Please enter both email and password")
            return
        if not self.validate_email(email):
            print("[DEBUG] Invalid email format")
            messagebox.showerror("Error", "Please enter a valid email address")
            return
        threading.Thread(target=self._login_with_email_thread, args=(email, password), daemon=True).start()

    def _login_with_email_thread(self, email: str, password: str):
        print(f"[DEBUG] Thread started for email login: {email}")
        try:
            success, passkey = self.auth_manager.verify_email_password(email, password)
            print(f"[DEBUG] Thread result: success={success}, passkey={passkey}")
            self.dialog.after(0, lambda: self._handle_email_login_result(success, passkey, email))
        except Exception as e:
            print(f"[DEBUG] Exception in email login thread: {e}")
            self.dialog.after(0, lambda: messagebox.showerror("Error", f"Login failed: {str(e)}"))

    def _handle_email_login_result(self, success, passkey, email):
        if isinstance(passkey, str) and ("locked" in passkey or "Account locked" in passkey):
            messagebox.showerror("Login Error", passkey)
        elif success and passkey:
            self._login_success(passkey, email)
        else:
            messagebox.showerror("Login Failed", "Invalid email or password. Too many failed attempts may lock your account.")

    def register_user(self):
        print("[DEBUG] Register button pressed")
        email = self.email_var.get().strip()
        password = self.password_var.get()
        confirm_password = self.confirm_password_var.get()
        if not email or not password or not confirm_password:
            print("[DEBUG] Registration fields missing")
            messagebox.showerror("Error", "Please fill in all fields")
            return
        if not self.validate_email(email):
            print("[DEBUG] Invalid registration email format")
            messagebox.showerror("Error", "Please enter a valid email address")
            return
        if not self.validate_password(password):
            print("[DEBUG] Registration password too short")
            messagebox.showerror("Error", "Password must be at least 6 characters long")
            return
        if password != confirm_password:
            print("[DEBUG] Registration passwords do not match")
            messagebox.showerror("Error", "Passwords do not match")
            return
        threading.Thread(target=self._register_user_thread, args=(email, password), daemon=True).start()

    def _register_user_thread(self, email: str, password: str):
        print(f"[DEBUG] Thread started for registration: {email}")
        try:
            success, message, passkey = self.auth_manager.register_user(email, password)
            print(f"[DEBUG] Registration thread result: success={success}, message={message}, passkey={passkey}")
            self.dialog.after(0, lambda: self._handle_register_result(success, message, passkey, email))
        except Exception as e:
            print(f"[DEBUG] Exception in registration thread: {e}")
            self.dialog.after(0, lambda: messagebox.showerror("Error", f"Registration failed: {str(e)}"))

    def _handle_register_result(self, success, message, passkey, email):
        print(f"[DEBUG] Handle register result: success={success}, message={message}, passkey={passkey}, email={email}")
        if success:
            email_success, email_message = self.email_manager.send_passkey_email(email, passkey, email)
            print(f"[DEBUG] Email send result: success={email_success}, message={email_message}")
            if email_success:
                self._registration_success(email, passkey)
            else:
                messagebox.showwarning(
                    "Registration Successful", 
                    f"Account created but email failed: {email_message}\n\nYour passkey: {passkey}\n\nPlease save this passkey!"
                )
        else:
            messagebox.showerror("Error", message)
    
    def _login_success(self, passkey: str, email: str):
        """Handle successful login"""
        messagebox.showinfo("Success", f"Welcome back, {email}!")
        self.dialog.destroy()
        self.on_success(passkey)
    
    def _registration_success(self, email: str, passkey: str):
        """Handle successful registration"""
        messagebox.showinfo(
            "Registration Successful", 
            f"Welcome to Buddy AI, {email}!\n\nYour passkey has been sent to your email.\n\nYou can now log in with your passkey or email/password."
        )
        self.dialog.destroy()
        self.on_success(passkey)

    def reset_password(self):
        email = self.email_var.get().strip()
        if not self.validate_email(email):
            messagebox.showerror("Reset Error", "Please enter a valid email to reset your password.")
            return
        success, msg = self.auth_manager.reset_password(email)
        if success:
            messagebox.showinfo("Reset Password", msg)
        else:
            messagebox.showerror("Reset Error", msg)

    def show_modal(self):
        # Do not block the mainloop; just show the dialog
        pass 