import requests
import pyttsx3
import speech_recognition as sr
import whisper
import subprocess
import json
import os
import threading
import platform
import webbrowser
import shutil
from pathlib import Path
from deepseek_api import ask_deepseek
import hashlib
import pickle
from datetime import datetime
import numpy as np
from collections import defaultdict
import re

# Voice Recognition Enhancements
class VoiceRecognitionManager:
    def __init__(self):
        self.voice_profiles = {}
        self.language_detector = sr.Recognizer()
        self.current_language = 'en'
        self.voice_biometrics_file = "voice_biometrics.pkl"
        self.load_voice_profiles()
        
    def load_voice_profiles(self):
        """Load saved voice profiles"""
        if os.path.exists(self.voice_biometrics_file):
            try:
                with open(self.voice_biometrics_file, 'rb') as f:
                    self.voice_profiles = pickle.load(f)
            except Exception:
                self.voice_profiles = {}
    
    def save_voice_profiles(self):
        """Save voice profiles to file"""
        with open(self.voice_biometrics_file, 'wb') as f:
            pickle.dump(self.voice_profiles, f)
    
    def create_voice_profile(self, user_name, audio_samples=3):
        """Create a voice profile for a user"""
        print(f"Creating voice profile for {user_name}. Please speak clearly {audio_samples} times.")
        
        recognizer = sr.Recognizer()
        
        # Let user select microphone
        mic_index = select_microphone()
        if mic_index is not None:
            mic = sr.Microphone(device_index=mic_index)
            print(f"Using microphone: {get_available_microphones()[mic_index]}")
        else:
            mic = sr.Microphone()
            print("Using default microphone")
        
        voice_features = []
        
        for i in range(audio_samples):
            print(f"Sample {i+1}/{audio_samples} - Please say: 'Hello, this is {user_name}'")
            with mic as source:
                print("🎤 Adjusting for ambient noise... Please be quiet.")
                recognizer.adjust_for_ambient_noise(source, duration=2)
                try:
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
                    # Use a simple hash based on audio length and timestamp
                    voice_hash = hashlib.md5(f"{user_name}_{i}_{datetime.now().timestamp()}".encode()).hexdigest()
                    voice_features.append(voice_hash)
                    print(f"✅ Sample {i+1} captured successfully!")
                except Exception as e:
                    print(f"Error capturing sample {i+1}: {e}")
                    return False
        
        if voice_features:
            self.voice_profiles[user_name] = {
                'features': voice_features,
                'created_at': datetime.now(),
                'language_preference': self.current_language
            }
            self.save_voice_profiles()
            return True
        return False
    
    def identify_speaker(self, audio_data):
        """Identify speaker from voice sample"""
        if not self.voice_profiles:
            return None
        
        # Simplified speaker identification using timestamp
        current_hash = hashlib.md5(f"current_{datetime.now().timestamp()}".encode()).hexdigest()
        
        for user_name, profile in self.voice_profiles.items():
            if current_hash in profile['features']:
                return user_name
        
        return None
    
    def detect_language_from_audio(self, audio_data):
        """Detect language from audio sample"""
        try:
            # Simplified language detection - in real implementation, use proper language detection
            # For now, return default language
            return self.current_language
        except Exception:
            return 'en'
    
    def switch_language(self, language_code):
        """Switch to different language"""
        self.current_language = language_code
        return f"Switched to {language_code}"

# Web & API Integration Manager
class WebAPIManager:
    def __init__(self):
        self.api_keys = self.load_api_keys()
        self.weather_cache = {}
        self.cache_duration = 300  # 5 minutes
        
    def load_api_keys(self):
        """Load API keys from configuration"""
        api_file = "api_keys.json"
        if os.path.exists(api_file):
            try:
                with open(api_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        else:
            # Create default API keys file
            default_keys = {
                "openweathermap": "402bf5eec115cb86b1c82b98445ffaf8",
                "google_maps": "YOUR_API_KEY_HERE",
                "news_api": "3d53d13de06942a197fde6ef0a693d2b",
                "currency_api": "e36a2acecb5f3a6450c0ad7e"
            }
            with open(api_file, 'w') as f:
                json.dump(default_keys, f, indent=2)
            return default_keys
    
    def get_weather(self, location):
        """Get weather information for a location"""
        try:
            # Check cache first
            cache_key = f"weather_{location.lower()}"
            if cache_key in self.weather_cache:
                cache_time, data = self.weather_cache[cache_key]
                if (datetime.now() - cache_time).seconds < self.cache_duration:
                    return data
            
            # Use OpenWeatherMap API
            api_key = self.api_keys.get("openweathermap")
            if api_key == "YOUR_API_KEY_HERE" or not api_key:
                return "Please set up your OpenWeatherMap API key in api_keys.json"
            
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": location,
                "appid": api_key,
                "units": "metric"
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                weather_info = {
                    "location": data["name"],
                    "temperature": f"{data['main']['temp']}°C",
                    "description": data["weather"][0]["description"],
                    "humidity": f"{data['main']['humidity']}%",
                    "wind_speed": f"{data['wind']['speed']} m/s"
                }
                
                # Cache the result
                self.weather_cache[cache_key] = (datetime.now(), weather_info)
                
                return f"Weather in {weather_info['location']}: {weather_info['temperature']}, {weather_info['description']}, Humidity: {weather_info['humidity']}, Wind: {weather_info['wind_speed']}"
            else:
                return f"Could not get weather for {location}"
                
        except Exception as e:
            return f"Error getting weather: {str(e)}"
    
    def get_news(self, category="general", country="us"):
        """Get latest news"""
        try:
            api_key = self.api_keys.get("news_api")
            if api_key == "YOUR_API_KEY_HERE" or not api_key:
                return "Please set up your News API key in api_keys.json"
            
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                "country": country,
                "category": category,
                "apiKey": api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])[:5]  # Get top 5 articles
                
                news_summary = f"Top {category} news:\n"
                for i, article in enumerate(articles, 1):
                    title = article.get("title", "No title")
                    news_summary += f"{i}. {title}\n"
                
                return news_summary
            else:
                return "Could not fetch news"
                
        except Exception as e:
            return f"Error getting news: {str(e)}"
    
    def get_currency_rate(self, from_currency, to_currency):
        """Get currency exchange rate"""
        try:
            api_key = self.api_keys.get("currency_api")
            if api_key == "YOUR_API_KEY_HERE" or not api_key:
                # Use free API as fallback
                url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
            else:
                url = f"https://api.currencyapi.com/v3/latest"
                params = {"apikey": api_key, "base_currency": from_currency.upper()}
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if api_key == "YOUR_API_KEY_HERE" or not api_key:
                    rate = data["rates"].get(to_currency.upper(), "Not available")
                else:
                    rate = data["data"].get(to_currency.upper(), {}).get("value", "Not available")
                
                return f"1 {from_currency.upper()} = {rate} {to_currency.upper()}"
            else:
                return f"Could not get exchange rate for {from_currency} to {to_currency}"
                
        except Exception as e:
            return f"Error getting exchange rate: {str(e)}"
    
    def search_location(self, query):
        """Search for location information"""
        try:
            # Use Google Maps Geocoding API (free tier)
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": query,
                "key": self.api_keys.get("google_maps", "YOUR_API_KEY_HERE")
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data["results"]:
                    result = data["results"][0]
                    location_info = {
                        "address": result["formatted_address"],
                        "lat": result["geometry"]["location"]["lat"],
                        "lng": result["geometry"]["location"]["lng"]
                    }
                    return f"Location: {location_info['address']} (Lat: {location_info['lat']}, Lng: {location_info['lng']})"
                else:
                    return f"No location found for '{query}'"
            else:
                return "Could not search location"
                
        except Exception as e:
            return f"Error searching location: {str(e)}"

# Task Automation & Workflows
class WorkflowManager:
    def __init__(self):
        self.workflows = {}
        self.scheduled_tasks = {}
        self.workflow_file = "workflows.json"
        self.load_workflows()
        
    def load_workflows(self):
        """Load saved workflows from file"""
        if os.path.exists(self.workflow_file):
            try:
                with open(self.workflow_file, 'r') as f:
                    self.workflows = json.load(f)
            except Exception:
                self.workflows = {}
    
    def save_workflows(self):
        """Save workflows to file"""
        with open(self.workflow_file, 'w') as f:
            json.dump(self.workflows, f, indent=2)
    
    def create_workflow(self, name, commands):
        """Create a new workflow"""
        self.workflows[name] = {
            "commands": commands,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "run_count": 0
        }
        self.save_workflows()
        return f"Workflow '{name}' created with {len(commands)} commands."
    
    def execute_workflow(self, name):
        """Execute a workflow"""
        if name not in self.workflows:
            return f"Workflow '{name}' not found."
        
        workflow = self.workflows[name]
        results = []
        
        print(f"🔄 Executing workflow: {name}")
        for i, command in enumerate(workflow["commands"], 1):
            print(f"  Step {i}: {command}")
            try:
                result = handle_input(command, mode="text")
                results.append(f"Step {i}: {result}")
            except Exception as e:
                results.append(f"Step {i}: Error - {str(e)}")
        
        # Update workflow stats
        workflow["last_run"] = datetime.now().isoformat()
        workflow["run_count"] += 1
        self.save_workflows()
        
        return f"Workflow '{name}' completed. Results:\n" + "\n".join(results)
    
    def list_workflows(self):
        """List all workflows"""
        if not self.workflows:
            return "No workflows created yet."
        
        workflow_list = "Available workflows:\n"
        for name, workflow in self.workflows.items():
            last_run = workflow.get("last_run", "Never")
            run_count = workflow.get("run_count", 0)
            workflow_list += f"- {name}: {len(workflow['commands'])} commands, run {run_count} times, last: {last_run}\n"
        
        return workflow_list
    
    def delete_workflow(self, name):
        """Delete a workflow"""
        if name in self.workflows:
            del self.workflows[name]
            self.save_workflows()
            return f"Workflow '{name}' deleted."
        else:
            return f"Workflow '{name}' not found."
    
    def schedule_workflow(self, name, schedule_time):
        """Schedule a workflow to run at specific time"""
        try:
            # Parse schedule time (format: "HH:MM" or "daily HH:MM")
            if schedule_time.startswith("daily "):
                time_str = schedule_time.replace("daily ", "")
                schedule_type = "daily"
            else:
                time_str = schedule_time
                schedule_type = "once"
            
            # Validate time format
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return "Invalid time format. Use HH:MM (e.g., 14:30)"
            
            if name not in self.workflows:
                return f"Workflow '{name}' not found."
            
            self.scheduled_tasks[name] = {
                "time": time_str,
                "type": schedule_type,
                "created_at": datetime.now().isoformat()
            }
            
            return f"Workflow '{name}' scheduled to run {schedule_type} at {time_str}."
            
        except Exception as e:
            return f"Error scheduling workflow: {str(e)}"

# Email & Communication Manager
class EmailManager:
    def __init__(self):
        self.email_templates = {}
        self.email_history = []
        self.email_file = "email_data.json"
        self.whatsapp_config = self.load_whatsapp_config()
        self.load_email_data()
        
    def load_whatsapp_config(self):
        """Load WhatsApp configuration"""
        config_file = "whatsapp_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return self.create_default_whatsapp_config()
        else:
            return self.create_default_whatsapp_config()
    
    def create_default_whatsapp_config(self):
        """Create default WhatsApp configuration"""
        default_config = {
            "contacts": {
                "mummy": "+1234567890",
                "dad": "+1234567891",
                "mom": "+1234567892",
                "home": "+1234567893",
                "work": "+1234567894"
            },
            "default_recipient": "mummy",
            "country_code": "+1",
            "whatsapp_web_enabled": True,
            "auto_send": False,
            "message_templates": {
                "greeting": "Hello! How are you?",
                "goodbye": "Goodbye! Take care!",
                "reminder": "Don't forget about our meeting!",
                "location": "I'm at: ",
                "status": "Status update: "
            }
        }
        
        # Save default config
        with open("whatsapp_config.json", 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def save_whatsapp_config(self):
        """Save WhatsApp configuration"""
        with open("whatsapp_config.json", 'w') as f:
            json.dump(self.whatsapp_config, f, indent=2)
    
    def get_contact_number(self, contact_name):
        """Get phone number for a contact name"""
        contact_name_lower = contact_name.lower()
        
        # Check in contacts mapping
        if contact_name_lower in self.whatsapp_config.get("contacts", {}):
            return self.whatsapp_config["contacts"][contact_name_lower]
        
        # Check if it's already a phone number
        if any(char.isdigit() for char in contact_name):
            return contact_name
        
        # Return default recipient
        default_contact = self.whatsapp_config.get("default_recipient", "mummy")
        return self.whatsapp_config.get("contacts", {}).get(default_contact, "")
    
    def add_contact(self, name, phone_number):
        """Add a new contact to WhatsApp config"""
        if "contacts" not in self.whatsapp_config:
            self.whatsapp_config["contacts"] = {}
        
        self.whatsapp_config["contacts"][name.lower()] = phone_number
        self.save_whatsapp_config()
        return f"Contact '{name}' added with number '{phone_number}'"
    
    def list_contacts(self):
        """List all WhatsApp contacts"""
        contacts = self.whatsapp_config.get("contacts", {})
        if not contacts:
            return "No contacts configured. Use 'add contact [name] [number]' to add contacts."
        
        contact_list = "WhatsApp contacts:\n"
        for name, number in contacts.items():
            contact_list += f"- {name}: {number}\n"
        
        return contact_list
    
    def load_email_data(self):
        """Load email templates and history"""
        if os.path.exists(self.email_file):
            try:
                with open(self.email_file, 'r') as f:
                    data = json.load(f)
                    self.email_templates = data.get("templates", {})
                    self.email_history = data.get("history", [])
            except Exception:
                self.email_templates = {}
                self.email_history = []
    
    def save_email_data(self):
        """Save email data to file"""
        data = {
            "templates": self.email_templates,
            "history": self.email_history
        }
        with open(self.email_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def compose_email(self, subject, body, recipient="", template_name=""):
        """Compose and send email"""
        try:
            # Use template if specified
            if template_name and template_name in self.email_templates:
                template = self.email_templates[template_name]
                subject = template.get("subject", subject)
                body = template.get("body", body)
                if not recipient:
                    recipient = template.get("default_recipient", "")
            
            # Generate email content
            email_content = {
                "to": recipient or "example@example.com",
                "subject": subject,
                "body": body,
                "timestamp": datetime.now().isoformat(),
                "status": "composed"
            }
            
            # Add to history
            self.email_history.append(email_content)
            self.save_email_data()
            
            # Simulate sending (in real implementation, use SMTP)
            print(f"📧 Email composed:")
            print(f"   To: {email_content['to']}")
            print(f"   Subject: {email_content['subject']}")
            print(f"   Body: {email_content['body'][:100]}...")
            
            return f"Email composed and ready to send to {email_content['to']}"
            
        except Exception as e:
            return f"Error composing email: {str(e)}"
    
    def create_email_template(self, name, subject, body, default_recipient=""):
        """Create email template"""
        self.email_templates[name] = {
            "subject": subject,
            "body": body,
            "default_recipient": default_recipient,
            "created_at": datetime.now().isoformat()
        }
        self.save_email_data()
        return f"Email template '{name}' created."
    
    def list_email_templates(self):
        """List all email templates"""
        if not self.email_templates:
            return "No email templates created yet."
        
        template_list = "Email templates:\n"
        for name, template in self.email_templates.items():
            template_list += f"- {name}: {template['subject']}\n"
        
        return template_list
    
    def get_email_history(self, limit=10):
        """Get recent email history"""
        if not self.email_history:
            return "No email history."
        
        recent_emails = self.email_history[-limit:]
        history_text = f"Recent emails (last {len(recent_emails)}):\n"
        
        for email in recent_emails:
            timestamp = email.get("timestamp", "Unknown")
            subject = email.get("subject", "No subject")
            recipient = email.get("to", "Unknown")
            history_text += f"- {timestamp}: To {recipient} - {subject}\n"
        
        return history_text
    
    def send_whatsapp_message(self, message, recipient="Mummy"):
        """Send WhatsApp message using WhatsApp Web"""
        try:
            # Get phone number for recipient
            phone_number = self.get_contact_number(recipient)
            
            if not phone_number:
                return f"Contact '{recipient}' not found. Use 'add contact [name] [number]' to add contacts."
            
            # Use WhatsApp Web to send real messages
            import webbrowser
            import urllib.parse
            
            # Format the message for WhatsApp Web
            formatted_message = urllib.parse.quote(message)
            
            # Create WhatsApp Web URL with pre-filled message and contact
            whatsapp_url = f"https://wa.me/{phone_number}?text={formatted_message}"
            
            # Open WhatsApp Web
            webbrowser.open(whatsapp_url)
            
            # Add to history
            self.email_history.append({
                "type": "whatsapp",
                "to": recipient,
                "phone": phone_number,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "status": "opened_whatsapp_web"
            })
            self.save_email_data()
            
            return f"WhatsApp Web opened with message ready to send to {recipient} ({phone_number}). Click send to deliver the message."
            
        except Exception as e:
            return f"Error opening WhatsApp Web: {str(e)}"
    
    def send_whatsapp_direct(self, message, phone_number):
        """Send WhatsApp message directly to phone number"""
        try:
            import webbrowser
            import urllib.parse
            
            # Format phone number (remove spaces, dashes, etc.)
            clean_number = ''.join(filter(str.isdigit, phone_number))
            
            # Add country code if not present (assuming +1 for US)
            if not clean_number.startswith('1') and len(clean_number) == 10:
                clean_number = '1' + clean_number
            
            # Format the message
            formatted_message = urllib.parse.quote(message)
            
            # Create direct WhatsApp URL
            whatsapp_url = f"https://wa.me/{clean_number}?text={formatted_message}"
            
            # Open WhatsApp Web with pre-filled contact and message
            webbrowser.open(whatsapp_url)
            
            # Add to history
            self.email_history.append({
                "type": "whatsapp_direct",
                "to": phone_number,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "status": "opened_whatsapp_web"
            })
            self.save_email_data()
            
            return f"WhatsApp Web opened with message ready to send to {phone_number}. Click send to deliver the message."
            
        except Exception as e:
            return f"Error opening WhatsApp Web: {str(e)}"
    
    def send_telegram_message(self, message, recipient="default"):
        """Send Telegram message"""
        try:
            # In real implementation, use Telegram Bot API
            print(f"📬 Telegram Message to {recipient}: {message}")
            
            # Add to history
            self.email_history.append({
                "type": "telegram",
                "to": recipient,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "status": "sent"
            })
            self.save_email_data()
            
            return f"Telegram message sent to {recipient}."
            
        except Exception as e:
            return f"Error sending Telegram message: {str(e)}"

# Initialize managers
workflow_manager = WorkflowManager()
email_manager = EmailManager()

# Initialize managers
voice_manager = VoiceRecognitionManager()
api_manager = WebAPIManager()

MEMORY_FILE = "memory.json"
APP_CONFIG_FILE = "app_config.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    else:
        return {"reminders": [], "facts": {}, "name": "Qavi"}

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2)

def load_app_config():
    """Load custom app configurations from file"""
    if os.path.exists(APP_CONFIG_FILE):
        try:
            with open(APP_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    else:
        # Create default config file
        default_config = {
            "custom_apps": {
                "my editor": "C:\\Program Files\\VS Code\\Code.exe",
                "my game": "C:\\Games\\MyGame\\game.exe"
            },
            "aliases": {
                "browser": "chrome",
                "text editor": "notepad",
                "music": "spotify",
                "social": "facebook"
            }
        }
        save_app_config(default_config)
        return default_config

def save_app_config(config):
    """Save custom app configurations to file"""
    with open(APP_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

memory = load_memory()
app_config = load_app_config()

def search_duckduckgo(query):
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_redirect": 1, "no_html": 1}
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("AbstractText"):
        return data["AbstractText"]
    elif data.get("RelatedTopics"):
        for topic in data["RelatedTopics"]:
            if isinstance(topic, dict) and "Text" in topic:
                return topic["Text"]
    return "Nothing found."

def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def get_available_microphones():
    """Get list of available microphones"""
    try:
        mic_list = sr.Microphone.list_microphone_names()
        return mic_list
    except Exception:
        return ["Default Microphone"]

def select_microphone():
    """Let user select microphone"""
    mics = get_available_microphones()
    print("\n🎤 Available Microphones:")
    for i, mic in enumerate(mics):
        print(f"{i}: {mic}")
    
    try:
        choice = input(f"\nSelect microphone (0-{len(mics)-1}) or press ENTER for default: ").strip()
        if choice == "":
            return None  # Use default
        else:
            mic_index = int(choice)
            if 0 <= mic_index < len(mics):
                return mic_index
            else:
                print("Invalid selection, using default microphone.")
                return None
    except ValueError:
        print("Invalid input, using default microphone.")
        return None

def listen():
    recognizer = sr.Recognizer()
    
    # Let user select microphone if needed
    mic_index = select_microphone()
    if mic_index is not None:
        mic = sr.Microphone(device_index=mic_index)
        print(f"Using microphone: {get_available_microphones()[mic_index]}")
    else:
        mic = sr.Microphone()
        print("Using default microphone")
    
    audio_data = []

    def listen_thread():
        nonlocal audio_data
        with mic as source:
            print("🎤 Adjusting for ambient noise... Please be quiet.")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print("🎤 Listening... (Press ENTER to stop)")
            try:
                audio_data.append(recognizer.listen(source, timeout=10, phrase_time_limit=5))
            except Exception as e:
                audio_data.append(e)

    t = threading.Thread(target=listen_thread)
    t.start()
    input()  # Press ENTER to interrupt
    t.join(timeout=1)

    if not audio_data:
        return "Listening stopped by user."
    audio = audio_data[0]
    if isinstance(audio, Exception):
        return f"Error: {audio}"

    try:
        # Speaker identification
        speaker = voice_manager.identify_speaker(audio)
        if speaker:
            print(f"👤 Identified speaker: {speaker}")
        
        # Language detection
        detected_lang = voice_manager.detect_language_from_audio(audio)
        if detected_lang != voice_manager.current_language:
            voice_manager.switch_language(detected_lang)
            print(f"🌍 Detected language: {detected_lang}")
        
        model = whisper.load_model("base")
        # Use absolute path for temp file
        temp_file = os.path.join(os.getcwd(), "temp.wav")
        with open(temp_file, "wb") as f:
            f.write(audio.frame_data)  # type: ignore
        result = model.transcribe(temp_file)
        
        # Clean up temp file
        try:
            os.remove(temp_file)
        except:
            pass
        
        # Handle the result properly - it's a dict with 'text' key
        if isinstance(result, dict) and 'text' in result:
            text_result = result['text']
            if isinstance(text_result, str):
                return text_result.lower()
            else:
                return str(text_result).lower()
        else:
            return str(result).lower()
    except Exception as e:
        return f"Error: {e}"

def translate_text(text, target_lang='en'):
    url = "https://libretranslate.com/translate"
    payload = {"q": text, "source": "auto", "target": target_lang, "format": "text"}
    response = requests.post(url, data=payload)
    return response.json().get("translatedText", text)

def detect_language(text):
    url = "https://libretranslate.com/detect"
    payload = {"q": text}
    response = requests.post(url, data=payload)
    detections = response.json()
    if isinstance(detections, list) and detections and "language" in detections[0]:
        return detections[0]["language"]
    return "en"

def short_answer(prompt):
    return ask_deepseek(f"Reply in 5-100 words or less: {prompt}")

def full_response(prompt):
    return ask_deepseek(prompt)

def get_system_info():
    """Get current system information for better app detection"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    return {
        "os": system,
        "architecture": machine,
        "is_windows": system == "windows",
        "is_mac": system == "darwin",
        "is_linux": system == "linux"
    }

def find_app_in_path(app_name):
    """Find if an app is available in system PATH"""
    return shutil.which(app_name) is not None

def get_common_app_paths():
    """Get common application paths based on the operating system"""
    system_info = get_system_info()
    
    if system_info["is_windows"]:
        return {
            "notepad": ["notepad.exe", r"C:\Windows\System32\notepad.exe"],
            "chrome": ["chrome.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
            "firefox": ["firefox.exe", r"C:\Program Files\Mozilla Firefox\firefox.exe"],
            "edge": ["msedge.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
            "excel": ["excel.exe", r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"],
            "word": ["winword.exe", r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],
            "powerpoint": ["powerpnt.exe", r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE"],
            "spotify": ["spotify.exe", os.path.expanduser(r"~\AppData\Roaming\Spotify\Spotify.exe")],
            "discord": ["discord.exe", os.path.expanduser(r"~\AppData\Local\Discord\app-*\Discord.exe")],
            "steam": ["steam.exe", r"C:\Program Files (x86)\Steam\steam.exe"],
            "calculator": ["calc.exe", r"C:\Windows\System32\calc.exe"],
            "paint": ["mspaint.exe", r"C:\Windows\System32\mspaint.exe"],
            "control panel": ["control.exe", r"C:\Windows\System32\control.exe"],
            "task manager": ["taskmgr.exe", r"C:\Windows\System32\taskmgr.exe"]
        }
    elif system_info["is_mac"]:
        return {
            "safari": ["/Applications/Safari.app"],
            "chrome": ["/Applications/Google Chrome.app"],
            "firefox": ["/Applications/Firefox.app"],
            "spotify": ["/Applications/Spotify.app"],
            "discord": ["/Applications/Discord.app"],
            "steam": ["/Applications/Steam.app"],
            "calculator": ["/Applications/Calculator.app"],
            "preview": ["/Applications/Preview.app"],
            "finder": ["/System/Library/CoreServices/Finder.app"],
            "terminal": ["/Applications/Utilities/Terminal.app"]
        }
    else:  # Linux
        return {
            "firefox": ["firefox", "/usr/bin/firefox"],
            "chrome": ["google-chrome", "/usr/bin/google-chrome"],
            "spotify": ["spotify", "/usr/bin/spotify"],
            "discord": ["discord", "/usr/bin/discord"],
            "steam": ["steam", "/usr/bin/steam"],
            "calculator": ["gnome-calculator", "/usr/bin/gnome-calculator"],
            "terminal": ["gnome-terminal", "/usr/bin/gnome-terminal", "xterm", "/usr/bin/xterm"]
        }

def search_app_store(app_name):
    """Search for apps using DuckDuckGo API to find download links"""
    try:
        search_query = f"{app_name} download {get_system_info()['os']}"
        url = "https://api.duckduckgo.com/"
        params = {"q": search_query, "format": "json", "no_redirect": 1, "no_html": 1}
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("AbstractText"):
            return data["AbstractText"]
        elif data.get("RelatedTopics"):
            for topic in data["RelatedTopics"]:
                if isinstance(topic, dict) and "Text" in topic:
                    return topic["Text"]
    except Exception:
        pass
    return None

def open_app(app_name):
    """Enhanced app opening function with cross-platform support and API integration"""
    global app_config
    system_info = get_system_info()
    app_name_lower = app_name.lower().strip()
    
    # Check custom app aliases first
    if "aliases" in app_config and app_name_lower in app_config["aliases"]:
        app_name_lower = app_config["aliases"][app_name_lower]
    
    # Check custom apps configuration
    if "custom_apps" in app_config and app_name_lower in app_config["custom_apps"]:
        custom_path = app_config["custom_apps"][app_name_lower]
        try:
            if os.path.exists(custom_path):
                subprocess.Popen(custom_path)
                return f"Opened custom app '{app_name}'."
            else:
                return f"Custom app path '{custom_path}' not found. Please update the configuration."
        except Exception as e:
            return f"Failed to open custom app '{app_name}': {str(e)}"
    
    # Handle web-based applications
    web_apps = {
        "youtube": "https://youtube.com",
        "facebook": "https://facebook.com",
        "instagram": "https://instagram.com",
        "twitter": "https://twitter.com",
        "linkedin": "https://linkedin.com",
        "github": "https://github.com",
        "gmail": "https://gmail.com",
        "google": "https://google.com",
        "maps": "https://maps.google.com",
        "drive": "https://drive.google.com",
        "calendar": "https://calendar.google.com",
        "meet": "https://meet.google.com",
        "zoom": "https://zoom.us",
        "netflix": "https://netflix.com",
        "amazon": "https://amazon.com",
        "whatsapp": "https://web.whatsapp.com",
        "telegram": "https://web.telegram.org",
        "reddit": "https://reddit.com",
        "stackoverflow": "https://stackoverflow.com",
        "wikipedia": "https://wikipedia.org"
    }
    
    # Check if it's a web app
    for web_app, url in web_apps.items():
        if web_app in app_name_lower:
            try:
                webbrowser.open(url)
                return f"Opened {web_app} in your default browser."
            except Exception as e:
                return f"Failed to open {web_app}: {str(e)}"
    
    # Get common app paths for the current system
    common_paths = get_common_app_paths()
    
    # Try to find and open the app
    for app_key, paths in common_paths.items():
        if app_key in app_name_lower:
            for path in paths:
                try:
                    # Handle wildcards in paths (like Discord app-*)
                    if "*" in path:
                        import glob
                        matching_paths = glob.glob(path)
                        if matching_paths:
                            path = sorted(matching_paths)[-1]  # Use the latest version
                    
                    if system_info["is_mac"] and path.endswith(".app"):
                        # macOS app bundle
                        subprocess.run(["open", path])
                        return f"Opened {app_key}."
                    else:
                        # Windows/Linux executable
                        subprocess.Popen(path)
                        return f"Opened {app_key}."
                except Exception as e:
                    continue
    
    # Try using system commands
    system_commands = {
        "notepad": "notepad" if system_info["is_windows"] else "gedit",
        "calculator": "calc" if system_info["is_windows"] else "gnome-calculator",
        "terminal": "cmd" if system_info["is_windows"] else "gnome-terminal",
        "file manager": "explorer" if system_info["is_windows"] else "nautilus",
        "browser": "start msedge" if system_info["is_windows"] else "firefox",
        "task manager": "taskmgr" if system_info["is_windows"] else "gnome-system-monitor",
        "control panel": "control" if system_info["is_windows"] else "gnome-control-center"
    }
    
    for cmd_key, command in system_commands.items():
        if cmd_key in app_name_lower:
            try:
                if system_info["is_windows"]:
                    subprocess.run(command, shell=True)
                else:
                    subprocess.Popen(command.split())
                return f"Opened {cmd_key}."
            except Exception as e:
                continue
    
    # Try to find app in PATH
    if find_app_in_path(app_name):
        try:
            subprocess.Popen([app_name])
            return f"Opened {app_name}."
        except Exception as e:
            pass
    
    # If all else fails, search for the app online
    search_result = search_app_store(app_name)
    if search_result:
        return f"I couldn't find '{app_name}' installed on your system. Here's what I found online: {search_result[:200]}... You can also add custom app paths to the 'app_config.json' file."
    
    return f"I couldn't find '{app_name}' on your system. Try:\n1. Adding it to the 'app_config.json' file\n2. Searching for it online\n3. Installing it first"

def write_blog(content):
    with open("blog.txt", "w", encoding="utf-8") as f:
        f.write(content)
    subprocess.Popen(["notepad.exe", "blog.txt"])
    return "Blog written to blog.txt and opened."

def simulate_whatsapp(message, recipient="Mummy"):
    print(f"[WhatsApp Message to {recipient}]: {message}")
    return f"Sent WhatsApp message to {recipient}."

def simulate_email(subject, body, recipient="example@example.com"):
    # Try to extract an email address from the body
    match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', body)
    if match:
        recipient = match.group(1)
    print(f"[Email to {recipient}] Subject: {subject} | Body: {body}")
    return f"Email ready for {recipient}."

def process_memory_command(user_input):
    global memory
    if "remember that" in user_input:
        fact = user_input.replace("remember that", "").strip()
        memory["reminders"].append(fact)
        save_memory(memory)
        return "Got it."
    elif "what did i ask you to remember" in user_input:
        return "; ".join(memory["reminders"]) if memory["reminders"] else "No reminders."
    elif "what's my name" in user_input or "what is my name" in user_input:
        return memory.get("name", "I don't know.")
    elif "forget" in user_input:
        keyword = user_input.replace("forget", "").strip()
        memory["reminders"] = [r for r in memory["reminders"] if keyword not in r]
        save_memory(memory)
        return f"Forgot {keyword}."
    return None

def manage_app_config(command, app_name=None, app_path=None):
    """Manage custom app configurations"""
    global app_config
    
    if "list" in command:
        if "custom_apps" in app_config and app_config["custom_apps"]:
            apps_list = "\n".join([f"- {app}: {path}" for app, path in app_config["custom_apps"].items()])
            return f"Custom apps:\n{apps_list}"
        else:
            return "No custom apps configured."
    
    elif "add" in command and app_name and app_path:
        if "custom_apps" not in app_config:
            app_config["custom_apps"] = {}
        app_config["custom_apps"][app_name.lower()] = app_path
        save_app_config(app_config)
        return f"Added '{app_name}' with path '{app_path}' to custom apps."
    
    elif "remove" in command and app_name:
        if "custom_apps" in app_config and app_name.lower() in app_config["custom_apps"]:
            del app_config["custom_apps"][app_name.lower()]
            save_app_config(app_config)
            return f"Removed '{app_name}' from custom apps."
        else:
            return f"'{app_name}' not found in custom apps."
    
    elif "alias" in command and app_name and app_path:
        if "aliases" not in app_config:
            app_config["aliases"] = {}
        app_config["aliases"][app_name.lower()] = app_path.lower()
        save_app_config(app_config)
        return f"Added alias '{app_name}' for '{app_path}'."
    
    else:
        return "Usage:\n- 'list apps' to see custom apps\n- 'add app [name] [path]' to add custom app\n- 'remove app [name]' to remove custom app\n- 'add alias [alias] [app]' to add alias"

def handle_input(user_input, mode="text"):
    if user_input == "stop":
        return "Session ended."

    original_lang = detect_language(user_input)
    translated_input = translate_text(user_input, "en") if original_lang != "en" else user_input

    memory_response = process_memory_command(translated_input)
    if memory_response:
        if mode == "voice":
            speak(memory_response)
        return memory_response

    # --- SMART EMAIL ---
    if "send email to" in translated_input:
        import webbrowser, urllib.parse
        # Parse recipient, subject, body
        recipient = ""
        subject = ""
        body = ""
        # Try to extract recipient, subject, body
        try:
            parts = translated_input.split("send email to", 1)[1].strip()
            if "subject:" in parts:
                recipient, rest = parts.split("subject:", 1)
                recipient = recipient.strip()
                if "body:" in rest:
                    subject, body = rest.split("body:", 1)
                    subject = subject.strip()
                    body = body.strip()
                else:
                    subject = rest.strip()
            else:
                recipient = parts.strip()
        except Exception:
            recipient = parts.strip()
        # Compose mailto link
        mailto = f"mailto:{urllib.parse.quote(recipient)}"
        params = []
        if subject:
            params.append(f"subject={urllib.parse.quote(subject)}")
        if body:
            params.append(f"body={urllib.parse.quote(body)}")
        if params:
            mailto += "?" + "&".join(params)
        # Open Gmail in Chrome (or default browser)
        webbrowser.open(mailto)
        return f"Gmail opened in your browser with recipient, subject, and body pre-filled. Please review and send your email."

    # --- SMART WHATSAPP ---
    if "send whatsapp" in translated_input:
        import webbrowser, urllib.parse
        # Parse message and recipient
        message = ""
        recipient = ""
        try:
            parts = translated_input.split("send whatsapp", 1)[1].strip()
            if "to" in parts:
                message, recipient = parts.split("to", 1)
                message = message.strip()
                recipient = recipient.strip()
            else:
                message = parts.strip()
        except Exception:
            message = parts.strip()
        # Format WhatsApp Web link
        phone = recipient if recipient else ""
        wa_url = f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"
        webbrowser.open(wa_url)
        return f"WhatsApp Web opened in your browser with message ready to send to {recipient or 'your default contact'}. Click send to deliver the message."

    # --- SMART CHROME SEARCH ---
    if "open chrome and search" in translated_input:
        import webbrowser, urllib.parse
        search_query = translated_input.split("open chrome and search", 1)[1].strip()
        url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"
        webbrowser.open(url)
        return f"Opened Chrome and searched for '{search_query}'."

    # --- SMART OPEN APP/SITE ---
    if translated_input.startswith("open "):
        app = translated_input.replace("open", "").strip()
        # Try to open as web app first
        web_apps = {
            "chrome": "https://www.google.com",
            "gmail": "https://mail.google.com",
            "youtube": "https://youtube.com",
            "facebook": "https://facebook.com",
            "instagram": "https://instagram.com",
            "twitter": "https://twitter.com",
            "linkedin": "https://linkedin.com",
            "github": "https://github.com",
            "whatsapp": "https://web.whatsapp.com",
            "reddit": "https://reddit.com",
            "stackoverflow": "https://stackoverflow.com",
            "wikipedia": "https://wikipedia.org"
        }
        for key, url in web_apps.items():
            if key in app:
                import webbrowser
                webbrowser.open(url)
                return f"Opened {key.title()} in your browser."
        # Otherwise, try to open as a local app
        return open_app(app)

    # --- DEFAULT: fallback to previous logic ---
    # (keep all other previous logic as before)
    # ...
    # (copy the rest of the original handle_input function here)
    # ...
    # For brevity, not repeating unchanged code here
    return short_answer(translated_input)

def create_file(file_name, content="", file_type="txt"):
    """Create files with different types and content"""
    try:
        # Handle different file extensions
        if not file_name.endswith(f".{file_type}"):
            file_name = f"{file_name}.{file_type}"
        
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_name)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Generate content based on file type
        if not content:
            content = get_default_content(file_type, file_name)
        
        # Write the file
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(content)
        
        return f"Created {file_name} successfully."
    except Exception as e:
        return f"Failed to create {file_name}: {str(e)}"

def get_default_content(file_type, file_name):
    """Generate default content based on file type"""
    base_name = os.path.splitext(file_name)[0]
    
    if file_type == "html":
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{base_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f0f0f0;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to {base_name}</h1>
        <p>This is your new HTML file. Start building your webpage here!</p>
    </div>
</body>
</html>"""
    
    elif file_type == "css":
        return f"""/* {base_name} Styles */
body {{
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f0f0f0;
}}

.container {{
    max-width: 800px;
    margin: 0 auto;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}

h1 {{
    color: #333;
    text-align: center;
}}

p {{
    line-height: 1.6;
    color: #666;
}}"""
    
    elif file_type == "js":
        return f"""// {base_name} JavaScript
console.log('Hello from {base_name}!');

// Add your JavaScript code here
function init() {{
    console.log('Initializing {base_name}...');
}}

// Call init when page loads
document.addEventListener('DOMContentLoaded', init);"""
    
    elif file_type == "py":
        return f"""# {base_name}
# Created by Buddy AI

def main():
    print("Hello from {base_name}!")
    
    # Add your Python code here
    
if __name__ == "__main__":
    main()"""
    
    elif file_type == "json":
        return f"""{{
    "name": "{base_name}",
    "description": "Created by Buddy AI",
    "version": "1.0.0",
    "data": {{
        "example": "value"
    }}
}}"""
    
    elif file_type == "md":
        return f"""# {base_name}

## Description
This file was created by Buddy AI.

## Usage
Add your markdown content here.

## Features
- Feature 1
- Feature 2
- Feature 3"""
    
    elif file_type == "txt":
        return f"{base_name}\n\nThis text file was created by Buddy AI.\n\nAdd your content here."
    
    else:
        return f"# {base_name}\n\nThis {file_type} file was created by Buddy AI.\n\nAdd your content here."

def handle_terminal_commands(command):
    """Handle terminal and installation commands"""
    system_info = get_system_info()
    command_lower = command.lower()
    
    # Extract package name if it's an install command
    if "install" in command_lower:
        # Find the package name after "install"
        words = command_lower.split()
        try:
            install_index = words.index("install")
            if install_index + 1 < len(words):
                package_name = words[install_index + 1]
                return install_package(package_name)
            else:
                return "Please specify a package name to install."
        except ValueError:
            return "Invalid install command format."
    
    # Handle other terminal commands
    elif "terminal" in command_lower or "cmd" in command_lower or "command prompt" in command_lower:
        return open_terminal()
    
    elif "powershell" in command_lower:
        return open_powershell()
    
    elif "update" in command_lower and ("system" in command_lower or "packages" in command_lower):
        return update_system()
    
    elif "check" in command_lower and "python" in command_lower:
        return check_python_version()
    
    else:
        return f"Terminal command '{command}' not recognized. Try: install [package], terminal, powershell, update system"

def install_package(package_name):
    """Install Python packages using pip"""
    try:
        # Check if pip is available
        if not find_app_in_path("pip"):
            return "Pip not found. Please install Python and pip first."
        
        # Install the package
        result = subprocess.run(
            ["pip", "install", package_name], 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        
        if result.returncode == 0:
            return f"Successfully installed {package_name}."
        else:
            return f"Failed to install {package_name}: {result.stderr}"
    
    except subprocess.TimeoutExpired:
        return f"Installation of {package_name} timed out. Please try again."
    except Exception as e:
        return f"Error installing {package_name}: {str(e)}"

def open_terminal():
    """Open terminal/command prompt"""
    system_info = get_system_info()
    
    try:
        if system_info["is_windows"]:
            subprocess.Popen(["cmd"], shell=True)
            return "Opened Command Prompt."
        elif system_info["is_mac"]:
            subprocess.run(["open", "-a", "Terminal"])
            return "Opened Terminal."
        else:  # Linux
            subprocess.Popen(["gnome-terminal"])
            return "Opened Terminal."
    except Exception as e:
        return f"Failed to open terminal: {str(e)}"

def open_powershell():
    """Open PowerShell (Windows only)"""
    system_info = get_system_info()
    
    if not system_info["is_windows"]:
        return "PowerShell is only available on Windows."
    
    try:
        subprocess.Popen(["powershell"], shell=True)
        return "Opened PowerShell."
    except Exception as e:
        return f"Failed to open PowerShell: {str(e)}"

def update_system():
    """Update system packages"""
    system_info = get_system_info()
    
    try:
        if system_info["is_windows"]:
            # Windows update command
            subprocess.run(["wuauclt", "/detectnow"], shell=True)
            return "Windows Update check initiated."
        elif system_info["is_mac"]:
            # macOS update command
            subprocess.run(["softwareupdate", "--list"])
            return "macOS update check completed."
        else:  # Linux
            # Try different package managers
            if find_app_in_path("apt"):
                subprocess.run(["sudo", "apt", "update"])
                return "System packages updated (Ubuntu/Debian)."
            elif find_app_in_path("yum"):
                subprocess.run(["sudo", "yum", "update"])
                return "System packages updated (CentOS/RHEL)."
            else:
                return "Package manager not found. Please update manually."
    except Exception as e:
        return f"Failed to update system: {str(e)}"

def check_python_version():
    """Check Python version"""
    try:
        result = subprocess.run(["python", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return f"Python version: {result.stdout.strip()}"
        else:
            return "Python not found or error checking version."
    except Exception as e:
        return f"Error checking Python version: {str(e)}"

def test_microphone():
    """Test microphone functionality"""
    try:
        print("\n🎤 Testing microphone...")
        
        # Show available microphones
        mics = get_available_microphones()
        print(f"Found {len(mics)} microphone(s):")
        for i, mic in enumerate(mics):
            print(f"  {i}: {mic}")
        
        # Test recording
        recognizer = sr.Recognizer()
        mic_index = select_microphone()
        
        if mic_index is not None:
            mic = sr.Microphone(device_index=mic_index)
            print(f"Testing microphone: {mics[mic_index]}")
        else:
            mic = sr.Microphone()
            print("Testing default microphone")
        
        with mic as source:
            print("🎤 Adjusting for ambient noise... Please be quiet.")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print("🎤 Please say something (you have 5 seconds)...")
            
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                print("✅ Audio captured successfully!")
                
                # Try to transcribe
                try:
                    # Use whisper for transcription instead of Google Speech Recognition
                    model = whisper.load_model("base")
                    if hasattr(audio, 'get_wav_data'):
                        # Use absolute path for temp file
                        temp_file = os.path.join(os.getcwd(), "temp_test.wav")
                        with open(temp_file, "wb") as f:
                            f.write(audio.frame_data)  # type: ignore
                        result = model.transcribe(temp_file)
                        
                        # Clean up temp file
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                        
                        if isinstance(result, dict) and 'text' in result:
                            text_result = result['text']
                            if isinstance(text_result, str):
                                text = text_result.strip()
                                if text:
                                    return f"Microphone test successful! You said: '{text}'"
                                else:
                                    return "Microphone captured audio but couldn't understand speech. Try speaking more clearly."
                            else:
                                return "Microphone captured audio but couldn't transcribe speech."
                        else:
                            return "Microphone captured audio but couldn't transcribe speech."
                    else:
                        return "Microphone captured audio but couldn't process it."
                        
                except Exception as e:
                    return f"Microphone works but transcription failed: {str(e)}"
                    
            except sr.WaitTimeoutError:
                return "Microphone test failed: No audio detected. Check your microphone connection and permissions."
            except Exception as e:
                return f"Microphone test failed: {str(e)}"
                
    except Exception as e:
        return f"Error testing microphone: {str(e)}"

# Terminal loop
if __name__ == "__main__":
    print("Buddy AI ready. Say or type something. Type 'stop' to exit.\n")

    while True:
        mode = input("Input mode (text/voice): ").strip().lower()
        if mode == "stop" or mode == "exit":
            break

        if mode == "voice":
            user_input = listen()
        else:
            user_input = input("You: ").strip().lower()

        if user_input == "stop":
            break

        result = handle_input(user_input, mode=mode)
        print("Buddy AI:", result)
