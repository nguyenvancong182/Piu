"""
Metadata Service for Piu Application

This service handles metadata cache management, autofill, and parsing for YouTube uploads.
Business logic extracted from Piu.py to improve maintainability and testability.

Migration from Piu.py:
- Metadata cache loading/saving
- Autofill logic from metadata
- Metadata entry updates
- Filename parsing
"""

import logging
import os
import json
import re
from typing import Optional, Dict, Tuple

# Import utilities
try:
    from utils.helpers import get_identifier_from_source
except ImportError:
    def get_identifier_from_source(source_path_or_url: str) -> Optional[str]:
        """Fallback if helpers not available"""
        if not source_path_or_url:
            return None
        try:
            base_name = os.path.basename(source_path_or_url)
            return os.path.splitext(base_name)[0]
        except Exception:
            return None

# Constants
APP_NAME = "Piu"


class MetadataService:
    """
    Service for metadata cache management and autofill for YouTube uploads.
    
    This service contains all business logic for metadata operations,
    separate from UI handling which remains in Piu.py.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize Metadata Service.
        
        Args:
            logger: Optional logger instance. If None, creates a new logger.
        """
        self.logger = logger or logging.getLogger(APP_NAME)
        self.logger.info("[MetadataService] Initializing Metadata Service...")
        
        # Cache storage
        self.cache: Dict[str, Dict] = {}
        self.cache_path: Optional[str] = None
    
    # ========================================================================
    # CACHE MANAGEMENT METHODS
    # ========================================================================
    
    def load_cache(self, cache_path: Optional[str] = None) -> bool:
        """
        Load metadata cache from file.
        
        Args:
            cache_path: Path to metadata cache file. If None, uses self.cache_path.
            
        Returns:
            True if loaded successfully, False otherwise
        """
        log_prefix = "[MetadataService:LoadCache]"
        
        if cache_path:
            self.cache_path = cache_path
        elif not self.cache_path:
            self.logger.warning(f"{log_prefix} No cache path provided.")
            self.cache = {}
            return False
        
        if not os.path.exists(self.cache_path):
            self.logger.info(f"{log_prefix} Cache file does not exist: {self.cache_path}")
            self.cache = {}
            return False
        
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                loaded_cache = json.load(f)
                
            if not isinstance(loaded_cache, dict):
                self.logger.error(f"{log_prefix} Cache file does not contain a dictionary.")
                self.cache = {}
                return False
            
            self.cache = loaded_cache
            self.logger.info(f"{log_prefix} Successfully loaded {len(self.cache)} entries from '{os.path.basename(self.cache_path)}'.")
            return True
        
        except (json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"{log_prefix} Error reading or parsing JSON metadata file: {e}")
            self.cache = {}
            return False
        except Exception as e:
            self.logger.error(f"{log_prefix} Unexpected error loading metadata file: {e}", exc_info=True)
            self.cache = {}
            return False
    
    def save_cache(self, cache_path: Optional[str] = None) -> bool:
        """
        Save metadata cache to file.
        
        Args:
            cache_path: Path to save cache file. If None, uses self.cache_path.
            
        Returns:
            True if saved successfully, False otherwise
        """
        log_prefix = "[MetadataService:SaveCache]"
        
        save_path = cache_path or self.cache_path
        if not save_path:
            self.logger.warning(f"{log_prefix} No cache path to save.")
            return False
        
        try:
            # Ensure directory exists
            save_dir = os.path.dirname(save_path)
            if save_dir and not os.path.exists(save_dir):
                os.makedirs(save_dir, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            
            self.cache_path = save_path
            self.logger.info(f"{log_prefix} Successfully saved {len(self.cache)} entries to '{os.path.basename(save_path)}'.")
            return True
        
        except Exception as e:
            self.logger.error(f"{log_prefix} Error saving metadata cache: {e}", exc_info=True)
            return False
    
    def get_metadata(self, key: str) -> Optional[Dict]:
        """
        Get metadata for a key.
        
        Args:
            key: Identifier key
            
        Returns:
            Metadata dictionary or None if not found
        """
        return self.cache.get(key)
    
    def has_metadata(self, key: str) -> bool:
        """
        Check if metadata exists for a key.
        
        Args:
            key: Identifier key
            
        Returns:
            True if metadata exists, False otherwise
        """
        return key in self.cache
    
    def update_metadata(
        self,
        key: str,
        title: str,
        description: str = "",
        tags: str = "",
        thumbnail: str = "",
        playlist: str = "",
        base_thumbnail_for_increment: Optional[str] = None,
        auto_increment_thumb: bool = False
    ) -> bool:
        """
        Update or create metadata entry.
        
        Args:
            key: Identifier key
            title: Video title
            description: Video description
            tags: Video tags
            thumbnail: Thumbnail path
            playlist: Playlist name
            base_thumbnail_for_increment: Base thumbnail path for incrementing
            auto_increment_thumb: Whether to auto-increment thumbnail number
            
        Returns:
            True if updated successfully, False otherwise
        """
        log_prefix = "[MetadataService:Update]"
        
        template_description = description
        template_tags = tags
        template_playlist = playlist
        template_thumbnail = thumbnail
        source_of_template = "Direct input"
        
        # Priority 1: Auto-increment from base thumbnail if enabled
        if auto_increment_thumb and base_thumbnail_for_increment:
            self.logger.info(f"{log_prefix} Attempting to increment thumbnail from base: '{base_thumbnail_for_increment}'")
            source_of_template = f"Incremented from '{os.path.basename(base_thumbnail_for_increment)}'"
            try:
                dir_name = os.path.dirname(base_thumbnail_for_increment)
                base_name = os.path.basename(base_thumbnail_for_increment)
                filename_no_ext, ext = os.path.splitext(base_name)
                
                # Find last number in filename
                match_thumb = re.search(r'(\d+)(?!.*\d)', filename_no_ext)
                
                if match_thumb:
                    number_str = match_thumb.group(1)
                    original_length = len(number_str)
                    number = int(number_str)
                    new_number = number + 1
                    
                    start, end = match_thumb.span(1)
                    new_filename_no_ext = filename_no_ext[:start] + str(new_number).zfill(original_length) + filename_no_ext[end:]
                    
                    new_base_name = new_filename_no_ext + ext
                    template_thumbnail = os.path.join(dir_name, new_base_name)
                    self.logger.info(f"{log_prefix} Successfully incremented thumbnail: '{template_thumbnail}'")
                else:
                    template_thumbnail = base_thumbnail_for_increment
                    self.logger.warning(f"{log_prefix} No number found to increment in thumbnail base name: '{base_name}'")
            except Exception as e_thumb:
                self.logger.error(f"{log_prefix} Error processing thumbnail increment: {e_thumb}")
                template_thumbnail = base_thumbnail_for_increment
        
        # Priority 2: Get template from first cache entry if thumbnail still empty
        if not template_thumbnail:
            try:
                if self.cache and isinstance(self.cache, dict):
                    first_key = next(iter(self.cache))
                    template_data = self.cache[first_key]
                    template_thumbnail = template_data.get("thumbnail", "")
                    source_of_template = f"First entry (key: '{first_key}') from cache"
                else:
                    raise ValueError("Cache is empty or not a dictionary.")
            except Exception:
                source_of_template = "Empty (fallback)"
        
        # Priority 3: Get other fields from first cache entry if not provided
        if not template_description or not template_tags or not template_playlist:
            try:
                if self.cache and isinstance(self.cache, dict):
                    first_key = next(iter(self.cache))
                    template_data = self.cache[first_key]
                    if not template_description:
                        template_description = template_data.get("description", "")
                    if not template_tags:
                        template_tags = template_data.get("tags", "")
                    if not template_playlist:
                        template_playlist = template_data.get("playlist", "")
            except Exception as e_get_template:
                self.logger.warning(f"{log_prefix} Could not get template fields: {e_get_template}")
        
        # Update cache entry
        self.cache[key] = {
            "title": title,
            "description": template_description,
            "tags": template_tags,
            "thumbnail": template_thumbnail,
            "playlist": template_playlist
        }
        
        self.logger.info(f"{log_prefix} Updated/added key '{key}' (Template source: {source_of_template})")
        return True
    
    # ========================================================================
    # AUTOFILL METHODS
    # ========================================================================
    
    def autofill_youtube_fields(self, file_path: str, identifier: Optional[str] = None) -> Dict[str, str]:
        """
        Auto-fill YouTube fields from metadata cache.
        
        Args:
            file_path: Path to video file
            identifier: Optional identifier key. If None, extracts from file_path.
            
        Returns:
            Dictionary with filled fields: title, description, tags, thumbnail, playlist
        """
        log_prefix = "[MetadataService:Autofill]"
        
        result = {
            "title": "",
            "description": "",
            "tags": "",
            "thumbnail": "",
            "playlist": ""
        }
        
        # Get identifier
        if not identifier:
            identifier = get_identifier_from_source(file_path)
        
        if not identifier:
            self.logger.warning(f"{log_prefix} Could not extract identifier from file path: {file_path}")
            return result
        
        self.logger.info(f"{log_prefix} Looking for metadata with key: '{identifier}'")
        
        # Get metadata from cache
        metadata = self.get_metadata(identifier)
        if metadata:
            result["title"] = metadata.get('title', '')
            result["description"] = metadata.get('description', '')
            result["tags"] = metadata.get('tags', '')
            result["thumbnail"] = metadata.get('thumbnail', '')
            result["playlist"] = metadata.get('playlist', '')
            
            self.logger.info(f"{log_prefix} Successfully found and applied metadata for key '{identifier}'.")
        else:
            self.logger.warning(f"{log_prefix} No metadata found for key '{identifier}' in cache.")
        
        return result
    
    def get_title_from_filename(self, file_path: str) -> str:
        """
        Extract title from filename (without extension).
        
        Args:
            file_path: Path to file
            
        Returns:
            Title extracted from filename
        """
        try:
            base_name = os.path.basename(file_path)
            return os.path.splitext(base_name)[0]
        except Exception:
            return ""
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def extract_description_from_metadata(self, key: str) -> str:
        """
        Extract description from metadata for a given key.
        
        Args:
            key: Identifier key
            
        Returns:
            Description string or empty string if not found
        """
        metadata = self.get_metadata(key)
        if metadata:
            return metadata.get('description', '')
        return ""
    
    def parse_filename_metadata(self, filename: str) -> Dict[str, str]:
        """
        Parse metadata from filename (if there's a pattern).
        
        This is a placeholder for future filename parsing logic.
        
        Args:
            filename: Filename to parse
            
        Returns:
            Dictionary with parsed metadata
        """
        # Placeholder - can be extended with actual parsing logic
        return {
            "title": os.path.splitext(filename)[0],
            "description": "",
            "tags": "",
            "thumbnail": "",
            "playlist": ""
        }
    
    def get_cache_size(self) -> int:
        """
        Get number of entries in cache.
        
        Returns:
            Number of cache entries
        """
        return len(self.cache) if self.cache else 0
    
    def clear_cache(self):
        """Clear all entries from cache."""
        self.cache = {}
        self.logger.info("[MetadataService] Cache cleared.")

