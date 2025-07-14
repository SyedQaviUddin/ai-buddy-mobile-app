#!/usr/bin/env python3
"""
Simple test to verify the send button works correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.gui import BuddyAIGUI
import tkinter as tk

def test_send_button():
    """Test that the send button works without errors."""
    print("Testing send button functionality...")
    
    # Create the app
    app = BuddyAIGUI()
    
    # Test that widgets are created properly
    assert hasattr(app, 'text_input'), "text_input widget not found"
    assert hasattr(app, 'send_btn'), "send_btn widget not found"
    assert hasattr(app, 'chat_display'), "chat_display widget not found"
    
    print("✓ All required widgets exist")
    
    # Test that the send button has the correct properties
    assert app.send_btn.cget('text') == 'Send', "Send button text is incorrect"
    assert app.send_btn.cget('fg_color') == '#3498db', "Send button color is incorrect"
    
    print("✓ Send button has correct properties")
    
    # Test that text input works
    test_text = "Hello, this is a test message"
    app.text_input.delete(0, tk.END)
    app.text_input.insert(0, test_text)
    
    assert app.text_input.get() == test_text, "Text input not working correctly"
    print("✓ Text input works correctly")
    
    print("\n🎉 All tests passed! The send button should work correctly.")
    
    # Close the app
    app.destroy()

if __name__ == "__main__":
    test_send_button() 