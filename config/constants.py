"""
Constants and configuration values for Piu application.
This module contains all static configuration values.
"""

import os
import sys
import shutil
from pathlib import Path

# ==========================
# Basic App Information
# ==========================
APP_NAME = "Piu"
APP_AUTHOR = "CongBac&Piu"
CURRENT_VERSION = "1.1"

# ==========================
# File Names & Paths
# ==========================
CONFIG_FILENAME = "config.json"
FONT_CACHE_FILENAME = "font_cache.json"
LOG_FILENAME = "Piu_app.log"
CREDENTIALS_FILENAME = 'credentials.json'
TOKEN_FILENAME = 'token.json'

# ==========================
# API & Service URLs
# ==========================
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz5S6rEg8cwUGJtlQ5Qhg4QX2UBXB_U4TvoFgyhM_oOJcfIdG5JoEXxyDtTRdSpjdMeiA/exec"  # License check URL

# ==========================
# Intervals & Timing
# ==========================
UPDATE_CHECK_INTERVAL_SECONDS = 72 * 60 * 60  # Check every 72 hours
LICENSE_REVALIDATION_INTERVAL_SECONDS = 3 * 24 * 60 * 60  # Recheck every 3 days

# ==========================
# YouTube Settings
# ==========================
DEFAULT_REFERENCE_VIDEO_HEIGHT_FOR_FONT_SCALING = 1080
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# ==========================
# System Mutex
# ==========================
APP_MUTEX_NAME = f"Global\\PiuApp_{APP_NAME}_{APP_AUTHOR}_Mutex_v1"

# ==========================
# yt-dlp Path Resolution
# ==========================
def get_ytdlp_path():
    """Determine yt-dlp executable path"""
    _YTDLP_DEFAULT_COMMAND = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
    YTDLP_PATH = _YTDLP_DEFAULT_COMMAND
    
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS') is False:
        try:
            application_path = os.path.dirname(sys.executable)
            bundled_ytdlp_path = os.path.join(application_path, _YTDLP_DEFAULT_COMMAND)
            
            if os.path.exists(bundled_ytdlp_path):
                YTDLP_PATH = bundled_ytdlp_path
                import logging
                logging.info(f"Found bundled yt-dlp: {YTDLP_PATH}")
            else:
                system_ytdlp = shutil.which(_YTDLP_DEFAULT_COMMAND)
                if system_ytdlp:
                    YTDLP_PATH = system_ytdlp
                    logging.info(f"Found yt-dlp in PATH: {YTDLP_PATH}")
        except Exception:
            pass
    else:
        system_ytdlp = shutil.which(_YTDLP_DEFAULT_COMMAND)
        if system_ytdlp:
            YTDLP_PATH = system_ytdlp
    
    return YTDLP_PATH

# ==========================
# Google API Scopes
# ==========================
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/youtube'
]

# ==========================
# YouTube Data API
# ==========================
YOUTUBE_API_SERVICE_NAME = 'youtube' 
YOUTUBE_API_VERSION = 'v3'

# ==========================
# Sensitive Word Mapping (for AI safety)
# ==========================
# --- TỪ ĐIỂN ÁNH XẠ AN TOÀN CHO PROMPT AI ---
# Dùng để diễn giải các từ nhạy cảm cho Gemini hiểu theo hướng an toàn hơn
# mà không làm thay đổi kịch bản gốc cho người xem.
SENSITIVE_WORD_MAPPING = {
    # Từ khóa : "Cách diễn giải an toàn hơn cho AI"
    "giết": "kết liễu, hạ gục, chấm dứt trận đấu",
    "chém": "vung kiếm tạo vệt sáng, thực hiện đòn tấn công sắc bén",
    "đâm": "thực hiện một đòn tấn công xuyên thủng, đâm mạnh",
    "máu": "chất lỏng đỏ, biểu tượng của thương tổn trong trận chiến",
    "chết": "ngã gục, mất đi sinh lực, kết thúc hành trình",
    "tử vong": "hết sinh lực, không còn chuyển động",
    "thi thể": "thân xác bất động, dấu vết của trận chiến",
    "vũ khí": "pháp bảo, công cụ chiến đấu, vật phẩm đặc biệt",
    "kiếm": "thanh trường kiếm lấp lánh, pháp khí sắc bén",
    "đao": "vật phẩm lưỡi cong, tỏa ánh kim loại",
    "súng": "pháp khí hình ống, công cụ phóng năng lượng",
    "giận dữ": "biểu cảm nghiêm nghị, ánh mắt bừng cháy chiến ý",
    "quát mắng": "lên tiếng mạnh mẽ, thể hiện uy quyền",
    "bạo lực": "hành động mạnh mẽ, giao tranh kịch liệt",
    "đánh": "thực hiện đòn công kích, va chạm trong trận đấu",
    "xúc phạm": "lời nói sắc bén, ngôn từ khiêu khích",
    "kỳ thị": "thái độ phân biệt, thiên vị trong môn phái",
    "lạm dụng": "hành vi vượt giới hạn, sử dụng sức mạnh sai mục đích",
    "nhạy cảm": "chủ đề cần thận trọng, dễ gây hiểu lầm trong truyện",
    "gây tổn thương": "tác động mạnh đến thể chất hoặc tinh thần nhân vật",
    # Từ mới liên quan đến tình dục (trong ngữ cảnh văn học, tình cảm lãng mạn)
    "tình dục": "tình cảm sâu sắc, sự gắn kết lãng mạn giữa nhân vật",
    "yêu đương": "mối quan hệ tình cảm, sự rung động trái tim",
    "thân mật": "hành động gần gũi, biểu hiện tình cảm tinh tế",
    "cám dỗ": "sự lôi cuốn mạnh mẽ, sức hấp dẫn từ nhân vật",
    "hôn": "hành động biểu lộ tình cảm, nụ hôn nhẹ nhàng",
    "ân ái": "khoảnh khắc gần gũi, sự hòa hợp về tâm hồn và thể xác",
    "cởi đồ": "thay trang phục, để lộ bờ vai một cách tinh tế",
    "trên giường": "trong không gian riêng tư của phòng ngủ",
    "khỏa thân": "thân thể không trang phục, một hình ảnh nghệ thuật tinh tế",
    "quyến rũ": "tạo ra sức hút, vẻ đẹp đầy mê hoặc",
    "làm tình": "sự hòa hợp thể xác và tâm hồn, khoảnh khắc thân mật sâu sắc nhất",    
    # Từ mới liên quan đến trẻ em (trong ngữ cảnh bảo vệ, gia đình)
    "trẻ em": "những nhân vật nhỏ tuổi, thế hệ tương lai của môn phái",
    "trẻ con": "nhân vật hồn nhiên, mang năng lượng tươi mới",
    "trẻ thơ": "nhân vật non nớt, cần được bảo vệ trong cốt truyện",
    # Từ mới liên quan đến phân biệt chủng tộc (trong ngữ cảnh giả tưởng)
    "phân biệt": "thái độ bất công giữa các tộc, môn phái hoặc thế lực",
    "chủng tộc": "các dòng dõi, tộc người hoặc thế lực trong thế giới giả tưởng",
    "kỳ thị chủng tộc": "sự bất hòa giữa các tộc, môn phái trong truyện",
}

# ==========================
# Language Mapping
# ==========================
LANGUAGE_MAP_VI = {
    "vi": "Tiếng Việt",
    "en": "Tiếng Anh",
    "ja": "Tiếng Nhật",
    "zh-cn": "Tiếng Trung (Giản thể)",
    "fr": "Tiếng Pháp",
    "ko": "Tiếng Hàn",
    "de": "Tiếng Đức",
    "es": "Tiếng Tây Ban Nha",
    "it": "Tiếng Ý",
    "th": "Tiếng Thái",
    "ru": "Tiếng Nga",
    "pt": "Tiếng Bồ Đào Nha",
    "hi": "Tiếng Hindi",
    "auto": "Tự động dò"
}

# ==========================
# YouTube Categories
# ==========================
YOUTUBE_CATEGORIES = {
    '1': 'Phim và hoạt hình',
    '2': 'Ô tô và xe cộ',
    '10': 'Nhạc',
    '15': 'Thú cưng và động vật',
    '17': 'Thể thao',
    '19': 'Du lịch và sự kiện',
    '20': 'Trò chơi',
    '22': 'Mọi người và blog',
    '23': 'Hài kịch',
    '24': 'Giải trí',
    '25': 'Tin tức và chính trị',
    '26': 'Hướng dẫn và phong cách',
    '27': 'Giáo dục',
    '28': 'Khoa học và công nghệ',
    '29': 'Tổ chức phi lợi nhuận và hoạt động xã hội'
}

YOUTUBE_CATEGORY_NAVIGATION_ORDER = {
    '1':  0,  '2':  1,  '10': 2,  '15': 3,  '17': 4,
    '19': 5,  '20': 6, '22': 7,  '23': 8,  '24': 9,
    '25': 10, '26': 11, '27': 12, '28': 13, '29': 14,
}

# ==========================
# Whisper VRAM Requirements (MB)
# ==========================
WHISPER_VRAM_REQ_MB = {
    "tiny": 1024, "base": 1024, "small": 2048, "medium": 5120,
    "large-v1": 10240, "large-v2": 10240, "large-v3": 10240, "large": 10240,
}

# ==========================
# API Pricing (USD) - Updated Aug 2025
# ==========================
API_PRICING_USD = {
    "USD_TO_VND_RATE": 25500,
    "google_tts_chars_per_million": 4.00,
    "google_translate_chars_per_million": 20.00,
    "openai_tts_chars_per_million": 15.00,
    "imagen_images_per_image": 0.020,
    "dalle_images_per_image": 0.040,
    "gemini_calls_per_call_estimate": 0.0025,
    "openai_calls_per_call_estimate": 0.06,
}

# ==========================
# UI Layout Constants
# ==========================
DESIGN_WINDOW_WIDTH = 1425
DESIGN_WINDOW_HEIGHT = 920
DEFAULT_WINDOW_MARGIN = (12, 12, 28, 88)  # (left, top, right, bottom)

# DPI Scaling Constants
DPI_FONT_SCALING_RATIO = 96/72.0  # Standard font scaling for ~96dpi
DPI_WATCHER_INTERVAL_MS = 1000

# Subtitle Style Defaults
DEFAULT_SUBTITLE_FONT_SIZE = 60
DEFAULT_SUBTITLE_FONT_BOLD = True
DEFAULT_SUBTITLE_TEXT_COLOR = "255,255,255"
DEFAULT_SUBTITLE_TEXT_OPACITY = 100
DEFAULT_SUBTITLE_BG_MODE = "Đổ Bóng"
DEFAULT_SUBTITLE_BG_COLOR = "0,0,0"
DEFAULT_SUBTITLE_BG_OPACITY = 75
DEFAULT_SUBTITLE_OUTLINE_SIZE = 2.0
DEFAULT_SUBTITLE_OUTLINE_COLOR = "0,0,0"
DEFAULT_SUBTITLE_OUTLINE_OPACITY = 100
DEFAULT_SUBTITLE_MARGIN_V = 60

# ==========================
# CÁC HẰNG SỐ ĐƯỢC DI CHUYỂN TỪ PIU.PY
# ==========================

# Tên Mutex duy nhất cho ứng dụng
APP_MUTEX_NAME = f"Global\\{{PiuApp_{APP_NAME}_{APP_AUTHOR}_Mutex_v1}}"

# --- Từ điển ánh xạ mã ngôn ngữ sang tên tiếng Việt ---
LANGUAGE_MAP_VI = {
    "vi": "Tiếng Việt",
    "en": "Tiếng Anh",
    "ja": "Tiếng Nhật",
    "zh-cn": "Tiếng Trung (Giản thể)",
    "fr": "Tiếng Pháp",
    "ko": "Tiếng Hàn",
    "de": "Tiếng Đức",
    "es": "Tiếng Tây Ban Nha",
    "it": "Tiếng Ý",
    "th": "Tiếng Thái",
    "ru": "Tiếng Nga",
    "pt": "Tiếng Bồ Đào Nha",
    "hi": "Tiếng Hindi",
    "auto": "Tự động dò"
}

# --- Hằng số Google Sheets API ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly', # Quyền Sheets
    'https://www.googleapis.com/auth/youtube'                # Quyền quản lý toàn diện YouTube
]

# Ước tính VRAM yêu cầu (MB) cho các model Whisper khi chạy trên GPU
WHISPER_VRAM_REQ_MB = {
    "tiny": 1024,     # Khoảng 1 GB
    "base": 1024,     # Khoảng 1 GB
    "small": 2048,    # Khoảng 2 GB
    "medium": 5120,   # Khoảng 5 GB
    "large-v1": 10240, # Khoảng 10 GB (large cũ)
    "large-v2": 10240, # Khoảng 10 GB
    "large-v3": 10240, # Khoảng 10 GB
    "large": 10240,    # Thêm "large" chung cho tiện
}

# --- Từ điển ánh xạ ID Danh mục YouTube sang Tiếng Việt ---
YOUTUBE_CATEGORIES = {
    '1': 'Phim và hoạt hình',
    '2': 'Ô tô và xe cộ',
    '10': 'Nhạc',
    '15': 'Thú cưng và động vật',
    '17': 'Thể thao',
    '19': 'Du lịch và sự kiện',
    '20': 'Trò chơi',
    '22': 'Mọi người và blog',
    '23': 'Hài kịch',
    '24': 'Giải trí',
    '25': 'Tin tức và chính trị',
    '26': 'Hướng dẫn và phong cách',
    '27': 'Giáo dục',
    '28': 'Khoa học và công nghệ',
    '29': 'Tổ chức phi lợi nhuận và hoạt động xã hội'
}

# Ánh xạ Category ID sang số lần nhấn phím Mũi tên xuống
YOUTUBE_CATEGORY_NAVIGATION_ORDER = {
    '1':  0,  # Phim và hoạt hình
    '2':  1,  # Ô tô và xe cộ
    '10': 2,  # Nhạc
    '15': 3,  # Thú cưng và động vật
    '17': 4,  # Thể thao
    '19': 5,  # Du lịch và sự kiện
    '20': 6,  # Trò chơi
    '22': 7,  # Mọi người và blog
    '23': 8,  # Hài kịch
    '24': 9,  # Giải trí
    '25': 10, # Tin tức và chính trị
    '26': 11, # Hướng dẫn và phong cách
    '27': 12, # Giáo dục
    '28': 13, # Khoa học và công nghệ
    '29': 14, # Tổ chức phi lợi nhuận và hoạt động xã hội
}

# --- BẢNG GIÁ API ƯỚC TÍNH (USD) ---
API_PRICING_USD = {
    "USD_TO_VND_RATE": 25500,
    "google_tts_chars_per_million": 4.00,
    "google_translate_chars_per_million": 20.00,
    "openai_tts_chars_per_million": 15.00,
    "imagen_images_per_image": 0.020,
    "dalle_images_per_image": 0.040,
    "gemini_calls_per_call_estimate": 0.0025,
    "openai_calls_per_call_estimate": 0.06,
}

