"""
System utility functions for Piu application.

Functions for executing system commands, checking hardware, and managing shutdown.
"""

import os
import sys
import subprocess
import logging
import re
import psutil
from typing import Tuple


def normalize_hwid_string(s: str) -> str:
    """
    Normalize a hardware ID string.
    
    Args:
        s: Input string
        
    Returns:
        Normalized string (uppercase, alphanumeric only)
    """
    s = (s or "").strip().upper()
    s = re.sub(r"[^A-Z0-9-]", "", s)
    s = s.replace("-", "")
    return s


def is_plausible_hwid(s: str) -> bool:
    """
    Check if hardware ID is plausible (not invalid).
    
    Args:
        s: Hardware ID string to check
        
    Returns:
        True if plausible, False otherwise
    """
    if not s or len(s) < 8:
        return False
    if set(s) == {"F"} or set(s) == {"0"}:
        return False
    return True


def run_system_command(command):
    """
    Execute system command safely.
    
    Args:
        command: List of command arguments
        
    Returns:
        True if successful, False otherwise
    """
    logging.info(f"Executing system command: {' '.join(command)}")
    try:
        startupinfo = None
        creationflags = 0
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(
            command,
            check=False,
            shell=False,
            startupinfo=startupinfo,
            creationflags=creationflags,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            logging.info(f"Command executed successfully. Output: {result.stdout.strip()}")
            return True
        else:
            logging.error(f"Command failed with code {result.returncode}. Command: '{' '.join(command)}'. Error: {result.stderr.strip()}")
            return False
    except FileNotFoundError as e:
        logging.error(f"Error running command '{' '.join(command)}': File not found - {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error running command '{' '.join(command)}': {e}", exc_info=True)
        return False


def shutdown_system(delay_minutes=3):
    """
    Schedule system shutdown.
    
    Args:
        delay_minutes: Minutes before shutdown (default: 3)
        
    Returns:
        True if successful, False otherwise
    """
    logging.info(f"Requesting system shutdown after {delay_minutes} minutes...")
    if os.name == 'nt':
        seconds = delay_minutes * 60
        if run_system_command(['shutdown', '/s', '/t', str(seconds)]):
            logging.info("System shutdown scheduled successfully.")
            return True
    else:  # Linux/macOS (May require sudo)
        logging.warning("Shutdown on Linux/macOS may require sudo.")
        if run_system_command(['sudo', 'shutdown', '-h', f'+{delay_minutes}']):
            logging.info("System shutdown scheduled successfully (may require sudo).")
            return True
    logging.error("Could not schedule system shutdown.")
    return False


def cancel_shutdown_system():
    """
    Cancel scheduled system shutdown.
    
    Returns:
        True if successful, False otherwise
    """
    logging.info("Requesting to cancel system shutdown...")
    if os.name == 'nt':
        if run_system_command(['shutdown', '/a']):
            logging.info("System shutdown cancelled successfully.")
            return True
    else:  # Linux/macOS (May require sudo)
        logging.warning("Cancelling shutdown on Linux/macOS may require sudo.")
        if run_system_command(['sudo', 'shutdown', '-c']):
            logging.info("System shutdown cancelled successfully (may require sudo).")
            return True
    logging.warning("Could not cancel system shutdown (may not be scheduled?).")
    return False


def is_cuda_available():
    """
    Check if CUDA is available and get total VRAM if found.
    
    Returns:
        Tuple of (status_string, total_vram_mb)
        status_string: 'AVAILABLE', 'NO_DEVICE', 'COMMAND_NOT_FOUND', 'ERROR'
        total_vram_mb: Total VRAM in MB if found, otherwise 0
    """
    try:
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW
        
        logging.debug("Running nvidia-smi to check CUDA and VRAM...")
        r = subprocess.run(
            ["nvidia-smi"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            creationflags=creationflags,
            check=False,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        if r.returncode == 0:
            stdout_content = r.stdout if r.stdout else ""
            stdout_lower = stdout_content.lower()

            has_cuda_version = "cuda version" in stdout_lower
            gpu_line_pattern = r"\|\s*\d+\s+nvidia"
            has_gpu_listed = re.search(gpu_line_pattern, stdout_content, re.IGNORECASE | re.MULTILINE) is not None

            if has_cuda_version and has_gpu_listed:
                total_vram_mb = 0
                # Pattern to find Memory-Usage line, e.g.: | 12052MiB /  12288MiB |
                mem_pattern = r"(\d+)\s*MiB\s*/\s*(\d+)\s*MiB"
                match = re.search(mem_pattern, stdout_content)

                if match:
                    try:
                        total_vram_mb = int(match.group(2))  # Get total VRAM
                        logging.info(f"CUDA check: Found GPU, Total VRAM: {total_vram_mb} MiB")
                    except (ValueError, IndexError):
                        logging.warning("Could not parse VRAM from nvidia-smi output.")
                        total_vram_mb = 0
                else:
                    logging.warning("Could not find VRAM info matching pattern in nvidia-smi output.")
                    total_vram_mb = 0

                return 'AVAILABLE', total_vram_mb
            else:
                logging.info("nvidia-smi output does not indicate CUDA-capable GPU.")
                return 'NO_DEVICE', 0
        elif r.returncode == 1:
            logging.debug("nvidia-smi command not found or returned error.")
            return 'COMMAND_NOT_FOUND', 0
        else:
            logging.warning(f"nvidia-smi returned unexpected code: {r.returncode}")
            return 'ERROR', 0
    except FileNotFoundError:
        logging.debug("nvidia-smi command not found in PATH.")
        return 'COMMAND_NOT_FOUND', 0
    except Exception as e:
        logging.error(f"Unknown error running nvidia-smi: {e}", exc_info=True)
        return 'ERROR', 0


def cleanup_stale_chrome_processes(user_data_dir: str) -> bool:
    """
    Find and kill chrome.exe processes that are using the same user-data-dir.
    
    Args:
        user_data_dir: Path to Chrome user data directory
        
    Returns:
        True if any processes were killed, False otherwise
    """
    worker_log_prefix = "[ChromeCleanup]"
    logging.info(f"{worker_log_prefix} Bắt đầu dọn dẹp các tiến trình Chrome cũ có thể còn sót lại...")
    found_and_killed_process = False

    # Normalize path for accurate comparison
    target_user_data_arg = f"--user-data-dir={user_data_dir}"

    try:
        # Iterate through all running processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            # Only check chrome.exe processes
            if 'chrome.exe' in proc.info['name'].lower():
                try:
                    # Get command line used to launch process
                    cmdline = proc.info['cmdline']
                    # Check if command line contains our user-data-dir argument
                    if cmdline and any(target_user_data_arg in arg for arg in cmdline):
                        logging.warning(f"{worker_log_prefix} Tìm thấy tiến trình Chrome cũ (PID: {proc.pid}) đang sử dụng profile. Sẽ buộc dừng...")
                        proc.kill()  # Force kill process
                        proc.wait(timeout=3)  # Wait a bit for process to terminate
                        logging.info(f"{worker_log_prefix} Đã dừng thành công tiến trình PID: {proc.pid}")
                        found_and_killed_process = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Skip if process already terminated or no access permission
                    continue
    except Exception as e:
        logging.error(f"{worker_log_prefix} Lỗi không mong muốn trong quá trình dọn dẹp: {e}", exc_info=True)
    
    if not found_and_killed_process:
        logging.info(f"{worker_log_prefix} Không tìm thấy tiến trình Chrome cũ nào cần dọn dẹp.")
    
    return found_and_killed_process
