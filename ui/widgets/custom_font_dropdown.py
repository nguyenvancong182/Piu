"""
Custom Font Dropdown Widget for Piu Application.

A standalone dropdown widget for selecting fonts with lazy loading.
"""

import logging
import customtkinter as ctk


class CustomFontDropdown(ctk.CTkFrame):
    def __init__(self, master, font_variable, font_list_cache, parent_scrollable_frame, width=200, height=30, update_callback=None, **kwargs): # <--- THÊM update_callback
        super().__init__(master, width=width, height=height, fg_color=("#F9F9FA", "#343638"), **kwargs)
        self.update_callback = update_callback
        
        self.font_variable = font_variable
        self.font_list_cache = font_list_cache
        self.filtered_font_list = font_list_cache[:]
        self.width = width
        
        self.dropdown_toplevel = None
        self.search_entry = None
        self.scrollable_frame = None

        self.lazy_load_batch_size = 50
        self.last_rendered_index = 0
        self.is_loading_more = False
        self.scroll_step = 15
        
        self.original_scrollbar_command = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.display_label = ctk.CTkLabel(self, text=self.font_variable.get(), anchor="w", fg_color="transparent")
        self.display_label.grid(row=0, column=0, padx=(10, 5), sticky="ew")
        self._update_display_font()

        self.arrow_label = ctk.CTkLabel(self, text="▼", anchor="e", fg_color="transparent", width=20)
        self.arrow_label.grid(row=0, column=1, padx=(0, 5), sticky="e")
        
        self.bind("<Button-1>", self._open_dropdown)
        self.display_label.bind("<Button-1>", self._open_dropdown)
        self.arrow_label.bind("<Button-1>", self._open_dropdown)
        
        self.font_variable.trace_add("write", self._update_display_from_variable)
        
    def _update_display_font(self):
        try:
            selected_font_name = self.font_variable.get()
            display_font = ctk.CTkFont(family=selected_font_name, size=13)
            self.display_label.configure(font=display_font)
        except Exception:
            self.display_label.configure(font=("Segoe UI", 12))

    def _update_display_from_variable(self, *args):
        if self.display_label.winfo_exists():
            self.display_label.configure(text=self.font_variable.get())
            self._update_display_font()

# Bên trong lớp CustomFontDropdown

    def _open_dropdown(self, event):
        if self.dropdown_toplevel and self.dropdown_toplevel.winfo_exists():
            self._close_dropdown()
            return

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()

        self.dropdown_toplevel = ctk.CTkToplevel(self)
        self.dropdown_toplevel.geometry(f"{self.width + 20}x350+{x}+{y}")
        self.dropdown_toplevel.overrideredirect(True)
        self.dropdown_toplevel.attributes("-topmost", True)
        
        # Thêm fg_color để đảm bảo frame chính của popup có màu nền đúng theo theme
        popup_main_frame = ctk.CTkFrame(self.dropdown_toplevel, corner_radius=5, 
                                        border_width=1, border_color="gray50",
                                        fg_color=("gray92", "#282828")) # Ví dụ: màu xám sáng và xám rất tối
        popup_main_frame.pack(expand=True, fill="both")
        
        self.search_entry = ctk.CTkEntry(popup_main_frame, placeholder_text="🔎 Tìm kiếm font...")
        self.search_entry.pack(fill="x", padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_keyup)
        
        # Thêm fg_color cho scrollable_frame để nó cũng có nền theo theme, thay vì "transparent"
        self.scrollable_frame = ctk.CTkScrollableFrame(popup_main_frame, 
                                                       fg_color=("gray95", "#333333")) # Màu nền cho danh sách
        self.scrollable_frame.pack(expand=True, fill="both", padx=5, pady=(0, 5))
        
        self.dropdown_toplevel.bind("<MouseWheel>", self._on_mouse_wheel_scroll)
        self.dropdown_toplevel.bind("<Button-4>", self._on_mouse_wheel_scroll)
        self.dropdown_toplevel.bind("<Button-5>", self._on_mouse_wheel_scroll)
        self.dropdown_toplevel.bind("<Escape>", self._close_dropdown)

        self.dropdown_toplevel.focus_set()
        self.dropdown_toplevel.bind("<FocusOut>", self._on_focus_out)
        
        self._populate_or_filter_font_list()
        
        self.original_scrollbar_command = self.scrollable_frame._scrollbar.cget("command")
        self.scrollable_frame._scrollbar.configure(command=self._on_scrollbar_move)

    # Thêm lại hàm _on_focus_out
    def _on_focus_out(self, event=None):
        """Hàm này được gọi khi cửa sổ dropdown mất focus, và sẽ đóng nó lại."""
        self._close_dropdown()

    def _on_mouse_wheel_scroll(self, event):
        if hasattr(self.scrollable_frame, '_parent_canvas'):
            if event.num == 4 or event.delta > 0:
                self.scrollable_frame._parent_canvas.yview_scroll(-self.scroll_step, "units")
            elif event.num == 5 or event.delta < 0:
                self.scrollable_frame._parent_canvas.yview_scroll(self.scroll_step, "units")
            self._lazy_load_on_scroll()
        return "break"

    def _on_scrollbar_move(self, *args):
        if self.original_scrollbar_command:
            self.original_scrollbar_command(*args)
        self._lazy_load_on_scroll()

    def _on_search_keyup(self, event=None):
        search_term = self.search_entry.get().lower()
        self.filtered_font_list = [font for font in self.font_list_cache if search_term in font.lower()]
        self._populate_or_filter_font_list(is_searching=True)

    def _populate_or_filter_font_list(self, is_searching=False):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        if not self.font_list_cache:
            ctk.CTkLabel(self.scrollable_frame, text="Đang tải font...").pack(pady=10)
            return
        self.last_rendered_index = -1
        if is_searching:
            target_list = self.filtered_font_list
            items_to_show = target_list[:100]
            if len(target_list) > 100:
                self.after(10, lambda: ctk.CTkLabel(self.scrollable_frame, text=f"... và {len(target_list)-100} kết quả khác", text_color="gray").pack(anchor="w", padx=5))
        else:
            self.filtered_font_list = self.font_list_cache[:]
            items_to_show = self.filtered_font_list[:self.lazy_load_batch_size]
        if not items_to_show:
            ctk.CTkLabel(self.scrollable_frame, text="Không tìm thấy font." if is_searching else "Gõ để tìm font.", text_color="gray").pack(pady=10)
            return
        for font in items_to_show:
            self._create_font_button(font)
        self.last_rendered_index = len(items_to_show) - 1

    def _create_font_button(self, font_name):
        try:
            font_obj = ctk.CTkFont(family=font_name, size=14)
            font_button = ctk.CTkButton(
                self.scrollable_frame,
                text=font_name,
                font=font_obj,
                anchor="w",
                fg_color="transparent",
                # ### DÒNG SỬA 1 ### - Sửa hover_color để tương thích theme
                hover_color=("gray92", "#4A4A4A"),
                # ### DÒNG THÊM MỚI ### - Thêm text_color để chữ luôn rõ nét
                text_color=("gray10", "gray98"),
                command=lambda f=font_name: self._on_font_select(f)
            )
            font_button.pack(fill="x", padx=2, pady=1)
        except Exception:
            logging.warning(f"Không thể render nút cho font '{font_name}'")

    def _lazy_load_on_scroll(self, *args):
        search_term = self.search_entry.get()
        if search_term:
            return
        top, bottom = self.scrollable_frame._scrollbar.get()
        if self.is_loading_more or self.last_rendered_index >= len(self.filtered_font_list) - 1:
            return
        if bottom > 0.95:
            self.is_loading_more = True
            start_index = self.last_rendered_index + 1
            end_index = start_index + self.lazy_load_batch_size
            fonts_to_add = self.filtered_font_list[start_index:end_index]
            if fonts_to_add:
                logging.debug(f"Lazy loading: Thêm {len(fonts_to_add)} font mới...")
                for font in fonts_to_add:
                    self._create_font_button(font)
                self.last_rendered_index += len(fonts_to_add)
            self.after(100, lambda: setattr(self, 'is_loading_more', False))

    def _on_font_select(self, font_name):
        self.font_variable.set(font_name)
        self._close_dropdown()
        if self.update_callback:
            self.update_callback()

    def _close_dropdown(self, event=None):
        if self.dropdown_toplevel and self.dropdown_toplevel.winfo_exists():
            self.dropdown_toplevel.destroy()
            self.dropdown_toplevel = None

