import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading
import os
import json
import datetime
import sounddevice as sd
import queue
import importlib.util
import speech_recognition as sr
import pyttsx3
import markdown2
import webbrowser
import urllib.parse
import sys
import time
from textblob import TextBlob
import re
import requests
from PIL import Image, ImageTk
import io
# Add HuggingFace transformers for BLIP/CLIP
try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
except ImportError:
    BlipProcessor = None
    BlipForConditionalGeneration = None
try:
    import torch
except ImportError:
    torch = None
try:
    from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import StableDiffusionPipeline
except ImportError:
    StableDiffusionPipeline = None

# Import the new authentication system
from auth_dialog import AuthDialog
from simple_auth import SimpleAuthManager

# Try to import handle_input from main.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    import main
    handle_input = main.handle_input
except Exception as e:
    handle_input = None
    print(f"Could not import handle_input from main.py: {e}")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "Buddy AI"
LOGO_PATH = "bot_logo.png" if os.path.exists("bot_logo.png") else None
HISTORY_FILE = "chat_history.json"
USER_AVATAR_PATH = "user_avatar.png" if os.path.exists("user_avatar.png") else None
AI_AVATAR_PATH = "bot_logo.png" if os.path.exists("bot_logo.png") else None
EMOJI_LIST = ["👍", "😂", "😮", "❤️", "🔥", "👏", "🤔", "😢"]

SIDEBAR_ICONS = [
    "🌦️",  # Weather
    "📰",  # News
    "✉️",  # Email
    "💬",  # WhatsApp
    "⚙️",  # Workflows
    "🔧"   # Settings
]

ALL_CHATS_FILE = "all_chats.json"

class SettingsModal(ctk.CTkToplevel):
    def __init__(self, parent, theme_callback, speaker_callback):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x300")
        self.resizable(False, False)
        self.theme_callback = theme_callback
        self.speaker_callback = speaker_callback
        self.create_widgets()

    def create_widgets(self):
        ctk.CTkLabel(self, text="Settings", font=("Arial", 18, "bold")).pack(pady=10)
        # Theme switch
        ctk.CTkLabel(self, text="Theme:").pack(anchor="w", padx=30, pady=(20, 0))
        self.theme_var = tk.StringVar(value=ctk.get_appearance_mode())
        theme_frame = ctk.CTkFrame(self)
        theme_frame.pack(anchor="w", padx=30, pady=5)
        ctk.CTkRadioButton(theme_frame, text="Dark", variable=self.theme_var, value="dark", command=self.on_theme_change).pack(side="left", padx=5)
        ctk.CTkRadioButton(theme_frame, text="Light", variable=self.theme_var, value="light", command=self.on_theme_change).pack(side="left", padx=5)
        # Speaker output
        ctk.CTkLabel(self, text="Speaker Output:").pack(anchor="w", padx=30, pady=(20, 0))
        self.speaker_var = tk.StringVar()
        self.speaker_dropdown = ctk.CTkComboBox(self, variable=self.speaker_var, width=250)
        self.speaker_dropdown.pack(anchor="w", padx=30, pady=5)
        self.populate_speakers()
        self.speaker_dropdown.bind("<<ComboboxSelected>>", self.on_speaker_change)

    def populate_speakers(self):
        try:
            devices = sd.query_devices()
            speakers = [d['name'] for d in devices if isinstance(d, dict) and d.get('max_output_channels', 0) > 0]
            if not speakers:
                speakers = ["Default"]
            self.speaker_dropdown.configure(values=speakers)
            self.speaker_var.set(speakers[0])
        except Exception:
            self.speaker_dropdown.configure(values=["Default"])
            self.speaker_var.set("Default")

    def on_theme_change(self):
        self.theme_callback(self.theme_var.get())

    def on_speaker_change(self, event=None):
        self.speaker_callback(self.speaker_var.get())

class HistoryPanel(ctk.CTkFrame):
    def __init__(self, parent, export_callback, import_callback, clear_callback, search_callback):
        super().__init__(parent, width=250)
        self.export_callback = export_callback
        self.import_callback = import_callback
        self.clear_callback = clear_callback
        self.search_callback = search_callback
        self.create_widgets()

    def create_widgets(self):
        ctk.CTkLabel(self, text="Chat History", font=("Arial", 16, "bold")).pack(pady=(10, 5))
        # Search bar
        self.search_var = tk.StringVar()
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=10, pady=5)
        search_frame.grid_columnconfigure(0, weight=1)
        search_frame.grid_columnconfigure(1, weight=0)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=0, sticky="ew")
        search_entry.bind("<Return>", lambda e: self.search_callback(self.search_var.get()))
        ctk.CTkButton(search_frame, text="Search", width=60, command=lambda: self.search_callback(self.search_var.get())).grid(row=0, column=1, padx=5)
        # History list
        self.history_list = tk.Listbox(self, height=20, bg="#23272f", fg="#f8f8f2", font=("Segoe UI", 11))
        self.history_list.pack(fill="both", expand=True, padx=10, pady=5)
        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="Export", width=60, command=self.export_callback).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Import", width=60, command=self.import_callback).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Clear", width=60, command=self.clear_callback).pack(side="left", padx=2)

    def update_history(self, history):
        self.history_list.delete(0, tk.END)
        for item in history:
            user = item.get("user", "")
            text = item.get("text", "")
            self.history_list.insert(tk.END, f"{user}: {text}")

def center_popup(dialog, width, height):
    dialog.update_idletasks()
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

class BuddyAIGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x700")
        self.minsize(400, 500)
        self.configure(bg="#222831")
        
        # Authentication and user management
        self.auth_manager = SimpleAuthManager()
        self.current_user_passkey = None
        self.current_user_email = None
        self.profile_name = ""  # Initialize profile_name
        self.profile_avatar_img = None  # Initialize profile_avatar_img
        
        # Initialize components
        self.speaker_output = None
        self.chats = self.load_all_chats()
        if not self.chats:
            self.chats = [{"title": "Chat 1", "history": []}]
        self.current_chat_index = 0
        self.engine = pyttsx3.init()
        rate = self.engine.getProperty('rate')
        self.engine.setProperty('rate', int(rate * 0.9))
        self.input_mode = "text"  # Track input mode
        self.typing_indicator = False
        self.status_var = tk.StringVar(value="Ready")  # Add status var
        
        # Initialize avatar images (will be set later if files exist)
        self.user_avatar_img = None
        self.ai_avatar_img = None
        
        # Show authentication after mainloop starts
        self.withdraw()  # Hide main window until authenticated
        self.after(0, self.show_authentication)
        
        # Bind events
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Configure>", self.on_resize)

        self.live_chat_thread = None  # Track live chat thread
        self.live_chat_indicator = None
        self.uploaded_images = []  # Store uploaded image paths
        self.selected_image_path = None  # Store the currently selected image for input

    def show_authentication(self):
        def on_success(passkey):
            self.current_user_passkey = passkey
            user_info = self.auth_manager.get_user_info(passkey)
            if user_info:
                self.current_user_email = user_info['email']
            for widget in self.winfo_children():
                widget.destroy()
            self.deiconify()  # Show main window
            self.create_widgets()  # This will use the original, full-featured UI
            self.show_welcome_message()
        dialog = AuthDialog(self, on_success)
        # Do not call dialog.show_modal() if it blocks

    def create_widgets(self):
        # Load avatar images if they exist
        if USER_AVATAR_PATH and os.path.exists(USER_AVATAR_PATH):
            self.user_avatar_img = ImageTk.PhotoImage(Image.open(USER_AVATAR_PATH).resize((24, 24)))
        if AI_AVATAR_PATH and os.path.exists(AI_AVATAR_PATH):
            self.ai_avatar_img = ImageTk.PhotoImage(Image.open(AI_AVATAR_PATH).resize((24, 24)))
        
        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=90, corner_radius=0, fg_color="#181a20")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.grid_propagate(False)
        # Sidebar: logo, chat list, settings/profile
        if LOGO_PATH and os.path.exists(LOGO_PATH):
            self.logo_img = ctk.CTkImage(light_image=Image.open(LOGO_PATH), dark_image=Image.open(LOGO_PATH), size=(72, 72))
            self.logo_label = ctk.CTkLabel(self.sidebar, image=self.logo_img, text="")
            self.logo_label.pack(pady=(18, 8))
        else:
            self.logo_label = ctk.CTkLabel(self.sidebar, text="🤖", font=("Segoe UI", 40))
            self.logo_label.pack(pady=(18, 8))
        # New Chat button
        self.new_chat_btn = ctk.CTkButton(self.sidebar, text="＋ New Chat", width=80, height=32, font=("Segoe UI", 12, "bold"), fg_color="#27ae60", hover_color="#229954", text_color="#fff", corner_radius=10, command=self.new_chat)
        self.new_chat_btn.pack(pady=(4, 8))
        ctk.CTkLabel(self.sidebar, text="Chats", font=("Segoe UI", 11, "bold"), text_color="#aaa").pack(pady=(8, 0))
        self.chat_list = tk.Listbox(self.sidebar, height=10, bg="#181a20", fg="#fff", font=("Segoe UI", 11), borderwidth=0, highlightthickness=0, selectbackground="#23272f", activestyle='none')
        self.chat_list.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.chat_list.insert(0, "No chats.")
        self.chat_list.delete(0, tk.END)
        for i, chat in enumerate(self.chats):
            self.chat_list.insert(tk.END, chat["title"])
        self.chat_list.bind("<<ListboxSelect>>", self.on_chat_select)
        # Add WhatsApp, Email, and Weather buttons to the sidebar (matching style)
        self.weather_btn = ctk.CTkButton(self.sidebar, text="Weather", command=self.weather_action, font=("Segoe UI", 11), width=80, height=28, corner_radius=10, fg_color="#3498db", hover_color="#217dbb", text_color="#fff")
        self.weather_btn.pack(pady=4)
        self.email_btn = ctk.CTkButton(self.sidebar, text="Email", command=self.email_action, font=("Segoe UI", 11), width=80, height=28, corner_radius=10, fg_color="#3498db", hover_color="#217dbb", text_color="#fff")
        self.email_btn.pack(pady=4)
        self.whatsapp_btn = ctk.CTkButton(self.sidebar, text="WhatsApp", command=self.whatsapp_action, font=("Segoe UI", 11), width=80, height=28, corner_radius=10, fg_color="#3498db", hover_color="#217dbb", text_color="#fff")
        self.whatsapp_btn.pack(pady=4)
        # Settings/profile at bottom
        self.sidebar_bottom = ctk.CTkFrame(self.sidebar, fg_color="#181a20")
        self.sidebar_bottom.pack(side="bottom", fill="x", pady=8)
        self.theme_btn = ctk.CTkButton(self.sidebar_bottom, text="🌙", width=36, height=36, font=("Segoe UI", 16), fg_color="#23272f", hover_color="#31343b", text_color="#fff", corner_radius=12, command=self.toggle_theme)
        self.theme_btn.pack(side="left", padx=4)
        self.settings_btn = ctk.CTkButton(self.sidebar_bottom, text="⚙️", width=36, height=36, font=("Segoe UI", 16), fg_color="#23272f", hover_color="#31343b", text_color="#fff", corner_radius=12, command=self.open_settings)
        self.settings_btn.pack(side="left", padx=4)
        self.profile_btn = ctk.CTkButton(self.sidebar_bottom, text="👤", width=36, height=36, font=("Segoe UI", 16), fg_color="#23272f", hover_color="#31343b", text_color="#fff", corner_radius=12)
        self.profile_btn.pack(side="left", padx=4)
        # Live Chat toggle button
        self.live_chat_active = False
        self.live_chat_btn = ctk.CTkButton(self.sidebar_bottom, text="🎙️ Live Chat", width=120, height=36, font=("Segoe UI", 12), fg_color="#27ae60", hover_color="#229954", text_color="#fff", corner_radius=12, command=self.toggle_live_chat)
        self.live_chat_btn.pack(side="left", padx=8)

        # --- TOP BAR ---
        self.topbar = ctk.CTkFrame(self, height=48, fg_color="#23272f")
        self.topbar.pack(side="top", fill="x")
        self.topbar.grid_propagate(False)
        self.chat_title_label = ctk.CTkLabel(self.topbar, text=self.chats[self.current_chat_index]["title"], font=("Segoe UI", 14, "bold"), text_color="#fff")
        self.chat_title_label.pack(side="left", padx=16)
        ctk.CTkLabel(self.topbar, text="Turbo Model", font=("Segoe UI", 12), text_color="#aaa").pack(side="left", padx=8)
        ctk.CTkLabel(self.topbar, text="Quick Settings", font=("Segoe UI", 12), text_color="#fff").pack(side="right", padx=16)

        # --- MAIN CHAT AREA ---
        self.main_frame = ctk.CTkFrame(self, fg_color="#181a20")
        self.main_frame.pack(side="left", fill="both", expand=True)
        self.main_frame.grid_propagate(False)
        self.chat_canvas = tk.Canvas(self.main_frame, bg="#181a20", highlightthickness=0, borderwidth=0)
        self.chat_canvas.pack(side="top", fill="both", expand=True, padx=0, pady=(0, 0))
        self.chat_scroll = tk.Scrollbar(self.main_frame, orient="vertical", command=self.chat_canvas.yview)
        self.chat_scroll.pack(side="right", fill="y")
        self.chat_canvas.configure(yscrollcommand=self.chat_scroll.set)
        self.chat_bubble_frame = tk.Frame(self.chat_canvas, bg="#181a20")
        self.chat_canvas.create_window((0, 0), window=self.chat_bubble_frame, anchor="nw")
        self.chat_bubble_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))
        # Welcome message
        self.add_bubble("Welcome to Buddy AI!\nAsk me anything, or start a new chat.", user="Buddy AI", is_welcome=True)

        # --- INPUT BAR ---
        self.input_bar = ctk.CTkFrame(self.main_frame, fg_color="#23272f")
        self.input_bar.pack(side="bottom", fill="x", pady=0, padx=32)
        self.input_bar.grid_columnconfigure(0, weight=0)
        self.input_bar.grid_columnconfigure(1, weight=1)
        self.input_bar.grid_columnconfigure(2, weight=0)
        self.input_bar.grid_columnconfigure(3, weight=0)
        self.input_bar.grid_columnconfigure(4, weight=0)
        self.input_bar.grid_columnconfigure(5, weight=0)
        # Image preview area
        self.image_preview_frame = ctk.CTkFrame(self.input_bar, fg_color="#23272f")
        self.image_preview_frame.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=0)
        self.image_preview_label = None
        self.remove_image_btn = None
        # Text entry
        self.input_entry = ctk.CTkEntry(self.input_bar, placeholder_text="Send a message...", height=40, font=("Segoe UI", 13), corner_radius=20)
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=0)
        self.input_entry.bind("<Return>", self.on_send_and_stop_tts)
        self.input_entry.bind("<Button-1>", lambda e: self.stop_speaking())
        # Buttons (same size and aligned)
        btn_size = 44
        self.send_btn = ctk.CTkButton(self.input_bar, text="➤", width=btn_size, height=btn_size, font=("Segoe UI", 16), corner_radius=10, fg_color="#3498db", hover_color="#217dbb", text_color="#fff", command=self.on_send)
        self.send_btn.grid(row=0, column=2, padx=(0, 8), pady=0)
        self.create_img_btn = ctk.CTkButton(self.input_bar, text="🎨Create image", width=btn_size, height=btn_size, font=("Segoe UI", 16), corner_radius=10, fg_color="#8e44ad", hover_color="#6c3483", text_color="#fff", command=self.open_image_prompt)
        self.create_img_btn.grid(row=0, column=3, padx=(0, 8), pady=0)
        self.mic_btn = ctk.CTkButton(self.input_bar, text="🎤", width=btn_size, height=btn_size, font=("Segoe UI", 16), corner_radius=10, fg_color="#3498db", hover_color="#217dbb", text_color="#fff", command=self.on_mic)
        self.mic_btn.grid(row=0, column=4, padx=(0, 8), pady=0)
        self.image_btn = ctk.CTkButton(self.input_bar, text="📷upload", width=btn_size, height=btn_size, font=("Segoe UI", 16), corner_radius=10, fg_color="#3498db", hover_color="#217dbb", text_color="#fff", command=self.on_image_upload)
        self.image_btn.grid(row=0, column=5, padx=(0, 0), pady=0)
        self.listening = False  # Track mic listening state

        # Profile button opens profile modal
        self.profile_btn.configure(command=self.open_profile)

        # Restore right-side HistoryPanel
        self.history_panel = HistoryPanel(
            self,
            export_callback=self.export_history,
            import_callback=self.import_history,
            clear_callback=self.clear_history,
            search_callback=self.search_history
        )
        self.history_panel.pack(side="right", fill="y", padx=(4, 0), pady=10)
        self.display_chat_history()

    def add_bubble(self, message, user="Buddy AI", is_welcome=False, animated=False):
        # Add a chat bubble to the chat area
        bubble_frame = tk.Frame(self.chat_bubble_frame, bg="#181a20")
        align = "w" if user == "You" else "e"
        bubble_color = "#23272f" if user == "You" else "#3498db"
        text_color = "#fff" if user == "You" else "#fff"
        avatar = "🧑" if user == "You" else "🤖"
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M")
        if is_welcome:
            tk.Label(bubble_frame, text=message, font=("Segoe UI", 13, "italic"), bg="#181a20", fg="#aaa").pack(padx=24, pady=16)
        else:
            tk.Label(bubble_frame, text=avatar, font=("Segoe UI", 18), bg="#181a20", fg=text_color).pack(side="left" if user=="You" else "right", padx=8)
            msg_lbl = tk.Label(bubble_frame, text=message, font=("Segoe UI", 12), bg=bubble_color, fg=text_color, wraplength=480, justify="left", padx=16, pady=10, bd=0, relief="flat")
            msg_lbl.pack(side="left" if user=="You" else "right", padx=4)
            tk.Label(bubble_frame, text=timestamp, font=("Segoe UI", 9), bg="#181a20", fg="#888").pack(side="left" if user=="You" else "right", padx=8)
        bubble_frame.pack(anchor=align, fill="none", pady=6, padx=12)
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)
        if animated:
            self.thinking_bubble = msg_lbl
            self.animate_thinking()

    def animate_thinking(self):
        if not self.typing_indicator:
            return
        if hasattr(self, 'thinking_bubble') and self.thinking_bubble:
            current = getattr(self, '_thinking_dots', 0)
            dots = '.' * (current % 4)
            self.thinking_bubble.configure(text=f'Buddy AI is thinking{dots}')
            self._thinking_dots = (current + 1) % 4
            self.after(500, self.animate_thinking)

    def logout(self):
        """Logout current user"""
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            # Clear user session
            self.current_user_passkey = None
            self.current_user_email = None
            
            # Clear the interface
            for widget in self.winfo_children():
                widget.destroy()
            
            # Show authentication again
            self.show_authentication()

    def show_welcome_message(self):
        self.add_bubble("Welcome to Buddy AI! How can I help you today?", user="Buddy AI", is_welcome=True)
        self.input_entry.focus_set()

    def insert_message(self, message, user="Buddy AI", timestamp=None, save=True, markdown=False):
        self.add_bubble(message, user=user)
        if save:
            self.chats[self.current_chat_index]["history"].append({"user": user, "text": message})
            self.save_all_chats()
            if hasattr(self, "history_panel"):
                self.history_panel.update_history(self.chats[self.current_chat_index]["history"])
        self.input_entry.focus_set()

    def render_markdown(self, text):
        # For now, just add as plain text. You can extend this to render markdown in bubbles.
        self.add_bubble(text, user="Buddy AI")

    def on_send_and_stop_tts(self, event=None):
        self.stop_speaking()
        self.on_send()

    def on_send(self, event=None):
        user_text = self.input_entry.get().strip()
        image_path = self.selected_image_path
        if not user_text and not image_path:
            return
        self.input_mode = "text"
        self.input_entry.delete(0, tk.END)
        self.remove_selected_image()
        self.status_var.set("Thinking...")
        self.show_loading()
        # Send both image and text as a single bubble if image is present
        if image_path:
            self.add_image_text_bubble(image_path, user_text, user="You")
            if ("image" in user_text.lower() or "this" in user_text.lower()) and ("what" in user_text.lower() or "describe" in user_text.lower() or "search" in user_text.lower()):
                threading.Thread(target=self.handle_image_query, args=(user_text,), daemon=True).start()
            else:
                threading.Thread(target=self.get_ai_response, args=(user_text,), daemon=True).start()
        else:
            self.insert_message(user_text, user="You")
            threading.Thread(target=self.get_ai_response, args=(user_text,), daemon=True).start()

    def get_ai_response(self, user_text):
        try:
            if handle_input:
                # Use short_answer for concise output unless user asks for details
                if any(word in user_text.lower() for word in ["explain", "details", "long", "why", "how", "more"]):
                    response = handle_input(user_text)
                else:
                    response = handle_input(user_text)
            else:
                import main
                response = main.short_answer(user_text)
            self.after(0, lambda: self.display_ai_response(response))
        except Exception as e:
            self.after(0, lambda: self.display_ai_response(f"Error: {str(e)}"))

    def display_ai_response(self, response):
        self.hide_loading()
        self.insert_message(response, user="Buddy AI", markdown=True)
        self.status_var.set("Ready")
        if getattr(self, 'last_input_was_voice', False):
            self.speak(response)
            self.last_input_was_voice = False
        elif self.input_mode == "voice":
            self.speak(response)

    def show_loading(self):
        self.typing_indicator = True
        if not hasattr(self, 'thinking_bubble') or self.thinking_bubble is None:
            self.thinking_bubble = self.add_bubble('Buddy AI is thinking', user='Buddy AI', is_welcome=False, animated=True)
        self.animate_thinking()

    def hide_loading(self):
        self.typing_indicator = False
        if hasattr(self, 'thinking_bubble') and self.thinking_bubble:
            self.thinking_bubble.destroy()
            self.thinking_bubble = None

    def on_mic(self):
        if getattr(self, 'listening', False):
            self.listening = False
            self.reset_mic_button()
            return
        self.input_mode = "voice"
        self.last_input_was_voice = True
        self.listening = True
        self.mic_btn.configure(text="Listening...", fg_color="#e74c3c")
        threading.Thread(target=self.capture_voice_input, daemon=True).start()

    def capture_voice_input(self):
        try:
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=1)
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                if not getattr(self, 'listening', True):
                    self.after(0, self.reset_mic_button)
                    return
                text = r.recognize_google(audio)  # type: ignore
                self.after(0, lambda: self.voice_to_text(text))
        except sr.WaitTimeoutError:
            self.after(0, self.reset_mic_button)
        except sr.UnknownValueError:
            self.after(0, self.reset_mic_button)
        except Exception as e:
            print(f"Voice recognition error: {e}")
            self.after(0, self.reset_mic_button)
        finally:
            self.listening = False

    def voice_to_text(self, text):
        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, text)
        self.on_send()

    def reset_mic_button(self):
        self.mic_btn.configure(text="🎤", fg_color="#3498db")
        self.listening = False

    def open_settings(self):
        dialog = SettingsModal(self, self.set_theme, self.set_speaker_output)
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.focus_force()

    def set_theme(self, theme):
        ctk.set_appearance_mode(theme)

    def set_speaker_output(self, speaker):
        self.speaker_output = speaker

    def load_all_chats(self):
        try:
            if os.path.exists(ALL_CHATS_FILE):
                with open(ALL_CHATS_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading all chats: {e}")
        return []

    def save_all_chats(self):
        try:
            with open(ALL_CHATS_FILE, 'w') as f:
                json.dump(self.chats, f, indent=2)
        except Exception as e:
            print(f"Error saving all chats: {e}")

    def export_history(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.chats[self.current_chat_index]["history"], f, indent=2)
                messagebox.showinfo("Success", "History exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export history: {e}")

    def import_history(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    imported_history = json.load(f)
                self.chats[self.current_chat_index]["history"].extend(imported_history)
                self.save_all_chats()
                messagebox.showinfo("Success", "History imported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import history: {e}")

    def clear_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all chat history for this chat?"):
            self.chats[self.current_chat_index]["history"] = []
            self.save_all_chats()
            for widget in self.chat_bubble_frame.winfo_children():
                widget.destroy()
            self.add_bubble("Welcome to Buddy AI!\nAsk me anything, or start a new chat.", user="Buddy AI", is_welcome=True)
            if hasattr(self, "history_panel"):
                self.history_panel.update_history(self.chats[self.current_chat_index]["history"])

    def search_history(self, query):
        if not query:
            return
        results = []
        for item in self.chats[self.current_chat_index]["history"]:
            if query.lower() in item.get('text', '').lower():
                results.append(item)
        if results:
            for widget in self.chat_bubble_frame.winfo_children():
                widget.destroy()
            for item in results:
                self.add_bubble(item['text'], user=item.get('user', 'Unknown'))
        else:
            messagebox.showinfo("Search", "No results found.")

    def speak(self, text):
        try:
            # Remove all emojis from the text before speaking
            def remove_emoji(s):
                emoji_pattern = re.compile(
                    "["
                    u"\U0001F600-\U0001F64F"  # emoticons
                    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                    u"\U0001F680-\U0001F6FF"  # transport & map symbols
                    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    u"\U00002700-\U000027BF"  # Dingbats
                    u"\U000024C2-\U0001F251"  # Enclosed characters
                    "]+", flags=re.UNICODE)
                return emoji_pattern.sub(r'', s)
            text = remove_emoji(text)
            if self.speaker_output and self.speaker_output != "Default":
                pass
            # Human-like TTS: add pauses between sentences
            sentences = text.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    self.engine.say(sentence)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Speech error: {e}")

    def on_resize(self, event):
        font_size = max(12, int(self.winfo_width() / 60))
        if hasattr(self, "send_btn"):
            self.send_btn.configure(font=("Segoe UI", font_size))
        if hasattr(self, "mic_btn"):
            self.mic_btn.configure(font=("Segoe UI", font_size+2))
        # Sidebar button size - check if buttons exist
        sidebar_buttons = []
        if hasattr(self, "settings_btn"):
            sidebar_buttons.append(self.settings_btn)
        for btn in sidebar_buttons:
            btn.configure(font=("Segoe UI", font_size))

    def weather_action(self):
        def send_weather():
            location = entry.get().strip()
            if location:
                self.input_entry.delete(0, tk.END)
                self.input_entry.insert(0, f"weather in {location}")
                self.on_send()
            dialog.destroy()
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Weather Check")
        dialog.geometry("320x140")
        dialog.resizable(True, True)
        center_popup(dialog, 320, 140)
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.focus_force()
        ctk.CTkLabel(dialog, text="Enter location:", font=("Segoe UI", 11)).pack(pady=10)
        entry = ctk.CTkEntry(dialog, width=180, height=28, font=("Segoe UI", 10))
        entry.pack(pady=4)
        entry.focus_set()
        
        ctk.CTkButton(dialog, text="Check Weather", command=send_weather, width=120, height=28, font=("Segoe UI", 10)).pack(pady=10)
        entry.bind("<Return>", lambda e: send_weather())

    def email_action(self):
        def send_email():
            recipient = entry_recipient.get().strip()
            subject = entry_subject.get().strip()
            body = text_body.get("1.0", tk.END).strip()
            if recipient and subject and body:
                self.input_entry.delete(0, tk.END)
                self.input_entry.insert(0, f"send email to {recipient} subject: {subject} body: {body}")
                self.on_send()
            dialog.destroy()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Send Email")
        dialog.geometry("400x320")
        dialog.resizable(True, True)
        center_popup(dialog, 400, 320)
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.focus_force()
        ctk.CTkLabel(dialog, text="Enter recipient email:", font=("Segoe UI", 11)).pack(pady=(16, 2))
        entry_recipient = ctk.CTkEntry(dialog, width=260, height=28, font=("Segoe UI", 11))
        entry_recipient.pack(pady=2)
        ctk.CTkLabel(dialog, text="Subject:", font=("Segoe UI", 11)).pack(pady=(10, 2))
        entry_subject = ctk.CTkEntry(dialog, width=260, height=28, font=("Segoe UI", 11))
        entry_subject.pack(pady=2)
        ctk.CTkLabel(dialog, text="Body:", font=("Segoe UI", 11)).pack(pady=(10, 2))
        text_body = ctk.CTkTextbox(dialog, width=260, height=80, font=("Segoe UI", 11))
        text_body.pack(pady=2)
        send_btn = ctk.CTkButton(dialog, text="Send Email", command=send_email, width=80, height=28, font=("Segoe UI", 11), corner_radius=10, fg_color="#3498db", hover_color="#217dbb", text_color="#fff")
        send_btn.pack(pady=16)
        entry_recipient.focus_set()
        entry_recipient.bind("<Return>", lambda e: entry_subject.focus_set())
        entry_subject.bind("<Return>", lambda e: text_body.focus_set())
        text_body.bind("<Control-Return>", lambda e: send_email())

    def whatsapp_action(self):
        def send_hello():
            recipient = entry.get().strip()
            if recipient:
                self.input_entry.delete(0, tk.END)
                self.input_entry.insert(0, f"send whatsapp hello to {recipient}")
                self.on_send()
            dialog.destroy()
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Send WhatsApp")
        dialog.geometry("320x140")
        dialog.resizable(True, True)
        center_popup(dialog, 320, 140)
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.focus_force()
        ctk.CTkLabel(dialog, text="Enter phone number:", font=("Segoe UI", 11)).pack(pady=10)
        entry = ctk.CTkEntry(dialog, width=180, height=28, font=("Segoe UI", 10))
        entry.pack(pady=4)
        entry.focus_set()
        
        ctk.CTkButton(dialog, text="Send WhatsApp", command=send_hello, width=120, height=28, font=("Segoe UI", 10)).pack(pady=10)
        entry.bind("<Return>", lambda e: send_hello())

    def on_close(self):
        self.save_all_chats()
        self.quit()

    def new_chat(self):
        # Create a new chat, switch to it, and update UI
        chat_title = datetime.datetime.now().strftime("Chat %Y-%m-%d %H:%M:%S")
        self.chats.append({"title": chat_title, "history": []})
        self.current_chat_index = len(self.chats) - 1
        self.chat_list.insert(tk.END, chat_title)
        self.chat_list.selection_clear(0, tk.END)
        self.chat_list.selection_set(self.current_chat_index)
        self.display_chat_history()
        self.save_all_chats()

    def toggle_theme(self):
        # Placeholder for theme toggle functionality
        pass

    def open_profile(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Profile")
        dialog.geometry("400x400")
        dialog.resizable(True, True)
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.focus_force()
        ctk.CTkLabel(dialog, text="Profile", font=("Segoe UI", 18, "bold")).pack(pady=(16, 8))
        # Avatar upload
        avatar_frame = ctk.CTkFrame(dialog)
        avatar_frame.pack(pady=8)
        avatar_img = getattr(self, "profile_avatar_img", None)
        avatar_label = ctk.CTkLabel(avatar_frame, image=avatar_img, text="" if avatar_img else "🧑", width=64, height=64)
        avatar_label.pack()
        def upload_avatar():
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
            if file_path:
                from PIL import Image, ImageTk
                img = Image.open(file_path).resize((64, 64))
                self.profile_avatar_img = ImageTk.PhotoImage(img)
                avatar_label.configure(image=self.profile_avatar_img, text="")
        ctk.CTkButton(avatar_frame, text="Upload Avatar", command=upload_avatar, width=120, height=28, font=("Segoe UI", 11)).pack(pady=4)
        # Name, Email, Password fields
        ctk.CTkLabel(dialog, text="Name:", font=("Segoe UI", 12)).pack(pady=(8, 2))
        name_var = tk.StringVar(value=getattr(self, "profile_name", ""))
        name_entry = ctk.CTkEntry(dialog, textvariable=name_var, width=260, height=28, font=("Segoe UI", 12))
        name_entry.pack(pady=2)
        ctk.CTkLabel(dialog, text="Email:", font=("Segoe UI", 12)).pack(pady=(8, 2))
        email_var = tk.StringVar(value=self.current_user_email or "")
        email_entry = ctk.CTkEntry(dialog, textvariable=email_var, width=260, height=28, font=("Segoe UI", 12))
        email_entry.pack(pady=2)
        ctk.CTkLabel(dialog, text="Password:", font=("Segoe UI", 12)).pack(pady=(8, 2))
        password_var = tk.StringVar(value="")
        password_entry = ctk.CTkEntry(dialog, textvariable=password_var, width=260, height=28, font=("Segoe UI", 12), show="*")
        password_entry.pack(pady=2)
        show_password_var = tk.BooleanVar(value=False)
        def toggle_password():
            if show_password_var.get():
                password_entry.configure(show="")
            else:
                password_entry.configure(show="*")
        show_password_btn = ctk.CTkCheckBox(dialog, text="Show Password", variable=show_password_var, command=toggle_password)
        show_password_btn.pack(pady=(0, 4))
        def reset_password():
            email = email_var.get().strip()
            if not email:
                messagebox.showerror("Error", "Enter your email to reset password.")
                return
            success, msg = self.auth_manager.reset_password(email)
            if success:
                messagebox.showinfo("Reset Password", msg)
            else:
                messagebox.showerror("Reset Password", msg)
        ctk.CTkButton(dialog, text="Reset Password", command=reset_password, width=120, height=28, font=("Segoe UI", 11)).pack(pady=(0, 8))
        # Validation and save
        def save_profile():
            if not name_var.get().strip():
                messagebox.showerror("Error", "Name cannot be empty")
                return
            if not email_var.get().strip() or "@" not in email_var.get():
                messagebox.showerror("Error", "Enter a valid email")
                return
            self.profile_name = name_var.get()
            self.current_user_email = email_var.get()
            # Save password logic here if needed
            dialog.destroy()
        ctk.CTkButton(dialog, text="Save", command=save_profile, width=80, height=28, font=("Segoe UI", 12), corner_radius=10, fg_color="#3498db", hover_color="#217dbb", text_color="#fff").pack(pady=16)

    def toggle_live_chat(self):
        if self.live_chat_active:
            self.live_chat_active = False
            self.live_chat_btn.configure(fg_color="#27ae60", text="🎙️ Live Chat")
            self.add_bubble("Live Voice Chat mode disabled.", user="Buddy AI")
            if self.live_chat_indicator:
                self.live_chat_indicator.destroy()
                self.live_chat_indicator = None
        else:
            self.live_chat_active = True
            self.live_chat_btn.configure(fg_color="#e67e22", text="🛑 Stop Live Chat")
            self.add_bubble("Live Voice Chat mode enabled. Speak and I'll reply!", user="Buddy AI")
            if not self.live_chat_indicator:
                self.live_chat_indicator = ctk.CTkLabel(self.sidebar_bottom, text="● Live", text_color="#e74c3c", font=("Segoe UI", 12, "bold"))
                self.live_chat_indicator.pack(side="left", padx=4)
            if self.live_chat_thread and self.live_chat_thread.is_alive():
                return
            self.live_chat_thread = threading.Thread(target=self.live_voice_chat_loop, daemon=True)
            self.live_chat_thread.start()

    def live_voice_chat_loop(self):
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        while self.live_chat_active:
            try:
                with mic as source:
                    self.status_var.set("Listening (Live Chat)...")
                    recognizer.adjust_for_ambient_noise(source, duration=1)
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=16)
                try:
                    text = recognizer.recognize_google(audio)  # type: ignore
                    # Spell correction
                    corrected = str(TextBlob(text).correct())
                    self.after(0, lambda: self.insert_message(text, user="You"))
                    import main
                    response = main.short_answer(corrected)
                    self.after(0, lambda: self.display_ai_response(response))
                    self.after(0, lambda: self.speak(response))
                except sr.UnknownValueError:
                    self.after(0, lambda: self.add_bubble("Sorry, I didn't catch that.", user="Buddy AI"))
            except Exception as e:
                print(f"Live chat error: {e}")
                break
        self.status_var.set("Ready")
        if self.live_chat_indicator:
            self.live_chat_indicator.destroy()
            self.live_chat_indicator = None

    def stop_speaking(self):
        try:
            self.engine.stop()
        except Exception:
            pass

    def on_image_upload(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
        if file_path:
            self.selected_image_path = file_path
            self.show_image_preview(file_path)

    def show_image_preview(self, image_path):
        # Remove previous preview if exists
        for widget in self.image_preview_frame.winfo_children():
            widget.destroy()
        try:
            img = Image.open(image_path)
            img.thumbnail((32, 32))
            tk_img = ImageTk.PhotoImage(img)
            self.image_preview_label = tk.Label(self.image_preview_frame, image=tk_img, bg="#23272f")
            setattr(self.image_preview_label, "image", tk_img)  # Keep reference for linter
            self.image_preview_label.pack(side="left")
            # Remove button
            self.remove_image_btn = ctk.CTkButton(self.image_preview_frame, text="✖", width=24, height=24, font=("Segoe UI", 12), fg_color="#e74c3c", hover_color="#c0392b", text_color="#fff", command=self.remove_selected_image)
            self.remove_image_btn.pack(side="left", padx=(4, 0))
        except Exception:
            tk.Label(self.image_preview_frame, text="[Image error]", bg="#23272f", fg="#f00").pack()

    def remove_selected_image(self):
        self.selected_image_path = None
        for widget in self.image_preview_frame.winfo_children():
            widget.destroy()

    def add_image_text_bubble(self, image_path, message, user="You"):
        # Add an image and text as a single chat bubble
        bubble_frame = tk.Frame(self.chat_bubble_frame, bg="#181a20")
        align = "w" if user == "You" else "e"
        avatar = "🧑" if user == "You" else "🤖"
        try:
            img = Image.open(image_path)
            img.thumbnail((120, 120))
            tk_img = ImageTk.PhotoImage(img)
            img_label = tk.Label(bubble_frame, image=tk_img, bg="#181a20")
            setattr(img_label, "image", tk_img)  # Keep reference for linter
            img_label.pack(side="left" if user=="You" else "right", padx=8)
        except Exception:
            tk.Label(bubble_frame, text="[Image could not be loaded]", bg="#181a20", fg="#f00").pack()
        if message:
            msg_lbl = tk.Label(bubble_frame, text=message, font=("Segoe UI", 12), bg="#23272f", fg="#fff", wraplength=320, justify="left", padx=12, pady=8, bd=0, relief="flat")
            msg_lbl.pack(side="left" if user=="You" else "right", padx=4)
        tk.Label(bubble_frame, text=avatar, font=("Segoe UI", 18), bg="#181a20").pack(side="left" if user=="You" else "right", padx=8)
        bubble_frame.pack(anchor=align, fill="none", pady=6, padx=12)
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def handle_image_query(self, user_text):
        # Only handle the last uploaded image
        image_path = self.selected_image_path
        if not image_path:
            self.after(0, lambda: self.display_ai_response("No image found to analyze."))
            return
        # Always try to describe the image using BLIP (if available)
        if (BlipProcessor is not None and BlipForConditionalGeneration is not None and torch is not None and isinstance(BlipProcessor, type) and isinstance(BlipForConditionalGeneration, type)):
            try:
                processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
                model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
                if isinstance(processor, tuple) or isinstance(model, tuple):
                    self.after(0, lambda: self.display_ai_response("BLIP processor/model are not valid (tuple type). Please reinstall 'transformers'."))
                    return
                if not (hasattr(processor, 'decode') and hasattr(model, 'generate')):
                    self.after(0, lambda: self.display_ai_response("BLIP processor/model are not valid. Please reinstall 'transformers'."))
                    return
                from PIL import Image as PILImage
                raw_image = PILImage.open(image_path).convert('RGB')
                inputs = processor(raw_image, return_tensors="pt")
                pixel_values = inputs["pixel_values"]
                try:
                    import numpy as np
                    if not isinstance(pixel_values, torch.FloatTensor):
                        if hasattr(pixel_values, 'numpy'):
                            pixel_values = torch.as_tensor(pixel_values.numpy(), dtype=torch.float32)  # type: ignore
                        elif isinstance(pixel_values, np.ndarray):
                            pixel_values = torch.as_tensor(pixel_values, dtype=torch.float32)  # type: ignore
                        else:
                            pixel_values = torch.as_tensor(pixel_values, dtype=torch.float32)  # type: ignore
                except Exception:
                    self.after(0, lambda: self.display_ai_response("BLIP input pixel_values could not be converted to torch.FloatTensor. Please check your transformers and torch installation."))
                    return
                out = model.generate(pixel_values=pixel_values)  # type: ignore
                caption = processor.decode(out[0], skip_special_tokens=True)
                self.after(0, lambda: self.display_ai_response(f"Image description: {caption}"))
            except Exception as e:
                self.after(0, lambda: self.display_ai_response(f"Image analysis failed: {e}"))
        else:
            self.after(0, lambda: self.display_ai_response(
                "Image captioning model not installed.\n\nTo enable image description, please install the following packages:\n\n  pip install transformers torch Pillow\n\nThen restart Buddy AI."
            ))

    def open_image_prompt(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Create Image with AI")
        dialog.geometry("400x180")
        dialog.resizable(False, False)
        center_popup(dialog, 400, 180)
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.focus_force()
        ctk.CTkLabel(dialog, text="Describe the image you want to create:", font=("Segoe UI", 12)).pack(pady=12)
        prompt_var = tk.StringVar()
        entry = ctk.CTkEntry(dialog, textvariable=prompt_var, width=320, height=32, font=("Segoe UI", 12))
        entry.pack(pady=8)
        entry.focus_set()
        def on_generate():
            prompt = prompt_var.get().strip()
            if prompt:
                dialog.destroy()
                self.add_bubble(f"Generating image for: '{prompt}'", user="You")
                self.show_loading()
                threading.Thread(target=self.generate_image_from_prompt, args=(prompt,), daemon=True).start()
        ctk.CTkButton(dialog, text="Generate", command=on_generate, width=100, height=32, font=("Segoe UI", 12)).pack(pady=12)
        entry.bind("<Return>", lambda e: on_generate())

    def generate_image_from_prompt(self, prompt):
        try:
            import torch
            from PIL import Image as PILImage
            if StableDiffusionPipeline is None:
                raise ImportError
            # Load pipeline (cache for future calls)
            if not hasattr(self, '_sd_pipe'):
                if torch.cuda.is_available():
                    self._sd_pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5", revision="fp16", torch_dtype=torch.float16)
                    self._sd_pipe = self._sd_pipe.to("cuda")
                else:
                    self._sd_pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5")
                    self._sd_pipe = self._sd_pipe.to("cpu")
            pipe = self._sd_pipe
            result = pipe(prompt)
            image = result[0] if isinstance(result, tuple) else result.images[0]
            if not isinstance(image, PILImage.Image):
                try:
                    import numpy as np
                    import torch
                    if isinstance(image, torch.Tensor):
                        image = image.cpu().numpy()
                    if isinstance(image, np.ndarray):
                        image = PILImage.fromarray((image * 255).astype('uint8'))
                except Exception:
                    raise RuntimeError('Generated image is not a valid PIL Image and could not be converted.')
            temp_path = os.path.join("data", f"generated_{int(time.time())}.png")
            image.save(temp_path)
            self.after(0, lambda: [self.hide_loading(), self.add_image_text_bubble(temp_path, f"AI Image: {prompt}", user="Buddy AI")])
        except ImportError:
            self.after(0, lambda: self.display_ai_response(
                "Image generation requires the 'diffusers', 'torch', and 'Pillow' libraries.\nInstall them with:\n  pip install diffusers torch Pillow"
            ))
        except Exception as e:
            self.after(0, lambda: [self.hide_loading(), self.display_ai_response(f"Image generation failed: {e}")])

    def display_chat_history(self):
        for widget in self.chat_bubble_frame.winfo_children():
            widget.destroy()
        for item in self.chats[self.current_chat_index]["history"]:
            self.add_bubble(item["text"], user=item.get("user", "Buddy AI"))
        if not self.chats[self.current_chat_index]["history"]:
            self.add_bubble("Welcome to Buddy AI!\nAsk me anything, or start a new chat.", user="Buddy AI", is_welcome=True)
        if hasattr(self, "history_panel"):
            self.history_panel.update_history(self.chats[self.current_chat_index]["history"])
        self.chat_title_label.configure(text=self.chats[self.current_chat_index]["title"])

    def on_chat_select(self, event):
        selection = self.chat_list.curselection()
        if selection:
            self.current_chat_index = selection[0]
            self.display_chat_history()

def start_app():
    app = BuddyAIGUI()
    app.mainloop()  
if __name__ == "__main__":
    start_app()  
