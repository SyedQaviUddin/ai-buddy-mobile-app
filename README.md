# 🤖 Buddy AI Desktop App

A powerful AI assistant desktop application with voice recognition, modern GUI, and secure authentication.

## ✨ Features
- Secure authentication (email, password, passkey)
- Voice and text chat with AI
- Email and WhatsApp integration
- Modern GUI with dark mode
- User avatars and chat history
- System integration (app launcher, file manager, etc.)
- Settings and configuration panels

## 📁 What to Upload to GitHub
**Required:**
- `gui/` folder (all Python files, requirements.txt, config files inside)
- `config/` folder (all JSON config files)
- `data/` folder (sample user and chat data, but remove any sensitive/personal info)
- `assets/` folder (images like `bot_logo.png` and any required resources)
- `requirements.txt` (in root, if present)
- `README.md` (this file)

**Optional:**
- You may include sample test files (e.g., `test_system.py`, `test_simple_system.py`)
- You may include sample data files, but clear out any private or sensitive data

**Do NOT upload:**
- Any files with personal credentials (real API keys, real emails/passwords)
- Large model files unless required for demo (e.g., Vosk model)
- `__pycache__/` or other build/temp folders

## 🚀 Quick Start
1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd buddy-ai
   ```
2. Install dependencies:
   ```bash
   cd gui
   pip install -r requirements.txt
   ```
3. Configure email and API settings in `config/` as needed.
4. Run the app:
   ```bash
   python gui.py
   ```

## 🗂️ Project Structure
```
buddy-ai/
├── gui/                # Main desktop app code
├── config/             # Configuration files (email, API, etc.)
├── data/               # User and chat data (sample/demo)
├── assets/             # Images and resources
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```

## 📝 Notes
- Make sure to clear any personal data from config/data before uploading.
- If you use large models (e.g., Vosk), consider providing a download link instead of uploading.
- Add a `.gitignore` to exclude `__pycache__/`, temp files, and sensitive info.

---

**Ready for your interview and GitHub upload!**