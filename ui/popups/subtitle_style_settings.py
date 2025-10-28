"""
SubtitleStyleSettingsWindow class for Piu application.
Manages subtitle style settings (font, colors, outline, etc.)
Extracted from Piu.py
"""

import customtkinter as ctk
import logging
import os
import json
from tkinter import filedialog, messagebox, colorchooser
import matplotlib.font_manager as font_manager

from ui.widgets.tooltip import Tooltip
from ui.widgets.custom_font_dropdown import CustomFontDropdown


class SubtitleStyleSettingsWindow(ctk.CTkToplevel):
# Khởi tạo giao diện
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app

        self.title("🎨 Cài đặt Kiểu Phụ đề (Hardsub)")
        # THAY ĐỔI KÍCH THƯỚC Ở ĐÂY
        desired_popup_width = 620
        desired_popup_height = 750
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
            logging.info(f"SubtitleStyleSettingsWindow: Đã căn giữa tại ({int(position_x)}, {int(position_y)}) với kích thước {final_popup_width}x{final_popup_height}")
        except Exception as e:
            logging.warning(f"Không thể căn giữa SubtitleStyleSettingsWindow: {e}")
            self.geometry(f"{desired_popup_width}x{desired_popup_height}")


        # --- StringVars cục bộ cho các Entry số ---
        self.font_size_str_var = ctk.StringVar(value=str(self.master_app.sub_style_font_size_var.get()))
        self.outline_size_str_var = ctk.StringVar(value=str(self.master_app.sub_style_outline_size_var.get()))
        self.marginv_str_var = ctk.StringVar(value=str(self.master_app.sub_style_marginv_var.get()))

        # CODE MỚI CHO PREVIEW 
        preview_frame = ctk.CTkFrame(self, fg_color=("#404040", "#282828"), height=120, corner_radius=8)
        preview_frame.pack(fill="x", padx=15, pady=(15, 10))
        preview_frame.pack_propagate(False) # Ngăn frame co lại theo nội dung

        self.preview_image_label = ctk.CTkLabel(
            preview_frame, 
            text="Xem trước sẽ hiện ở đây...", # Text tạm thời
            text_color="gray"
        )
        self.preview_image_label.pack(expand=True, fill="both")
        # KẾT THÚC ĐOẠN CODE MỚI

        self.main_scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll_frame.pack(expand=True, fill="both", padx=15, pady=15)
        
        self._create_style_widgets() # Đảm bảo tên hàm này khớp với định nghĩa của bạn

        bottom_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_button_frame.pack(fill="x", padx=15, pady=(5, 15), side="bottom")

        cancel_button = ctk.CTkButton(bottom_button_frame, text="Hủy", width=100, command=self._on_close_window)
        cancel_button.pack(side="right", padx=(10, 0))

        save_button = ctk.CTkButton(bottom_button_frame, text="Lưu và Đóng", width=130, command=self._save_settings_and_close, fg_color="#1f6aa5")
        save_button.pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._on_close_window)
        self.after(10, self._update_all_dependent_controls_visibility)
        self.after(200, self._update_preview_image)

#-----------------------------------------------------------------------------------------------------
# Hàm helper để tìm đường dẫn file
    def _find_font_file(self, font_name, is_bold=False):
        """
        Hàm helper tìm đường dẫn file font, sử dụng matplotlib.font_manager để có kết quả chính xác.
        """
        # Cache để không phải tìm lại nhiều lần, giúp tăng tốc
        if not hasattr(self, '_font_cache'):
            self._font_cache = {}
        
        cache_key = f"{font_name}_{'bold' if is_bold else 'regular'}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        try:
            # Tạo một đối tượng FontProperties để mô tả font cần tìm
            font_prop = font_manager.FontProperties(
                family=font_name,
                weight='bold' if is_bold else 'normal'
            )
            
            # Dùng findfont để tìm kiếm chuyên nghiệp. Nó sẽ tự xử lý các biến thể tên file.
            found_path = font_manager.findfont(font_prop, fallback_to_default=False)
            
            if found_path:
                logging.info(f"Đã tìm thấy file cho font '{font_name}' (Bold: {is_bold}): {found_path}")
                self._font_cache[cache_key] = found_path
                return found_path
            
        except Exception as e_fm:
            # Nếu findfont không tìm thấy, nó sẽ ném ra lỗi.
            # Chúng ta sẽ bắt lỗi này và coi như không tìm thấy.
            pass

        # Nếu không tìm thấy, lưu kết quả vào cache và trả về None
        logging.warning(f"Không tìm thấy file font cho '{font_name}' (Bold: {is_bold}) bằng font_manager.")
        self._font_cache[cache_key] = None
        return None


# Hàm Tạo và cập nhật ảnh xem trước dựa trên các cài đặt hiện tại.
    def _update_preview_image(self):
        """Tạo và cập nhật ảnh xem trước dựa trên các cài đặt hiện tại."""
        from PIL import Image, ImageDraw, ImageFont
        
        try:
            # --- 1. Lấy tất cả cài đặt hiện tại từ các biến ---
            font_size = int(self.font_size_str_var.get() or "60")
            font_name = self.master_app.sub_style_font_name_var.get()
            is_bold = self.master_app.sub_style_font_bold_var.get()
            
            text_color_tuple = self._parse_color_string_to_tuple(self.master_app.sub_style_text_color_rgb_str_var.get())
            text_opacity = self.master_app.sub_style_text_opacity_percent_var.get()
            text_alpha = int(255 * (text_opacity / 100.0))
            text_color_rgba = (*text_color_tuple, text_alpha)

            background_mode = self.master_app.sub_style_background_mode_var.get()
            
        except (ValueError, TypeError) as e:
            logging.warning(f"Giá trị cài đặt không hợp lệ cho preview: {e}. Bỏ qua cập nhật.")
            return

        # --- 2. Tạo ảnh nền ---
        preview_width, preview_height = 580, 100
        img = Image.new('RGBA', (preview_width, preview_height), (40, 40, 40, 255))
        draw = ImageDraw.Draw(img)

        # --- 3. Chuẩn bị font ---
        font_path = self._find_font_file(font_name, is_bold=is_bold)
        if not font_path and is_bold:
            font_path = self._find_font_file(font_name, is_bold=False)
        if not font_path:
            font_path = self._find_font_file("Arial") 
            if not font_path:
                self.preview_image_label.configure(text="Lỗi: Không tìm thấy font Arial.")
                return 
        try:
            pil_font = ImageFont.truetype(font_path, size=font_size)
        except Exception as e:
            self.preview_image_label.configure(text=f"Lỗi tải font:\n{os.path.basename(font_path)}")
            return
            
        # --- 4. Vẽ phụ đề mẫu ---
        sample_text = "Đây là dòng phụ đề mẫu\nđể xem trước font chữ."
        text_position = (preview_width / 2, preview_height / 2)

        # <<< --- BẮT ĐẦU KHỐI LOGIC VẼ ĐÃ SỬA --- >>>
        if background_mode == "Box Nền":
            bg_color_tuple = self._parse_color_string_to_tuple(self.master_app.sub_style_bg_color_rgb_str_var.get())
            bg_opacity = self.master_app.sub_style_bg_box_actual_opacity_percent_var.get()
            bg_alpha = int(255 * (bg_opacity / 100.0))
            bg_color_rgba = (*bg_color_tuple, bg_alpha)
            
            bbox = draw.textbbox(text_position, sample_text, font=pil_font, anchor="mm", align="center")
            padded_bbox = (bbox[0] - 8, bbox[1] - 4, bbox[2] + 8, bbox[3] + 4)
            draw.rounded_rectangle(padded_bbox, radius=5, fill=bg_color_rgba)
        
        elif background_mode == "Đổ Bóng":
            # Để xem trước, ta sẽ vẽ một viền chữ mờ bằng màu của bóng
            shadow_color_tuple = self._parse_color_string_to_tuple(self.master_app.sub_style_bg_color_rgb_str_var.get())
            shadow_opacity = self.master_app.sub_style_bg_box_actual_opacity_percent_var.get()
            shadow_alpha = int(255 * (shadow_opacity / 100.0))
            shadow_color_rgba = (*shadow_color_tuple, shadow_alpha)
            
            # Kích thước của bóng có thể lấy từ kích thước viền
            shadow_size = int(float(self.outline_size_str_var.get() or "2.0"))

            # Vẽ bóng (là một viền chữ dày)
            draw.text(text_position, sample_text, font=pil_font, 
                      anchor="mm", align="center", 
                      stroke_width=shadow_size, 
                      stroke_fill=shadow_color_rgba)
        
        elif background_mode == "Không Nền":
            # Chỉ vẽ viền chữ nếu checkbox được bật
            if self.master_app.sub_style_outline_enabled_var.get():
                outline_size = float(self.outline_size_str_var.get() or "2.0")
                outline_color_tuple = self._parse_color_string_to_tuple(self.master_app.sub_style_outline_color_rgb_str_var.get())
                outline_opacity = self.master_app.sub_style_outline_opacity_percent_var.get()
                outline_alpha = int(255 * (outline_opacity / 100.0))
                outline_color_rgba = (*outline_color_tuple, outline_alpha)

                draw.text(text_position, sample_text, font=pil_font, 
                          anchor="mm", align="center", 
                          stroke_width=int(outline_size), 
                          stroke_fill=outline_color_rgba)

        # Vẽ chữ chính LÊN TRÊN TẤT CẢ
        draw.text(text_position, sample_text, font=pil_font, fill=text_color_rgba, anchor="mm", align="center")
        # <<< --- KẾT THÚC KHỐI LOGIC VẼ ĐÃ SỬA --- >>>

        # --- 5. Hiển thị ảnh đã tạo ---
        try:
            ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=(preview_width, preview_height))
            self.preview_image_label.configure(image=ctk_image, text="")
            self.preview_image_label.image = ctk_image 
        except Exception as e:
            logging.error(f"Lỗi khi hiển thị ảnh preview: {e}")
            

# hàm "Trigger" trung gian tránh việc cập nhật ảnh liên tục và gây giật
    def _trigger_preview_update(self, *args):
        # Dùng after() để tránh gọi hàm cập nhật quá dồn dập
        # Nó sẽ hủy lệnh gọi cũ và chỉ thực hiện lệnh gọi cuối cùng sau 150ms
        if hasattr(self, '_after_id_preview'):
            self.after_cancel(self._after_id_preview)
        
        self._after_id_preview = self.after(150, self._update_preview_image)


    def _parse_color_string_to_tuple(self, color_str, default_color=(255,255,255)): #
        try:
            parts = list(map(int, color_str.split(','))) #
            return tuple(parts) if len(parts) == 3 and all(0 <= val <= 255 for val in parts) else default_color #
        except:
            return default_color #

    def _format_color_tuple_to_string(self, color_tuple): #
        return f"{int(color_tuple[0])},{int(color_tuple[1])},{int(color_tuple[2])}" #

    def _get_contrasting_text_color(self, hex_bg_color): #
        try:
            r = int(hex_bg_color[1:3], 16); g = int(hex_bg_color[3:5], 16); b = int(hex_bg_color[5:7], 16) #
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255 #
            return "black" if luminance > 0.55 else "white" #
        except:
            return "white" #

    def _pick_color(self, string_var_to_update, title="Chọn màu"): #
        current_color_str = string_var_to_update.get() #
        initial_color_tuple = self._parse_color_string_to_tuple(current_color_str) #
        initial_hex_color = '#%02x%02x%02x' % initial_color_tuple #
        
        chosen_color_info = colorchooser.askcolor(title=title, initialcolor=initial_hex_color, parent=self) #
        
        if chosen_color_info and chosen_color_info[0]:
            new_color_tuple = tuple(map(int, chosen_color_info[0]))
            new_color_str = self._format_color_tuple_to_string(new_color_tuple)
            string_var_to_update.set(new_color_str)
            self._trigger_preview_update() 

    def _create_color_button_with_label(self, parent_frame, row, col_button, string_var_instance):
        button_attr_name = f"btn_color_{string_var_instance._name}"

        def _update_button_display_on_var_change(*args):
            target_button = getattr(self, button_attr_name, None)
            if target_button and target_button.winfo_exists():
                current_color_str_val = string_var_instance.get()
                current_color_tuple_val = self._parse_color_string_to_tuple(current_color_str_val)
                current_hex_color_val = '#%02x%02x%02x' % current_color_tuple_val
                target_button.configure(
                    text=current_color_str_val,
                    fg_color=current_hex_color_val,
                    text_color=self._get_contrasting_text_color(current_hex_color_val)
                )

        initial_str_val = string_var_instance.get()
        initial_tuple_val = self._parse_color_string_to_tuple(initial_str_val)
        initial_hex_val = '#%02x%02x%02x' % initial_tuple_val

        color_button_widget = ctk.CTkButton(
            parent_frame, text=initial_str_val, width=150, height=28,
            fg_color=initial_hex_val,
            text_color=self._get_contrasting_text_color(initial_hex_val),
            command=lambda sv=string_var_instance: self._pick_color(sv, f"Chọn màu cho {sv._name}")
        )
        color_button_widget.grid(row=row, column=col_button, padx=5, pady=5, sticky="ew")
        setattr(self, button_attr_name, color_button_widget)
        string_var_instance.trace_add("write", _update_button_display_on_var_change)

    def _create_slider_with_label(self, parent_frame, row, col_slider, col_value, int_var_instance, value_label_attr_name):
        slider_widget = ctk.CTkSlider(
            parent_frame, from_=0, to=100, number_of_steps=100,
            variable=int_var_instance,
            command=lambda value, attr_name=value_label_attr_name: (self._update_slider_value_label(attr_name, value), self._trigger_preview_update())
        )
        slider_widget.grid(row=row, column=col_slider, padx=5, pady=5, sticky="ew")
        value_display_label = ctk.CTkLabel(parent_frame, text=f"{int_var_instance.get()}%", width=45, font=("Segoe UI", 11))
        value_display_label.grid(row=row, column=col_value, padx=(5,0), pady=5, sticky="w")
        setattr(self, value_label_attr_name, value_display_label)

    def _update_slider_value_label(self, label_attribute_name, value): #
        target_label = getattr(self, label_attribute_name, None) #
        if target_label and target_label.winfo_exists(): #
            target_label.configure(text=f"{int(value)}%") #

    def _create_style_widgets(self):
        label_font_ui = ("Segoe UI", 12)
        section_font_ui = ("Segoe UI", 13, "bold")
        entry_width_small = 70
        entry_width_medium = 100

        # === Nhóm: Nhập / Xuất Style ===
        preset_group_frame = ctk.CTkFrame(self.main_scroll_frame)
        preset_group_frame.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(preset_group_frame, text="⚙️ Quản lý Style (File .json):", font=section_font_ui, anchor="w").pack(fill="x", padx=5, pady=(5,5))

        preset_controls_frame = ctk.CTkFrame(preset_group_frame, fg_color="transparent")
        preset_controls_frame.pack(fill="x", padx=10, pady=5)
        preset_controls_frame.grid_columnconfigure((0, 1), weight=1)

        self.import_style_button = ctk.CTkButton(preset_controls_frame, text="Nhập Style từ File...", command=self._import_style_from_file)
        self.import_style_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.export_style_button = ctk.CTkButton(preset_controls_frame, text="Xuất Style ra File...", command=self._export_style_to_file)
        self.export_style_button.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        # --- Nhóm: Font Chữ ---
        font_group_frame = ctk.CTkFrame(self.main_scroll_frame)
        font_group_frame.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(font_group_frame, text="✒ Font Chữ:", font=section_font_ui, anchor="w").pack(fill="x", padx=5, pady=(5,5))

        font_options_frame = ctk.CTkFrame(font_group_frame, fg_color="transparent")
        font_options_frame.pack(fill="x", padx=10)
        font_options_frame.grid_columnconfigure(1, weight=1)
        font_options_frame.grid_columnconfigure(4, weight=0)

        ctk.CTkLabel(font_options_frame, text="Tên Font:", font=label_font_ui).grid(row=0, column=0, padx=(0,5), pady=5, sticky="e")
        self.custom_font_dropdown = CustomFontDropdown(
            master=font_options_frame, font_variable=self.master_app.sub_style_font_name_var,
            font_list_cache=self.master_app.system_fonts_cache, parent_scrollable_frame=self.main_scroll_frame,
            width=250, height=30, update_callback=self._trigger_preview_update
        )
        self.custom_font_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.refresh_fonts_button = ctk.CTkButton(font_options_frame, text="🔄", width=30, height=30, command=self.master_app._force_rescan_fonts)
        self.refresh_fonts_button.grid(row=0, column=2, padx=(5, 0), pady=5, sticky="w")
        Tooltip(self.refresh_fonts_button, "Quét lại danh sách font trên máy tính (hữu ích khi bạn vừa cài font mới)")
        ctk.CTkLabel(font_options_frame, text="Kích thước:", font=label_font_ui).grid(row=0, column=3, padx=(15,5), pady=5, sticky="e")
        self.font_size_entry = ctk.CTkEntry(font_options_frame, textvariable=self.font_size_str_var, width=entry_width_small)
        self.font_size_entry.grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.font_size_entry.bind("<KeyRelease>", self._trigger_preview_update)
        self.font_bold_checkbox = ctk.CTkCheckBox(font_options_frame, text="In đậm", variable=self.master_app.sub_style_font_bold_var, font=label_font_ui, command=self._trigger_preview_update)
        self.font_bold_checkbox.grid(row=0, column=5, padx=(15,5), pady=5, sticky="w")

        # --- Nhóm: Màu Sắc & Độ Mờ Chữ ---
        text_appearance_group_frame = ctk.CTkFrame(self.main_scroll_frame)
        text_appearance_group_frame.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(text_appearance_group_frame, text="🌈 Màu Chữ & Độ Đục:", font=section_font_ui, anchor="w").pack(fill="x", padx=5, pady=(5,5))
        text_color_opacity_frame_internal = ctk.CTkFrame(text_appearance_group_frame, fg_color="transparent")
        text_color_opacity_frame_internal.pack(fill="x", padx=10)
        text_color_opacity_frame_internal.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(text_color_opacity_frame_internal, text="Màu chữ (R,G,B):", font=label_font_ui).grid(row=0, column=0, padx=(0,5), pady=5, sticky="e")
        self._create_color_button_with_label(text_color_opacity_frame_internal, 0, 1, self.master_app.sub_style_text_color_rgb_str_var)
        ctk.CTkLabel(text_color_opacity_frame_internal, text="Độ đục chữ (%):", font=label_font_ui).grid(row=0, column=2, padx=(15,5), pady=5, sticky="e")
        self._create_slider_with_label(text_color_opacity_frame_internal, 0, 3, 4, self.master_app.sub_style_text_opacity_percent_var, "text_opacity_val_lbl")
        
        # --- Nhóm: Box Nền / Đổ Bóng (ĐÃ SỬA LẠI LAYOUT) ---
        bg_box_group_frame = ctk.CTkFrame(self.main_scroll_frame)
        bg_box_group_frame.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(bg_box_group_frame, text="📦 Nền Phụ đề:", font=section_font_ui, anchor="w").pack(fill="x", padx=5, pady=(5,0))
        ctk.CTkLabel(bg_box_group_frame, text="Kiểu Nền:", font=label_font_ui).pack(side="left", padx=(15, 10), pady=(5,5))
        self.background_mode_selector = ctk.CTkSegmentedButton(
            bg_box_group_frame, values=["Không Nền", "Box Nền", "Đổ Bóng"],
            variable=self.master_app.sub_style_background_mode_var,
            command=lambda value: (self._update_all_dependent_controls_visibility(), self._trigger_preview_update())
        )
        self.background_mode_selector.pack(side="left", fill="x", expand=True, padx=(0, 15), pady=(5,5))
        
        self.bg_box_details_frame = ctk.CTkFrame(bg_box_group_frame, fg_color="transparent")
        self.bg_box_details_frame.grid_columnconfigure(1, weight=1) # Cột 1 (widget) sẽ giãn ra

        # Hàng 0: Màu sắc
        self.bg_color_label = ctk.CTkLabel(self.bg_box_details_frame, text="Màu (R,G,B):", font=label_font_ui)
        self.bg_color_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="e")
        self._create_color_button_with_label(self.bg_box_details_frame, 0, 1, self.master_app.sub_style_bg_color_rgb_str_var)
        
        # Hàng 1: Độ đục
        self.bg_opacity_label = ctk.CTkLabel(self.bg_box_details_frame, text="Độ đục (%):", font=label_font_ui)
        self.bg_opacity_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="e")
        slider_container_for_bg = ctk.CTkFrame(self.bg_box_details_frame, fg_color="transparent")
        slider_container_for_bg.grid(row=1, column=1, padx=0, pady=0, sticky="ew")
        slider_container_for_bg.grid_columnconfigure(0, weight=1)
        self._create_slider_with_label(slider_container_for_bg, 0, 0, 1, self.master_app.sub_style_bg_box_actual_opacity_percent_var, "bg_opacity_val_lbl")

        # --- Nhóm: Viền Chữ (Outline) --- (Giữ nguyên)
        # ... (code của bạn cho phần Outline ở đây) ...
        outline_group_frame = ctk.CTkFrame(self.main_scroll_frame)
        outline_group_frame.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(outline_group_frame, text="✒ Viền Chữ (Outline):", font=section_font_ui, anchor="w").pack(fill="x", padx=5, pady=(5,0))
        
        self.outline_enabled_checkbox = ctk.CTkCheckBox(
            outline_group_frame, text="Bật Viền Chữ",
            variable=self.master_app.sub_style_outline_enabled_var,
            command=lambda: (self._update_all_dependent_controls_visibility(), self._trigger_preview_update()),
            font=label_font_ui            
        )
        self.outline_enabled_checkbox.pack(anchor="w", padx=15, pady=(2,5))

        self.outline_details_frame = ctk.CTkFrame(outline_group_frame, fg_color="transparent")
        self.outline_details_frame.pack(fill="x", pady=(0,5), padx=5)
        self.outline_details_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.outline_details_frame, text="Màu viền (R,G,B):", font=label_font_ui).grid(row=0, column=0, padx=(0,5), pady=5, sticky="e")
        self._create_color_button_with_label(self.outline_details_frame, 0, 1, self.master_app.sub_style_outline_color_rgb_str_var)
        
        ctk.CTkLabel(self.outline_details_frame, text="Độ đục viền (%):", font=label_font_ui).grid(row=1, column=0, padx=(0,5), pady=5, sticky="e")
        self._create_slider_with_label(self.outline_details_frame, 1, 1, 2, self.master_app.sub_style_outline_opacity_percent_var, "outline_opacity_val_lbl")
        
        ctk.CTkLabel(self.outline_details_frame, text="Kích thước viền:", font=label_font_ui).grid(row=2, column=0, padx=(0,5), pady=5, sticky="e")
        self.outline_size_entry = ctk.CTkEntry(self.outline_details_frame, textvariable=self.outline_size_str_var, width=entry_width_medium)
        self.outline_size_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.outline_size_entry.bind("<KeyRelease>", self._trigger_preview_update)
        
        # --- Nhóm: Lề (Margins) ---
        margin_group_frame = ctk.CTkFrame(self.main_scroll_frame)
        margin_group_frame.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(margin_group_frame, text="📏 Lề Dưới:", font=section_font_ui, anchor="w").pack(fill="x", padx=5, pady=(5,5))
        
        margin_options_frame = ctk.CTkFrame(margin_group_frame, fg_color="transparent")
        margin_options_frame.pack(fill="x", padx=10)
        margin_options_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(margin_options_frame, text=" Lề dưới (pixels):", font=label_font_ui).grid(row=0, column=0, padx=(0,5), pady=5, sticky="w")
        self.marginv_entry = ctk.CTkEntry(margin_options_frame, textvariable=self.marginv_str_var, width=entry_width_medium)
        self.marginv_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.marginv_entry.bind("<KeyRelease>", self._trigger_preview_update)


    def _update_all_dependent_controls_visibility(self, *args):
        is_outline_enabled = self.master_app.sub_style_outline_enabled_var.get()
        background_mode = self.master_app.sub_style_background_mode_var.get()
        
        # --- Xử lý Frame chi tiết của Box Nền / Đổ Bóng ---
        show_bg_details = background_mode in ["Box Nền", "Đổ Bóng"]
        if hasattr(self, 'bg_box_details_frame') and self.bg_box_details_frame.winfo_exists():
            parent_frame = self.bg_box_details_frame.master
            if show_bg_details:
                # <<< BẮT ĐẦU THÊM LOGIC MỚI >>>
                if background_mode == "Box Nền":
                    self.bg_color_label.configure(text="Màu box (R,G,B):")
                    self.bg_opacity_label.configure(text="Độ đục box (%):")
                elif background_mode == "Đổ Bóng":
                    self.bg_color_label.configure(text="Màu bóng (R,G,B):")
                    self.bg_opacity_label.configure(text="Độ đục bóng (%):")
                # <<< KẾT THÚC LOGIC MỚI >>>

                if not self.bg_box_details_frame.winfo_ismapped():
                    self.bg_box_details_frame.pack(in_=parent_frame, fill="x", pady=(0,10), padx=20, after=self.background_mode_selector)
            else:
                if self.bg_box_details_frame.winfo_ismapped():
                    self.bg_box_details_frame.pack_forget()

        # --- Xử lý Frame chi tiết của Viền chữ và Checkbox Viền chữ ---
        # Vô hiệu hóa checkbox "Bật Viền Chữ" khi đang ở chế độ "Box Nền"
        outline_checkbox_state = "disabled" if background_mode == "Box Nền" else "normal"
        if hasattr(self, 'outline_enabled_checkbox') and self.outline_enabled_checkbox.winfo_exists():
            self.outline_enabled_checkbox.configure(state=outline_checkbox_state)
            if background_mode == "Box Nền": # Tự động bỏ tick nếu chọn Box Nền
                self.master_app.sub_style_outline_enabled_var.set(False)
        
        # Chỉ hiện các tùy chọn viền chữ nếu checkbox được bật VÀ không ở chế độ Box Nền
        show_outline_details = self.master_app.sub_style_outline_enabled_var.get() and background_mode != "Box Nền"
        if hasattr(self, 'outline_details_frame') and self.outline_details_frame.winfo_exists():
            parent_frame_outline = self.outline_details_frame.master
            if show_outline_details:
                if not self.outline_details_frame.winfo_ismapped():
                    self.outline_details_frame.pack(in_=parent_frame_outline, fill="x", pady=(0,10), padx=20, after=self.outline_enabled_checkbox)
            else:
                if self.outline_details_frame.winfo_ismapped():
                    self.outline_details_frame.pack_forget()

    def _validate_and_save_settings(self): #
        logging.debug("[SubtitleStyleSettingsWindow] Bắt đầu _validate_and_save_settings.")
        try:
            # --- Font Size ---
            font_size_str = self.font_size_str_var.get().strip() # Lấy từ StringVar
            if not font_size_str:
                logging.warning("Subtitle Style: Kích thước font trống, đặt mặc định 60.")
                self.master_app.sub_style_font_size_var.set(60) # Set IntVar của master_app
            else:
                try:
                    font_size_int = int(font_size_str)
                    if not (8 <= font_size_int <= 150):
                        messagebox.showerror("Giá trị không hợp lệ", f"Kích thước font ('{font_size_str}') phải là số nguyên từ 8 đến 150.", parent=self)
                        return False
                    self.master_app.sub_style_font_size_var.set(font_size_int)
                except ValueError:
                    messagebox.showerror("Giá trị không hợp lệ", f"Kích thước font ('{font_size_str}') phải là một số nguyên.", parent=self)
                    return False

            # --- Màu sắc --- (Giữ nguyên logic validate màu từ def.txt )
            color_vars_to_validate = {
                "Màu chữ": self.master_app.sub_style_text_color_rgb_str_var,
                "Màu nền box": self.master_app.sub_style_bg_color_rgb_str_var,
            }
            if self.master_app.sub_style_outline_enabled_var.get():
                 color_vars_to_validate["Màu viền"] = self.master_app.sub_style_outline_color_rgb_str_var
            for label, color_var in color_vars_to_validate.items():
                color_str = color_var.get()
                try:
                    parts = [p.strip() for p in color_str.split(',')]
                    if not (len(parts) == 3 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)):
                        messagebox.showerror("Màu không hợp lệ", f"{label} ('{color_str}') không đúng định dạng R,G,B (0-255).", parent=self)
                        return False
                except Exception:
                    messagebox.showerror("Màu không hợp lệ", f"{label} ('{color_str}') có lỗi khi phân tích.", parent=self)
                    return False


            # --- Outline Size ---
            if self.master_app.sub_style_outline_enabled_var.get():
                outline_size_str = self.outline_size_str_var.get().strip() # Lấy từ StringVar
                if not outline_size_str:
                    logging.warning("Subtitle Style: Kích thước viền trống (khi viền bật), đặt mặc định 1.0.")
                    self.master_app.sub_style_outline_size_var.set(1.0) # Set DoubleVar của master_app
                else:
                    try:
                        outline_size_float = float(outline_size_str)
                        if not (0.0 <= outline_size_float <= 10.0):
                            messagebox.showerror("Giá trị không hợp lệ", f"Kích thước viền ('{outline_size_str}') phải từ 0.0 đến 10.0.", parent=self)
                            return False
                        self.master_app.sub_style_outline_size_var.set(outline_size_float)
                    except ValueError:
                        messagebox.showerror("Giá trị không hợp lệ", f"Kích thước viền ('{outline_size_str}') phải là một số thực.", parent=self)
                        return False
            else: # Nếu viền không bật, có thể đặt giá trị mặc định cho DoubleVar nếu muốn
                if not self.outline_size_str_var.get().strip(): # Nếu StringVar cũng trống
                    self.master_app.sub_style_outline_size_var.set(1.0)


            # --- MarginV (Lề dưới) ---
            marginv_str = self.marginv_str_var.get().strip() # Lấy từ StringVar
            if not marginv_str:
                logging.warning("Subtitle Style: Lề dưới trống, đặt mặc định 25.")
                self.master_app.sub_style_marginv_var.set(25) # Set IntVar của master_app
            else:
                try:
                    margin_val_int = int(marginv_str)
                    if not (-100 <= margin_val_int <= 300):
                        messagebox.showerror("Giá trị không hợp lệ", f"Lề dưới ('{marginv_str}') phải là số nguyên (ví dụ: từ -100 đến 300).", parent=self)
                        return False
                    self.master_app.sub_style_marginv_var.set(margin_val_int)
                except ValueError:
                    messagebox.showerror("Giá trị không hợp lệ", f"Lề dưới ('{marginv_str}') phải là một số nguyên.", parent=self)
                    return False

            logging.info("[SubtitleStyleSettingsWindow] Xác thực cài đặt style thành công.")
            return True
        except Exception as e_val_style:
            logging.error(f"[SubtitleStyleSettingsWindow] Lỗi validation style: {e_val_style}", exc_info=True)
            messagebox.showerror("Lỗi Validate Style", f"Lỗi khi kiểm tra giá trị cài đặt style:\n{e_val_style}", parent=self)
            return False


    # --- CÁC HÀM MỚI CHO TÍNH NĂNG LƯU PRESET FONTSTYLE ---

    def _apply_style_data(self, preset_data):
        """Hàm helper để áp dụng dữ liệu từ một dictionary vào các biến UI."""
        try:
            # Cập nhật các biến (IntVar, StringVar, BooleanVar, DoubleVar)
            self.master_app.sub_style_font_name_var.set(preset_data.get("sub_style_font_name", "Arial"))
            self.master_app.sub_style_font_size_var.set(preset_data.get("sub_style_font_size", 60))
            self.master_app.sub_style_font_bold_var.set(preset_data.get("sub_style_font_bold", True))
            self.master_app.sub_style_text_color_rgb_str_var.set(preset_data.get("sub_style_text_color_rgb_str", "255,255,255"))
            self.master_app.sub_style_text_opacity_percent_var.set(preset_data.get("sub_style_text_opacity_percent", 100))
            self.master_app.sub_style_background_mode_var.set(preset_data.get("sub_style_background_mode", "Đổ Bóng"))
            self.master_app.sub_style_bg_color_rgb_str_var.set(preset_data.get("sub_style_bg_color_rgb_str", "0,0,0"))
            self.master_app.sub_style_bg_box_actual_opacity_percent_var.set(preset_data.get("sub_style_bg_box_actual_opacity_percent", 75))
            self.master_app.sub_style_outline_enabled_var.set(preset_data.get("sub_style_outline_enabled", False))
            self.master_app.sub_style_outline_size_var.set(preset_data.get("sub_style_outline_size", 2.0))
            self.master_app.sub_style_outline_color_rgb_str_var.set(preset_data.get("sub_style_outline_color_rgb_str", "0,0,0"))
            self.master_app.sub_style_outline_opacity_percent_var.set(preset_data.get("sub_style_outline_opacity_percent", 100))
            self.master_app.sub_style_marginv_var.set(preset_data.get("margin_v", 60))

            # Cập nhật các biến StringVars cục bộ cho các Entry
            self.font_size_str_var.set(str(self.master_app.sub_style_font_size_var.get()))
            self.outline_size_str_var.set(str(self.master_app.sub_style_outline_size_var.get()))
            self.marginv_str_var.set(str(self.master_app.sub_style_marginv_var.get()))
            
            # Kích hoạt cập nhật các control phụ thuộc
            self._update_all_dependent_controls_visibility()
            self._trigger_preview_update() # Yêu cầu vẽ lại ảnh xem trước
            
            logging.info("Đã áp dụng thành công dữ liệu style vào giao diện.")
            return True
        except Exception as e:
            logging.error(f"Lỗi khi áp dụng dữ liệu style: {e}", exc_info=True)
            return False

    def _import_style_from_file(self):
        """Mở hộp thoại để chọn file .json và tải cài đặt style."""
        file_path = filedialog.askopenfilename(
            title="Chọn File Style (.json)",
            filetypes=[("JSON Style Files", "*.json"), ("All files", "*.*")],
            parent=self
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                preset_data = json.load(f)
            
            # Kiểm tra xem có phải là file style hợp lệ không (bằng cách kiểm tra một vài key)
            if "sub_style_font_name" not in preset_data or "margin_v" not in preset_data:
                messagebox.showerror("File không hợp lệ", "File JSON đã chọn không có vẻ là một file style hợp lệ của Piu.", parent=self)
                return

            if self._apply_style_data(preset_data):
                messagebox.showinfo("Thành công", f"Đã nhập thành công style từ file:\n{os.path.basename(file_path)}", parent=self)

        except (json.JSONDecodeError, IOError) as e:
            messagebox.showerror("Lỗi Đọc File", f"Không thể đọc hoặc phân tích file style.\nLỗi: {e}", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi Không xác định", f"Đã xảy ra lỗi khi nhập style:\n{e}", parent=self)

    def _export_style_to_file(self):
        """Thu thập cài đặt hiện tại và lưu chúng vào một file .json do người dùng chọn."""
        file_path = filedialog.asksaveasfilename(
            title="Lưu File Style",
            defaultextension=".json",
            filetypes=[("JSON Style Files", "*.json"), ("All files", "*.*")],
            initialfile="My-Piu-Style.json",
            parent=self
        )
        if not file_path:
            return
            
        # Xác thực các giá trị hiện tại trước khi lưu
        if not self._validate_and_save_settings():
            logging.warning("Xác thực cài đặt style thất bại. Hủy xuất file.")
            # _validate_and_save_settings đã hiện messagebox lỗi rồi
            return

        # Thu thập tất cả các giá trị hiện tại từ master_app
        current_style_data = {
            "sub_style_font_name": self.master_app.sub_style_font_name_var.get(),
            "sub_style_font_size": self.master_app.sub_style_font_size_var.get(),
            "sub_style_font_bold": self.master_app.sub_style_font_bold_var.get(),
            "sub_style_text_color_rgb_str": self.master_app.sub_style_text_color_rgb_str_var.get(),
            "sub_style_text_opacity_percent": self.master_app.sub_style_text_opacity_percent_var.get(),
            "sub_style_background_mode": self.master_app.sub_style_background_mode_var.get(),
            "sub_style_bg_color_rgb_str": self.master_app.sub_style_bg_color_rgb_str_var.get(),
            "sub_style_bg_box_actual_opacity_percent": self.master_app.sub_style_bg_box_actual_opacity_percent_var.get(),
            "sub_style_outline_enabled": self.master_app.sub_style_outline_enabled_var.get(),
            "sub_style_outline_size": self.master_app.sub_style_outline_size_var.get(),
            "sub_style_outline_color_rgb_str": self.master_app.sub_style_outline_color_rgb_str_var.get(),
            "sub_style_outline_opacity_percent": self.master_app.sub_style_outline_opacity_percent_var.get(),
            "margin_v": self.master_app.sub_style_marginv_var.get(),
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(current_style_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Thành công", f"Đã xuất cài đặt style hiện tại ra file:\n{os.path.basename(file_path)}", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi Lưu File", f"Không thể lưu file style.\nLỗi: {e}", parent=self)

    # --- KẾT THÚC KHỐI HÀM MỚI ---

    def _save_settings_and_close(self): #
        logging.info("[SubtitleStyleSettingsWindow] Nút 'Lưu và Đóng' (Style) được nhấn.")
        if self._validate_and_save_settings(): #
            try:
                self.master_app.save_current_config() #
                logging.info("[SubtitleStyleSettingsWindow] Đã lưu config style.") #
            except Exception as e_save_cfg_style: #
                logging.error(f"[SubtitleStyleSettingsWindow] Lỗi lưu config: {e_save_cfg_style}", exc_info=True) #
                messagebox.showerror("Lỗi Lưu Config", f"Lỗi khi lưu cấu hình: {e_save_cfg_style}", parent=self) #
                return #
            self._on_close_window() #
        else:
            logging.warning("[SubtitleStyleSettingsWindow] Validation style thất bại, không lưu và không đóng.") #

    def _on_close_window(self): #
        logging.info("[SubtitleStyleSettingsWindow] Cửa sổ Style đang được đóng.") #
        if hasattr(self, 'grab_status') and self.grab_status() != "none": #
            try: self.grab_release() #
            except Exception: pass
        try: self.destroy() #
        except Exception: pass

