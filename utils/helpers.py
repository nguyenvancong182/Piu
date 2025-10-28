"""
Helper utility functions for Piu application.

These are pure utility functions that can be extracted safely.
"""

import os
import sys
import logging
import re
import subprocess
import threading
from pathlib import Path
from typing import Optional
from unidecode import unidecode


def safe_int(s, default=0) -> int:
    """
    Safely convert to int, return default value if failed.
    
    Args:
        s: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(s)
    except (ValueError, TypeError):
        return default


def parse_timecode(tc: str) -> int:
    """
    Convert timecode string HH:MM:SS,ms to milliseconds.
    
    Args:
        tc: Timecode string (e.g., "01:23:45,678")
        
    Returns:
        Milliseconds, or 0 if invalid
    """
    try:
        h, m, sms = tc.split(":")
        s, ms = sms.split(",")
        return (int(h)*3600 + int(m)*60 + int(s))*1000 + int(ms)
    except Exception:
        return 0


def ms_to_tc(ms: int | float) -> str:
    """
    Convert milliseconds to timecode string HH:MM:SS,ms.
    
    Args:
        ms: Milliseconds (int or float)
        
    Returns:
        Timecode string (e.g., "01:23:45,678")
    """
    if not isinstance(ms, (int, float)): 
        try:
            ms = float(ms)
        except ValueError:
            logging.error(f"ms_to_tc: Invalid input '{ms}', returning 00:00:00,000")
            return "00:00:00,000"

    ms_int = int(round(float(ms))) 
    
    if ms_int < 0: 
        ms_int = 0
    
    hh = ms_int // 3600000
    ms_int %= 3600000
    mm = ms_int // 60000
    ms_int %= 60000
    ss = ms_int // 1000
    ms_int %= 1000
    
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms_int:03d}"


def get_default_downloads_folder() -> str:
    """
    Get default Downloads folder path for current user.
    
    Returns:
        Path to user's Downloads folder, or "." if unavailable
    """
    try:
        # Use Path.home() to get user's home directory
        # Then join with 'Downloads'
        downloads_path = Path.home() / "Downloads"
        return str(downloads_path)
    except Exception as e:
        logging.error(f"Could not determine default Downloads folder: {e}. Using current directory.")
        # Return current directory if error
        return "."


def open_file_with_default_app(filepath: str):
    """
    Open file with default OS application.
    
    Args:
        filepath: Path to file to open
    """
    try:
        abs_path = os.path.abspath(filepath)
        logging.info(f"Opening file with default app: {abs_path}")
        if sys.platform == "win32":
            os.startfile(abs_path.replace("/", "\\"))
        elif sys.platform == "darwin":  # macOS
            subprocess.run(["open", abs_path], check=True)
        else:  # Linux and other Unix OS
            subprocess.run(["xdg-open", abs_path], check=True)
    except FileNotFoundError:
        logging.error(f"Could not open file: File not found '{filepath}'")
        # Note: messagebox not available in utils module
        # Error will be logged
    except Exception as e:
        logging.error(f"Error opening file '{filepath}': {e}", exc_info=True)


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for both dev and PyInstaller.
    
    Args:
        relative_path: Relative path from project root
        
    Returns:
        Absolute path to the resource
    """
    try:
        base_path = sys._MEIPASS  # PyInstaller creates this folder
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def create_safe_filename(original_name: str, remove_accents: bool = True, max_length: Optional[int] = None) -> str:
    """
    Create a safe filename for the OS by sanitizing special characters.
    
    Args:
        original_name: Original filename string
        remove_accents: True to remove diacritics using unidecode
        max_length: Maximum length for filename (without extension)
        
    Returns:
        Cleaned safe filename string
    """
    try:
        from unidecode import unidecode
    except ImportError:
        unidecode = None
        if remove_accents:
            logging.warning("unidecode not available, cannot remove accents")
    
    if not isinstance(original_name, str):
        logging.warning(f"Invalid input type for create_safe_filename: {type(original_name)}")
        return "invalid_filename_input"
    
    import re
    import platform
    
    s = original_name
    
    # 1. Remove diacritics if requested
    if remove_accents and unidecode:
        try:
            s = unidecode(s)
        except Exception as e:
            logging.warning(f"Unidecode failed for '{original_name}': {e}")
    
    # 2. Remove invalid characters
    invalid_chars_pattern = r'[<>:"/\\|?*\x00-\x1f]+'
    s = re.sub(invalid_chars_pattern, '', s)
    
    # 3. Handle spaces and hyphens
    s = s.strip()
    s = re.sub(r'\s*-\s*', '-', s)
    s = re.sub(r'[\s.]+', '_', s)
    
    # 4. Strip leading/trailing special chars
    s = s.strip(' ._')
    
    # 5. Check Windows reserved names
    reserved_names = {'CON', 'PRN', 'AUX', 'NUL'} | {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}
    if platform.system() == "Windows" and s.upper() in reserved_names:
        logging.warning(f"Filename '{s}' is Windows reserved name. Adding underscore.")
        s = f"_{s}_"
    
    # 6. Limit length
    if max_length is not None and len(s) > max_length:
        s = s[:max_length]
        s = s.strip(' ._')
    
    # 7. Ensure not empty
    if not s:
        logging.warning(f"Filename became empty after cleaning '{original_name}'. Using default.")
        return "cleaned_filename"
    
    return s


def remove_vietnamese_diacritics(filepath: str) -> str:
    """
    Rename file to remove Vietnamese diacritics and clean the name.
    
    Args:
        filepath: Path to file to rename
        
    Returns:
        New path after renaming (or original if failed/no change needed)
    """
    folder = os.path.dirname(filepath)
    base = os.path.basename(filepath)
    name, ext = os.path.splitext(base)
    
    safe_name = create_safe_filename(name, remove_accents=True)
    new_base = safe_name + ext
    new_path = os.path.join(folder, new_base)
    
    if new_path.lower() == filepath.lower():
        return filepath
    
    if os.path.exists(new_path):
        return new_path
    
    try:
        os.replace(filepath, new_path)
        logging.info(f"Renamed '{base}' to '{new_base}'")
        return new_path
    except Exception as e:
        logging.error(f"Error renaming file '{filepath}' to '{new_path}': {e}")
        return filepath


def strip_series_chapter_prefix(title: str, series_name: str = "") -> str:
    """
    Remove series and chapter prefixes from title.
    
    Args:
        title: Title to clean
        series_name: Series name to remove if present
        
    Returns:
        Cleaned title without prefixes
    """
    import re
    
    t = (title or "").strip()
    if not t:
        return ""
    
    # Remove "<Series> - " if present
    if series_name:
        series_prefix = f"{series_name} - "
        if t.lower().startswith(series_prefix.lower()):
            t = t[len(series_prefix):].lstrip()
    
    # Remove "Chương <số>:" or "Chương <số>-"
    t = re.sub(r'(?i)^\s*Chương\s*\d+\s*[:\-\–]\s*', '', t).strip()
    return t


def sanitize_youtube_text(text: str, max_length: int = None) -> str:
    """
    Sanitize YouTube text by removing special characters.
    
    Args:
        text: Text to sanitize
        max_length: Maximum length for text
        
    Returns:
        Sanitized text string
    """
    import re
    
    if not text or not isinstance(text, str):
        return ""
    
    # Remove timestamps [00:00], (00:00), etc.
    text = re.sub(r'\s*(?:\[|\(|\<)\s*\d+[:\-]\d+\s*(?:\]|\)|\>)\s*', '', text)
    
    # Remove other bracketed content
    text = re.sub(r'\[.*?\]|\(.*?\)|\<.*?\>', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Limit length
    if max_length is not None and len(text) > max_length:
        text = text[:max_length].strip()
    
    return text


def get_dpi_scaling_factor(root_window) -> float:
    """
    Get actual DPI scaling factor of screen where window is displayed.
    Windows only. Uses Windows API for accurate per-monitor DPI.
    
    Args:
        root_window: Application main window (tkinter or ctk)
        
    Returns:
        float: Scaling factor (e.g. 1.0 for 100%, 1.25 for 125%)
               Returns 1.0 if not Windows or on error
    """
    import sys
    import ctypes
    import logging
    
    if sys.platform == "win32":
        try:
            # Get window handle (HWND) - unique identifier for window in Windows
            # For tkinter, need to use GetParent to get top-level window handle
            hwnd = ctypes.windll.user32.GetParent(root_window.winfo_id())
            
            # Call Windows API to get DPI for monitor containing window
            # This is most accurate method, works well with multiple monitors at different scales
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            
            # Standard Windows DPI is 96 (corresponds to 100%)
            # Scaling factor = current DPI / 96
            # Example: 125% screen will have DPI of 120. Factor = 120 / 96 = 1.25
            scaling_factor = dpi / 96.0
            
            logging.info(f"Detected Windows DPI Scaling: {scaling_factor*100:.0f}% (DPI: {dpi})")
            return scaling_factor
        except Exception as e:
            logging.error(f"Could not get DPI scaling from Windows API: {e}. Default to 1.0")
            # If any error, return 1.0 to avoid breaking UI
            return 1.0
    
    # Default return 1.0 for other OS like macOS or Linux
    return 1.0


def get_work_area(root):
    """
    Get actual work area size (excluding Taskbar).
    
    Args:
        root: Root window (tkinter or ctk)
        
    Returns:
        Tuple of (width, height) or (1280, 720) as fallback
    """
    import sys
    import ctypes
    import logging
    
    if sys.platform == "win32":
        try:
            from ctypes import wintypes
            
            # Windows RECT structure
            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG),
                ]
            
            rect = RECT()
            SPI_GETWORKAREA = 0x0030
            
            # Call Windows API
            if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
                work_width = rect.right - rect.left
                work_height = rect.bottom - rect.top
                logging.info(f"Got work area (WinAPI): {work_width}x{work_height}")
                return work_width, work_height
            else:
                logging.warning("SystemParametersInfoW (SPI_GETWORKAREA) failed.")
        except Exception as e:
            logging.error(f"Error getting work area via WinAPI: {e}")
    
    # Fallback for other OS or if WinAPI fails
    logging.info("Using fallback method (winfo_screenwidth/height) to get work area.")
    if root and hasattr(root, 'winfo_screenwidth'):
        return root.winfo_screenwidth(), root.winfo_screenheight()
    return 1280, 720  # Final fallback


def play_sound_async(audio_path: str, playsound_available: bool = True, playsound_func=None):
    """
    Play audio file in a separate thread.
    
    Args:
        audio_path: Path to audio file
        playsound_available: Flag indicating if playsound library is available
        playsound_func: The playsound function if available
    """
    if not playsound_available:
        logging.warning("Playsound library not available, cannot play sound.")
        return
    
    if not audio_path or not isinstance(audio_path, str) or not os.path.isfile(audio_path):
        logging.warning(f"Invalid audio path or file doesn't exist: '{audio_path}'")
        return
    
    def play_thread_target(path):
        try:
            logging.info(f"Attempting to play audio: {path}")
            if playsound_func:
                playsound_func(path)
            logging.info("Audio playback completed.")
        except PermissionError as e:
            if "[WinError 32]" in str(e):
                logging.warning(f"Ignoring playsound temp file cleanup error: {e}")
            else:
                logging.error(f"Other PermissionError during playsound: {e}")
        except Exception as e:
            logging.error(f"Error playing audio '{path}': {e}", exc_info=True)
    
    try:
        import threading
        logging.info("Starting audio playback thread...")
        thread = threading.Thread(target=play_thread_target, args=(audio_path,), daemon=True, name="SoundPlayerThread")
        thread.start()
    except Exception as e:
        logging.error(f"Error starting audio playback thread: {e}", exc_info=True)


def parse_color_string_to_tuple(color_str, default_color_tuple=(255, 255, 255)):
    """
    Convert color string "R,G,B" to tuple (R, G, B).
    
    Args:
        color_str: Color string in format "R,G,B"
        default_color_tuple: Default RGB tuple if parsing fails
        
    Returns:
        Tuple (R, G, B) with values 0-255
    """
    try:
        # Remove extra whitespace and split by comma
        parts = [p.strip() for p in color_str.split(',')]
        # Convert to integers
        rgb_values = list(map(int, parts))
        
        # Check if there are exactly 3 values in range 0-255
        if len(rgb_values) == 3 and all(0 <= val <= 255 for val in rgb_values):
            return tuple(rgb_values)
        else:
            logging.warning(f"Invalid color string: '{color_str}'. Must be 'R,G,B' with values 0-255. Using default {default_color_tuple}.")
            return default_color_tuple
    except ValueError:
        logging.warning(f"Error parsing color string '{color_str}' (ValueError). Must be integers R,G,B. Using default {default_color_tuple}.")
        return default_color_tuple
    except Exception as e:
        logging.warning(f"Unknown error parsing color string '{color_str}': {e}. Using default {default_color_tuple}.")
        return default_color_tuple


def format_timestamp(seconds: float, separator: str = ','):
    """
    Format seconds to HH:MM:SS,ms or HH:MM:SS.ms format.
    
    Args:
        seconds: Time in seconds (must be >= 0)
        separator: Separator for milliseconds (',' or '.')
        
    Returns:
        Formatted string like "01:23:45,678" or "01:23:45.678"
    """
    assert seconds >= 0, "Timestamp must be non-negative"
    milliseconds = round(seconds * 1000.0)
    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000
    minutes = milliseconds // 60_000
    milliseconds %= 60_000
    secs = milliseconds // 1_000
    milliseconds %= 1_000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{milliseconds:03d}"


def normalize_string_for_comparison(text: str) -> str:
    """
    Normalize a string for comparison purposes.
    - Remove Vietnamese diacritics
    - Convert to lowercase
    - Keep only alphanumeric characters
    
    Args:
        text: Input string to normalize
        
    Returns:
        Normalized string (alphanumeric only, lowercase, no accents)
    """
    if not text:
        return ""
    try:
        # 1. Remove diacritics (e.g., "Thương Khung" -> "Thuong Khung")
        no_accents = unidecode(text)
        # 2. Convert to lowercase
        lowercased = no_accents.lower()
        # 3. Keep only letters and numbers, remove everything else (spaces, |, -, etc.)
        alphanumeric_only = re.sub(r'[^a-z0-9]', '', lowercased)
        return alphanumeric_only
    except Exception as e:
        logging.error(f"Error normalizing string '{text}': {e}")
        return text.lower()  # Return lowercase if error


def get_identifier_from_source(source_path_or_url: str) -> Optional[str]:
    """
    Create a consistent identifier key from a URL or file path.
    - For YouTube links, it will be the video ID
    - For local files, it will be the filename without extension
    
    Args:
        source_path_or_url: URL or local file path
        
    Returns:
        Identifier string (video ID or filename) or None if invalid input
    """
    if not source_path_or_url:
        return None

    try:
        # Check if it's a URL
        if source_path_or_url.startswith(('http://', 'https://')):
            # Use strong, proven regex to extract exactly 11 characters of YouTube ID
            video_id_match = re.search(
                r'(?:youtube(?:-nocookie)?\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})',
                source_path_or_url
            )
            
            if video_id_match:
                video_id = video_id_match.group(1)
                logging.debug(f"[get_identifier] Successfully extracted YouTube ID: '{video_id}' from URL.")
                return video_id
            else:
                # Fallback: If not YouTube link, use part of URL
                clean_url = re.sub(r'https?://(www\.)?', '', source_path_or_url)
                safe_name = create_safe_filename(clean_url, max_length=50)
                logging.warning(f"[get_identifier] Could not extract YouTube ID, using safe name from URL: '{safe_name}'")
                return safe_name
        else:
            # If it's a local file path
            base_name = os.path.basename(source_path_or_url)
            identifier = os.path.splitext(base_name)[0]
            logging.debug(f"[get_identifier] Got filename as identifier: '{identifier}'")
            return identifier
    except Exception as e:
        logging.error(f"[get_identifier] Error creating identifier for '{source_path_or_url}': {e}")
        # Final fallback if error
        return create_safe_filename(os.path.basename(source_path_or_url), max_length=50)


def parse_ai_response(ai_response_text: str) -> dict:
    """
    Parse AI response text into structured title, content, and notes.
    
    (PHIÊN BẢN 4.1 - DELIMITERS EN + FALLBACK VIỆT + DỰ PHÒNG "Title:" + DÒNG ĐẦU)
    Phân tích văn bản từ AI:
    - Ưu tiên tách theo <<<TITLE>>>, <<<CONTENT>>>, <<<NOTES>>> (chế độ EN TTS)
    - Nếu không có, fallback sang định dạng tiếng Việt cũ (1/2/3 hoặc nhãn)
    - Nếu vẫn chưa có title, bắt "Title: ..." (EN) hoặc lấy dòng đầu hợp lệ
    - Làm sạch markdown phổ biến và số chú thích [1], [2], ...
    
    Args:
        ai_response_text: Raw text response from AI
        
    Returns:
        Dictionary with keys: 'title', 'content', 'notes'
    """
    parsed = {"title": "", "content": "", "notes": ""}
    if not ai_response_text or not ai_response_text.strip():
        return parsed

    # -------------------- HELPERS --------------------
    def clean_text(text: str) -> str:
        if not text:
            return ""
        # 0) Bỏ code fences ```...``` nếu có
        text = re.sub(r"^```(?:\w+)?\s*|\s*```$", "", text.strip(), flags=re.DOTALL)
        # 1) Xóa các ký tự markdown phổ biến
        text = re.sub(r'[\*#_`]+', '', text)
        # 2) Xóa các số chú thích dạng [1], [2], [123]...
        text = re.sub(r'\[\d+\]', '', text)
        # 3) Rút gọn nhiều dòng trống
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 4) Làm gọn khoảng trắng đầu/cuối dòng
        return text.strip()

    # XÓA header rơi vãi kiểu "Title:" / "Edited Content:" / "Nội dung biên tập:" trong CONTENT
    def strip_header_lines(s: str) -> str:
        if not s:
            return s
        lines = s.splitlines()
        removed = 0
        while lines and removed < 3 and re.match(
            r'(?i)^\s*(?:title|edited\s*content|content\s*edit|nội dung biên tập|tiêu đề|notes?|ghi chú)\s*[:\-]\s*',
            lines[0]
        ):
            lines.pop(0)
            removed += 1
        return "\n".join(lines).strip()

    text = ai_response_text

    # =========================================================
    # 1) ƯU TIÊN: ĐỊNH DẠNG EN VỚI DELIMITERS <<<...>>>
    #    Cho phép khoảng trắng trước delimiter; multi-line; DOTALL.
    # =========================================================
    m_title = re.search(
        r'(?mi)^\s*<<<TITLE>>>\s*\r?\n(.*?)\r?\n(?=<<<CONTENT>>>|\Z)',
        text,
        re.DOTALL,
    )
    m_content = re.search(
        r'(?mi)^\s*<<<CONTENT>>>\s*\r?\n(.*?)(?=\r?\n<<<NOTES>>>|\Z)',
        text,
        re.DOTALL,
    )
    m_notes = re.search(
        r'(?mi)^\s*<<<NOTES>>>\s*\r?\n(.*)\Z',
        text,
        re.DOTALL,
    )

    if m_title or m_content or m_notes:
        parsed["title"] = clean_text(m_title.group(1)) if m_title else ""
        parsed["content"] = clean_text(m_content.group(1)) if m_content else ""
        notes_raw = m_notes.group(1).strip() if m_notes else ""
        parsed["notes"] = clean_text(notes_raw)

        # Làm sạch CONTENT nếu model lỡ in nhãn
        parsed["content"] = strip_header_lines(parsed["content"])
        # Giới hạn độ dài title phòng trường hợp model xổ quá dài
        if parsed["title"]:
            parsed["title"] = parsed["title"][:180].strip()
        return parsed

    # =========================================================
    # 2) FALLBACK: ĐỊNH DẠNG TIẾNG VIỆT CŨ (nhãn + 1/2/3)
    # =========================================================
    # Tìm điểm bắt đầu thực sự của nội dung (giữ logic gốc)
    start_pos = -1
    match_title_label = re.search(r"Tiêu đề chương:", text, re.IGNORECASE)
    match_number_one = re.search(r"^\s*1\.", text, re.MULTILINE)

    if match_title_label:
        start_pos = match_title_label.start()
    elif match_number_one:
        start_pos = match_number_one.start()

    content_to_parse = text[start_pos:] if start_pos != -1 else text

    # Nhãn tiếng Việt trực tiếp
    title_match = re.search(
        r"Tiêu đề chương:\s*(.*?)\s*(?=2\.|Nội dung biên tập:|$)",
        content_to_parse,
        re.DOTALL | re.IGNORECASE,
    )
    if title_match:
        parsed["title"] = clean_text(title_match.group(1))

    content_match = re.search(
        r"Nội dung biên tập:\s*(.*?)\s*(?=3\.|Ghi chú ngắn gọn lỗi đã sửa:|$)",
        content_to_parse,
        re.DOTALL | re.IGNORECASE,
    )
    if content_match:
        parsed["content"] = clean_text(content_match.group(1))

    notes_match = re.search(
        r"Ghi chú ngắn gọn lỗi đã sửa:\s*(.*)",
        content_to_parse,
        re.DOTALL | re.IGNORECASE,
    )
    if notes_match:
        parsed["notes"] = clean_text(notes_match.group(1))

    # Dự phòng dạng 1./2./3. (giữ logic gốc)
    if not parsed["title"] and not parsed["content"] and not parsed["notes"]:
        part1_match = re.search(r"1\.\s*(.*?)\s*(?=2\.)", content_to_parse, re.DOTALL)
        part2_match = re.search(r"2\.\s*(.*?)\s*(?=3\.)", content_to_parse, re.DOTALL)
        part3_match = re.search(r"3\.\s*(.*)", content_to_parse, re.DOTALL)

        if part1_match:
            raw_title = re.sub(
                r"^Tiêu đề chương:\s*", "", part1_match.group(1).strip(), flags=re.IGNORECASE
            )
            parsed["title"] = clean_text(raw_title)
        if part2_match:
            raw_content = re.sub(
                r"^Nội dung biên tập:\s*", "", part2_match.group(1).strip(), flags=re.IGNORECASE
            )
            parsed["content"] = clean_text(raw_content)
        if part3_match:
            raw_notes = re.sub(
                r"^Ghi chú ngắn gọn lỗi đã sửa:\s*", "", part3_match.group(1).strip(), flags=re.IGNORECASE
            )
            parsed["notes"] = clean_text(raw_notes)

    # =========================================================
    # 3) FALLBACK BỔ SUNG: "Title: ..." (EN) + LẤY DÒNG ĐẦU
    #    (đặt sau các bước trên để không phá pattern chính)
    # =========================================================
    if not parsed["title"]:
        # a) "Title: ..."
        m_title_en = re.search(r'(?mi)^\s*Title\s*[:\-]\s*(.+)$', text)
        if m_title_en:
            parsed["title"] = clean_text(m_title_en.group(1))

    if not parsed["title"]:
        # b) Lấy dòng đầu tiên nếu đủ "chất lượng" (không phải nhãn)
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        first_line = lines[0] if lines else ""
        if first_line and not re.match(
            r'(?i)^(tiêu đề|title|nội dung|edited\s*content|content\s*edit|ghi chú|notes?)\s*[:\-]',
            first_line
        ):
            parsed["title"] = clean_text(first_line)[:120]

    # Nếu đã tách được title/notes mà content rỗng, lấy phần còn lại làm content (giữ logic cũ)
    if not parsed["content"] and (parsed["title"] or parsed["notes"]):
        temp_content = content_to_parse
        if title_match:
            temp_content = temp_content.replace(title_match.group(0), "")
        if notes_match:
            temp_content = temp_content.replace(notes_match.group(0), "")
        parsed["content"] = clean_text(temp_content)

    # Nếu vẫn rỗng tất cả, trả thẳng toàn bộ (đã clean) vào content (giữ nguyên)
    elif not parsed["title"] and not parsed["content"] and not parsed["notes"]:
        parsed["content"] = clean_text(content_to_parse)

    # Làm sạch dòng nhãn lạc trong content (phòng xa)
    parsed["content"] = strip_header_lines(parsed["content"])

    # Giới hạn độ dài title phòng trường hợp model xổ quá dài
    if parsed["title"]:
        parsed["title"] = parsed["title"][:180].strip()

    return parsed


def validate_volume_input(P: str) -> bool:
    """
    Validate that input contains only integer from 0-100.
    P: Potential value of the entry if the change is accepted.
    
    Args:
        P: String value to validate
        
    Returns:
        True if valid (empty or 0-100), False otherwise
    """
    if P == "":
        return True  # Allow deletion to empty
    try:
        # Only allow input if length is not more than 3 characters
        if len(P) > 3:
            return False
        # Convert to number and check
        value = int(P)
        if 0 <= value <= 100:
            return True  # Valid
        else:
            return False  # Outside range 0-100
    except ValueError:
        # If cannot convert to number (e.g., user enters text)
        return False


def sanitize_script_for_ai(original_script: str, cfg=None) -> str:
    """
    Tạo một bản sao của kịch bản và thay thế trực tiếp các từ nhạy cảm
    bằng các diễn giải an toàn từ SENSITIVE_WORD_MAPPING.
    Hàm này chỉ dùng để tạo input "sạch" cho AI, không làm thay đổi kịch bản gốc.
    
    Args:
        original_script: Original script text
        cfg: Optional config object (for compatibility check)
        
    Returns:
        Sanitized script with sensitive words replaced
    """
    from config.constants import SENSITIVE_WORD_MAPPING
    
    if not original_script:
        return original_script

    sanitized_script = original_script
    found_words = []

    # Sắp xếp các từ khóa theo độ dài giảm dần để tránh thay thế chồng chéo
    # Ví dụ: "chém giết" sẽ được thay thế trước "chém" hoặc "giết"
    sorted_keywords = sorted(SENSITIVE_WORD_MAPPING.keys(), key=len, reverse=True)

    for sensitive_word in sorted_keywords:
        # Dùng re.sub để thay thế không phân biệt chữ hoa chữ thường
        # \b đảm bảo chúng ta chỉ thay thế toàn bộ từ
        pattern = re.compile(r'\b' + re.escape(sensitive_word) + r'\b', re.IGNORECASE)
        
        # Chỉ thay thế nếu từ đó thực sự có trong chuỗi
        if pattern.search(sanitized_script):
            found_words.append(sensitive_word)
            safe_interpretation = SENSITIVE_WORD_MAPPING[sensitive_word]
            sanitized_script = pattern.sub(safe_interpretation, sanitized_script)
    
    if found_words:
        logging.info(f"[SanitizeScript] Đã thay thế {len(found_words)} từ khóa trong kịch bản cho AI: {found_words}")
    
    return sanitized_script