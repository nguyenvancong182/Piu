"""
Script to create imagen_settings.py from extract
"""
headers = '''"""
ImagenSettingsWindow class for Piu application.
Manages Imagen image generation settings.
"""
import customtkinter as ctk
import logging
import os
import json
from tkinter import filedialog, messagebox
import threading
import time

from utils.helpers import get_default_downloads_folder, safe_int
from ui.widgets.menu_utils import textbox_right_click_menu
'''

with open('extract_imagen_temp.txt', 'r', encoding='utf-8') as f:
    content = f.read()

with open('ui/popups/imagen_settings.py', 'w', encoding='utf-8') as f:
    f.write(headers + '\n' + content)

print("Created ui/popups/imagen_settings.py")

