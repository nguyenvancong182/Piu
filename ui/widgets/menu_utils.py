"""
Menu utility functions for Piu application.
"""

from tkinter import Menu

def textbox_right_click_menu(event):
    """Create a right-click context menu for textbox widgets."""
    menu = Menu(event.widget, tearoff=0)
    # Thêm icon vào từng lệnh cho bắt mắt
    menu.add_command(label="📋 Paste", command=lambda: event.widget.event_generate('<<Paste>>'))
    menu.add_command(label="📑 Copy", command=lambda: event.widget.event_generate('<<Copy>>'))
    menu.add_command(label="✂ Cut", command=lambda: event.widget.event_generate('<<Cut>>'))
    menu.add_separator()
    menu.add_command(
        label="🗑 Xóa hết",
        foreground="red",  # Nếu tkinter hỗ trợ (nhiều bản không nhận màu, nhưng thử vẫn ok)
        command=lambda: clear_all_links(event.widget)
    )
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()


def clear_all_links(widget):
    """Clear all text from a widget."""
    #from tkinter import messagebox
    #answer = messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa hết nội dung này không?")
    #if answer:
    try:
        widget.delete("1.0", "end")
    except Exception:
        widget.delete(0, "end")

