# -*- coding: utf-8 -*-
# File: ui/tabs/download_tab.py

import customtkinter as ctk
import os
import logging
import webbrowser
from tkinter import filedialog, messagebox

# Import các thành phần UI chung
from config.ui_constants import get_theme_colors
from ui.widgets.tooltip import Tooltip
from ui.widgets.menu_utils import textbox_right_click_menu

# Import các hàm tiện ích
from utils.helpers import get_default_downloads_folder, open_file_with_default_app
from config.constants import APP_NAME


class DownloadTab(ctk.CTkFrame):
    """
    Lớp quản lý toàn bộ giao diện và logic cho Tab Tải Xuống (Download).
    """

    def __init__(self, master, master_app):
        """
        Khởi tạo frame cho Tab Tải Xuống.

        Args:
            master (ctk.CTkFrame): Frame cha (main_content_frame từ SubtitleApp).
            master_app (SubtitleApp): Instance của ứng dụng chính (PiuApp).
        """
        super().__init__(master, fg_color="transparent")
        self.master_app = master_app
        self.logger = logging.getLogger(APP_NAME)

        # Khai báo các widget con của tab này (sẽ được gán trong _build_ui)
        self.download_url_text = None
        self.download_playlist_check = None
        self.optimize_mobile_checkbox = None
        self.disable_sheet_check_checkbox = None
        self.download_path_display_label = None
        self.download_rename_check = None
        self.download_rename_entry_frame = None
        self.download_rename_entry = None
        self.download_video_quality_menu = None
        self.download_audio_quality_menu = None
        self.auto_dub_checkbox = None
        self.download_auto_dub_config_frame = None
        self.auto_upload_dl_checkbox = None
        self.download_auto_upload_config_frame = None
        self.download_sound_check = None
        self.download_sound_button = None
        self.download_shutdown_check = None
        self.download_stop_on_error_check = None
        self.download_use_cookies_checkbox = None
        self.download_cookies_path_label = None
        self.download_cookies_button = None
        self.add_sheet_button = None
        self.all_button = None
        self.download_start_button = None
        self.download_stop_button = None
        self.open_download_folder_button = None
        self.download_queue_section = None
        self.piu_button_dl_ref = None
        self.key_button_dl_ref = None
        self.update_button_dl_ref = None
        self.clear_log_button_ref = None
        self.download_log_textbox = None
        self.download_progress_bar = None

        # Gọi hàm xây dựng UI (sẽ thêm hàm này ở bước sau)
        self._build_ui() 

        self.logger.info("DownloadTab đã được khởi tạo.")

    def _build_ui(self):
        """ 
        Tạo các thành phần UI cho chế độ xem 'Tải xuống'.
        (Đây là hàm _create_download_tab cũ, đã được đổi tên và sửa lỗi tham chiếu)
        """
        self.logger.debug("Đang tạo UI Chế độ xem Tải xuống (Theme-Aware)...")

        colors = get_theme_colors()
        panel_bg_color = colors["panel_bg"]
        card_bg_color = colors["card_bg"]
        log_textbox_bg_color = colors["log_textbox_bg"]
        danger_button_color = colors["danger_button"]
        danger_button_hover_color = colors["danger_button_hover"]
        special_action_button_color = colors["special_action_button"]
        special_action_hover_color = colors["special_action_hover"]

        main_frame_dl = ctk.CTkFrame(self, fg_color="transparent") # Sửa: master là self (DownloadTab)
        main_frame_dl.pack(fill="both", expand=True)

        main_frame_dl.grid_columnconfigure(0, weight=1, uniform="panelgroup")
        main_frame_dl.grid_columnconfigure(1, weight=2, uniform="panelgroup")
        main_frame_dl.grid_rowconfigure(0, weight=1)    

        left_panel_dl_container = ctk.CTkFrame(main_frame_dl, fg_color=panel_bg_color, corner_radius=12)
        left_panel_dl_container.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        left_panel_dl_container.pack_propagate(False)

        left_dl_scrollable_content = ctk.CTkScrollableFrame(
            left_panel_dl_container,
            fg_color="transparent"
        )
        left_dl_scrollable_content.pack(expand=True, fill="both", padx=0, pady=0)

        # === CỤM NÚT HÀNH ĐỘNG CHÍNH ===
        self._create_download_action_buttons_section(
            left_dl_scrollable_content,
            special_action_button_color,
            special_action_hover_color,
            danger_button_color,
            danger_button_hover_color
        )
        # === INPUT CONFIG SECTION ===
        self._create_download_input_config_section(left_dl_scrollable_content, card_bg_color)
        # === OUTPUT CONFIG SECTION ===
        self._create_download_output_config_section(left_dl_scrollable_content, card_bg_color)
        # === FORMAT & QUALITY SECTION ===
        self._create_download_format_quality_section(left_dl_scrollable_content, card_bg_color)
        # === AUTO OPTIONS SECTIONS ===
        self._create_download_auto_options_sections(left_dl_scrollable_content, card_bg_color)
        # === EXTRAS & COOKIES SECTION ===
        self._create_download_extras_cookies_sections(left_dl_scrollable_content, card_bg_color)
        # === RIGHT PANEL (Queue, Log, Progress) ===
        self._create_download_right_panel(
            main_frame_dl, panel_bg_color, card_bg_color, log_textbox_bg_color, 
            special_action_button_color, special_action_hover_color
        )

    def _create_download_action_buttons_section(self, parent_frame, special_action_button_color, special_action_hover_color, danger_button_color, danger_button_hover_color):
        """Tạo cụm nút hành động chính (Start, Stop, Sheet, All)."""
        action_buttons_main_frame_download = ctk.CTkFrame(parent_frame, fg_color="transparent")
        action_buttons_main_frame_download.pack(pady=10, padx=10, fill="x")

        btn_row_1_download = ctk.CTkFrame(action_buttons_main_frame_download, fg_color="transparent")
        btn_row_1_download.pack(fill="x", pady=(0, 5))

        self.add_sheet_button = ctk.CTkButton(
        btn_row_1_download,
        text="📑 Thêm từ Sheet",
        height=35, font=("Segoe UI", 13, "bold"),
        command=self.master_app.fetch_links_from_sheet, # Sửa: self.master_app.
        state="normal"
        )
        self.add_sheet_button.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.all_button = ctk.CTkButton(
        btn_row_1_download,
        text="🚀 ALL (D/S/D)",
        height=35, font=("Segoe UI", 13, "bold"),
        command=self.master_app.start_download_and_sub, # Sửa: self.master_app.
        fg_color=special_action_button_color,
        hover_color=special_action_hover_color
        )
        self.all_button.pack(side="left", expand=True, fill="x", padx=(3, 0))

        self.download_start_button = ctk.CTkButton(
        action_buttons_main_frame_download,
        text="✅ Bắt đầu Tải (Chỉ Tải)",
        height=45, font=("Segoe UI", 15, "bold"),
        command=self.master_app.start_download, # Sửa: self.master_app.
        )
        self.download_start_button.pack(fill="x", pady=5)

        btn_row_3_download_controls = ctk.CTkFrame(action_buttons_main_frame_download, fg_color="transparent")
        btn_row_3_download_controls.pack(fill="x", pady=(5, 0))
        btn_row_3_download_controls.grid_columnconfigure((0, 1), weight=1)

        self.download_stop_button = ctk.CTkButton(
        btn_row_3_download_controls,
        text="🛑 Dừng Tải",
        height=35, font=("Segoe UI", 13, "bold"),
        command=self.master_app.stop_download, # Sửa: self.master_app.
        fg_color=danger_button_color,
        hover_color=danger_button_hover_color,
        state=ctk.DISABLED,
        border_width=0
        )
        self.download_stop_button.grid(row=0, column=0, padx=(0, 2), pady=0, sticky="ew")

        self.open_download_folder_button = ctk.CTkButton(
            btn_row_3_download_controls,
            text="📂 Mở Thư Mục Tải",
            height=35, font=("Segoe UI", 13, "bold"),
            command=self.open_download_folder, # Hàm đã được chuyển sang DownloadTab
            border_width=0
        )
        self.open_download_folder_button.grid(row=0, column=1, padx=(3, 0), pady=0, sticky="ew")

    def _create_download_input_config_section(self, parent_frame, card_bg_color):
        """Tạo cụm nhập link và tùy chọn playlist/mobile/sheet."""
        input_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        input_config_frame.pack(fill="x", padx=10, pady=(0, 5))
        input_config_frame.grid_columnconfigure(0, weight=1)
        input_config_frame.grid_columnconfigure(1, weight=0)

        input_label = ctk.CTkLabel(input_config_frame, text="🖋 Nhập link", anchor='w', font=("Segoe UI", 12, "bold"))
        input_label.grid(row=0, column=0, padx=(10, 5), pady=(5, 0), sticky="w")

    # Widget 'self.download_playlist_check' thuộc về class này
    # Biến 'self.master_app.download_playlist_var' thuộc về app chính
        self.download_playlist_check = ctk.CTkCheckBox(
        input_config_frame, text="Tải cả playlist?", 
        variable=self.master_app.download_playlist_var, # Sửa: self.master_app.
        checkbox_height=18, checkbox_width=18, font=("Segoe UI", 12)
        )
        self.download_playlist_check.grid(row=0, column=1, padx=(5, 10), pady=(5, 0), sticky="e")

        self.download_url_text = ctk.CTkTextbox(
        input_config_frame, 
        height=100, wrap="word", font=("Consolas", 10), border_width=1
        )
        self.download_url_text.grid(row=1, column=0, columnspan=2, padx=10, pady=(2, 5), sticky="ew")
        self.download_url_text.bind("<Button-3>", textbox_right_click_menu)

        checkbox_frame_bottom = ctk.CTkFrame(input_config_frame, fg_color="transparent")
        checkbox_frame_bottom.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        checkbox_frame_bottom.grid_columnconfigure((0, 1), weight=1)

        # Sửa: Khởi tạo biến optimize_for_mobile_var nếu chưa có trên master_app
        if not hasattr(self.master_app, 'optimize_for_mobile_var'):
            self.master_app.optimize_for_mobile_var = ctk.BooleanVar(value=self.master_app.cfg.get("optimize_for_mobile", False))

        self.optimize_mobile_checkbox = ctk.CTkCheckBox(
        checkbox_frame_bottom, text="Tối ưu Mobile", 
        variable=self.master_app.optimize_for_mobile_var, # Sửa: self.master_app.
        onvalue=True, offvalue=False, checkbox_width=18, checkbox_height=18,
        font=("Segoe UI", 11), 
        command=self.master_app.save_current_config # Sửa: self.master_app.
        )
        self.optimize_mobile_checkbox.grid(row=0, column=0, sticky="w")

        self.disable_sheet_check_checkbox = ctk.CTkCheckBox(
        checkbox_frame_bottom, text="Tắt kiểm tra Sheet", 
        variable=self.master_app.disable_auto_sheet_check_var, # Sửa: self.master_app.
        checkbox_height=18, checkbox_width=18, font=("Segoe UI", 11), 
        command=self.master_app.save_current_config # Sửa: self.master_app.
        )
        self.disable_sheet_check_checkbox.grid(row=0, column=1, sticky="e")

    def _create_download_output_config_section(self, parent_frame, card_bg_color):
        """Tạo cụm chọn thư mục output và đổi tên."""
        output_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        output_config_frame.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(output_config_frame, text="📁 Đầu ra & Đổi tên", font=("Segoe UI", 12, "bold")).pack(pady=(5,2), padx=10, anchor="w")
        path_frame_inner = ctk.CTkFrame(output_config_frame, fg_color="transparent")
        path_frame_inner.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(path_frame_inner, text="Lưu tại:", width=50, anchor='w').pack(side="left")

        self.download_path_display_label = ctk.CTkLabel(
        path_frame_inner, 
        textvariable=self.master_app.download_path_var, # Sửa: self.master_app.
        anchor="w", wraplength=170, font=("Segoe UI", 10), 
        text_color=("gray30", "gray70")
        )
        self.download_path_display_label.pack(side="left", fill="x", expand=True, padx=(5, 5))
        ctk.CTkButton(
            path_frame_inner, text="Chọn", width=50, height=28, 
            command=self.select_download_path # Hàm đã được chuyển sang DownloadTab
        ).pack(side="left")

        display_path = self.master_app.download_path_var.get()
        self.download_path_display_label.configure(text=display_path if display_path else "Chưa chọn")
        self.master_app.download_path_var.trace_add("write", lambda *a: self.download_path_display_label.configure(text=self.master_app.download_path_var.get() or "Chưa chọn"))

        self.download_rename_check = ctk.CTkCheckBox(
            output_config_frame, text="Đổi tên hàng loạt?", 
            variable=self.master_app.download_rename_var, # Sửa: self.master_app.
            checkbox_height=18, checkbox_width=18, 
            command=self.toggle_download_rename_entry # Sửa: self.
        )
        self.download_rename_check.pack(anchor='w', padx=10, pady=(5,2))

        self.download_rename_entry_frame = ctk.CTkFrame(output_config_frame, fg_color="transparent")
        self.download_rename_entry_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(self.download_rename_entry_frame, text="Tên chung:", width=70, anchor='w').pack(side="left")

        self.download_rename_entry = ctk.CTkEntry(
            self.download_rename_entry_frame, 
            textvariable=self.master_app.download_rename_box_var, # Sửa: self.master_app.
            state="disabled", font=("Consolas", 10)
        )
        self.download_rename_entry.pack(side="left", fill="x", expand=True)
        # Gọi hàm toggle để khởi tạo trạng thái ban đầu
        self.master_app.after(50, self.toggle_download_rename_entry)

    def _create_download_format_quality_section(self, parent_frame, card_bg_color):
        """Tạo cụm chọn định dạng (video/mp3) và chất lượng."""
        format_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        format_config_frame.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(format_config_frame, text="⚙️ Định dạng & Chất lượng", font=("Segoe UI", 12, "bold")).pack(pady=(5,5), padx=10, anchor="w")

        mode_frame_inner = ctk.CTkFrame(format_config_frame, fg_color="transparent")
        mode_frame_inner.pack(fill="x", padx=10, pady=(5,5))
        modes = [("Video", "video"), ("MP3", "mp3"), ("Cả 2", "both")]
        mode_frame_inner.grid_columnconfigure((0, 1, 2), weight=1)
        for i, (text, value) in enumerate(modes):
         rb = ctk.CTkRadioButton(
             mode_frame_inner, text=text, 
             variable=self.master_app.download_mode_var, # Sửa: self.master_app.
             value=value, radiobutton_width=18, radiobutton_height=18
         )
         rb.grid(row=0, column=i, padx=5, pady=5, sticky="w")

        qual_frame_inner = ctk.CTkFrame(format_config_frame, fg_color="transparent")
        qual_frame_inner.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(qual_frame_inner, text="Video:", width=50, anchor='w').grid(row=0, column=0, pady=(0,5), sticky='w')
        video_options = ["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
        current_v_quality = self.master_app.download_video_quality_var.get()
        if current_v_quality not in video_options: 
            current_v_quality = "1080p"; self.master_app.download_video_quality_var.set(current_v_quality)

        self.download_video_quality_menu = ctk.CTkOptionMenu(
        qual_frame_inner, 
        variable=self.master_app.download_video_quality_var, # Sửa: self.master_app.
        values=video_options
        )
        self.download_video_quality_menu.grid(row=0, column=1, sticky='ew', padx=5)

        ctk.CTkLabel(qual_frame_inner, text="MP3:", width=50, anchor='w').grid(row=1, column=0, pady=(5,5), sticky='w')
        audio_options = ["best", "320k", "256k", "192k", "128k", "96k"]
        current_a_quality = self.master_app.download_audio_quality_var.get();
        if current_a_quality not in audio_options: 
            current_a_quality = "320k"; self.master_app.download_audio_quality_var.set(current_a_quality)

        self.download_audio_quality_menu = ctk.CTkOptionMenu(
        qual_frame_inner, 
        variable=self.master_app.download_audio_quality_var, # Sửa: self.master_app.
        values=audio_options
        )
        self.download_audio_quality_menu.grid(row=1, column=1, sticky='ew', padx=5)
        qual_frame_inner.grid_columnconfigure(1, weight=1)

    def _create_download_auto_options_sections(self, parent_frame, card_bg_color):
        """Tạo cụm tùy chọn tự động (Dub và Upload)."""
        self.download_auto_dub_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        self.download_auto_dub_config_frame.pack(fill="x", padx=10, pady=(0, 5)) 

        self.auto_dub_checkbox = ctk.CTkCheckBox(
        self.download_auto_dub_config_frame, 
        text="🎙 Tự Động Thuyết Minh (Sau Sub)",
        variable=self.master_app.download_auto_dub_after_sub_var, # Sửa: self.master_app.
        checkbox_height=18, checkbox_width=18,
        font=("Segoe UI", 13)
        )
        self.auto_dub_checkbox.pack(side="left", anchor="w", padx=10, pady=10)

        self.download_auto_upload_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        self.download_auto_upload_config_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.auto_upload_dl_checkbox = ctk.CTkCheckBox(
        self.download_auto_upload_config_frame,
        text="📤 Tự động Upload YT (Sau khi tải xong)",
        variable=self.master_app.auto_upload_after_download_var, # Sửa: self.master_app.
        checkbox_height=18, checkbox_width=18,
        font=("Segoe UI", 13)
        )
        self.auto_upload_dl_checkbox.pack(side="left", anchor="w", padx=10, pady=10)

    def _create_download_extras_cookies_sections(self, parent_frame, card_bg_color):
        """Tạo cụm tùy chọn khác (âm thanh, tắt máy) và cookies."""
        extras_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        extras_config_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(extras_config_frame, text="✨ Tùy chọn khác", font=("Segoe UI", 12, "bold")).pack(pady=(5,5), padx=10, anchor="w")
        options_grid = ctk.CTkFrame(extras_config_frame, fg_color="transparent")
        options_grid.pack(fill="x", padx=10, pady=(0, 10))

        self.download_sound_check = ctk.CTkCheckBox(
        options_grid, text="🔔", 
        variable=self.master_app.download_sound_var, # Sửa: self.master_app.
        checkbox_height=18, checkbox_width=18, 
        command=self.toggle_download_sound_button, width=20 # Sửa: self.
        )
        self.download_sound_check.grid(row=0, column=0, padx=(0, 0), sticky='w')

        self.download_sound_button = ctk.CTkButton(
            options_grid, text=" Chọn Âm", width=60, height=28, state="disabled", 
            command=self.select_download_sound # Hàm đã được chuyển sang DownloadTab
        )
        self.download_sound_button.grid(row=0, column=1, padx=(5, 5), sticky='w')

        self.download_shutdown_check = ctk.CTkCheckBox(
            options_grid, text="⏰ Tắt máy", 
            variable=self.master_app.download_shutdown_var, # Sửa: self.master_app.
            checkbox_height=18, checkbox_width=18
        )
        self.download_shutdown_check.grid(row=0, column=2, padx=(10, 0), sticky='w')

        self.download_stop_on_error_check = ctk.CTkCheckBox(
            options_grid, text="✋ Dừng khi lỗi", 
            variable=self.master_app.download_stop_on_error_var, # Sửa: self.master_app.
            checkbox_height=18, checkbox_width=18
        )
        self.download_stop_on_error_check.grid(row=0, column=3, padx=(10, 0), sticky='w')

        cookies_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        cookies_config_frame.pack(fill="x", padx=10, pady=(0, 10))
        cookies_config_frame.grid_columnconfigure(1, weight=1)

        self.download_use_cookies_checkbox = ctk.CTkCheckBox(
            cookies_config_frame,
            text="🍪 Sử dụng Cookies trình duyệt",
            variable=self.master_app.download_use_cookies_var, # Sửa: self.master_app.
            font=("Segoe UI", 12, "bold"),
            checkbox_height=18, checkbox_width=18,
            command=self.master_app._toggle_cookies_button_state # Sửa: self.master_app.
        )
        self.download_use_cookies_checkbox.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        self.download_cookies_path_label = ctk.CTkLabel(cookies_config_frame, text="(Chưa chọn file cookies.txt)", text_color="gray", font=("Segoe UI", 10), wraplength=350, padx=5)
        self.download_cookies_path_label.grid(row=1, column=0, columnspan=2, padx=(25, 5), pady=2, sticky="ew")

        self.download_cookies_button = ctk.CTkButton(
            cookies_config_frame, text="Chọn file Cookies...", width=120, 
            command=self._select_cookies_file # Hàm đã được chuyển sang DownloadTab
        )
        self.download_cookies_button.grid(row=1, column=2, padx=10, pady=2, sticky="e")

        # Gọi hàm trên master_app để khởi tạo trạng thái cookies button
        self.master_app.after(50, self.master_app._toggle_cookies_button_state)

    def _create_download_right_panel(self, main_frame, panel_bg_color, card_bg_color, log_textbox_bg_color, special_action_button_color, special_action_hover_color):
        """Tạo panel bên phải (Hàng chờ, Log, Progress bar)."""
        right_panel_dl = ctk.CTkFrame(main_frame, fg_color=panel_bg_color, corner_radius=12)
        right_panel_dl.grid(row=0, column=1, pady=0, sticky="nsew")

        right_panel_dl.grid_columnconfigure(0, weight=1)
        right_panel_dl.grid_rowconfigure(0, weight=0)
        right_panel_dl.grid_rowconfigure(1, weight=1)
        right_panel_dl.grid_rowconfigure(2, weight=0)

        self.download_queue_section = ctk.CTkScrollableFrame(right_panel_dl, label_text="📋 Hàng chờ (Download)", label_font=("Poppins", 14, "bold"), height=150)
        self.download_queue_section.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        log_section_frame = ctk.CTkFrame(right_panel_dl, fg_color="transparent")
        log_section_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 5))
        log_section_frame.grid_rowconfigure(1, weight=1)
        log_section_frame.grid_columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(log_section_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(log_header, text="📜 Log Tải Xuống:", font=("Poppins", 15, "bold")).pack(side="left", padx=(0,10))

        buttons_container_log_header = ctk.CTkFrame(log_header, fg_color=card_bg_color, corner_radius=6)
        buttons_container_log_header.pack(side="right", fill="x", expand=True, padx=(5,0))
        num_log_header_buttons = 4
        for i in range(num_log_header_buttons):
            buttons_container_log_header.grid_columnconfigure(i, weight=1)

        button_height_log = 28
        button_font_style_log = ("Poppins", 11)

        self.piu_button_dl_ref = ctk.CTkButton(
        buttons_container_log_header, text="🎬 Piu...",
        height=button_height_log, font=button_font_style_log,
        command=lambda: webbrowser.open("https://www.youtube.com/@PiuKeTruyen"),
        fg_color=special_action_button_color,
        hover_color=special_action_hover_color
        )
        self.piu_button_dl_ref.grid(row=0, column=0, padx=(0,2), pady=2, sticky="ew")
        Tooltip(self.piu_button_dl_ref, "Ủng hộ kênh Youtube 'Piu Kể Chuyện' nhé! ❤")

        self.key_button_dl_ref = ctk.CTkButton(
        buttons_container_log_header, text="🔑 Nhập Key",
        height=button_height_log, font=button_font_style_log,
        command=lambda: self.master_app.prompt_and_activate("🔑 Nhập Key Để Kích Hoạt :"), # Sửa: self.master_app.
        fg_color=("#29b369", "#009999"),
        hover_color=("#CC0000", "#CC0000"),
        text_color=("white", "white"),
        corner_radius=8
        )
        self.key_button_dl_ref.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        Tooltip(self.key_button_dl_ref, "Nhập key để kích hoạt bản quyền")

        self.update_button_dl_ref = ctk.CTkButton(
            buttons_container_log_header, text="🔔 Cập nhật",
            height=button_height_log, font=button_font_style_log,
            command=self.master_app.manual_check_update # Sửa: self.master_app.
        )
        self.update_button_dl_ref.grid(row=0, column=2, padx=2, pady=2, sticky="ew")

        self.clear_log_button_ref = ctk.CTkButton(
            buttons_container_log_header, text="Clear Log",
            height=button_height_log, font=button_font_style_log,
            command=self.clear_download_log # Hàm đã được chuyển sang DownloadTab
        )
        self.clear_log_button_ref.grid(row=0, column=3, padx=(2,0), pady=2, sticky="ew")

        self.download_log_textbox = ctk.CTkTextbox(
            log_section_frame, wrap="word", font=("Consolas", 12), 
            state="disabled", fg_color=log_textbox_bg_color, border_width=1
        )
        self.download_log_textbox.grid(row=1, column=0, sticky="nsew", padx=0, pady=(2,0))
        try:
            self.download_log_textbox.configure(state="normal")
            self.download_log_textbox.insert("1.0", self.master_app.download_log_placeholder) # Sửa: self.master_app.
            self.download_log_textbox.configure(state="disabled")
        except Exception as e:
            self.logger.error(f"Lỗi khi chèn placeholder vào download_log_textbox: {e}")

        self.download_progress_bar = ctk.CTkProgressBar(
        right_panel_dl,
        orientation="horizontal",
        height=15,
        progress_color=("#10B981", "#34D399"),
        fg_color=("#D4D8DB", "#4A4D50")
        )
        self.download_progress_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        self.download_progress_bar.set(0)        

# Dán vào cuối class DownloadTab trong file ui/tabs/download_tab.py

    def set_download_ui_state(self, downloading):
        """
        Bật/tắt các nút và thành phần điều khiển của tab Download.
        (ĐÃ ĐƯỢC REFACTOR VÀ CHUYỂN SANG DownloadTab)
        """
        self.logger.info(f"[UI Download] Đặt trạng thái, downloading={downloading}")
        self.master_app.is_downloading = downloading # Sửa: self.master_app.

        # Kiểm tra bản quyền từ master_app
        is_app_active = self.master_app._is_app_fully_activated() # Sửa: self.master_app.

        target_state_normal = "normal" if is_app_active and not downloading else "disabled"
        stop_button_target = "normal" if is_app_active and downloading else "disabled"
        unactivated_text_short = "🔒 Kích hoạt"

        # Các widget này là 'self.' vì chúng thuộc về DownloadTab
        widgets_to_toggle = [
            self.download_start_button, self.all_button, self.add_sheet_button,
            self.download_playlist_check, self.download_video_quality_menu,
            self.download_audio_quality_menu, self.download_sound_check,
            self.download_shutdown_check, self.download_stop_on_error_check,
            self.download_rename_check, self.download_url_text,
            self.optimize_mobile_checkbox, self.disable_sheet_check_checkbox,
            self.auto_dub_checkbox, self.auto_upload_dl_checkbox,
            self.download_use_cookies_checkbox
        ]

        for widget in widgets_to_toggle:
            if widget and widget.winfo_exists():
                try:
                    widget.configure(state=target_state_normal)
                except Exception: pass # Bỏ qua lỗi (ví dụ CTkTextbox)

        # Xử lý riêng cho các nút cần đổi text
        if not is_app_active:
            if self.download_start_button: self.download_start_button.configure(text="🔒 Kích hoạt (Tải)")
            if self.all_button: self.all_button.configure(text="🔒 Kích hoạt (ALL)")
            if self.add_sheet_button: self.add_sheet_button.configure(text="🔒 Kích hoạt (Sheet)")
        else:
            if self.download_start_button: self.download_start_button.configure(text="✅ Bắt đầu Tải (Chỉ Tải)")
            if self.all_button: self.all_button.configure(text="🚀 ALL (D/S/D)")
            if self.add_sheet_button: self.add_sheet_button.configure(text="📑 Thêm từ Sheet")

        if self.download_stop_button:
            self.download_stop_button.configure(state=stop_button_target)

        # Xử lý placeholder cho ô URL
        if self.download_url_text:
            current_text = self.download_url_text.get("1.0", "end-1c")
            placeholder = self.master_app.download_url_placeholder # Sửa: self.master_app.
            if not is_app_active:
                if current_text != placeholder:
                    self.download_url_text.delete("1.0", "end")
                    self.download_url_text.insert("1.0", placeholder)
            else:
                if current_text == placeholder:
                    self.download_url_text.delete("1.0", "end")

        # Gọi các hàm toggle để khởi tạo trạng thái ban đầu
        self.master_app.after(10, self.toggle_download_sound_button)
        self.master_app.after(20, self.toggle_download_rename_entry)
        self.master_app.after(30, self.master_app._toggle_cookies_button_state)

    def select_download_path(self):
        """ Mở dialog chọn thư mục lưu file tải về """
        initial_dir = self.master_app.download_path_var.get() or get_default_downloads_folder()
        path = filedialog.askdirectory(initialdir=initial_dir, parent=self.master_app)
        if path:
            self.master_app.download_path_var.set(path)
            self.logger.info(f"Đã chọn đường dẫn tải về: {path}")
        else:
            self.logger.info("Đã hủy chọn đường dẫn tải về.")

    def open_download_folder(self):
        """ Mở thư mục tải về hiện tại """
        current_path = self.master_app.download_path_var.get()
        if current_path and os.path.isdir(current_path):
            self.logger.info(f"Đang mở thư mục tải về: {current_path}")
            open_file_with_default_app(current_path)
        else:
            messagebox.showwarning("Lỗi", "Đường dẫn tải về không hợp lệ hoặc chưa chọn.", parent=self.master_app)
            self.logger.warning(f"Đường dẫn tải về không hợp lệ hoặc bị thiếu: {current_path}")

    def toggle_download_rename_entry(self):
        """Hiện/ẩn ô nhập tên chung khi checkbox 'Đổi tên hàng loạt' thay đổi."""
        if not hasattr(self, 'download_rename_entry') or not self.download_rename_entry:
            return
        
        if self.master_app.download_rename_var.get():
            # Hiện entry và cho phép nhập
            self.download_rename_entry_frame.pack(fill="x", padx=10, pady=(0, 10))
            self.download_rename_entry.configure(state="normal")
        else:
            # Ẩn entry
            self.download_rename_entry_frame.pack_forget()
            self.download_rename_entry.configure(state="disabled")

    def select_download_sound(self):
        """ Mở dialog chọn file âm thanh """
        initial_dir = os.path.dirname(self.master_app.download_sound_path_var.get()) if self.master_app.download_sound_path_var.get() else "."
        f = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("Audio files", "*.wav *.mp3")],
            title="Chọn file âm thanh thông báo",
            parent=self.master_app
        )
        if f and os.path.isfile(f):
             self.master_app.download_sound_path_var.set(f)
             self.logger.info(f"Đã chọn file âm thanh download: {f}")
             self.master_app.save_current_config()
        elif f:
             messagebox.showwarning("File không tồn tại", f"Đường dẫn file đã chọn không hợp lệ:\n{f}", parent=self.master_app)

    def _select_cookies_file(self):
        """Mở dialog để người dùng chọn file cookies.txt."""
        initial_dir = os.path.dirname(self.master_app.download_cookies_path_var.get()) if self.master_app.download_cookies_path_var.get() else get_default_downloads_folder()
        filepath = filedialog.askopenfilename(
            title="Chọn file cookies.txt",
            initialdir=initial_dir,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            parent=self.master_app
        )
        if filepath:
            self.master_app.download_cookies_path_var.set(filepath)
            self._update_cookies_label()  # Gọi từ DownloadTab
            self.master_app.save_current_config() # Lưu lại lựa chọn
    
    def _update_cookies_label(self):
        """Cập nhật label hiển thị đường dẫn file cookies"""
        lbl = getattr(self, 'download_cookies_path_label', None)
        if lbl and lbl.winfo_exists():
            SUCCESS_COLOR = ("#0B8457", "lightgreen")
            ERROR_COLOR = ("#B71C1C", "#FF8A80")
            WARNING_COLOR = ("#E65100", "#FFB74D")
            DEFAULT_COLOR = ("gray30", "gray70")
            path = self.master_app.download_cookies_path_var.get()
            if self.master_app.download_use_cookies_var.get():
                if path and os.path.exists(path):
                    lbl.configure(text=f"--Đã chọn: {os.path.basename(path)}", text_color=SUCCESS_COLOR)
                elif path:
                    lbl.configure(text=f"Lỗi: File '{os.path.basename(path)}' không tồn tại!", text_color=ERROR_COLOR)
                else:
                    lbl.configure(text="(Vui lòng chọn file cookies.txt)", text_color=WARNING_COLOR)
            else:
                lbl.configure(text="(Tính năng cookies đang tắt)", text_color=DEFAULT_COLOR)

    def clear_download_log(self):
        """ Xóa nội dung trong ô log download """
        log_widget = getattr(self, 'download_log_textbox', None)
        if log_widget and log_widget.winfo_exists():
            try:
                log_widget.configure(state="normal")
                log_widget.delete("1.0", "end")
                # === THÊM ĐOẠN NÀY ===
                placeholder_to_insert = getattr(self.master_app, 'download_log_placeholder', "[Log và trạng thái tải xuống sẽ hiển thị ở đây... Cám ơn mọi người đã sử dụng phần mềm Piu.]")
                log_widget.insert("1.0", placeholder_to_insert)
                # === KẾT THÚC ===
                log_widget.configure(state="disabled")
                self.logger.info("Người dùng đã xóa log download (và placeholder đã được đặt lại).")
            except Exception as e:
                self.logger.error(f"Lỗi khi xóa log download: {e}")

    def toggle_download_sound_button(self):
        """Bật/tắt nút âm thanh khi tải"""
        btn = getattr(self, 'download_sound_button', None)
        if not (btn and btn.winfo_exists()):
            return
        try:
            is_active = self.master_app._is_app_fully_activated()
            is_downloading = bool(getattr(self.master_app, 'is_downloading', False))
            sound_enabled = bool(self.master_app.download_sound_var.get()) if (
                hasattr(self.master_app, 'download_sound_var') and self.master_app.download_sound_var
            ) else False
            can_enable = is_active and (not is_downloading) and sound_enabled
            target_state = "normal" if can_enable else "disabled"
            if str(btn.cget("state")) != target_state:
                btn.configure(state=target_state)
        except Exception as e:
            self.logger.error(f"Lỗi bật/tắt nút âm thanh download: {e}")

    def _reenable_fetch_button(self):
        """Bật lại nút 'Thêm từ Sheet' sau khi xử lý xong"""
        if hasattr(self, 'add_sheet_button') and self.add_sheet_button and self.add_sheet_button.winfo_exists():
            try:
                self.add_sheet_button.configure(state="normal", text="📑 Thêm từ Sheet")
            except Exception as e:
                self.logger.warning(f"Không thể bật lại nút Thêm từ Sheet: {e}")
        else:
            self.logger.warning("Không thể bật lại nút 'Thêm từ Sheet': Không tìm thấy tham chiếu hoặc nút đã bị hủy.")

    def update_download_progress(self, value):
        """Cập nhật progress bar download (thread-safe) - Giá trị từ 0 đến 100"""
        self.logger.debug(f"DEBUG CẬP NHẬT PROGRESS: Nhận giá trị = {value}")
        if hasattr(self, 'download_progress_bar') and self.download_progress_bar and self.download_progress_bar.winfo_exists():
            def _update():
                try:
                    value_float = float(value) / 100.0
                    value_clamped = max(0.0, min(1.0, value_float))
                    self.download_progress_bar.set(value_clamped)
                except Exception as e:
                    self.logger.warning(f"Lỗi cập nhật progress bar download: {e}")
            self.master_app.after(0, _update)

    def set_download_progress_indeterminate(self, start=True):
        """Đặt progress bar download ở chế độ indeterminate (mô phỏng)"""
        if hasattr(self, 'download_progress_bar') and self.download_progress_bar and self.download_progress_bar.winfo_exists():
            if start:
                self.logger.debug("Mô phỏng progress indeterminate (đặt về 0)")
            else:
                self.logger.debug("Đặt progress bar trở lại chế độ determinate")

    def log_download(self, message):
        """Ghi log vào ô Download Log (thread-safe)"""
        log_widget = getattr(self, 'download_log_textbox', None)
        if log_widget and log_widget.winfo_exists():
            if not message.endswith('\n'):
                message += '\n'

            def _insert_task_with_state_change():
                try:
                    log_widget.configure(state="normal")

                    current_content_full = log_widget.get("1.0", "end-1c")
                    placeholder_to_check = getattr(self.master_app, 'download_log_placeholder', "")

                    if placeholder_to_check and current_content_full == placeholder_to_check:
                        log_widget.delete("1.0", "end")

                    log_widget.insert("end", message)
                    log_widget.see("end")
                    log_widget.configure(state="disabled")
                except Exception as e:
                    self.logger.error(f"Lỗi trong quá trình chèn/thay đổi trạng thái log: {e}")

            self.master_app.after(0, _insert_task_with_state_change)
        else:
            self.logger.info(f"[Dự phòng Log Download] {message.strip()}")
