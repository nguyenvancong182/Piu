"""
BrandingSettingsWindow class for Piu application.
Manages branding settings: logo, intro, and outro configuration.
"""
import customtkinter as ctk
import logging
import os
import json
from tkinter import filedialog, messagebox

# Import helpers
from utils.helpers import get_default_downloads_folder
from config.settings import save_config


class BrandingSettingsWindow(ctk.CTkToplevel):
# Khởi tạo Giao diện
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app

        self.title("🖼️ Cài đặt Logo, Intro & Outro")
        # THAY ĐỔI KÍCH THƯỚC Ở ĐÂY
        desired_popup_width = 620
        desired_popup_height = 520
        self.geometry(f"{desired_popup_width}x{desired_popup_height}")
        
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()

        # Căn giữa cửa sổ
        try:
            master_app.update_idletasks()
            self.update_idletasks()
            
            master_x = master_app.winfo_x()
            master_y = master_app.winfo_y()
            master_width = master_app.winfo_width()
            master_height = master_app.winfo_height()
            
            # Sử dụng kích thước mong muốn nếu winfo_width/height trả về giá trị không đáng tin cậy
            popup_width_actual = self.winfo_width()
            popup_height_actual = self.winfo_height()

            final_popup_width = desired_popup_width if popup_width_actual <= 1 else popup_width_actual
            final_popup_height = desired_popup_height if popup_height_actual <= 1 else popup_height_actual
            
            position_x = master_x + (master_width // 2) - (final_popup_width // 2)
            position_y = master_y + (master_height // 2) - (final_popup_height // 2)
            
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            
            if position_x + final_popup_width > screen_width:
                position_x = screen_width - final_popup_width
            if position_y + final_popup_height > screen_height:
                position_y = screen_height - final_popup_height
            if position_x < 0: position_x = 0
            if position_y < 0: position_y = 0
                
            self.geometry(f"{final_popup_width}x{final_popup_height}+{int(position_x)}+{int(position_y)}")
            logging.info(f"BrandingSettingsWindow: Đã căn giữa tại ({int(position_x)}, {int(position_y)}) với kích thước {final_popup_width}x{final_popup_height}")

        except Exception as e:
            logging.warning(f"Không thể căn giữa cửa sổ BrandingSettingsWindow: {e}")
            # Nếu lỗi, vẫn giữ geometry đã đặt ở trên
            self.geometry(f"{desired_popup_width}x{desired_popup_height}")

        # --- Các biến StringVar cục bộ cho các Entry số ---
        self.logo_size_percent_str_var = ctk.StringVar(
            value=str(self.master_app.branding_logo_size_percent_var.get())
        )
        self.logo_margin_px_str_var = ctk.StringVar(
            value=str(self.master_app.branding_logo_margin_px_var.get())
        )

        self.main_scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll_frame.pack(expand=True, fill="both", padx=15, pady=15)
        
        self._create_widgets()

        self.bottom_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_button_frame.pack(fill="x", padx=15, pady=(0, 15), side="bottom")

        self.cancel_button = ctk.CTkButton(self.bottom_button_frame, text="Hủy", width=100, command=self._on_close_window)
        self.cancel_button.pack(side="right", padx=(10, 0))

        self.save_button = ctk.CTkButton(self.bottom_button_frame, text="Lưu Cài Đặt", width=120, command=self._save_settings_and_close, fg_color="#1f6aa5")
        self.save_button.pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._on_close_window)
        self.after(10, self._update_dependent_controls_state) # Gọi sau chút để UI kịp tạo

# Bên trong lớp BrandingSettingsWindow

    def _create_widgets(self):
        """Tạo các widget con cho cửa sổ cài đặt branding."""
        label_font_ui = ("Segoe UI", 12)
        section_font_ui = ("Segoe UI", 13, "bold")

        # === Nhóm: Nhập / Xuất Cấu hình Branding ===
        config_group_frame = ctk.CTkFrame(self.main_scroll_frame)
        config_group_frame.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(config_group_frame, text="⚙️ Quản lý Cấu hình Branding (File .json):", font=section_font_ui, anchor="w").pack(fill="x", padx=5, pady=(5,5))

        config_controls_frame = ctk.CTkFrame(config_group_frame, fg_color="transparent")
        config_controls_frame.pack(fill="x", padx=10, pady=5)
        config_controls_frame.grid_columnconfigure((0, 1), weight=1) # Chia đều không gian cho 2 nút

        self.import_branding_button = ctk.CTkButton(config_controls_frame, text="Nhập từ File...", command=self._import_branding_from_file)
        self.import_branding_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.export_branding_button = ctk.CTkButton(config_controls_frame, text="Xuất ra File...", command=self._export_branding_to_file)
        self.export_branding_button.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # === Phần Intro Video ===
        # SỬA Ở ĐÂY: Gán cho self.intro_frame TRƯỚC khi dùng
        self.intro_frame = ctk.CTkFrame(self.main_scroll_frame)
        self.intro_frame.pack(fill="x", pady=(0, 10), padx=5)
        # Bây giờ mới cấu hình cột cho self.intro_frame
        self.intro_frame.grid_columnconfigure(1, weight=1) # Cho label đường dẫn giãn ra

        self.intro_enabled_checkbox = ctk.CTkCheckBox(
            self.intro_frame, # Sử dụng self.intro_frame
            text="🎬 Thêm Video Intro",
            variable=self.master_app.branding_intro_enabled_var,
            font=label_font_ui,
            command=lambda: self._update_dependent_controls_state("intro_video")            
        )
        self.intro_enabled_checkbox.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        self.intro_path_label = ctk.CTkLabel(self.intro_frame, text="Đường dẫn: (Chưa chọn)", anchor="w", wraplength=350, text_color="gray", font=("Segoe UI", 10))
        self.intro_path_label.grid(row=1, column=0, columnspan=2, padx=(25, 5), pady=2, sticky="ew")
        
        self.select_intro_button = ctk.CTkButton(self.intro_frame, text="Chọn File Intro...", width=120, command=self._select_intro_file)
        self.select_intro_button.grid(row=1, column=2, padx=5, pady=2, sticky="e")
        self._update_path_label(self.intro_path_label, self.master_app.branding_intro_path_var.get())

        ### THÊM KHỐI CODE NÀY VÀO NGAY SAU KHỐI INTRO VIDEO ###
        # === Phần Intro từ Ảnh ===
        self.intro_image_frame = ctk.CTkFrame(self.main_scroll_frame, fg_color="transparent")
        self.intro_image_frame.pack(fill="x", pady=(0, 10), padx=20) # Thụt vào một chút
        self.intro_image_frame.grid_columnconfigure(1, weight=1)

        self.intro_from_image_checkbox = ctk.CTkCheckBox(
            self.intro_image_frame,
            text="Tạo Intro từ Ảnh",
            variable=self.master_app.branding_intro_from_image_enabled_var,
            font=label_font_ui,
            command=lambda: self._update_dependent_controls_state("intro_image")
        )
        self.intro_from_image_checkbox.grid(row=0, column=0, columnspan=3, padx=5, pady=2, sticky="w")

        self.intro_image_path_label = ctk.CTkLabel(self.intro_image_frame, text="Đường dẫn ảnh: (Chưa chọn)", anchor="w", wraplength=280, text_color="gray", font=("Segoe UI", 9))
        self.intro_image_path_label.grid(row=1, column=0, columnspan=2, padx=(20, 5), pady=2, sticky="ew")
        self.select_intro_image_button = ctk.CTkButton(self.intro_image_frame, text="Chọn Ảnh...", width=100, command=self._select_intro_image)
        self.select_intro_image_button.grid(row=1, column=2, padx=5, pady=2, sticky="e")

        ctk.CTkLabel(self.intro_image_frame, text="Thời lượng (giây):", anchor="e", font=label_font_ui).grid(row=2, column=0, padx=(20, 2), pady=2, sticky="e")
        self.intro_image_duration_entry = ctk.CTkEntry(self.intro_image_frame, textvariable=self.master_app.branding_intro_image_duration_var, width=70)
        self.intro_image_duration_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        ### KẾT THÚC THÊM MỚI ###

        # === Phần Outro Video ===
        # Tương tự, gán cho self.outro_frame TRƯỚC khi dùng
        self.outro_frame = ctk.CTkFrame(self.main_scroll_frame)
        self.outro_frame.pack(fill="x", pady=(0, 10), padx=5)
        self.outro_frame.grid_columnconfigure(1, weight=1)

        self.outro_enabled_checkbox = ctk.CTkCheckBox(
            self.outro_frame, # Sử dụng self.outro_frame
            text="🎬 Thêm Video Outro",
            variable=self.master_app.branding_outro_enabled_var,
            font=label_font_ui,
            command=lambda: self._update_dependent_controls_state("outro_video")
        )
        self.outro_enabled_checkbox.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        self.outro_path_label = ctk.CTkLabel(self.outro_frame, text="Đường dẫn: (Chưa chọn)", anchor="w", wraplength=350, text_color="gray", font=("Segoe UI", 10))
        self.outro_path_label.grid(row=1, column=0, columnspan=2, padx=(25, 5), pady=2, sticky="ew")

        self.select_outro_button = ctk.CTkButton(self.outro_frame, text="Chọn File Outro...", width=120, command=self._select_outro_file)
        self.select_outro_button.grid(row=1, column=2, padx=5, pady=2, sticky="e")
        self._update_path_label(self.outro_path_label, self.master_app.branding_outro_path_var.get())

        ### THÊM KHỐI CODE NÀY VÀO NGAY SAU KHỐI OUTRO VIDEO ###
        # === Phần Outro từ Ảnh ===
        self.outro_image_frame = ctk.CTkFrame(self.main_scroll_frame, fg_color="transparent")
        self.outro_image_frame.pack(fill="x", pady=(0, 10), padx=20)
        self.outro_image_frame.grid_columnconfigure(1, weight=1)

        self.outro_from_image_checkbox = ctk.CTkCheckBox(
            self.outro_image_frame,
            text="Tạo Outro từ Ảnh",
            variable=self.master_app.branding_outro_from_image_enabled_var,
            font=label_font_ui,
            command=lambda: self._update_dependent_controls_state("outro_image")
        )
        self.outro_from_image_checkbox.grid(row=0, column=0, columnspan=3, padx=5, pady=2, sticky="w")

        self.outro_image_path_label = ctk.CTkLabel(self.outro_image_frame, text="Đường dẫn ảnh: (Chưa chọn)", anchor="w", wraplength=280, text_color="gray", font=("Segoe UI", 9))
        self.outro_image_path_label.grid(row=1, column=0, columnspan=2, padx=(20, 5), pady=2, sticky="ew")
        self.select_outro_image_button = ctk.CTkButton(self.outro_image_frame, text="Chọn Ảnh...", width=100, command=self._select_outro_image)
        self.select_outro_image_button.grid(row=1, column=2, padx=5, pady=2, sticky="e")

        ctk.CTkLabel(self.outro_image_frame, text="Thời lượng (giây):", anchor="e", font=label_font_ui).grid(row=2, column=0, padx=(20, 2), pady=2, sticky="e")
        self.outro_image_duration_entry = ctk.CTkEntry(self.outro_image_frame, textvariable=self.master_app.branding_outro_image_duration_var, width=70)
        self.outro_image_duration_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        ### KẾT THÚC THÊM MỚI ###

        # === Phần Logo (Watermark) ===
        # Gán cho self.logo_main_frame TRƯỚC khi dùng
        self.logo_main_frame = ctk.CTkFrame(self.main_scroll_frame)
        self.logo_main_frame.pack(fill="x", pady=(0, 5), padx=5)
        self.logo_main_frame.grid_columnconfigure(1, weight=1)

        self.logo_enabled_checkbox = ctk.CTkCheckBox(
            self.logo_main_frame, # Sử dụng self.logo_main_frame
            text="🖼 Chèn Logo (Watermark)",
            variable=self.master_app.branding_logo_enabled_var,
            font=label_font_ui,
            command=self._update_dependent_controls_state 
        )
        self.logo_enabled_checkbox.grid(row=0, column=0, columnspan=3, padx=5, pady=(5,0), sticky="w")

        self.logo_path_label = ctk.CTkLabel(self.logo_main_frame, text="Đường dẫn: (Chưa chọn)", anchor="w", wraplength=350, text_color="gray", font=("Segoe UI", 10))
        self.logo_path_label.grid(row=1, column=0, columnspan=2, padx=(25, 5), pady=2, sticky="ew")
        self.select_logo_button = ctk.CTkButton(self.logo_main_frame, text="Chọn File Logo...", width=120, command=self._select_logo_file)
        self.select_logo_button.grid(row=1, column=2, padx=5, pady=2, sticky="e")
        self._update_path_label(self.logo_path_label, self.master_app.branding_logo_path_var.get())

        # Frame con cho các cài đặt chi tiết của Logo
        self.logo_settings_frame = ctk.CTkFrame(self.main_scroll_frame, fg_color="transparent")
        # KHÔNG pack/grid self.logo_settings_frame ở đây, _update_dependent_controls_state sẽ làm
        self.logo_settings_frame.grid_columnconfigure(1, weight=1) 

        # Vị trí Logo
        ctk.CTkLabel(self.logo_settings_frame, text="Vị trí Logo:", anchor="e", font=label_font_ui).grid(row=0, column=0, padx=(20,2), pady=5, sticky="e")
        self.logo_position_menu = ctk.CTkOptionMenu(
            self.logo_settings_frame, variable=self.master_app.branding_logo_position_var,
            values=["bottom_right", "bottom_left", "top_right", "top_left", "center"]
        )
        self.logo_position_menu.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        # ... (các widget còn lại của logo_settings_frame) ...
        ctk.CTkLabel(self.logo_settings_frame, text="Độ mờ (0-100%):", anchor="e", font=label_font_ui).grid(row=1, column=0, padx=(20,2), pady=5, sticky="e")
        self.logo_opacity_slider = ctk.CTkSlider(
            self.logo_settings_frame, from_=0, to=100, number_of_steps=100,
            variable=self.master_app.branding_logo_opacity_var, command=self._update_opacity_label
        )
        self.logo_opacity_slider.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.logo_opacity_value_label = ctk.CTkLabel(self.logo_settings_frame, text=f"{self.master_app.branding_logo_opacity_var.get()}%", width=40, font=("Segoe UI", 11))
        self.logo_opacity_value_label.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(self.logo_settings_frame, text="Kích thước (% video width):", anchor="e", font=label_font_ui).grid(row=2, column=0, padx=(20,2), pady=5, sticky="e")
        self.logo_size_entry = ctk.CTkEntry(self.logo_settings_frame, textvariable=self.logo_size_percent_str_var, width=60)
        self.logo_size_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(self.logo_settings_frame, text="%").grid(row=2, column=2, padx=0, pady=5, sticky="w")

        ctk.CTkLabel(self.logo_settings_frame, text="Lề Logo (pixels):", anchor="e", font=label_font_ui).grid(row=3, column=0, padx=(20,2), pady=5, sticky="e")
        self.logo_margin_entry = ctk.CTkEntry(self.logo_settings_frame, textvariable=self.logo_margin_px_str_var, width=60)
        self.logo_margin_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(self.logo_settings_frame, text="px").grid(row=3, column=2, padx=0, pady=5, sticky="w")


    def _validate_and_save_settings(self): # Đảm bảo hàm này validate đúng biến của Branding
        logging.debug("[BrandingSettingsWindow] Bắt đầu _validate_and_save_settings cho Branding.")
        try:
            # Opacity (từ Slider, dùng IntVar)
            try:
                opacity_val = self.master_app.branding_logo_opacity_var.get()
                if not (0 <= opacity_val <= 100):
                    self.master_app.branding_logo_opacity_var.set(max(0, min(100, opacity_val)))
            except Exception:
                 self.master_app.branding_logo_opacity_var.set(80) # Mặc định

            # Kích thước Logo (từ Entry, dùng StringVar -> IntVar)
            size_str = self.logo_size_percent_str_var.get().strip()
            if not size_str: self.master_app.branding_logo_size_percent_var.set(10) # Mặc định
            else:
                try:
                    size_val = int(size_str)
                    if not (1 <= size_val <= 100):
                        messagebox.showerror("Giá trị không hợp lệ", "Kích thước logo phải từ 1 đến 100%.", parent=self)
                        return False
                    self.master_app.branding_logo_size_percent_var.set(size_val)
                except ValueError:
                    messagebox.showerror("Giá trị không hợp lệ", "Kích thước logo phải là số nguyên.", parent=self)
                    return False

            # Lề Logo (từ Entry, dùng StringVar -> IntVar)
            margin_str = self.logo_margin_px_str_var.get().strip()
            if not margin_str: self.master_app.branding_logo_margin_px_var.set(10) # Mặc định
            else:
                try:
                    margin_val = int(margin_str)
                    if margin_val < 0: # Có thể cho phép lề âm nếu FFmpeg hỗ trợ, nhưng thường là không âm
                        messagebox.showerror("Giá trị không hợp lệ", "Lề logo phải là số không âm.", parent=self)
                        return False
                    self.master_app.branding_logo_margin_px_var.set(margin_val)
                except ValueError:
                    messagebox.showerror("Giá trị không hợp lệ", "Lề logo phải là số nguyên.", parent=self)
                    return False
            
            # Các kiểm tra khác cho đường dẫn file intro, outro, logo nếu cần (đảm bảo file tồn tại nếu checkbox được chọn)
            if self.master_app.branding_intro_enabled_var.get() and not (self.master_app.branding_intro_path_var.get() and os.path.exists(self.master_app.branding_intro_path_var.get())):
                messagebox.showerror("Thiếu File", "Đã bật Video Intro nhưng chưa chọn file hoặc file không tồn tại.", parent=self)
                return False
            # Tương tự cho Outro và Logo...

            logging.info("[BrandingSettingsWindow] Xác thực cài đặt Branding thành công.")
            return True
        except Exception as e_val:
            logging.error(f"[BrandingSettingsWindow] Lỗi validation: {e_val}", exc_info=True)
            messagebox.showerror("Lỗi Validate", f"Lỗi khi kiểm tra giá trị cài đặt:\n{e_val}", parent=self)
            return False

    def _save_settings_and_close(self):
        # (Nội dung hàm này như đã cung cấp ở lần trả lời trước, nó gọi _validate_and_save_settings)
        logging.info("[BrandingSettingsWindow] Nút 'Lưu và Đóng' (Branding) được nhấn.")
        if self._validate_and_save_settings():
            try:
                self.master_app.save_current_config()
                logging.info("[BrandingSettingsWindow] Đã lưu config branding.")
            except Exception as e_save:
                logging.error(f"[BrandingSettingsWindow] Lỗi lưu config: {e_save}", exc_info=True)
                messagebox.showerror("Lỗi Lưu", f"Lỗi khi lưu cấu hình: {e_save}", parent=self)
                return # Không đóng nếu lỗi lưu
            self._on_close_window() # Đóng cửa sổ
        else:
            logging.warning("[BrandingSettingsWindow] Validation thất bại, không lưu và không đóng.")


    def _on_close_window(self):
        logging.info("[BrandingSettingsWindow] Cửa sổ Branding đang được đóng.")
        if hasattr(self, 'grab_status') and self.grab_status() != "none":
            try: self.grab_release()
            except Exception: pass
        try: self.destroy()
        except Exception: pass

    def _update_path_label(self, label_widget, path_value):
        """Cập nhật label hiển thị đường dẫn, với màu sắc tương thích Light/Dark mode."""
        
        # Định nghĩa các cặp màu cho từng trạng thái
        # Tuple: (màu cho chế độ Sáng, màu cho chế độ Tối)
        SUCCESS_COLOR = ("#0B8457", "lightgreen")
        ERROR_COLOR = ("#B71C1C", "#FF8A80")
        DEFAULT_COLOR = ("gray30", "gray70")

        if not label_widget or not label_widget.winfo_exists():
            return

        if path_value and os.path.exists(path_value):
            # hiển thị đường dẫn đầy đủ >>>
            label_widget.configure(text=f"Đã chọn: {path_value}", text_color=SUCCESS_COLOR)
        elif path_value:
            # hiển thị đường dẫn đầy đủ >>>
            label_widget.configure(text=f"LỖI: '{path_value}' không tồn tại!", text_color=ERROR_COLOR)
        else:
            label_widget.configure(text="Đường dẫn: (Chưa chọn)", text_color=DEFAULT_COLOR)

    def _select_intro_file(self):
        initial_dir = os.path.dirname(self.master_app.branding_intro_path_var.get()) if self.master_app.branding_intro_path_var.get() and os.path.exists(os.path.dirname(self.master_app.branding_intro_path_var.get())) else get_default_downloads_folder()
        file_path = filedialog.askopenfilename(title="Chọn Video Intro", initialdir=initial_dir, filetypes=(("Video files", "*.mp4 *.avi *.mkv *.mov *.webm"), ("All files", "*.*")), parent=self)
        if file_path:
            self.master_app.branding_intro_path_var.set(file_path)
            self._update_path_label(self.intro_path_label, file_path)
        self._update_dependent_controls_state()

    def _select_intro_image(self):
        file_path = filedialog.askopenfilename(title="Chọn Ảnh cho Intro", filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")], parent=self)
        if file_path:
            self.master_app.branding_intro_image_path_var.set(file_path)
            self._update_path_label(self.intro_image_path_label, file_path)

    def _select_outro_file(self):
        initial_dir = os.path.dirname(self.master_app.branding_outro_path_var.get()) if self.master_app.branding_outro_path_var.get() and os.path.exists(os.path.dirname(self.master_app.branding_outro_path_var.get())) else get_default_downloads_folder()
        file_path = filedialog.askopenfilename(title="Chọn Video Outro", initialdir=initial_dir, filetypes=(("Video files", "*.mp4 *.avi *.mkv *.mov *.webm"), ("All files", "*.*")), parent=self)
        if file_path:
            self.master_app.branding_outro_path_var.set(file_path)
            self._update_path_label(self.outro_path_label, file_path)
        self._update_dependent_controls_state()

    def _select_outro_image(self):
        file_path = filedialog.askopenfilename(title="Chọn Ảnh cho Outro", filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")], parent=self)
        if file_path:
            self.master_app.branding_outro_image_path_var.set(file_path)
            self._update_path_label(self.outro_image_path_label, file_path)

    def _select_logo_file(self):
        initial_dir = os.path.dirname(self.master_app.branding_logo_path_var.get()) if self.master_app.branding_logo_path_var.get() and os.path.exists(os.path.dirname(self.master_app.branding_logo_path_var.get())) else get_default_downloads_folder()
        file_path = filedialog.askopenfilename(title="Chọn File Ảnh Logo (Ưu tiên PNG)", initialdir=initial_dir, filetypes=(("Image files", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")), parent=self)
        if file_path:
            self.master_app.branding_logo_path_var.set(file_path)
            self._update_path_label(self.logo_path_label, file_path)
        self._update_dependent_controls_state()

    def _update_opacity_label(self, value):
        if hasattr(self, 'logo_opacity_value_label') and self.logo_opacity_value_label.winfo_exists():
            self.logo_opacity_value_label.configure(text=f"{int(value)}%")

# Hàm dùng để bật tắt các control phụ thuộc
    def _update_dependent_controls_state(self, source=None):
        """Cập nhật trạng thái các control phụ thuộc, xử lý logic loại trừ lẫn nhau."""
        logging.debug(f"BrandingSettings: _update_dependent_controls_state được gọi từ nguồn: {source}")

        ### KHỐI LOGIC MỚI: XỬ LÝ LOẠI TRỪ LẪN NHAU ###
        # Nếu người dùng vừa tick vào checkbox "Intro từ ảnh"
        if source == "intro_image" and self.master_app.branding_intro_from_image_enabled_var.get():
            self.master_app.branding_intro_enabled_var.set(False)
        # Nếu người dùng vừa tick vào checkbox "Intro từ video"
        elif source == "intro_video" and self.master_app.branding_intro_enabled_var.get():
            self.master_app.branding_intro_from_image_enabled_var.set(False)
        
        # Tương tự cho Outro
        if source == "outro_image" and self.master_app.branding_outro_from_image_enabled_var.get():
            self.master_app.branding_outro_enabled_var.set(False)
        elif source == "outro_video" and self.master_app.branding_outro_enabled_var.get():
            self.master_app.branding_outro_from_image_enabled_var.set(False)
        ### KẾT THÚC KHỐI LOGIC MỚI ###

        # Lấy lại giá trị các biến sau khi đã xử lý loại trừ để cập nhật UI
        is_intro_video_enabled = self.master_app.branding_intro_enabled_var.get()
        is_intro_image_enabled = self.master_app.branding_intro_from_image_enabled_var.get()
        is_outro_video_enabled = self.master_app.branding_outro_enabled_var.get()
        is_outro_image_enabled = self.master_app.branding_outro_from_image_enabled_var.get()
        is_logo_enabled = self.master_app.branding_logo_enabled_var.get()

        # --- Intro Video ---
        self.select_intro_button.configure(state="normal" if is_intro_video_enabled else "disabled")
        self._update_path_label(self.intro_path_label, self.master_app.branding_intro_path_var.get() if is_intro_video_enabled else "")
        if not is_intro_video_enabled: 
            self.master_app.branding_intro_path_var.set("")

        # --- Intro from Image ---
        self.select_intro_image_button.configure(state="normal" if is_intro_image_enabled else "disabled")
        self.intro_image_duration_entry.configure(state="normal" if is_intro_image_enabled else "disabled")
        self._update_path_label(self.intro_image_path_label, self.master_app.branding_intro_image_path_var.get() if is_intro_image_enabled else "")
        if not is_intro_image_enabled:
            self.master_app.branding_intro_image_path_var.set("")

        # --- Outro Video ---
        self.select_outro_button.configure(state="normal" if is_outro_video_enabled else "disabled")
        self._update_path_label(self.outro_path_label, self.master_app.branding_outro_path_var.get() if is_outro_video_enabled else "")
        if not is_outro_video_enabled: 
            self.master_app.branding_outro_path_var.set("")

        # --- Outro from Image ---
        self.select_outro_image_button.configure(state="normal" if is_outro_image_enabled else "disabled")
        self.outro_image_duration_entry.configure(state="normal" if is_outro_image_enabled else "disabled")
        self._update_path_label(self.outro_image_path_label, self.master_app.branding_outro_image_path_var.get() if is_outro_image_enabled else "")
        if not is_outro_image_enabled:
            self.master_app.branding_outro_image_path_var.set("")

        # --- Logo Controls ---
        if hasattr(self, 'select_logo_button'):
            self.select_logo_button.configure(state="normal" if is_logo_enabled else "disabled")
        if hasattr(self, 'logo_path_label'):
            self._update_path_label(self.logo_path_label, self.master_app.branding_logo_path_var.get() if is_logo_enabled else "")
        if not is_logo_enabled and hasattr(self.master_app, 'branding_logo_path_var'):
            self.master_app.branding_logo_path_var.set("")
            if hasattr(self, 'logo_path_label'): self._update_path_label(self.logo_path_label, "")

        # --- Hiện/ẩn frame cài đặt chi tiết của Logo ---
        logo_settings_widgets_refs = [
            getattr(self, 'logo_position_menu', None), 
            getattr(self, 'logo_opacity_slider', None), 
            getattr(self, 'logo_opacity_value_label', None), 
            getattr(self, 'logo_size_entry', None), 
            getattr(self, 'logo_margin_entry', None)
        ]
        
        logo_settings_frame_ref = getattr(self, 'logo_settings_frame', None)
        logo_main_frame_ref = getattr(self, 'logo_main_frame', None)

        if not all(widget and widget.winfo_exists() for widget in [logo_settings_frame_ref, logo_main_frame_ref, self.main_scroll_frame]):
            logging.error("BrandingSettings: Một trong các frame chính đã bị hủy.")
            return

        if is_logo_enabled:
            for widget_item in logo_settings_widgets_refs:
                if widget_item and widget_item.winfo_exists(): 
                    widget_item.configure(state="normal")
            
            if not logo_settings_frame_ref.winfo_ismapped():
                logo_settings_frame_ref.pack(in_=self.main_scroll_frame, fill="x", pady=(0, 10), padx=(5, 5), after=logo_main_frame_ref)
        else:
            if logo_settings_frame_ref.winfo_ismapped():
                logo_settings_frame_ref.pack_forget()
            for widget_item in logo_settings_widgets_refs:
                if widget_item and widget_item.winfo_exists(): 
                    widget_item.configure(state="disabled")
        
        logging.debug(f"BrandingSettings: Cập nhật UI hoàn tất. is_logo_enabled: {is_logo_enabled}")

    # --- THÊM CÁC HÀM NÀY VÀO TRONG LỚP BrandingSettingsWindow ---

    def _apply_branding_data(self, branding_data):
        """Hàm helper để áp dụng dữ liệu từ dictionary vào các biến UI branding."""
        try:
            # Cập nhật các biến BooleanVar và StringVar
            self.master_app.branding_intro_enabled_var.set(branding_data.get("branding_intro_enabled", False))
            self.master_app.branding_intro_path_var.set(branding_data.get("branding_intro_path", ""))
            self.master_app.branding_outro_enabled_var.set(branding_data.get("branding_outro_enabled", False))
            self.master_app.branding_outro_path_var.set(branding_data.get("branding_outro_path", ""))
            self.master_app.branding_logo_enabled_var.set(branding_data.get("branding_logo_enabled", False))
            self.master_app.branding_logo_path_var.set(branding_data.get("branding_logo_path", ""))
            self.master_app.branding_logo_position_var.set(branding_data.get("branding_logo_position", "bottom_right"))
            
            # Cập nhật các biến IntVar
            self.master_app.branding_logo_opacity_var.set(branding_data.get("branding_logo_opacity_percent", 80))
            self.master_app.branding_logo_size_percent_var.set(branding_data.get("branding_logo_size_percent", 10))
            self.master_app.branding_logo_margin_px_var.set(branding_data.get("branding_logo_margin_px", 10))

            # Cập nhật các biến StringVar cục bộ cho các Entry số để UI hiển thị đúng
            self.logo_size_percent_str_var.set(str(self.master_app.branding_logo_size_percent_var.get()))
            self.logo_margin_px_str_var.set(str(self.master_app.branding_logo_margin_px_var.get()))

            # Kích hoạt cập nhật toàn bộ UI để phản ánh các giá trị mới
            self._update_dependent_controls_state() # Chỉ cần gọi hàm này là đủ

            logging.info("Đã áp dụng thành công dữ liệu branding vào giao diện.")
            return True
        except Exception as e:
            logging.error(f"Lỗi khi áp dụng dữ liệu branding: {e}", exc_info=True)
            return False

    def _import_branding_from_file(self):
        """Mở hộp thoại để chọn file .json và tải cấu hình branding."""
        file_path = filedialog.askopenfilename(
            title="Chọn File Cấu hình Branding (.json)",
            filetypes=[("JSON Branding Files", "*.json"), ("All files", "*.*")],
            parent=self
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                branding_data = json.load(f)
            
            # Kiểm tra xem có phải là file branding hợp lệ không
            if "branding_logo_position" not in branding_data and "branding_intro_enabled" not in branding_data:
                messagebox.showerror("File không hợp lệ", "File JSON đã chọn không có vẻ là một file cấu hình branding hợp lệ của Piu.", parent=self)
                return

            if self._apply_branding_data(branding_data):
                messagebox.showinfo("Thành công", f"Đã nhập thành công cấu hình branding từ file:\n{os.path.basename(file_path)}", parent=self)

        except Exception as e:
            messagebox.showerror("Lỗi Nhập File", f"Không thể đọc hoặc áp dụng file cấu hình branding.\nLỗi: {e}", parent=self)

    def _export_branding_to_file(self):
        """Thu thập cài đặt branding hiện tại và lưu chúng vào một file .json."""
        file_path = filedialog.asksaveasfilename(
            title="Lưu File Cấu hình Branding",
            defaultextension=".json",
            filetypes=[("JSON Branding Files", "*.json"), ("All files", "*.*")],
            initialfile="My-Piu-Branding.json",
            parent=self
        )
        if not file_path:
            return
            
        if not self._validate_and_save_settings():
            logging.warning("Xác thực cài đặt branding thất bại. Hủy xuất file.")
            return

        # Thu thập tất cả các giá trị hiện tại
        current_branding_data = {
            "branding_intro_enabled": self.master_app.branding_intro_enabled_var.get(),
            "branding_intro_path": self.master_app.branding_intro_path_var.get(),
            "branding_outro_enabled": self.master_app.branding_outro_enabled_var.get(),
            "branding_outro_path": self.master_app.branding_outro_path_var.get(),
            "branding_logo_enabled": self.master_app.branding_logo_enabled_var.get(),
            "branding_logo_path": self.master_app.branding_logo_path_var.get(),
            "branding_logo_position": self.master_app.branding_logo_position_var.get(),
            "branding_logo_opacity_percent": self.master_app.branding_logo_opacity_var.get(),
            "branding_logo_size_percent": self.master_app.branding_logo_size_percent_var.get(),
            "branding_logo_margin_px": self.master_app.branding_logo_margin_px_var.get(),
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(current_branding_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Thành công", f"Đã xuất cấu hình branding hiện tại ra file:\n{os.path.basename(file_path)}", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi Lưu File", f"Không thể lưu file cấu hình branding.\nLỗi: {e}", parent=self)

