"""
Custom Voice Dropdown Widget for Piu Application.

A standalone dropdown widget for selecting voices with search functionality.
"""

import logging
import customtkinter as ctk


class CustomVoiceDropdown(ctk.CTkFrame):
    """
    Tạo một dropdown tùy chỉnh cho việc chọn giọng đọc, có hỗ trợ tìm kiếm, cuộn chuột,
    và tự động cuộn đến mục đang được chọn khi mở ra.
    """
    def __init__(self, master, master_app, variable, values_dict, width=200, height=30, **kwargs):
        super().__init__(master, width=width, height=height, fg_color=("#F9F9FA", "#343638"), **kwargs)
        
        self.master_app = master_app
        self.variable = variable
        self.values_dict = values_dict
        self.filtered_list = list(values_dict.keys())
        self.width = width
        
        self.dropdown_toplevel = None
        self.search_entry = None
        self.scrollable_frame = None
        self.scroll_step = 15

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        initial_display_name = self.variable.get()
        if hasattr(self.master_app, 'dub_selected_voice_id_var'):
            current_voice_id = self.master_app.dub_selected_voice_id_var.get()
            for name, v_id in self.values_dict.items():
                if v_id == current_voice_id:
                    initial_display_name = name
                    break

        self.display_label = ctk.CTkLabel(self, text=initial_display_name, anchor="w", fg_color="transparent")
        self.display_label.grid(row=0, column=0, padx=(10, 5), sticky="ew")

        self.arrow_label = ctk.CTkLabel(self, text="▼", anchor="e", fg_color="transparent", width=20)
        self.arrow_label.grid(row=0, column=1, padx=(0, 5), sticky="e")
        
        self.bind("<Button-1>", self._open_dropdown)
        self.display_label.bind("<Button-1>", self._open_dropdown)
        self.arrow_label.bind("<Button-1>", self._open_dropdown)
        
        self.variable.trace_add("write", self._update_display_from_variable)
        
    def _update_display_from_variable(self, *args):
        if self.display_label.winfo_exists():
            self.display_label.configure(text=self.variable.get())
            
    def _open_dropdown(self, event):
        if self.dropdown_toplevel and self.dropdown_toplevel.winfo_exists():
            self._close_dropdown()
            return

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()

        self.dropdown_toplevel = ctk.CTkToplevel(self)
        popup_width = self.winfo_width()
        self.dropdown_toplevel.geometry(f"{popup_width}x350+{x}+{y}")
        self.dropdown_toplevel.overrideredirect(True)
        self.dropdown_toplevel.attributes("-topmost", True)
        
        popup_main_frame = ctk.CTkFrame(self.dropdown_toplevel, corner_radius=5, border_width=1, border_color="gray50", fg_color=("gray92", "#282828"))
        popup_main_frame.pack(expand=True, fill="both")
        
        self.search_entry = ctk.CTkEntry(popup_main_frame, placeholder_text="🔎 Tìm kiếm giọng...")
        self.search_entry.pack(fill="x", padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_keyup)
        
        self.scrollable_frame = ctk.CTkScrollableFrame(popup_main_frame, fg_color=("gray95", "#333333"))
        self.scrollable_frame.pack(expand=True, fill="both", padx=5, pady=(0, 5))
        
        self.dropdown_toplevel.bind("<MouseWheel>", self._on_mouse_wheel_scroll)
        self.dropdown_toplevel.bind("<Button-4>", self._on_mouse_wheel_scroll)
        self.dropdown_toplevel.bind("<Button-5>", self._on_mouse_wheel_scroll)
        self.dropdown_toplevel.bind("<Escape>", self._close_dropdown)
        self.dropdown_toplevel.focus_set()
        self.dropdown_toplevel.bind("<FocusOut>", self._on_focus_out)
        
        self._populate_list()
        self.after(100, self._scroll_to_selected)

    def _scroll_to_selected(self):
        """(ĐÃ SỬA LỖI VỊ TRÍ CUỘN) Tìm widget và cuộn đến đúng vị trí."""
        if not self.scrollable_frame or not self.scrollable_frame.winfo_exists():
            return
        
        selected_name = self.variable.get()
        all_widgets = self.scrollable_frame.winfo_children()
        
        # Chỉ lọc ra các nút bấm để tính toán chỉ số
        all_buttons_in_frame = [w for w in all_widgets if isinstance(w, ctk.CTkButton)]
        
        if not all_buttons_in_frame:
            return

        for i, widget in enumerate(all_buttons_in_frame):
            if widget.cget("text") == selected_name:
                try:
                    # ### BẮT ĐẦU SỬA LỖI TÍNH TOÁN ###
                    # Tính toán vị trí dựa trên chỉ số của nút trong danh sách nút
                    total_buttons = len(all_buttons_in_frame)
                    if total_buttons == 0: return

                    # Tính toán vị trí phần trăm (fraction) để cuộn đến
                    scroll_position = i / total_buttons
                    
                    # Điều chỉnh một chút để mục được chọn không bị nằm sát mép trên
                    offset = 2 / total_buttons # Lùi lại khoảng 2 mục
                    final_scroll_position = max(0.0, scroll_position - offset)

                    # Sử dụng after để đảm bảo canvas đã sẵn sàng để cuộn
                    self.scrollable_frame.after(50, lambda pos=final_scroll_position: self.scrollable_frame._parent_canvas.yview_moveto(pos))
                    logging.info(f"Đã cuộn đến mục '{selected_name}' ở vị trí tương đối: {final_scroll_position:.3f}")
                    # ### KẾT THÚC SỬA LỖI ###
                    break
                except Exception as e:
                    logging.error(f"Lỗi khi cuộn đến mục đã chọn: {e}")
                    break

    def _on_mouse_wheel_scroll(self, event):
        if hasattr(self.scrollable_frame, '_parent_canvas'):
            if event.delta > 0 or event.num == 4:
                self.scrollable_frame._parent_canvas.yview_scroll(-self.scroll_step, "units")
            elif event.delta < 0 or event.num == 5:
                self.scrollable_frame._parent_canvas.yview_scroll(self.scroll_step, "units")
        return "break"

    def _on_focus_out(self, event=None):
        self._close_dropdown()
        
    def _on_search_keyup(self, event=None):
        search_term = self.search_entry.get().lower()
        self.filtered_list = [name for name in self.values_dict.keys() if search_term in name.lower()]
        self._populate_list()
        
    def _populate_list(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        for display_name in self.filtered_list:
            if display_name.startswith("---"):
                ctk.CTkLabel(self.scrollable_frame, text=display_name, font=("Segoe UI", 11, "italic"), text_color="gray").pack(fill="x", padx=5, pady=(5,2))
            else:
                voice_button = ctk.CTkButton(
                    self.scrollable_frame, text=display_name, anchor="w",
                    fg_color="transparent", hover_color=("gray92", "#4A4A4A"),
                    text_color=("gray10", "gray98"),
                    command=lambda dn=display_name: self._on_voice_select(dn)
                )
                voice_button.pack(fill="x", padx=2, pady=1)

    def _on_voice_select(self, display_name):
        self.variable.set(display_name)
        if hasattr(self.master_app, 'dub_on_voice_selected'):
            self.master_app.dub_on_voice_selected(display_name)
        self._close_dropdown()

    def _close_dropdown(self, event=None):
        if self.dropdown_toplevel and self.dropdown_toplevel.winfo_exists():
            self.dropdown_toplevel.destroy()
            self.dropdown_toplevel = None

    def update_values(self, new_values_dict):
        self.values_dict = new_values_dict
        self.filtered_list = list(new_values_dict.keys())
        
        if self.dropdown_toplevel and self.dropdown_toplevel.winfo_exists():
            self._populate_list()

        current_display_name = self.variable.get()
        if current_display_name not in self.values_dict:
             if self.filtered_list:
                 first_valid_item = next((item for item in self.filtered_list if not item.startswith("---")), self.filtered_list[0])
                 self.variable.set(first_valid_item)
             else:
                 self.variable.set("Không có lựa chọn")
        self._update_display_from_variable()

