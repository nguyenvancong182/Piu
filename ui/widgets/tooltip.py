"""
Tooltip widget for Piu application.
"""

import customtkinter as ctk


class Tooltip:
    """
    Tạo một tooltip có độ trễ, được căn giữa bên dưới widget và tương thích theme Sáng/Tối.
    """
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.after_id = None
        
        self.widget.bind("<Enter>", self.schedule_show_tooltip)
        self.widget.bind("<Leave>", self.schedule_hide_tooltip)
        self.widget.bind("<Button-1>", self.schedule_hide_tooltip)

    def schedule_show_tooltip(self, event=None):
        self.unschedule_show() # Hủy lịch hiện cũ nếu có
        self.after_id = self.widget.after(self.delay, self.show_tooltip)

    def schedule_hide_tooltip(self, event=None):
        self.unschedule_show()
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def unschedule_show(self):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def show_tooltip(self):
        if self.tooltip_window or not self.text:
            return

        # 1. Tạo cửa sổ Toplevel và Label
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.attributes("-topmost", True)
        
        # ### THAY ĐỔI CHÍNH VỀ MÀU SẮC ###
        # Thêm text_color để tương phản với fg_color ở cả 2 chế độ
        label = ctk.CTkLabel(
            self.tooltip_window, 
            text=self.text, 
            font=("Segoe UI", 11, "normal"),
            fg_color=("#E5E5E5", "#2D2D2D"),  # (Màu nền cho chế độ Sáng, Tối)
            text_color=("#1C1C1C", "#DCE4EE"), # (Màu chữ cho chế độ Sáng, Tối)
            corner_radius=4
        )
        label.pack(ipadx=5, ipady=3)
        
        # ### THAY ĐỔI CHÍNH VỀ VỊ TRÍ ###
        
        # 2. Bắt Toplevel phải tính toán kích thước của nó
        self.tooltip_window.update_idletasks()
        
        # 3. Lấy tất cả thông số cần thiết
        widget_x = self.widget.winfo_rootx()
        widget_y = self.widget.winfo_rooty()
        widget_height = self.widget.winfo_height()
        widget_width = self.widget.winfo_width()
        
        # Lấy chiều rộng của label bên trong, đây là cách chính xác nhất
        tooltip_width = label.winfo_reqwidth()
        
        # 4. Tính toán vị trí mới
        new_x = widget_x + (widget_width // 2) - (tooltip_width // 2)
        new_y = widget_y + widget_height + 5 # 5 pixel khoảng cách

        # 5. Áp dụng vị trí đã tính toán
        self.tooltip_window.wm_geometry(f"+{new_x}+{new_y}")

    def hide_tooltip(self, event=None): # Giữ lại hàm này cho tương thích
        self.schedule_hide_tooltip(event)

