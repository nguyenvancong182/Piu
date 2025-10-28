"""Create metadata_manager.py from extract"""
headers = '''"""
MetadataManagerWindow class for Piu application.
Manages metadata for YouTube batch uploads.
"""
import customtkinter as ctk
import logging
import os
import json
import csv
from tkinter import filedialog, messagebox

'''

with open('extract_metadata.txt', 'r', encoding='utf-8') as f:
    content = f.read()

with open('ui/popups/metadata_manager.py', 'w', encoding='utf-8') as f:
    f.write(headers + '\n' + content)

print("Created ui/popups/metadata_manager.py")

