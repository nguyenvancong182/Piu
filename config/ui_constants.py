"""
UI Constants for Piu Application
Theme colors and UI-related constants
"""


def get_theme_colors():
    """
    Get theme colors used across all tabs.
    
    Returns:
        dict: Dictionary containing all theme colors
    """
    return {
        "panel_bg": ("gray92", "gray14"),
        "card_bg": ("gray86", "gray17"),
        "textbox_bg": ("#F9F9F9", "#212121"),
        "log_textbox_bg": ("#F9F9F9", "#212121"),
        "danger_button": ("#D32F2F", "#C62828"),
        "danger_button_hover": ("#C62828", "#B71C1C"),
        "special_action_button": ("#336666", "#336666"),
        "special_action_hover": ("darkred", "darkred"),
        "secondary_button": ("gray70", "gray25")
    }

