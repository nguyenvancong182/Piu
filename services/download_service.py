"""
Download service helpers for running yt-dlp with streaming stdout.
"""

import logging
import os
import subprocess
import sys
from typing import Callable, Generator, Iterable, List, Optional, Sequence


def stream_process_output(
    full_cmd: Sequence[str],
    *,
    process_name: str = "yt-dlp",
    hide_console_window: bool = True,
    set_current_process: Optional[Callable[[subprocess.Popen], None]] = None,
    clear_current_process: Optional[Callable[[], None]] = None,
) -> Generator[str, None, int]:
    """
    Spawn a subprocess and yield stdout lines as they arrive.

    Args:
        full_cmd: Complete command list (program + args)
        process_name: Label for logs
        hide_console_window: On Windows, create the process with no window
        set_current_process: Optional callback to expose the Popen object
        clear_current_process: Optional callback to clear process reference

    Yields:
        Lines (str) from combined stdout/stderr stream.

    Returns:
        Process return code (via StopIteration.value)
    """
    startupinfo = None
    creationflags = 0
    if hide_console_window and os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW

    logging.info(f"[{process_name}] Spawning: {subprocess.list2cmdline(list(full_cmd))}")
    proc: Optional[subprocess.Popen] = None
    try:
        proc = subprocess.Popen(
            list(full_cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            universal_newlines=True,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
        if set_current_process:
            try:
                set_current_process(proc)
            except Exception:
                logging.debug("set_current_process callback error, continuing.")

        logging.info(f"[{process_name}] Started (PID: {proc.pid})")

        # Stream stdout
        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, ""):
            yield line

        # End of stream: wait for return code
        rc = proc.wait(timeout=900)
        logging.info(f"[{process_name}] Exited with code {rc}")
        return rc

    finally:
        try:
            if clear_current_process:
                clear_current_process()
        except Exception:
            logging.debug("clear_current_process callback error, continuing.")
"""
Download Service for Piu Application

This service handles YouTube video download using yt-dlp.
Currently this is a SKELETON - full logic is still in Piu.py.

Migration Strategy:
1. Create this skeleton
2. Gradually move functions here from Piu.py
3. Update imports one at a time
4. Test after each change
"""

import subprocess
import os
import logging
from typing import List, Dict, Optional

try:
    from config.constants import get_ytdlp_path
except ImportError:
    # Fallback if constants not available yet
    import shutil
    import sys
    
    def get_ytdlp_path():
        """Fallback yt-dlp path finder"""
        cmd = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
        return shutil.which(cmd) or cmd


class DownloadService:
    """
    Service for handling YouTube video downloads using yt-dlp.
    
    TODO: Gradually migrate download logic from Piu.py:
    - start_download() method
    - run_download() method
    - Queue management
    - Sheet integration
    """
    
    def __init__(self):
        """Initialize download service"""
        self.ytdlp_path = get_ytdlp_path()
        logging.info(f"DownloadService initialized with yt-dlp: {self.ytdlp_path}")
    
    def is_available(self) -> bool:
        """
        Check if yt-dlp is available.
        
        Returns:
            True if yt-dlp can be used
        """
        return self.ytdlp_path is not None
    
    def get_default_downloads_folder(self) -> str:
        """
        Get default downloads folder path.
        
        Returns:
            Path to user's Downloads folder
        """
        if os.name == 'nt':  # Windows
            try:
                downloads_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
                if os.path.exists(downloads_folder):
                    return downloads_folder
            except Exception:
                pass
            return os.getcwd()
        else:  # Linux/Mac
            return os.path.expanduser('~/Downloads')
    
    def validate_url(self, url: str) -> bool:
        """
        Validate a YouTube URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid
        """
        if not url or not isinstance(url, str):
            return False
        
        return url.startswith(('http://', 'https://')) and (
            'youtube.com' in url or 
            'youtu.be' in url
        )
    
    def parse_urls_from_text(self, text: str) -> List[str]:
        """
        Parse URLs from multiline text.
        
        Args:
            text: Text containing URLs
            
        Returns:
            List of valid URLs
        """
        urls = []
        seen = set()
        
        for line in text.splitlines():
            url = line.strip()
            if self.validate_url(url) and url not in seen:
                urls.append(url)
                seen.add(url)
        
        return urls
    
    def build_ytdlp_command(
        self,
        url: str,
        output_path: str,
        mode: str = "video",
        video_quality: str = "1080",
        audio_quality: str = "128",
        playlist: bool = False,
        cookies_file: Optional[str] = None
    ) -> List[str]:
        """
        Build yt-dlp command for downloading.
        
        Args:
            url: YouTube URL
            output_path: Output folder path
            mode: Download mode (video/audio)
            video_quality: Video quality (e.g., "1080")
            audio_quality: Audio quality (e.g., "128")
            playlist: Download as playlist
            cookies_file: Path to cookies file
            
        Returns:
            Command list for subprocess
        """
        cmd = [self.ytdlp_path]
        
        # Output path
        cmd.extend(["-o", os.path.join(output_path, "%(title)s.%(ext)s")])
        
        # Mode
        if mode == "audio":
            cmd.append("-x")
            cmd.extend(["--audio-format", "mp3"])
            cmd.extend(["--audio-quality", f"{audio_quality}K"])
        else:  # video
            cmd.extend(["-f", f"bestvideo[height<={video_quality}]+bestaudio/best[height<={video_quality}]"])
        
        # Playlist
        if playlist:
            cmd.append("--yes-playlist")
        
        # Cookies
        if cookies_file and os.path.exists(cookies_file):
            cmd.extend(["--cookies", cookies_file])
        
        # URL
        cmd.append(url)
        
        return cmd
    
    def download_video(
        self,
        url: str,
        output_path: str,
        config: Dict,
        progress_callback=None
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Download a single video.
        
        Args:
            url: Video URL
            output_path: Output folder
            config: Download configuration
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (success, downloaded_file_path, error_message)
        """
        try:
            cmd = self.build_ytdlp_command(
                url=url,
                output_path=output_path,
                mode=config.get("mode", "video"),
                video_quality=config.get("v_quality", "1080"),
                audio_quality=config.get("a_quality", "128"),
                playlist=config.get("download_playlist", False),
                cookies_file=config.get("cookies_file")
            )
            
            logging.info(f"Executing yt-dlp: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logging.info(f"Successfully downloaded: {url}")
                return True, None, None
            else:
                error_msg = result.stderr or result.stdout
                logging.error(f"Download failed: {error_msg}")
                return False, None, error_msg
                
        except subprocess.TimeoutExpired:
            error_msg = "Download timed out"
            logging.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            logging.error(error_msg)
            return False, None, error_msg

