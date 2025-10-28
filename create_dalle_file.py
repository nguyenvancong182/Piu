"""Create dalle_settings.py from extract"""
headers = '''"""
DalleSettingsWindow class for Piu application.
Manages DALL-E image generation settings.
"""
import customtkinter as ctk
import logging
import os
from tkinter import filedialog, messagebox
import threading
import time

from utils.helpers import get_default_downloads_folder, safe_int
'''

with open('extract_dalle.txt', 'r', encoding='utf-8') as f:
    content = f.read()

with open('ui/popups/dalle_settings.py', 'w', encoding='utf-8') as f:
    f.write(headers + '\n' + content)

print("Created ui/popups/dalle_settings.py")

