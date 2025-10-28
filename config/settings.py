"""
Settings and configuration management for Piu application.
This module handles loading and saving configuration files.
"""

import os
import json
import time
import shutil
import sys
import logging
from tkinter import messagebox

try:
    import appdirs
    APPDIRS_AVAILABLE = True
except ImportError:
    APPDIRS_AVAILABLE = False

from .constants import APP_NAME, APP_AUTHOR, CONFIG_FILENAME, FONT_CACHE_FILENAME


def get_config_path():
    """Determine and return full path to config file based on OS"""
    global APPDIRS_AVAILABLE
    config_dir = None
    
    if APPDIRS_AVAILABLE:
        try:
            config_dir = appdirs.user_config_dir(appname=APP_NAME, appauthor=APP_AUTHOR)
        except Exception as e:
            logging.error(f"Error getting config dir from appdirs: {e}. Using fallback.")
            APPDIRS_AVAILABLE = False
    
    if config_dir is None:
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            config_dir = base_path
            logging.warning(f"Using fallback: Save config in app directory: {config_dir}")
        except NameError:
            config_dir = os.path.abspath(".")
            logging.warning(f"Using fallback: Save config in current directory: {config_dir}")
    
    return os.path.join(config_dir, CONFIG_FILENAME)


def get_font_cache_path():
    """Get full path to font_cache.json, alongside config.json"""
    config_dir = os.path.dirname(get_config_path())
    return os.path.join(config_dir, FONT_CACHE_FILENAME)


def get_google_voices_cache_path():
    """Get full path to google_voices.json, alongside config.json"""
    config_dir = os.path.dirname(get_config_path())
    return os.path.join(config_dir, "google_voices.json")


def load_config():
    """Load configuration from standard path"""
    full_config_path = get_config_path()
    logging.info(f"Attempting to load config from: {full_config_path}")
    
    if os.path.exists(full_config_path):
        try:
            with open(full_config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                logging.info(f"Config loaded successfully from: {full_config_path}")
                return config_data
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error in '{full_config_path}': {e}. Using default config.")
            try:
                backup_path = full_config_path + f".corrupted_{int(time.time())}"
                shutil.copy2(full_config_path, backup_path)
                logging.info(f"Backed up corrupted config to: {backup_path}")
            except Exception as backup_e:
                logging.error(f"Cannot backup corrupted config: {backup_e}")
            return {}
        except Exception as e:
            logging.error(f"Unexpected error loading config '{full_config_path}': {e}. Using default config.")
            return {}
    else:
        logging.info(f"Config file not found at '{full_config_path}'. Using default config.")
        return {}


def save_config(cfg):
    """Save configuration to standard path"""
    full_config_path = get_config_path()
    logging.info(f"Attempting to save config to: {full_config_path}")
    
    try:
        config_dir = os.path.dirname(full_config_path)
        os.makedirs(config_dir, exist_ok=True)
        
        logging.debug(f"Data to save to config.json: {json.dumps(cfg, indent=2, ensure_ascii=False)}")
        
        with open(full_config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Config saved successfully to: {full_config_path}")
    except PermissionError:
        logging.error(f"Permission denied when saving config to '{full_config_path}'.")
        try:
            messagebox.showerror("Permission Error", 
                                f"Cannot save config to:\n{full_config_path}\n\nPlease check permissions.")
        except Exception:
            pass
    except Exception as e:
        logging.error(f"Unexpected error saving config '{full_config_path}': {e}", exc_info=True)
        try:
            messagebox.showerror("Config Save Error", 
                                f"An unexpected error occurred while saving config:\n{e}")
        except Exception:
            pass

