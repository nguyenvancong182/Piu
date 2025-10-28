"""
UI Helper Functions for Piu Application

These are utility functions for checking UI state and safely calling UI methods.
"""

import logging
import threading
import os


def is_ui_alive(app_instance) -> bool:
    """
    Check if UI is alive and not shutting down.
    
    Args:
        app_instance: The application instance (SubtitleApp)
        
    Returns:
        True if UI is alive and not shutting down
    """
    try:
        if getattr(app_instance, "_is_shutting_down", False):
            return False
        return bool(app_instance.winfo_exists())
    except Exception:
        return False


def safe_after(app_instance, delay_ms, fn):
    """
    Safely call a function on the main thread if UI is alive.
    If UI is closed, run the function in a background thread to avoid blocking.
    
    Args:
        app_instance: The application instance (SubtitleApp)
        delay_ms: Delay in milliseconds
        fn: Function to call
        
    Returns:
        True if scheduled on main thread, False if run in background
    """
    try:
        if is_ui_alive(app_instance):
            app_instance.after(delay_ms, fn)
            return True
    except Exception as e:
        logging.debug(f"[UI] after() failed: {e}")
    # Fallback: run in background
    threading.Thread(target=fn, daemon=True).start()
    return False


def update_path_label(label_widget, path_value):
    """
    Helper function to update text and color for path display labels.
    
    Args:
        label_widget: The label widget to update
        path_value: The file path to display
    """
    if not label_widget or not label_widget.winfo_exists():
        return
    
    display_text = os.path.basename(path_value) if path_value else "(Chưa chọn)"
    text_color = ("gray30", "gray70")  # Default color
    
    if path_value:
        if os.path.exists(path_value):
            text_color = ("#0B8457", "lightgreen")  # Green if exists
        else:
            text_color = ("#B71C1C", "#FF8A80")  # Red if not exists
            display_text += " (Không tìm thấy!)"
    
    label_widget.configure(text=display_text, text_color=text_color)


def norm_no_diacritics(s: str) -> str:
    """
    Normalize string by removing Vietnamese diacritics.
    
    Args:
        s: Input string
        
    Returns:
        Normalized lowercase string without diacritics
    """
    import unicodedata
    try:
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()
    except Exception:
        return (s or "").lower()


def is_readyish(msg: str) -> bool:
    """
    Check if a status message is a "ready" message.
    
    Args:
        msg: Status message to check
        
    Returns:
        True if message indicates "ready" state
    """
    raw = str(msg or "")
    norm = norm_no_diacritics(raw)
    return (
        raw.strip().startswith("✅") or
        "san sang" in norm or          # "Sẵn sàng" (không dấu)
        "sẵn sàng" in raw.lower() or   # có dấu
        "ready" in norm
    )


def locked_msg_for_view(view: str) -> str:
    """
    Get locked status message for a specific view.
    
    Args:
        view: Current view name
        
    Returns:
        Locked status message for the view
    """
    locked_map = {
        "↓ Tải Xuống": "🔒 Download: Cần kích hoạt.",
        "≡ Tạo Phụ Đề": "🔒 Subtitle: Cần kích hoạt.",
        "♪ Thuyết Minh": "🔒 Dubbing: Cần kích hoạt.",
        "📤 Upload YT": "🔒 Upload YT: Cần kích hoạt.",
        "✍ AI Biên Tập": "🔒 AI Biên Tập: Cần kích hoạt.",
    }
    return locked_map.get(view, "🔒 Cần kích hoạt.")


def ready_msg_for_view(view: str) -> str:
    """
    Get ready status message for a specific view.
    
    Args:
        view: Current view name
        
    Returns:
        Ready status message for the view
    """
    ready_map = {
        "↓ Tải Xuống": "✅ Download: Sẵn sàng nhận link.",
        "≡ Tạo Phụ Đề": "✅ Subtitle: Sẵn sàng xử lý file.",
        "♪ Thuyết Minh": "✅ Dubbing: Sẵn sàng lồng tiếng.",
        "📤 Upload YT": "✅ Upload YT: Sẵn sàng upload Video.",
        "✍ AI Biên Tập": "✅ AI Biên Tập: Sẵn sàng biên tập Kịch Bản.",
    }
    return ready_map.get(view, "✅ Sẵn sàng!")
