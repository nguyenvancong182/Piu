"""
YouTube Service for Piu Application

This service consolidates YouTube upload services and provides unified queue/batch management.
Business logic extracted from Piu.py to improve maintainability and testability.

Migration from Piu.py:
- Queue management (add/remove tasks)
- Batch processing orchestration
- Consolidation of existing YouTube services (API, Browser, Upload helpers)
"""

import logging
import uuid
from typing import Optional, List, Dict, Callable, Tuple, Any

# Selenium imports (optional)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    HAS_SELENIUM = True
except ImportError:
    webdriver = None
    Service = None
    HAS_SELENIUM = False

# Import existing YouTube services
try:
    from services.youtube_upload_service import (
        upload_youtube_thumbnail,
        get_playlist_id_by_name,
        add_video_to_playlist
    )
except ImportError:
    upload_youtube_thumbnail = None
    get_playlist_id_by_name = None
    add_video_to_playlist = None
    logging.warning("YouTube upload service helpers not available")

try:
    from services.youtube_upload_api_service import upload_video_to_youtube
except ImportError:
    upload_video_to_youtube = None
    logging.warning("YouTube API upload service not available")

try:
    from services.youtube_browser_upload_service import (
        init_chrome_driver,
        YOUTUBE_LOCATORS
    )
except ImportError:
    init_chrome_driver = None
    YOUTUBE_LOCATORS = None
    logging.warning("YouTube browser upload service not available")

# Constants
APP_NAME = "Piu"


class YouTubeService:
    """
    Unified YouTube upload service that consolidates API, Browser, and Upload helpers.
    
    This service provides:
    - Queue management (add/remove tasks)
    - Access to upload methods (API, Browser, helpers)
    - Batch processing orchestration support
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize YouTube Service.
        
        Args:
            logger: Optional logger instance. If None, creates a new logger.
        """
        self.logger = logger or logging.getLogger(APP_NAME)
        self.logger.info("[YouTubeService] Initializing YouTube Service...")
        
        # Queue state
        self.queue: List[Dict] = []
        self.currently_processing_task_id: Optional[str] = None
        self.is_uploading: bool = False
        
        # Batch state
        self._batch_finished_once = False
    
    # ========================================================================
    # QUEUE MANAGEMENT METHODS
    # ========================================================================
    
    def add_task_to_queue(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags_str: str = "",
        playlist_name: str = "",
        thumbnail_path: str = "",
        privacy_status: str = "public",
        category_id: str = "22"  # Default: People & Blogs
    ) -> Dict:
        """
        Add a task to the upload queue.
        
        Args:
            video_path: Path to video file
            title: Video title (will be truncated to 100 chars if needed)
            description: Video description
            tags_str: Comma-separated tags
            playlist_name: Playlist name to add video to
            thumbnail_path: Path to thumbnail image
            privacy_status: Privacy status (public, unlisted, private)
            category_id: YouTube category ID
            
        Returns:
            Task dictionary with 'id' and other fields
        """
        log_prefix = "[YouTubeService:AddTask]"
        
        # Truncate title if needed
        if len(title) > 100:
            title = title[:100]
            self.logger.warning(f"{log_prefix} Title too long, truncated to 100 chars: '{title}'")
        
        # Create task
        task_data = {
            "id": str(uuid.uuid4()),
            "video_path": video_path,
            "title": title,
            "description": description,
            "tags_str": tags_str,
            "playlist_name": playlist_name,
            "thumbnail_path": thumbnail_path,
            "privacy_status": privacy_status,
            "category_id": category_id,
            "status": "Chờ xử lý"
        }
        
        self.queue.append(task_data)
        self.logger.info(f"{log_prefix} Added task '{title}' to queue. Total: {len(self.queue)}")
        
        return task_data
    
    def remove_task_from_queue(self, task_id: str) -> bool:
        """
        Remove a task from the upload queue.
        
        Args:
            task_id: ID of task to remove
            
        Returns:
            True if task was removed, False otherwise
        """
        initial_len = len(self.queue)
        self.queue = [task for task in self.queue if task.get('id') != task_id]
        
        removed = len(self.queue) < initial_len
        if removed:
            self.logger.info(f"[YouTubeService:RemoveTask] Removed task (ID: {task_id}) from queue.")
        
        return removed
    
    def get_queue(self) -> List[Dict]:
        """
        Get current upload queue.
        
        Returns:
            List of task dictionaries
        """
        return self.queue.copy()
    
    def clear_queue(self):
        """Clear all tasks from the upload queue."""
        self.queue.clear()
        self.logger.info("[YouTubeService] Queue cleared.")
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task dictionary if found, None otherwise
        """
        return next((t for t in self.queue if t.get('id') == task_id), None)
    
    def get_current_task(self) -> Optional[Dict]:
        """
        Get currently processing task.
        
        Returns:
            Current task dictionary if any, None otherwise
        """
        if self.currently_processing_task_id:
            return self.get_task_by_id(self.currently_processing_task_id)
        return None
    
    def get_waiting_tasks(self) -> List[Dict]:
        """
        Get all waiting tasks (excluding currently processing).
        
        Returns:
            List of waiting task dictionaries
        """
        if not self.currently_processing_task_id:
            return self.queue.copy()
        
        return [task for task in self.queue if task.get('id') != self.currently_processing_task_id]
    
    # ========================================================================
    # BATCH PROCESSING STATE MANAGEMENT
    # ========================================================================
    
    def start_batch(self, first_task_id: Optional[str] = None):
        """
        Start batch processing. Mark the service as uploading.
        
        Args:
            first_task_id: Optional ID of first task to process
        """
        self.is_uploading = True
        self._batch_finished_once = False
        if first_task_id:
            self.currently_processing_task_id = first_task_id
        self.logger.info(f"[YouTubeService] Started batch processing (queue size: {len(self.queue)})")
    
    def stop_batch(self):
        """Stop batch processing."""
        self.is_uploading = False
        self.currently_processing_task_id = None
        self.logger.info("[YouTubeService] Stopped batch processing.")
    
    def finish_batch(self, stopped: bool = False):
        """
        Mark batch as finished.
        
        Args:
            stopped: Whether batch was stopped (True) or completed (False)
        """
        if self._batch_finished_once:
            self.logger.debug("[YouTubeService] Batch finished called multiple times, ignoring.")
            return
        
        self._batch_finished_once = True
        self.is_uploading = False
        self.currently_processing_task_id = None
        
        status = "stopped" if stopped else "completed"
        self.logger.info(f"[YouTubeService] Batch processing finished ({status}).")
    
    def set_current_task(self, task_id: Optional[str]):
        """
        Set currently processing task ID.
        
        Args:
            task_id: Task ID, or None to clear
        """
        self.currently_processing_task_id = task_id
    
    # ========================================================================
    # UPLOAD METHOD ACCESSORS
    # ========================================================================
    
    def upload_video_via_api(
        self,
        youtube_service,
        video_path: str,
        title: str,
        description: Optional[str],
        tags: List[str],
        privacy_status: str,
        category_id: str,
        progress_callback: Optional[Callable[[int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        stop_event=None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload video via YouTube API.
        
        This is a wrapper around upload_video_to_youtube from youtube_upload_api_service.
        
        Returns:
            Tuple of (success, video_id, error_message)
        """
        if upload_video_to_youtube is None:
            return False, None, "YouTube API upload service not available"
        
        return upload_video_to_youtube(
            youtube_service,
            video_path,
            title,
            description,
            tags,
            privacy_status,
            category_id,
            progress_callback,
            log_callback,
            stop_event
        )
    
    def upload_thumbnail(
        self,
        youtube_service,
        video_id: str,
        thumbnail_path: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Upload thumbnail for a video.
        
        This is a wrapper around upload_youtube_thumbnail from youtube_upload_service.
        """
        if upload_youtube_thumbnail is None:
            self.logger.warning("[YouTubeService] Thumbnail upload service not available")
            return False
        
        return upload_youtube_thumbnail(
            youtube_service,
            video_id,
            thumbnail_path,
            log_callback
        )
    
    def get_playlist_id(
        self,
        youtube_service,
        playlist_name: str,
        cache: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Get playlist ID by name.
        
        This is a wrapper around get_playlist_id_by_name from youtube_upload_service.
        """
        if get_playlist_id_by_name is None:
            self.logger.warning("[YouTubeService] Playlist service not available")
            return None
        
        return get_playlist_id_by_name(youtube_service, playlist_name, cache)
    
    def add_to_playlist(
        self,
        youtube_service,
        video_id: str,
        playlist_id: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Add video to playlist.
        
        This is a wrapper around add_video_to_playlist from youtube_upload_service.
        """
        if add_video_to_playlist is None:
            self.logger.warning("[YouTubeService] Add to playlist service not available")
            return False
        
        return add_video_to_playlist(youtube_service, video_id, playlist_id, log_callback)
    
    def init_chrome_driver_wrapper(
        self,
        chrome_portable_exe_path: str,
        chromedriver_exe_path: str,
        headless: bool,
        max_retries: int = 3,
        retry_delay: int = 5
    ) -> Tuple[Optional[Any], Optional[Any], str]:
        """
        Initialize Chrome WebDriver for browser upload.
        
        This is a wrapper around init_chrome_driver from youtube_browser_upload_service.
        """
        if init_chrome_driver is None:
            self.logger.warning("[YouTubeService] Browser upload service not available")
            return None, None, ""
        
        return init_chrome_driver(
            chrome_portable_exe_path,
            chromedriver_exe_path,
            headless,
            max_retries,
            retry_delay
        )
    
    def get_youtube_locators(self) -> Optional[Dict]:
        """
        Get YouTube locators for browser automation.
        
        Returns:
            YOUTUBE_LOCATORS dictionary if available, None otherwise
        """
        return YOUTUBE_LOCATORS


# Convenience function for backward compatibility
def get_youtube_service(logger: Optional[logging.Logger] = None) -> YouTubeService:
    """
    Get an instance of YouTubeService.
    
    Args:
        logger: Optional logger instance
        
    Returns:
        YouTubeService instance
    """
    return YouTubeService(logger)

