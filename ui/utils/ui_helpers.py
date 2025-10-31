"""
UI Helper Functions for Piu Application

These are utility functions for checking UI state and safely calling UI methods.
"""

import logging
import threading
import os
import customtkinter as ctk


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


def setup_popup_window(
    popup,
    master,
    width: int,
    height: int,
    title: str = "",
    resizable: bool = False,
    topmost: bool = True,
    grab_set: bool = True,
    transient: bool = False
):
    """
    Setup common popup window properties.
    
    Args:
        popup: The popup window (ctk.CTkToplevel or tk.Toplevel)
        master: Master window instance
        width: Popup width
        height: Popup height
        title: Window title (optional)
        resizable: Whether window is resizable (default: False)
        topmost: Whether window stays on top (default: True)
        grab_set: Whether to grab focus (default: True)
        transient: Whether window is transient to master (default: False)
    """
    if title:
        popup.title(title)
    
    popup.geometry(f"{width}x{height}")
    popup.resizable(resizable, resizable)
    
    if topmost:
        popup.attributes("-topmost", True)
    
    if grab_set:
        popup.grab_set()
    
    if transient:
        popup.transient(master)


def center_popup_on_master(popup, master, width: int, height: int, delay_ms: int = 50):
    """
    Center popup window on master window with screen bounds checking.
    
    Args:
        popup: The popup window
        master: Master window instance
        width: Popup width
        height: Popup height
        delay_ms: Delay before centering (to allow geometry to be set, default: 50ms)
        
    Returns:
        True if centering was scheduled, False otherwise
    """
    def _center():
        try:
            master.update_idletasks()
            popup.update_idletasks()
            
            master_x = master.winfo_x()
            master_y = master.winfo_y()
            master_width = master.winfo_width()
            master_height = master.winfo_height()
            
            # Use actual popup size if available, otherwise use desired size
            popup_width_actual = popup.winfo_width()
            popup_height_actual = popup.winfo_height()
            
            final_width = width if popup_width_actual <= 1 else popup_width_actual
            final_height = height if popup_height_actual <= 1 else popup_height_actual
            
            # Calculate center position
            center_x = master_x + (master_width // 2) - (final_width // 2)
            center_y = master_y + (master_height // 2) - (final_height // 2)
            
            # Check screen bounds
            screen_width = popup.winfo_screenwidth()
            screen_height = popup.winfo_screenheight()
            
            if center_x + final_width > screen_width:
                center_x = screen_width - final_width
            if center_y + final_height > screen_height:
                center_y = screen_height - final_height
            if center_x < 0:
                center_x = 0
            if center_y < 0:
                center_y = 0
            
            popup.geometry(f"{final_width}x{final_height}+{int(center_x)}+{int(center_y)}")
            
        except Exception as e:
            logging.warning(f"Không thể căn giữa popup: {e}")
            # Fallback: use desired geometry
            try:
                popup.geometry(f"{width}x{height}")
            except Exception:
                pass
    
    try:
        if hasattr(popup, 'after'):
            popup.after(delay_ms, _center)
        else:
            # If no after method, call immediately
            _center()
        return True
    except Exception as e:
        logging.warning(f"Không thể schedule centering: {e}")
        _center()
        return False
