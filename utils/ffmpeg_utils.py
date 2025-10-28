"""
FFmpeg utility functions for Piu application.

Functions for finding and managing FFmpeg/FFprobe executables.
"""

import os
import sys
import shutil
import logging
import subprocess
import threading
import platform
from pathlib import Path
from utils.helpers import create_safe_filename


def find_ffmpeg():
    """
    Find ffmpeg executable, prioritizing bundled version or system PATH.
    
    Returns:
        Path to ffmpeg executable, or None if not found
    """
    ffmpeg_exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    
    # Check if running from PyInstaller package
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        # Check alongside executable
        path_alongside = os.path.join(application_path, ffmpeg_exe_name)
        if os.path.exists(path_alongside):
            logging.info(f"Found bundled ffmpeg: {path_alongside}")
            return path_alongside
        # Check in 'bin' subfolder
        path_in_bin = os.path.join(application_path, 'bin', ffmpeg_exe_name)
        if os.path.exists(path_in_bin):
            logging.info(f"Found bundled ffmpeg in 'bin': {path_in_bin}")
            return path_in_bin
    
    # Check system PATH
    system_path = shutil.which(ffmpeg_exe_name)
    if system_path:
        logging.info(f"Found ffmpeg in system PATH: {system_path}")
        return system_path
    
    logging.error(f"Could not find '{ffmpeg_exe_name}' bundled or in system PATH.")
    return None


def find_ffprobe():
    """
    Find ffprobe executable, prioritizing version alongside ffmpeg or in PATH.
    
    Returns:
        Path to ffprobe executable, or None if not found
    """
    ffprobe_exe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    ffmpeg_path = find_ffmpeg()  # Get ffmpeg path
    
    # 1. Try to find ffprobe in same directory as ffmpeg
    if ffmpeg_path:
        ffprobe_alongside_ffmpeg = os.path.join(os.path.dirname(ffmpeg_path), ffprobe_exe_name)
        if os.path.exists(ffprobe_alongside_ffmpeg) and os.access(ffprobe_alongside_ffmpeg, os.X_OK):
            logging.info(f"Found ffprobe alongside ffmpeg: {ffprobe_alongside_ffmpeg}")
            return ffprobe_alongside_ffmpeg
    
    # 2. Try system PATH
    system_ffprobe_path = shutil.which(ffprobe_exe_name)
    if system_ffprobe_path:
        logging.info(f"Found ffprobe in system PATH: {system_ffprobe_path}")
        return system_ffprobe_path
    
    # 3. Try current directory (same level as script)
    local_ffprobe_path = os.path.join(os.path.abspath("."), ffprobe_exe_name)
    if os.path.exists(local_ffprobe_path) and os.access(local_ffprobe_path, os.X_OK):
        logging.info(f"Found ffprobe in current directory: {local_ffprobe_path}")
        return local_ffprobe_path
    
    logging.error(f"Could not find '{ffprobe_exe_name}' alongside ffmpeg, in PATH, or current directory.")
    return None


def create_ffmpeg_concat_file_list(file_paths, output_list_file):
    """
    Create FFmpeg concat demuxer file list.
    
    Args:
        file_paths: List of file paths (video or audio)
        output_list_file: Path to output list file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(output_list_file, "w", encoding="utf-8") as f_list:
            for file_path in file_paths:
                # FFmpeg concat demuxer requires POSIX paths
                safe_path = Path(os.path.abspath(file_path)).as_posix()
                f_list.write(f"file '{safe_path}'\n")
        return True
    except Exception as e:
        logging.error(f"Error creating FFmpeg concat file list ({os.path.basename(output_list_file)}): {e}")
        return False


def ffmpeg_split_media(input_path, output_folder, segment_duration_seconds=900):
    """
    Use FFmpeg to split a media file into smaller segments.
    Returns a list of paths to the created segment files.
    
    Args:
        input_path: Path to input media file
        output_folder: Output directory for segments
        segment_duration_seconds: Duration of each segment in seconds (default: 900 = 15 minutes)
        
    Returns:
        List of created segment file paths, or None if failed
    """
    log_prefix = f"[{threading.current_thread().name}_SplitMedia]"
    ffmpeg_executable = find_ffmpeg()
    if not ffmpeg_executable:
        logging.error(f"{log_prefix} Không tìm thấy FFmpeg.")
        return None

    base_name, ext = os.path.splitext(os.path.basename(input_path))
    safe_base_name = create_safe_filename(base_name, remove_accents=False)
    output_pattern = os.path.join(output_folder, f"{safe_base_name}_part_%03d{ext}")

    command = [
        ffmpeg_executable, "-y",
        "-i", os.path.abspath(input_path),
        "-c", "copy",          # Sao chép codec, không mã hóa lại, rất nhanh
        "-map", "0",           # Sao chép tất cả các luồng (video, audio, sub...)
        "-segment_time", str(segment_duration_seconds), # Thời lượng mỗi đoạn (giây)
        "-f", "segment",       # Chế độ chia file
        "-reset_timestamps", "1", # Reset timestamp cho mỗi file con
        os.path.abspath(output_pattern)
    ]

    logging.info(f"{log_prefix} Bắt đầu chia file '{base_name}' thành các đoạn {segment_duration_seconds}s...")
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        
        # Tìm các file đã được tạo ra
        created_files = sorted([
            os.path.join(output_folder, f) for f in os.listdir(output_folder)
            if f.startswith(f"{safe_base_name}_part_") and f.endswith(ext)
        ])
        
        logging.info(f"{log_prefix} Đã chia thành công {len(created_files)} file con.")
        return created_files

    except subprocess.CalledProcessError as e:
        logging.error(f"{log_prefix} Lỗi FFmpeg khi chia file: {e.stderr}")
        return None
    except Exception as e:
        logging.error(f"{log_prefix} Lỗi không mong muốn khi chia file: {e}", exc_info=True)
        return None


def get_video_duration_s(video_path_to_probe):
    """
    Get video duration in seconds using ffprobe.
    Returns float duration or 0.0 if error.
    
    Args:
        video_path_to_probe: Path to video file
        
    Returns:
        Duration in seconds (float) or 0.0 if error
    """
    ffprobe_exe_path = find_ffprobe()
    if not ffprobe_exe_path or not os.path.exists(video_path_to_probe):
        logging.warning(f"[GetDuration] ffprobe không có hoặc file '{os.path.basename(video_path_to_probe)}' không tồn tại.")
        return 0.0
    try:
        command = [ffprobe_exe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path_to_probe]
        creation_flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False, creationflags=creation_flags)
        if result.returncode == 0 and result.stdout.strip() and result.stdout.strip().lower() != "n/a":
            duration = float(result.stdout.strip())
            logging.debug(f"[GetDuration] Thời lượng của '{os.path.basename(video_path_to_probe)}' là {duration:.3f}s")
            return duration
        else:
            logging.warning(f"[GetDuration] ffprobe lỗi hoặc không trả về duration. Output: '{result.stdout.strip()}'.")
            return 0.0
    except Exception as e:
        logging.error(f"[GetDuration] Exception khi lấy duration: {e}", exc_info=False)
        return 0.0

