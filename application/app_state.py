"""
State Management for Piu Application

This module will manage all application state.
Currently this is a Skeleton - we will gradually migrate state from Piu.py
"""

import customtkinter as ctk
from config.settings import load_config, save_config
import logging


class StateManager:
    """
    Centralized state management for Piu application.
    
    This class will gradually take over state management from SubtitleApp.
    Migration strategy:
    1. Start with critical state (config, queues)
    2. Add state gradually as needed
    3. Keep Piu.py working throughout
    """
    
    def __init__(self):
        """
        Initialize state manager.
        Load configuration and initialize basic state.
        """
        logging.info("Initializing StateManager...")
        
        # === Configuration ===
        self.cfg = load_config()
        
        # === UI State Variables ===
        self.ui_vars = {}
        
        # === Process Status Flags ===
        self.is_shutting_down = False
        self.is_automated_quit = False
        self.shutdown_scheduled = False
        self.shutdown_requested_by_task = False
        
        # === Current View ===
        self.current_view = None  # 'subtitle', 'download', 'dubbing', 'upload'
        
        # === Queue Management ===
        # These will be managed gradually
        self.download_queue = []
        self.dubbing_queue = []
        
        # === Model State ===
        self.whisper_model = None
        self.loaded_model_name = None
        self.loaded_model_device = None
        self.is_loading_model = False
        
        # === CUDA/GPU State ===
        self.cuda_status = "UNKNOWN"
        self.gpu_vram_mb = 0
        
        # === Current Working State ===
        self.current_file = None
        self.current_srt_path = None
        self.temp_folder = None
        
        logging.info("StateManager initialized")
    
    def get_config(self, key, default=None):
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        return self.cfg.get(key, default)
    
    def set_config(self, key, value):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.cfg[key] = value
    
    def save_config(self):
        """
        Save current configuration to file.
        """
        try:
            save_config(self.cfg)
            logging.info("State config saved successfully")
        except Exception as e:
            logging.error(f"Failed to save config: {e}")
    
    def register_ui_var(self, name: str, var: ctk.StringVar | ctk.BooleanVar | ctk.IntVar):
        """
        Register a UI variable for centralized management.
        
        Args:
            name: Variable name
            var: Variable instance
        """
        self.ui_vars[name] = var
    
    def get_ui_var(self, name: str):
        """
        Get a registered UI variable.
        
        Args:
            name: Variable name
            
        Returns:
            Variable instance or None
        """
        return self.ui_vars.get(name)
    
    def is_model_loaded(self) -> bool:
        """
        Check if Whisper model is loaded.
        
        Returns:
            True if model is loaded
        """
        return self.whisper_model is not None
    
    def set_model(self, model, device=None):
        """
        Set the loaded Whisper model.
        
        Args:
            model: Model instance
            device: Device ('cuda' or 'cpu')
        """
        self.whisper_model = model
        self.loaded_model_device = device
    
    def unload_model(self):
        """
        Unload the current model.
        """
        self.whisper_model = None
        self.loaded_model_name = None
        self.loaded_model_device = None
    
    def get_state_summary(self) -> dict:
        """
        Get a summary of current state for debugging.
        
        Returns:
            Dictionary with state summary
        """
        return {
            'model_loaded': self.is_model_loaded(),
            'model_name': self.loaded_model_name,
            'current_view': self.current_view,
            'download_queue_size': len(self.download_queue),
            'dubbing_queue_size': len(self.dubbing_queue),
            'cuda_status': self.cuda_status,
        }

