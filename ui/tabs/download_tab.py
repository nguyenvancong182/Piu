# -*- coding: utf-8 -*-
# File: ui/tabs/download_tab.py

import customtkinter as ctk
import os
import logging
import webbrowser
import threading
import json
import re
import sys
from tkinter import filedialog, messagebox
from pathlib import Path

# Import các thành phần UI chung
from config.ui_constants import get_theme_colors
from ui.widgets.tooltip import Tooltip
from ui.widgets.menu_utils import textbox_right_click_menu

# Import các hàm tiện ích
from utils.helpers import get_default_downloads_folder, open_file_with_default_app, get_identifier_from_source, play_sound_async, create_safe_filename
from utils.ffmpeg_utils import find_ffmpeg
from config.constants import APP_NAME
from config.settings import save_config
from services.google_api_service import get_google_api_service
from services.download_service import stream_process_output as ytdlp_stream_output
from googleapiclient.errors import HttpError
from contextlib import contextmanager
from utils.keep_awake import KeepAwakeManager
import time

# Import YTDLP_PATH từ Piu.py (hoặc get_ytdlp_path)
try:
    from config.constants import get_ytdlp_path
    _get_ytdlp_path = get_ytdlp_path
except ImportError:
    import shutil
    def _get_ytdlp_path():
        cmd = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
        return shutil.which(cmd) or cmd

# Helper để lấy YTDLP_PATH
def _get_ytdlp_path_safe():
    """Lấy đường dẫn yt-dlp an toàn"""
    try:
        return _get_ytdlp_path()
    except Exception:
        return "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"

# Helper để kiểm tra PLAYSOUND_AVAILABLE từ master_app
def _get_playsound_available(master_app):
    """Lấy trạng thái PLAYSOUND_AVAILABLE từ master_app"""
    return getattr(master_app, 'PLAYSOUND_AVAILABLE', False)

# Helper để sử dụng keep_awake từ master_app
@contextmanager
def keep_awake_helper(master_app, reason: str = "Processing"):
    """Helper context manager cho keep_awake sử dụng master_app's keep_awake"""
    if hasattr(master_app, 'keep_awake'):
        # Gọi keep_awake từ master_app nếu có
        with master_app.keep_awake(reason):
            yield
    else:
        # Fallback: tạo instance riêng nếu không có trong master_app
        keeper = KeepAwakeManager()
        tk = keeper.acquire(reason)
        try:
            yield
        finally:
            keeper.release(tk)


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

        # --------------------
        # Biến cấu hình của ĐOWNLOAD
        # --------------------
        
        # --- Biến & Cấu hình Cụ thể cho Tải xuống ---
        self.download_playlist_var = ctk.BooleanVar(value=self.master_app.cfg.get("download_playlist", False))
        self.download_path_var = ctk.StringVar(value=self.master_app.cfg.get("download_path", get_default_downloads_folder()))
        self.download_mode_var = ctk.StringVar(value=self.master_app.cfg.get("download_mode", "video"))
        self.download_video_quality_var = ctk.StringVar(value=self.master_app.cfg.get("download_video_quality", "1080p"))
        self.download_audio_quality_var = ctk.StringVar(value=self.master_app.cfg.get("download_audio_quality", "320k"))
        self.download_sound_var = ctk.BooleanVar(value=self.master_app.cfg.get("download_sound_enabled", False))
        self.download_sound_path_var = ctk.StringVar(value=self.master_app.cfg.get("download_sound_path", ""))
        self.download_shutdown_var = ctk.BooleanVar(value=self.master_app.cfg.get("download_shutdown_enabled", False))
        self.download_rename_var = ctk.BooleanVar(value=self.master_app.cfg.get("download_rename_enabled", False))
        self.download_rename_box_var = ctk.StringVar(value=self.master_app.cfg.get("download_rename_base_name", ""))
        self.download_stop_on_error_var = ctk.BooleanVar(value=self.master_app.cfg.get("download_stop_on_error", False))
        self.download_auto_dub_after_sub_var = ctk.BooleanVar(value=self.master_app.cfg.get("download_auto_dub_after_sub", False))
        self.auto_upload_after_download_var = ctk.BooleanVar(value=self.master_app.cfg.get("auto_upload_after_download", False))
        self.download_use_cookies_var = ctk.BooleanVar(value=self.master_app.cfg.get("download_use_cookies", False))
        self.download_cookies_path_var = ctk.StringVar(value=self.master_app.cfg.get("download_cookies_path", ""))

        # --- Biến trạng thái cho Download ---
        self.download_urls_list = []  # Lưu danh sách URL chờ
        self.current_download_url = None  # Lưu URL đang tải
        self.download_thread = None
        self.download_retry_counts = {}
        self.globally_completed_urls = set()

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
        command=self.fetch_links_from_sheet, # Sửa: gọi hàm trong DownloadTab, không phải master_app
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
    # Biến 'self.download_playlist_var' thuộc về DownloadTab
        self.download_playlist_check = ctk.CTkCheckBox(
        input_config_frame, text="Tải cả playlist?", 
        variable=self.download_playlist_var,
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
        textvariable=self.download_path_var,
        anchor="w", wraplength=170, font=("Segoe UI", 10), 
        text_color=("gray30", "gray70")
        )
        self.download_path_display_label.pack(side="left", fill="x", expand=True, padx=(5, 5))
        ctk.CTkButton(
            path_frame_inner, text="Chọn", width=50, height=28, 
            command=self.select_download_path # Hàm đã được chuyển sang DownloadTab
        ).pack(side="left")

        display_path = self.download_path_var.get()
        self.download_path_display_label.configure(text=display_path if display_path else "Chưa chọn")
        self.download_path_var.trace_add("write", lambda *a: self.download_path_display_label.configure(text=self.download_path_var.get() or "Chưa chọn"))

        self.download_rename_check = ctk.CTkCheckBox(
            output_config_frame, text="Đổi tên hàng loạt?", 
            variable=self.download_rename_var,
            checkbox_height=18, checkbox_width=18, 
            command=self.toggle_download_rename_entry # Sửa: self.
        )
        self.download_rename_check.pack(anchor='w', padx=10, pady=(5,2))

        self.download_rename_entry_frame = ctk.CTkFrame(output_config_frame, fg_color="transparent")
        self.download_rename_entry_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(self.download_rename_entry_frame, text="Tên chung:", width=70, anchor='w').pack(side="left")

        self.download_rename_entry = ctk.CTkEntry(
            self.download_rename_entry_frame, 
            textvariable=self.download_rename_box_var,
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
             variable=self.download_mode_var,
             value=value, radiobutton_width=18, radiobutton_height=18
         )
         rb.grid(row=0, column=i, padx=5, pady=5, sticky="w")

        qual_frame_inner = ctk.CTkFrame(format_config_frame, fg_color="transparent")
        qual_frame_inner.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(qual_frame_inner, text="Video:", width=50, anchor='w').grid(row=0, column=0, pady=(0,5), sticky='w')
        video_options = ["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
        current_v_quality = self.download_video_quality_var.get()
        if current_v_quality not in video_options: 
            current_v_quality = "1080p"; self.download_video_quality_var.set(current_v_quality)

        self.download_video_quality_menu = ctk.CTkOptionMenu(
        qual_frame_inner, 
        variable=self.download_video_quality_var,
        values=video_options
        )
        self.download_video_quality_menu.grid(row=0, column=1, sticky='ew', padx=5)

        ctk.CTkLabel(qual_frame_inner, text="MP3:", width=50, anchor='w').grid(row=1, column=0, pady=(5,5), sticky='w')
        audio_options = ["best", "320k", "256k", "192k", "128k", "96k"]
        current_a_quality = self.download_audio_quality_var.get();
        if current_a_quality not in audio_options: 
            current_a_quality = "320k"; self.download_audio_quality_var.set(current_a_quality)

        self.download_audio_quality_menu = ctk.CTkOptionMenu(
        qual_frame_inner, 
        variable=self.download_audio_quality_var,
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
        variable=self.download_auto_dub_after_sub_var,
        checkbox_height=18, checkbox_width=18,
        font=("Segoe UI", 13)
        )
        self.auto_dub_checkbox.pack(side="left", anchor="w", padx=10, pady=10)

        self.download_auto_upload_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        self.download_auto_upload_config_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.auto_upload_dl_checkbox = ctk.CTkCheckBox(
        self.download_auto_upload_config_frame,
        text="📤 Tự động Upload YT (Sau khi tải xong)",
        variable=self.auto_upload_after_download_var,
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
        variable=self.download_sound_var,
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
            variable=self.download_shutdown_var,
            checkbox_height=18, checkbox_width=18
        )
        self.download_shutdown_check.grid(row=0, column=2, padx=(10, 0), sticky='w')

        self.download_stop_on_error_check = ctk.CTkCheckBox(
            options_grid, text="✋ Dừng khi lỗi", 
            variable=self.download_stop_on_error_var,
            checkbox_height=18, checkbox_width=18
        )
        self.download_stop_on_error_check.grid(row=0, column=3, padx=(10, 0), sticky='w')

        cookies_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        cookies_config_frame.pack(fill="x", padx=10, pady=(0, 10))
        cookies_config_frame.grid_columnconfigure(1, weight=1)

        self.download_use_cookies_checkbox = ctk.CTkCheckBox(
            cookies_config_frame,
            text="🍪 Sử dụng Cookies trình duyệt",
            variable=self.download_use_cookies_var,
            font=("Segoe UI", 12, "bold"),
            checkbox_height=18, checkbox_width=18,
            command=self._toggle_cookies_button_state
        )
        self.download_use_cookies_checkbox.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        self.download_cookies_path_label = ctk.CTkLabel(cookies_config_frame, text="(Chưa chọn file cookies.txt)", text_color="gray", font=("Segoe UI", 10), wraplength=350, padx=5)
        self.download_cookies_path_label.grid(row=1, column=0, columnspan=2, padx=(25, 5), pady=2, sticky="ew")

        self.download_cookies_button = ctk.CTkButton(
            cookies_config_frame, text="Chọn file Cookies...", width=120, 
            command=self._select_cookies_file # Hàm đã được chuyển sang DownloadTab
        )
        self.download_cookies_button.grid(row=1, column=2, padx=10, pady=2, sticky="e")

        # Gọi hàm để khởi tạo trạng thái cookies button
        self.master_app.after(50, self._toggle_cookies_button_state)

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
        self.master_app.after(30, self._toggle_cookies_button_state)

    def select_download_path(self):
        """ Mở dialog chọn thư mục lưu file tải về """
        initial_dir = self.download_path_var.get() or get_default_downloads_folder()
        path = filedialog.askdirectory(initialdir=initial_dir, parent=self.master_app)
        if path:
            self.download_path_var.set(path)
            self.logger.info(f"Đã chọn đường dẫn tải về: {path}")
        else:
            self.logger.info("Đã hủy chọn đường dẫn tải về.")

    def open_download_folder(self):
        """ Mở thư mục tải về hiện tại """
        current_path = self.download_path_var.get()
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
        
        if self.download_rename_var.get():
            # Hiện entry và cho phép nhập
            self.download_rename_entry_frame.pack(fill="x", padx=10, pady=(0, 10))
            self.download_rename_entry.configure(state="normal")
        else:
            # Ẩn entry
            self.download_rename_entry_frame.pack_forget()
            self.download_rename_entry.configure(state="disabled")

    def select_download_sound(self):
        """ Mở dialog chọn file âm thanh """
        initial_dir = os.path.dirname(self.download_sound_path_var.get()) if self.download_sound_path_var.get() else "."
        f = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("Audio files", "*.wav *.mp3")],
            title="Chọn file âm thanh thông báo",
            parent=self.master_app
        )
        if f and os.path.isfile(f):
             self.download_sound_path_var.set(f)
             self.logger.info(f"Đã chọn file âm thanh download: {f}")
             self.master_app.save_current_config()
        elif f:
             messagebox.showwarning("File không tồn tại", f"Đường dẫn file đã chọn không hợp lệ:\n{f}", parent=self.master_app)

    def _select_cookies_file(self):
        """Mở dialog để người dùng chọn file cookies.txt."""
        initial_dir = os.path.dirname(self.download_cookies_path_var.get()) if self.download_cookies_path_var.get() else get_default_downloads_folder()
        filepath = filedialog.askopenfilename(
            title="Chọn file cookies.txt",
            initialdir=initial_dir,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            parent=self.master_app
        )
        if filepath:
            self.download_cookies_path_var.set(filepath)
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
            path = self.download_cookies_path_var.get()
            if self.download_use_cookies_var.get():
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
            sound_enabled = bool(self.download_sound_var.get()) if (
                hasattr(self, 'download_sound_var') and self.download_sound_var
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

    def start_download(self):
        """
        Lấy thông tin từ UI (ưu tiên self.download_urls_list, sau đó đến textbox),
        kiểm tra, reset retry counts, và bắt đầu quá trình tải xuống trong một thread mới.
        Chỉ thực hiện tải, không tự động sub.
        """
        import time
        import threading
        
        self.logger.info("--- Nhấn nút Bắt đầu Tải (Chỉ Tải) ---")

        # --- Bước 1: Reset bộ đếm lỗi và xác định danh sách URL cần xử lý ---
        self.download_retry_counts.clear() 
        self.logger.info("Đã xóa self.download_retry_counts cho lượt tải mới.")
        # self.globally_completed_urls KHÔNG được clear ở đây để nhớ các link đã hoàn thành trong cả session.

        urls_to_process_initial = [] # Danh sách URL ban đầu để truyền cho config (chủ yếu để log)
        source_of_urls = ""

        if hasattr(self, 'download_urls_list') and self.download_urls_list:
            source_of_urls = "hàng chờ hiện tại (self.download_urls_list)"
            self.logger.info(f"Sẽ sử dụng {len(self.download_urls_list)} link từ {source_of_urls}.")
            # urls_to_process_initial sẽ được lấy từ self.download_urls_list ở dưới nếu cần
        elif hasattr(self, 'download_url_text') and self.download_url_text:
            # Ưu tiên 2: Nếu self.download_urls_list rỗng, đọc từ textbox
            urls_text_from_box = self.download_url_text.get("1.0", "end-1c").strip()
            if urls_text_from_box:
                source_of_urls = "ô nhập liệu textbox"
                self.logger.info(f"Hàng chờ (self.download_urls_list) rỗng. Đọc link từ {source_of_urls}.")
                
                temp_urls_from_box = []
                seen_urls_in_box = set()
                for line in urls_text_from_box.splitlines():
                    stripped_url = line.strip()
                    if stripped_url and stripped_url.startswith(('http://', 'https://')):
                        if stripped_url not in seen_urls_in_box:
                            temp_urls_from_box.append(stripped_url)
                            seen_urls_in_box.add(stripped_url)
                    elif stripped_url:
                         self.logger.warning(f"Bỏ qua URL không hợp lệ từ textbox: {stripped_url}")
                
                if temp_urls_from_box:
                    # Cập nhật self.download_urls_list bằng danh sách mới từ textbox
                    self.download_urls_list = list(temp_urls_from_box) 
                    self.logger.info(f"Đã cập nhật self.download_urls_list với {len(self.download_urls_list)} link từ {source_of_urls}.")
                else:
                    messagebox.showwarning("Link không hợp lệ", f"Không tìm thấy link hợp lệ nào trong {source_of_urls}.", parent=self.master_app)
                    return
            else: # Cả self.download_urls_list và textbox đều rỗng
                messagebox.showwarning("Thiếu link", "Vui lòng nhập link vào ô hoặc thêm từ Google Sheet.\nHàng chờ hiện tại cũng đang trống.", parent=self.master_app)
                return
        else: # Lỗi cấu trúc app
            messagebox.showerror("Lỗi Giao Diện", "Không tìm thấy nguồn nhập link (textbox hoặc hàng chờ).", parent=self.master_app)
            return

        # Sau khi xác định nguồn, urls_to_process_initial là bản sao của self.download_urls_list hiện tại
        if not self.download_urls_list: 
            messagebox.showwarning("Hàng chờ trống", f"Không có link nào để xử lý từ {source_of_urls}.", parent=self.master_app)
            return
        urls_to_process_initial = list(self.download_urls_list) # Để log số lượng ban đầu

        # --- Bước 2: Kiểm tra các tùy chọn khác ---
        download_path = self.download_path_var.get()
        if not download_path:
             messagebox.showerror("Lỗi Đường Dẫn", "Vui lòng chọn thư mục lưu tải về hợp lệ.", parent=self.master_app)
             return
        if self.download_rename_var.get() and not self.download_rename_box_var.get().strip():
             messagebox.showwarning("Thiếu tên file", "Vui lòng nhập tên chung khi chọn đổi tên hàng loạt!", parent=self.master_app)
             return
        sound_file_path = self.download_sound_path_var.get()
        if self.download_sound_var.get() and (not sound_file_path or not os.path.isfile(sound_file_path)):
            messagebox.showwarning("Thiếu file âm thanh", "Vui lòng chọn file âm thanh hợp lệ hoặc bỏ check 'Phát nhạc'.", parent=self.master_app)
            return

        # --- Bước 3: Chuẩn bị config cho thread ---
        config = {
            # "urls": urls_to_process_initial, # Không cần truyền list URL vào config nữa
            "mode": self.download_mode_var.get(),
            "folder": download_path,
            "v_quality": self.download_video_quality_var.get().replace("p", ""),
            "a_quality": self.download_audio_quality_var.get().replace("k", ""),
            "rename_all": self.download_rename_var.get(),
            "base_name": self.download_rename_box_var.get().strip(),
            "do_sound": self.download_sound_var.get(),
            "sound_file": sound_file_path,
            "do_shutdown": self.download_shutdown_var.get(),
            "stop_on_error": self.download_stop_on_error_var.get(),
            "download_playlist": self.download_playlist_var.get(),
            "auto_sub_after_download": False, # hoặc True
            "use_cookies": self.download_use_cookies_var.get(),
            "cookies_file": self.download_cookies_path_var.get()
        }
        self.logger.info(f"Config tải (CHỈ TẢI) đã chuẩn bị. Số link ban đầu trong hàng chờ: {len(urls_to_process_initial)} từ {source_of_urls}.")
        
        # --- Bước 4: Chuẩn bị giao diện và trạng thái ---
        self.current_download_url = None 
        self.update_download_queue_display() 

        # Xóa log download sử dụng method của DownloadTab
        try:
            self.clear_download_log()
        except Exception as e:
            self.logger.error(f"Lỗi khi xóa log download: {e}")

        self.master_app.stop_event.clear()
        self.set_download_ui_state(downloading=True)
        self.update_download_progress(0)

        self.log_download(f"🚀 Bắt đầu quá trình CHỈ TẢI (Nguồn: {source_of_urls})...")
        self.log_download(f"   - Số link hiện có trong hàng chờ: {len(self.download_urls_list)}")
        self.log_download(f"   - Chế độ: {config['mode']}")
        self.log_download(f"   - Lưu tại: {config['folder']}")

        # --- Bước 5: Lưu cài đặt hiện tại và ghi nhận yêu cầu tắt máy ---
        self.master_app.save_current_config() 
        self.master_app.shutdown_requested_by_task = self.download_shutdown_var.get()
        self.logger.info(f"Cấu hình UI đã lưu. Yêu cầu tắt máy bởi tác vụ: {self.master_app.shutdown_requested_by_task}")

        self.master_app.start_time = time.time() 
        self.master_app.update_time_realtime() 

        # --- Bước 6: Start download thread ---
        try:
            if self.download_thread and self.download_thread.is_alive():
                 self.logger.warning("Thread tải đang chạy!")
                 messagebox.showwarning("Đang xử lý", "Quá trình tải khác đang chạy, vui lòng đợi.", parent=self.master_app)
                 self.set_download_ui_state(downloading=True) 
                 return

            self.logger.info(f"CHUẨN BỊ TẠO THREAD (start_download): self.download_urls_list lúc này = {self.download_urls_list}")
            # Truyền config vào run_download
            self.download_thread = threading.Thread(target=self.run_download, args=(config,), daemon=True, name="DownloadWorker")
            self.download_thread.start()
            self.logger.info("Đã bắt đầu thread tải.")
        except Exception as e:
            self.logger.error(f"Lỗi bắt đầu thread tải: {e}", exc_info=True)
            messagebox.showerror("Lỗi", f"Không thể bắt đầu quá trình tải:\n{e}", parent=self.master_app)
            self.set_download_ui_state(downloading=False)

    def stop_download(self):
        """ Gửi tín hiệu dừng đến thread tải và cố gắng dừng tiến trình con.
            MODIFIED: Sẽ KHÔNG xóa URL đang tải bị dừng khỏi self.download_urls_list.
        """
        import subprocess
        
        self.logger.warning(">>> Yêu cầu Dừng Tải từ Nút của Người dùng <<<")

        is_running = self.download_thread and self.download_thread.is_alive()

        if is_running:
            self.log_download("\n🛑 Đang yêu cầu dừng quá trình tải...")
            self.master_app.stop_event.set()

            url_that_was_being_processed = self.current_download_url 

            self.master_app.is_downloading = False
            self.logger.info(f"[StopDownload] Đã đặt self.master_app.is_downloading = False.")

            if self.master_app.shutdown_requested_by_task: # Từ lần sửa lỗi trước
                self.logger.info(f"[StopDownload] Người dùng dừng tải, hủy yêu cầu tắt máy cho tác vụ này.")
                self.master_app.shutdown_requested_by_task = False

            # --- THAY ĐỔI Ở ĐÂY: KHÔNG XÓA URL KHỎI HÀNG CHỜ ---
            if url_that_was_being_processed:
                self.logger.info(f"[StopDownload] URL đang xử lý ('{url_that_was_being_processed[:60] if url_that_was_being_processed else 'None'}') sẽ được giữ lại trong hàng chờ theo yêu cầu.")
            # Các dòng code xóa "url_that_was_being_processed" khỏi "self.download_urls_list"
            # và "self.download_retry_counts" đã được BỎ ĐI hoặc COMMENT LẠI.
            # --- KẾT THÚC THAY ĐỔI ---

            self.current_download_url = None # Vẫn quan trọng để reset UI slot "ĐANG TẢI"

            proc = self.master_app.current_process
            if proc and proc.poll() is None:
                self.log_download("   -> Đang cố gắng dừng tiến trình con (yt-dlp/ffmpeg)...")
                try:
                    proc.terminate()
                    proc.wait(timeout=1.5)
                    self.log_download("   -> Tiến trình con đã dừng (terminate/wait).")
                except subprocess.TimeoutExpired:
                    self.log_download("   -> Tiến trình con không phản hồi, buộc dừng (kill)...")
                    try:
                        proc.kill()
                        self.log_download("   -> Đã buộc dừng (kill) tiến trình con.")
                    except Exception as kill_err:
                        self.log_download(f"   -> Lỗi khi buộc dừng (kill): {kill_err}")
                except Exception as e:
                    self.log_download(f"   -> Lỗi khi dừng tiến trình con: {e}")
                    if proc.poll() is None:
                        try:
                            proc.kill()
                            self.log_download("   -> Đã buộc dừng (kill) sau lỗi.")
                        except Exception as kill_err_B:
                            self.log_download(f"   -> Lỗi khi buộc dừng (kill) lần 2: {kill_err_B}")
            else:
                self.log_download("   -> Không tìm thấy tiến trình con đang chạy để dừng trực tiếp.")
            self.master_app.current_process = None

            self.master_app.after(0, lambda: self.set_download_ui_state(downloading=False))
            self.master_app.after(10, self.update_download_queue_display) 
            self.master_app.after(20, lambda: self.update_download_progress(0))
        else:
            self.log_download("\nℹ️ Không có tiến trình tải nào đang chạy để dừng.")
            self.set_download_ui_state(downloading=False)
            self.update_download_queue_display()

    def _toggle_cookies_button_state(self):
        """Bật/tắt nút chọn file cookies"""
        btn = getattr(self, 'download_cookies_button', None)
        if btn and btn.winfo_exists():
            new_state = "normal" if self.download_use_cookies_var.get() else "disabled"
            btn.configure(state=new_state)
        # Gọi hàm update label
        self._update_cookies_label()

    def update_download_queue_display(self):
        """ Cập nhật nội dung hiển thị trong CTkScrollableFrame của hàng chờ download (Thêm nút Lên/Xuống/Xóa). """
        queue_widget = getattr(self, 'download_queue_section', None)
        if not queue_widget or not hasattr(queue_widget, 'winfo_exists') or not queue_widget.winfo_exists():
            return

        for widget in queue_widget.winfo_children():
            widget.destroy()

        current_url = getattr(self, 'current_download_url', None)
        all_urls_in_list = getattr(self, 'download_urls_list', [])
        
        waiting_urls_only = []
        if all_urls_in_list:
            if current_url:
                temp_waiting_list = []
                found_current_in_list = False
                for u_in_all in all_urls_in_list:
                    if u_in_all == current_url and not found_current_in_list:
                        found_current_in_list = True 
                        continue 
                    temp_waiting_list.append(u_in_all)
                
                if not found_current_in_list and current_url is not None:
                     waiting_urls_only = list(all_urls_in_list)
                else:
                     waiting_urls_only = temp_waiting_list
            else: 
                waiting_urls_only = list(all_urls_in_list)
        
        queue_len_display = len(waiting_urls_only)

        if current_url:
            frame = ctk.CTkFrame(queue_widget, fg_color="#007bff", corner_radius=5)
            frame.pack(fill="x", pady=(2, 3), padx=2)
            display_url_current = current_url if len(current_url) < 80 else current_url[:77] + "..."
            label_text = f"▶️ ĐANG TẢI:\n   {display_url_current}"
            ctk.CTkLabel(frame, text=label_text, font=("Segoe UI", 10, "bold"), justify="left", anchor='w', text_color="white").pack(side="left", padx=5, pady=3)

        if not waiting_urls_only and not current_url:
            ctk.CTkLabel(queue_widget, text="[Hàng chờ download trống]", font=("Segoe UI", 11), text_color="gray").pack(anchor="center", pady=20)
        elif not waiting_urls_only and current_url:
            ctk.CTkLabel(queue_widget, text="[Đang xử lý link cuối cùng...]", font=("Segoe UI", 10, "italic"), text_color="gray").pack(anchor="center", pady=5)
        elif waiting_urls_only:
            for i, url_in_waiting_list in enumerate(waiting_urls_only):
                item_frame = ctk.CTkFrame(queue_widget, fg_color="transparent")
                item_frame.pack(fill="x", padx=2, pady=(1,2))

                display_url_waiting = url_in_waiting_list
                retry_count_for_this_url = self.download_retry_counts.get(url_in_waiting_list, 0)
                status_suffix = f" (Lỗi - thử {retry_count_for_this_url} lần)" if retry_count_for_this_url > 0 else ""

                ctk.CTkLabel(item_frame, text=f"{i+1}. {display_url_waiting}{status_suffix}", anchor="w", font=("Segoe UI", 10)).pack(side="left", padx=(5, 0), expand=True, fill="x")

                # --- KHUNG CHỨA CÁC NÚT ĐIỀU KHIỂN ---
                controls_button_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
                controls_button_frame.pack(side="right", padx=(0,5))

                # Nút Lên
                # SỬA STATE: Chỉ NORMAL nếu không đang tải VÀ không phải mục đầu tiên
                is_downloading = getattr(self.master_app, 'is_downloading', False)
                up_button_state_dl = ctk.NORMAL if not is_downloading and i > 0 else ctk.DISABLED
                up_button_dl = ctk.CTkButton(controls_button_frame, text="↑",
                                          width=26, height=26,
                                          font=("Segoe UI", 14, "bold"),
                                          command=lambda idx_disp=i: self.move_item_in_download_queue(idx_disp, "up"),
                                          state=up_button_state_dl)
                up_button_dl.pack(side="left", padx=(0, 2))

                # Nút Xuống
                # SỬA STATE: Chỉ NORMAL nếu không đang tải VÀ không phải mục cuối cùng
                down_button_state_dl = ctk.NORMAL if not is_downloading and i < queue_len_display - 1 else ctk.DISABLED
                down_button_dl = ctk.CTkButton(controls_button_frame, text="↓",
                                            width=26, height=26,
                                            font=("Segoe UI", 14, "bold"),
                                            command=lambda idx_disp=i: self.move_item_in_download_queue(idx_disp, "down"),
                                            state=down_button_state_dl)
                down_button_dl.pack(side="left", padx=2)

                # Nút Xóa
                # SỬA STATE: Chỉ NORMAL nếu không đang tải
                del_button_state_dl = ctk.NORMAL if not is_downloading else ctk.DISABLED
                del_button_dl = ctk.CTkButton(controls_button_frame, text="✕",
                                          width=26, height=26,
                                          font=("Segoe UI", 12, "bold"),
                                          command=lambda idx_disp=i: self.remove_item_from_download_queue(idx_disp),
                                          fg_color="#E74C3C", hover_color="#C0392B",
                                          text_color="white", state=del_button_state_dl)
                del_button_dl.pack(side="left", padx=(2,0))

    def move_item_in_download_queue(self, current_index_in_display, direction):
        """
        Di chuyển một mục trong hàng chờ tải xuống (self.download_urls_list) lên hoặc xuống.
        Lưu ý: current_index_in_display là chỉ số trong danh sách đang hiển thị (đã loại trừ current_download_url).
        """
        is_downloading = getattr(self.master_app, 'is_downloading', False)
        if is_downloading and self.current_download_url is not None:
            # Chỉ cho phép sắp xếp các mục chưa được tải
            pass
        elif is_downloading:
            messagebox.showwarning("Đang bận", "Không thể sắp xếp lại hàng chờ khi đang tải xuống và chưa có mục nào được xử lý.", parent=self.master_app)
            return
        
        waiting_urls_only = []
        if hasattr(self, 'download_urls_list') and self.download_urls_list:
            if self.current_download_url:
                waiting_urls_only = [url for url in self.download_urls_list if url != self.current_download_url]
            else:
                waiting_urls_only = list(self.download_urls_list)

        queue_len = len(waiting_urls_only)

        if not 0 <= current_index_in_display < queue_len:
            self.logger.warning(f"Yêu cầu di chuyển mục tải xuống ở vị trí hiển thị không hợp lệ: {current_index_in_display} (độ dài hàng chờ: {queue_len})")
            return

        actual_current_index_in_main_list = -1
        item_to_move_value = waiting_urls_only[current_index_in_display]

        # Tìm vị trí thực sự của item_to_move_value trong self.download_urls_list
        # (quan trọng nếu self.download_urls_list có cả current_download_url)
        try:
            # Tìm vị trí của item_to_move TRONG self.download_urls_list
            # Điều này quan trọng vì self.download_urls_list có thể có current_download_url ở đầu
            # mà không có trong waiting_urls_only.
            indices_in_main_list = [i for i, x in enumerate(self.download_urls_list) if x == item_to_move_value]
            if not indices_in_main_list:
                self.logger.error(f"Không tìm thấy mục '{item_to_move_value}' trong self.download_urls_list chính.")
                return
            
            # Ưu tiên index lớn hơn nếu current_download_url trùng với item_to_move
            # (Trường hợp này hiếm khi xảy ra nếu logic đúng, nhưng để phòng ngừa)
            if self.current_download_url == item_to_move_value and len(indices_in_main_list) > 1:
                 actual_current_index_in_main_list = indices_in_main_list[-1] # Lấy index cuối nếu có trùng
            else:
                 actual_current_index_in_main_list = indices_in_main_list[0]

        except ValueError:
            self.logger.error(f"Lỗi không tìm thấy mục '{item_to_move_value}' trong self.download_urls_list chính.")
            return

        new_actual_index_in_main_list = -1

        if direction == "up" and current_index_in_display > 0:
            # Mục tiêu là mục ở vị trí current_index_in_display - 1 trong waiting_urls_only
            target_item_value = waiting_urls_only[current_index_in_display - 1]
            # Tìm vị trí của target_item_value trong self.download_urls_list
            try:
                target_indices_in_main = [i for i, x in enumerate(self.download_urls_list) if x == target_item_value]
                if not target_indices_in_main: return # Should not happen
                new_actual_index_in_main_list = target_indices_in_main[0]
            except ValueError: return
        elif direction == "down" and current_index_in_display < queue_len - 1:
            # Mục tiêu là mục ở vị trí current_index_in_display + 1 trong waiting_urls_only
            target_item_value = waiting_urls_only[current_index_in_display + 1]
            # Tìm vị trí của target_item_value trong self.download_urls_list
            try:
                target_indices_in_main = [i for i, x in enumerate(self.download_urls_list) if x == target_item_value]
                if not target_indices_in_main: return
                new_actual_index_in_main_list = target_indices_in_main[0]
            except ValueError: return
        else:
            self.logger.debug(f"Không thể di chuyển mục tải xuống {current_index_in_display} theo hướng '{direction}'.")
            return

        if new_actual_index_in_main_list != -1 and actual_current_index_in_main_list != -1 :
            try:
                # Di chuyển trong self.download_urls_list
                item_value = self.download_urls_list.pop(actual_current_index_in_main_list)

                final_insert_position = new_actual_index_in_main_list
                if direction == "down" and new_actual_index_in_main_list < actual_current_index_in_main_list :
                     pass
                elif direction == "up" and new_actual_index_in_main_list > actual_current_index_in_main_list:
                    pass

                self.download_urls_list.insert(final_insert_position, item_value)
                
                self.logger.info(f"Đã di chuyển URL trong hàng chờ download từ vị trí thực tế {actual_current_index_in_main_list} sang {final_insert_position}.")
                
                self.update_download_queue_display()
                self.master_app.update_status(f"ℹ️ Đã cập nhật thứ tự hàng chờ download.")
            except IndexError:
                self.logger.error(f"Lỗi IndexError khi di chuyển mục trong hàng chờ download. Actual Current: {actual_current_index_in_main_list}, New Actual Target: {new_actual_index_in_main_list}")
            except Exception as e:
                self.logger.error(f"Lỗi không xác định khi di chuyển mục trong hàng chờ download: {e}", exc_info=True)
                messagebox.showerror("Lỗi Sắp xếp", f"Đã xảy ra lỗi khi sắp xếp lại hàng chờ download:\n{e}", parent=self.master_app)

    def remove_item_from_download_queue(self, index_in_display):
        """
        Xóa một mục khỏi hàng chờ tải xuống (self.download_urls_list) dựa trên
        chỉ số hiển thị của nó trong danh sách các link đang chờ.
        """
        is_downloading = getattr(self.master_app, 'is_downloading', False)
        if is_downloading and self.current_download_url is not None:
            # Chỉ cho phép xóa các mục chưa được tải (đang trong danh sách chờ)
            pass
        elif is_downloading:
            messagebox.showwarning("Đang bận", "Không thể xóa link khỏi hàng chờ khi đang tải và chưa có mục nào được chọn xử lý.", parent=self.master_app)
            return

        # Xác định danh sách các URL đang thực sự "chờ" (không bao gồm URL đang tải)
        waiting_urls_only = []
        if hasattr(self, 'download_urls_list') and self.download_urls_list:
            if self.current_download_url:
                waiting_urls_only = [url for url in self.download_urls_list if url != self.current_download_url]
            else:
                # Nếu không có current_download_url (chưa bắt đầu tải hoặc đã xong hết)
                waiting_urls_only = list(self.download_urls_list)
        
        if not 0 <= index_in_display < len(waiting_urls_only):
            self.logger.warning(f"Yêu cầu xóa mục tải xuống ở vị trí hiển thị không hợp lệ: {index_in_display}")
            return

        url_to_remove = waiting_urls_only[index_in_display]

        try:
            offset = 0
            if self.current_download_url:
                try:
                    pass # Logic tìm index thực sự sẽ phức tạp nếu current_download_url trùng với link trong waiting_urls_only
                except ValueError:
                    pass # current_download_url không có trong list (lạ)

            # Cách đơn giản và an toàn hơn: dựa vào giá trị của url_to_remove
            if url_to_remove in self.download_urls_list:
                self.download_urls_list.remove(url_to_remove) # Xóa lần xuất hiện đầu tiên của giá trị này
                
                # Cũng xóa khỏi bộ đếm lỗi và danh sách hoàn thành (nếu có và nếu cần)
                self.download_retry_counts.pop(url_to_remove, None)
                # self.globally_completed_urls.discard(url_to_remove) # Thường thì link lỗi không nằm trong đây
                                                                    # nhưng nếu người dùng muốn xóa link đã hoàn thành khỏi danh sách (nếu hiển thị)

                self.logger.info(f"Đã xóa URL '{url_to_remove[:60]}...' khỏi hàng chờ download.")
                
                self.update_download_queue_display() # Cập nhật giao diện
                self.master_app.update_status(f"ℹ️ Đã xóa 1 link khỏi hàng chờ download.")
            else:
                self.logger.warning(f"Không tìm thấy URL '{url_to_remove[:60]}...' trong self.download_urls_list để xóa.")

        except ValueError: # Xảy ra nếu url_to_remove không có trong self.download_urls_list (dù đã kiểm tra)
            self.logger.error(f"Lỗi ValueError khi cố xóa '{url_to_remove[:60]}...' (không tìm thấy).", exc_info=True)
        except Exception as e:
            self.logger.error(f"Lỗi không xác định khi xóa mục khỏi hàng chờ download: {e}", exc_info=True)
            messagebox.showerror("Lỗi Xóa Link", f"Đã xảy ra lỗi khi xóa link:\n{e}", parent=self.master_app)

    def fetch_links_from_sheet(self, callback=None, auto_triggered=False):
        """
        Xử lý việc lấy Sheet ID và Range từ người dùng (nếu cần khi không phải auto_triggered)
        và khởi chạy luồng _fetch_sheet_data_thread để lấy link.

        Args:
            callback (function, optional): Hàm được gọi sau khi luồng lấy dữ liệu Sheet hoàn tất.
                                           Signature: callback(success: bool, links: list|None, error_message: str|None)
            auto_triggered (bool, optional): True nếu được gọi tự động từ run_download.
                                             Sẽ không hiển thị dialog hỏi ID/Range hoặc các messagebox thông thường.
        """
        current_thread_name = threading.current_thread().name
        self.logger.info(f"[{current_thread_name}] Bắt đầu fetch_links_from_sheet. Auto: {auto_triggered}, Có callback: {callable(callback)}")

        sheet_id = self.master_app.sheet_id_var.get().strip()
        sheet_range = self.master_app.sheet_range_var.get().strip()

        # --- Xử lý lấy Sheet ID và Range từ người dùng nếu không phải auto_triggered ---
        if not auto_triggered:
            if not sheet_id:
                dialog_id = ctk.CTkInputDialog(text="Vui lòng nhập Google Sheet ID:", title="Nhập Sheet ID")
                try:
                    self.master_app.update_idletasks()
                    dialog_id.update_idletasks()
                    x = self.master_app.winfo_x() + (self.master_app.winfo_width() // 2) - (dialog_id.winfo_reqwidth() // 2)
                    y = self.master_app.winfo_y() + (self.master_app.winfo_height() // 2) - (dialog_id.winfo_reqheight() // 2)
                    dialog_id.geometry(f"+{x}+{y}")
                except Exception as e_center: self.logger.warning(f"Lỗi căn giữa dialog ID: {e_center}")
                
                entered_id = dialog_id.get_input()
                if entered_id is not None and entered_id.strip():
                    sheet_id = entered_id.strip()
                    self.master_app.sheet_id_var.set(sheet_id)
                    self.master_app.cfg['sheet_id'] = sheet_id # Cập nhật config trực tiếp
                else:
                    self.logger.info(f"[{current_thread_name}] Người dùng hủy nhập Sheet ID.")
                    if callback: self.master_app.after(0, lambda: callback(False, None, "Người dùng hủy nhập Sheet ID.")) # Gọi callback trên luồng chính
                    else: messagebox.showwarning("Thiếu thông tin", "Bạn cần nhập Google Sheet ID để tiếp tục.", parent=self.master_app)
                    self._reenable_fetch_button() # Bật lại nút nếu nó bị disable
                    return
            
            default_range_example = "Sheet1!B2:B" # Đưa ra ngoài để dùng chung
            if not sheet_range:
                dialog_range = ctk.CTkInputDialog(text=f"Vui lòng nhập Phạm vi cần đọc:\n(Ví dụ: {default_range_example})", title="Nhập Phạm vi Sheet")
                try:
                    self.master_app.update_idletasks()
                    dialog_range.update_idletasks()
                    x = self.master_app.winfo_x() + (self.master_app.winfo_width() // 2) - (dialog_range.winfo_reqwidth() // 2)
                    y = self.master_app.winfo_y() + (self.master_app.winfo_height() // 2) - (dialog_range.winfo_reqheight() // 2)
                    dialog_range.geometry(f"+{x}+{y}")
                except Exception as e_center: self.logger.warning(f"Lỗi căn giữa dialog Range: {e_center}")

                entered_range = dialog_range.get_input()
                if entered_range is not None and entered_range.strip():
                    if '!' not in entered_range or not entered_range.split('!')[1]: # Kiểm tra định dạng cơ bản
                        self.logger.warning(f"[{current_thread_name}] Định dạng Phạm vi Sheet không hợp lệ: {entered_range}")
                        if callback: self.master_app.after(0, lambda: callback(False, None, f"Định dạng Phạm vi Sheet không hợp lệ: {entered_range}"))
                        else: messagebox.showerror("Sai định dạng", f"Phạm vi '{entered_range}' không hợp lệ.\nVí dụ đúng: {default_range_example}", parent=self.master_app)
                        self._reenable_fetch_button()
                        return
                    else:
                        sheet_range = entered_range.strip()
                        self.master_app.sheet_range_var.set(sheet_range)
                        self.master_app.cfg['sheet_range'] = sheet_range # Cập nhật config trực tiếp
                else:
                    self.logger.info(f"[{current_thread_name}] Người dùng hủy nhập Phạm vi Sheet.")
                    if callback: self.master_app.after(0, lambda: callback(False, None, "Người dùng hủy nhập Phạm vi Sheet."))
                    else: messagebox.showwarning("Thiếu thông tin", f"Bạn cần nhập Phạm vi Sheet (ví dụ: {default_range_example}) để tiếp tục.", parent=self.master_app)
                    self._reenable_fetch_button()
                    return
        
        # --- Kiểm tra lại ID và Range trước khi chạy thread (quan trọng cho cả auto và manual) ---
        if not sheet_id or not sheet_range:
            log_msg = f"[{current_thread_name}] Thiếu Sheet ID ('{sheet_id}') hoặc Range ('{sheet_range}') để lấy link."
            self.logger.error(log_msg)
            if callback: self.master_app.after(0, lambda: callback(False, None, "Thiếu Sheet ID hoặc Range trong cấu hình."))
            if not auto_triggered: # Chỉ hiện lỗi cho người dùng nếu họ nhấn nút
                messagebox.showerror("Thiếu Thông Tin", "Sheet ID hoặc Phạm vi không được để trống trong cấu hình hoặc ô nhập.", parent=self.master_app)
                self._reenable_fetch_button()
            return

        # Lưu cấu hình nếu người dùng đã nhập (không phải auto) và có thay đổi
        if not auto_triggered: 
            self.master_app.save_current_config() # save_current_config sẽ lấy giá trị từ các StringVar
            self.logger.info(f"[{current_thread_name}] Đã lưu config (nếu có thay đổi từ dialog) trước khi lấy link Sheet.")

        # --- Vô hiệu hóa nút và cập nhật status (CHỈ KHI KHÔNG PHẢI AUTO_TRIGGERED) ---
        if not auto_triggered:
            self.master_app.update_status("🔄 Đang lấy link từ Google Sheet...")
            if hasattr(self, 'add_sheet_button') and self.add_sheet_button and self.add_sheet_button.winfo_exists():
                try: self.add_sheet_button.configure(state="disabled", text="Đang lấy...")
                except Exception: pass # Bỏ qua nếu nút không tồn tại/lỗi
        
        # --- Khởi chạy luồng lấy dữ liệu ---
        self.logger.info(f"[{current_thread_name}] Chuẩn bị chạy _fetch_sheet_data_thread. SheetID: {sheet_id}, Range: {sheet_range}, Auto: {auto_triggered}, Callback: {callable(callback)}")
        thread = threading.Thread(
            target=self._fetch_sheet_data_thread, 
            args=(sheet_id, sheet_range, callback, auto_triggered), # Truyền callback và auto_triggered
            daemon=True, 
            name="SheetReaderThread"
        )
        thread.start()

    def _fetch_sheet_data_thread(self, sheet_id, sheet_range, callback=None, auto_triggered=False):
        """
        Luồng thực hiện lấy dữ liệu từ Google Sheet bằng API chính thức.
        Gọi callback khi hoàn thành với kết quả.
        """
        thread_name = threading.current_thread().name
        self.logger.info(f"[{thread_name}] Bắt đầu _fetch_sheet_data_thread. SheetID: {sheet_id}, Range: {sheet_range}, Auto: {auto_triggered}")

        service = None
        fetched_links_list = None 
        was_successful = False
        error_msg_for_callback = None

        try:
            self.logger.debug(f"[{thread_name}] Đang thử lấy service Google Sheets...")
            service = get_google_api_service(api_name='sheets', api_version='v4') # Gọi đúng tên và truyền tham số Sheets API

            if service is None:
                # Lỗi xảy ra trong get_sheets_service() hoặc người dùng hủy xác thực
                error_msg_for_callback = "Lỗi xác thực hoặc người dùng hủy kết nối Google Sheets."
                self.logger.error(f"[{thread_name}] {error_msg_for_callback}")
                
                if auto_triggered and not self.master_app.cfg.get("google_auth_declined_in_current_session", False):
                    def _handle_auto_auth_fail_for_sheet_thread():
                        self.master_app.disable_auto_sheet_check_var.set(True) 
                        self.master_app.cfg["disable_auto_sheet_check"] = True 
                        self.master_app.cfg["google_auth_declined_in_current_session"] = True 
                        save_config(self.master_app.cfg) # Lưu lại config
                        self.logger.warning(f"[{thread_name}] Lỗi xác thực Google (tự động), đã tự động tắt kiểm tra Sheet cho session này và lưu config.")
                    self.master_app.after(0, _handle_auto_auth_fail_for_sheet_thread)
            else:
                # Xác thực thành công, xóa cờ lỗi session (nếu có) để lần sau nếu có lỗi vẫn hiện UI xác thực
                if "google_auth_declined_in_current_session" in self.master_app.cfg:
                    self.logger.info(f"[{thread_name}] Xác thực Google thành công, xóa cờ 'google_auth_declined_in_current_session'.")
                    self.master_app.cfg.pop("google_auth_declined_in_current_session")
                    save_config(self.master_app.cfg) # Lưu lại config
                
                self.logger.info(f"[{thread_name}] Lấy service Google Sheets thành công. Đang gọi API...")
                sheet_api_service = service.spreadsheets() # Đổi tên biến để tránh nhầm lẫn với module
                result = sheet_api_service.values().get(spreadsheetId=sheet_id, range=sheet_range).execute()
                values = result.get('values', [])
                self.logger.info(f"[{thread_name}] Phản hồi từ Google Sheets API: {len(values)} hàng dữ liệu.")

                if not values:
                    self.logger.info(f"[{thread_name}] Không tìm thấy dữ liệu (hàng rỗng) trong phạm vi Sheet chỉ định: {sheet_range}")
                    was_successful = True 
                    fetched_links_list = [] # Trả về list rỗng nếu không có dữ liệu
                    error_msg_for_callback = "Không có dữ liệu trong phạm vi Sheet đã chọn." 
                else:
                    temp_links = []
                    for row_idx, row_data in enumerate(values):
                        if row_data and len(row_data) > 0: # Kiểm tra hàng và cột có tồn tại
                             link_value = str(row_data[0]).strip() # Giả sử link ở cột đầu tiên (index 0)
                             if link_value.startswith(('http://', 'https://')):
                                  temp_links.append(link_value)
                             elif link_value: # Nếu có giá trị nhưng không phải link
                                  self.logger.warning(f"[{thread_name}] Bỏ qua giá trị không phải URL từ hàng {row_idx+1}, cột 1: '{link_value[:60]}...'")
                        else:
                             self.logger.debug(f"[{thread_name}] Bỏ qua hàng rỗng hoặc không có cột đầu tiên ở hàng {row_idx+1} từ sheet.")
                    
                    fetched_links_list = temp_links
                    was_successful = True # API gọi thành công, dù có thể không có link nào hợp lệ
                    self.logger.info(f"[{thread_name}] Trích xuất được {len(fetched_links_list)} link hợp lệ từ Sheet.")
        
        except HttpError as err:
            was_successful = False # Đánh dấu là không thành công
            error_content_decoded = getattr(err, 'content', b'').decode('utf-8', 'replace')
            error_msg_for_callback = f"Lỗi Google API (Sheet): Mã {err.resp.status}. "
            self.logger.error(f"[{thread_name}] {error_msg_for_callback} Nội dung: {error_content_decoded}", exc_info=False)
            try: # Cố gắng parse lỗi chi tiết từ JSON
                 error_json = json.loads(error_content_decoded)
                 error_detail_msg = error_json.get('error', {}).get('message', 'Không có chi tiết lỗi cụ thể từ JSON.')
                 error_msg_for_callback += error_detail_msg
                 # Thêm gợi ý dựa trên nội dung lỗi
                 if "PERMISSION_DENIED" in error_content_decoded.upper(): # upper() để bắt cả chữ thường
                     error_msg_for_callback += "\nGợi ý: Sheet có thể chưa được chia sẻ quyền xem cho tài khoản Google đã xác thực, hoặc Sheet ID/Phạm vi không đúng."
                 elif "REQUESTED_ENTITY_WAS_NOT_FOUND" in error_content_decoded.upper():
                      error_msg_for_callback += f"\nGợi ý: Sheet ID '{sheet_id}' có thể không tồn tại hoặc bạn không có quyền truy cập."
                 elif "UNABLE_TO_PARSE_RANGE" in error_content_decoded.upper():
                       error_msg_for_callback += f"\nGợi ý: Phạm vi '{sheet_range}' không hợp lệ."
            except json.JSONDecodeError:
                 error_msg_for_callback += f"Không thể phân tích phản hồi lỗi JSON. Phản hồi thô: {error_content_decoded[:250]}..."
            # Không return sớm, để khối finally gọi callback

        except Exception as e: # Bắt các lỗi không mong muốn khác
            was_successful = False
            error_msg_for_callback = f"Lỗi không xác định khi lấy link từ Sheet: {str(e)}"
            self.logger.error(f"[{thread_name}] {error_msg_for_callback}", exc_info=True)
            # Không return sớm
        
        finally:
            log_final_status = f"Hoàn tất _fetch_sheet_data_thread. Thành công kỹ thuật (API call): {was_successful}, Số link trích xuất: {len(fetched_links_list) if fetched_links_list is not None else 'N/A'}"
            self.logger.info(f"[{thread_name}] {log_final_status}")
            
            if callback:
                try:
                    # Gọi callback trên luồng chính
                    self.master_app.after(0, lambda cb=callback, s=was_successful, l=fetched_links_list, err=error_msg_for_callback: cb(s, l, err))
                    self.logger.debug(f"[{thread_name}] Đã lên lịch gọi callback với success={was_successful}.")
                except Exception as e_cb:
                    self.logger.error(f"[{thread_name}] Lỗi khi lên lịch gọi callback sau khi lấy link từ Sheet: {e_cb}", exc_info=True)
            
            # Chỉ xử lý UI (nút, status) nếu KHÔNG phải auto_triggered VÀ KHÔNG có callback
            # (Vì nếu có callback, callback sẽ chịu trách nhiệm xử lý UI tiếp theo)
            if not auto_triggered and not callback:
                if was_successful:
                    if fetched_links_list: # Có link
                        self.master_app.after(0, self._process_sheet_links, fetched_links_list) 
                        self.master_app.after(0, self.master_app.update_status, f"✅ Đã lấy {len(fetched_links_list)} link từ Google Sheet.")
                    else: # Không có link (list rỗng)
                         self.master_app.after(0, self.master_app.update_status, f"ℹ️ Không tìm thấy link nào trong phạm vi Sheet đã chọn.")
                         self.master_app.after(0, lambda msg="Không tìm thấy link nào trong phạm vi Sheet được chọn.": messagebox.showinfo("Không có link", msg, parent=self.master_app))
                else: # Không thành công (có error_msg_for_callback)
                    self.master_app.after(0, self.master_app.update_status, f"❌ Lỗi lấy link Sheet: {error_msg_for_callback[:100]}...") # Giới hạn độ dài msg
                    self.master_app.after(0, lambda msg=error_msg_for_callback: messagebox.showerror("Lỗi lấy link từ Sheet", msg, parent=self.master_app))
                
                self.master_app.after(10, self._reenable_fetch_button) # Bật lại nút "Thêm từ Sheet"

    def _process_sheet_links(self, links):
        """ Cập nhật ô Textbox với các link lấy được từ Sheet (chạy trên luồng chính) """
        download_textbox = getattr(self, 'download_url_text', None)
        if not download_textbox or not download_textbox.winfo_exists():
            self.logger.error("Textbox download_url_text không tồn tại để cập nhật link từ Sheet.")
            return

        if not isinstance(links, list):
             self.logger.error(f"Dữ liệu links nhận được không phải là list: {type(links)}")
             messagebox.showerror("Lỗi dữ liệu", "Dữ liệu link nhận được từ Google Sheet không đúng định dạng.", parent=self.master_app)
             return

        if not links:
            self.logger.info("Không có link hợp lệ nào được trả về từ Sheet.")
            messagebox.showinfo("Thông báo", "Không tìm thấy link nào trong phạm vi đã chọn trên Google Sheet hoặc Sheet trống.", parent=self.master_app)
            return

        try:
            current_content = download_textbox.get("1.0", "end-1c")
            current_links = set(line.strip() for line in current_content.splitlines() if line.strip())

            added_links = []
            for link in links:
                if link not in current_links:
                    added_links.append(link)
                    current_links.add(link)

            if not added_links:
                 self.logger.info("Không có link mới nào từ Sheet để thêm vào Textbox.")
                 messagebox.showinfo("Thông báo", "Tất cả link từ Sheet đã có trong ô nhập liệu.", parent=self.master_app)
                 return

            # Thêm các link mới vào textbox
            new_text_lines = []
            if current_content.strip():
                new_text_lines.append(current_content.strip())
            for new_link in added_links:
                new_text_lines.append(new_link)

            new_text_content = "\n".join(new_text_lines)
            download_textbox.configure(state="normal")
            download_textbox.delete("1.0", "end")
            download_textbox.insert("1.0", new_text_content)
            download_textbox.configure(state="normal") # Giữ state normal để người dùng có thể chỉnh sửa

            self.logger.info(f"Đã thêm {len(added_links)} link mới từ Sheet vào textbox. Tổng link trong textbox: {len(current_links) + len(added_links)}")

        except Exception as e:
            self.logger.error(f"Lỗi khi xử lý link từ Sheet: {e}", exc_info=True)
            messagebox.showerror("Lỗi", f"Đã xảy ra lỗi khi thêm link từ Sheet vào textbox:\n{e}", parent=self.master_app)

    def _fetch_links_from_sheet_sync(self, service, sheet_id, sheet_range):
        """
        Gọi API Google Sheets đồng bộ để lấy danh sách link.
        Trả về list các link hoặc None nếu có lỗi.
        """
        thread_name = threading.current_thread().name
        self.logger.info(f"[{thread_name}] SYNC Fetch: Đang gọi Sheets API. ID: {sheet_id}, Phạm vi: {sheet_range}")

        if not service:
            self.logger.error(f"[{thread_name}] SYNC Fetch: Thiếu đối tượng service Google Sheets.")
            return None

        try:
            sheet_api_service = service.spreadsheets()
            result = sheet_api_service.values().get(spreadsheetId=sheet_id, range=sheet_range).execute()
            values = result.get('values', [])

            if not values:
                self.logger.info(f"[{thread_name}] SYNC Fetch: Không có dữ liệu trong Sheet.")
                return []

            links = []
            for row_idx, row_data in enumerate(values):
                if row_data and len(row_data) > 0:
                    link_value = str(row_data[0]).strip()
                    if link_value.startswith(('http://', 'https://')):
                        links.append(link_value)
                    elif link_value:
                        self.logger.debug(f"[{thread_name}] SYNC Fetch: Bỏ qua giá trị không phải URL ở hàng {row_idx+1}.")

            self.logger.info(f"[{thread_name}] SYNC Fetch: Trích xuất được {len(links)} link từ Sheet.")
            return links

        except HttpError as err:
            error_content = getattr(err, 'content', b'').decode('utf-8', 'replace')
            self.logger.error(f"[{thread_name}] SYNC Fetch: Lỗi Google API. Mã {err.resp.status}. Nội dung: {error_content[:200]}...")
            return None
        except Exception as e:
            self.logger.error(f"[{thread_name}] SYNC Fetch: Lỗi không xác định: {e}", exc_info=True)
            return None

    def _execute_ytdlp(self, url, config, is_video, index, task_object_ref=None):
        """ Thực thi yt-dlp, xử lý output, progress và tùy chọn --ppa. """
        thread_name = threading.current_thread().name # Lấy tên luồng để log
        self.logger.info(f"[{thread_name}] Bắt đầu tải: {'Video' if is_video else 'MP3'} - {url[:70]}...")

        # Kiểm tra cờ dừng sớm
        if self.master_app.stop_event.is_set():
            self.logger.warning(f"[{thread_name}] Tác vụ bị dừng trước khi bắt đầu yt-dlp.")
            return (False, None)

        # Lấy YTDLP_PATH
        YTDLP_PATH = _get_ytdlp_path_safe()

        # Khởi tạo biến kết quả và trạng thái
        process_result = False
        output_filepath = None
        output_lines = [] # Lưu các dòng output từ yt-dlp để debug lỗi
        base_folder = Path(".") # Khởi tạo đường dẫn gốc
        proc = None # Khởi tạo biến tiến trình là None

        try:
            # --- 1. Chuẩn bị Thư mục Output ---
            base_folder_str = config.get("folder", ".") # Lấy đường dẫn từ config
            if not base_folder_str: # Xử lý nếu đường dẫn trống
                 self.logger.error(f"[{thread_name}] Đường dẫn thư mục tải về bị trống!")
                 self.master_app.after(0, lambda: self.log_download(f"   ❌ Lỗi: Đường dẫn lưu trống!"))
                 return (False, None)
            base_folder = Path(base_folder_str)
            try:
                base_folder.mkdir(parents=True, exist_ok=True) # Tạo thư mục nếu chưa có
                self.logger.debug(f"[{thread_name}] Đã đảm bảo thư mục tồn tại: {base_folder}")
            except OSError as e:
                self.logger.error(f"[{thread_name}] Không thể tạo thư mục '{base_folder}': {e}")
                self.master_app.after(0, lambda err=e, p=str(base_folder): self.log_download(f"   ❌ Lỗi tạo thư mục '{p}': {err}"))
                return (False, None) # Không thể tiếp tục nếu không có thư mục

            # --- 2. Xây dựng Lệnh cmd cho yt-dlp ---
            cmd = [YTDLP_PATH] # Bắt đầu với đường dẫn của yt-dlp

            # Tùy chọn Playlist
            if not config.get("download_playlist", False):
                cmd.append("--no-playlist")

            # Tìm và thêm đường dẫn ffmpeg
            ffmpeg_location = find_ffmpeg()
            if not ffmpeg_location:
                self.logger.error(f"[{thread_name}] Không tìm thấy ffmpeg.")
                self.master_app.after(0, lambda: self.log_download(f"   ❌ Lỗi: Không tìm thấy ffmpeg!"))
                self.master_app.after(0, lambda: self.master_app.update_status(f"❌ Lỗi tải: Thiếu ffmpeg."))
                return (False, None)

            # Thêm các tùy chọn yt-dlp chung
            common_options = [
                "--ffmpeg-location", ffmpeg_location,
                "--no-warnings",                  # Ẩn các cảnh báo thông thường
                "--restrict-filenames",           # Đảm bảo tên file an toàn cho HĐH
                "--progress-template",            # Định dạng dòng progress (có thể tùy chỉnh)
                    "download-title:%(info.title)s-ETA:%(progress.eta)s",
                "--socket-timeout", "30",         # Timeout cho kết nối mạng (giây)
                "--force-overwrite",              # Ghi đè nếu file đã tồn tại
            ]
            cmd.extend(common_options)

            # Thêm --verbose nếu muốn debug (mặc định comment lại)
            cmd.append("--verbose")

            # --- Chuẩn bị mẫu tên file output (-o) ---
            desired_ext = "mp4" if is_video else "mp3"
            output_tmpl_pattern = ""
            download_playlist = config.get("download_playlist", False)

            if config.get("rename_all", False) and config.get('base_name'):
                # ✅ NHÁNH ĐỔI TÊN HÀNG LOẠT (SỬA LỖI GHI ĐÈ)
                safe_base_name = create_safe_filename(config['base_name'], remove_accents=False)
                if download_playlist:
                    # Playlist -> để yt-dlp tự tăng index cho MỖI MỤC
                    index_token = "%(playlist_index)03d"
                else:
                    # Không phải playlist -> dùng index của bạn (hoặc %(autonumber)03d nếu 1 lệnh có nhiều URL)
                    # index ở đây là tham số truyền vào hàm
                    index_token = f"{index:03d}"  # hoặc: "%(autonumber)03d"

                audio_suffix = "_audio" if not is_video else ""
                # Giữ phần mở rộng cố định vì bạn đã ép mp3/mp4 bằng tham số
                output_tmpl_pattern = f"{safe_base_name} - {index_token}{audio_suffix}.{desired_ext}"
                self.logger.debug(f"[{thread_name}] Template rename_all: {output_tmpl_pattern}")

            else:
                # ✅ NHÁNH MẶC ĐỊNH (đã đúng, giữ nguyên tinh thần cũ)
                index_part = "%(playlist_index)03d - " if download_playlist else ""
                title_part = "%(title).15s"
                audio_suffix = "_audio" if not is_video else ""
                output_tmpl_pattern = f"{index_part}{title_part} - %(id)s{audio_suffix}.{desired_ext}"
                output_tmpl_pattern = re.sub(r'\s*-\s*-\s*', ' - ', output_tmpl_pattern).strip(' -')
                output_tmpl_pattern = re.sub(r'_-_', '_', output_tmpl_pattern)
                self.logger.debug(f"[{thread_name}] Template mặc định: {output_tmpl_pattern}")

            # Dọn chuỗi và fallback an toàn
            output_tmpl_pattern = output_tmpl_pattern.replace("--.", ".").replace("__", "_").strip(" _-.")
            if not output_tmpl_pattern or not output_tmpl_pattern.endswith(f".{desired_ext}"):
                output_tmpl_pattern = f"downloaded_file_{index}.{desired_ext}"

            output_tmpl = str(base_folder / output_tmpl_pattern)
            cmd.extend(["-o", output_tmpl])

            # Dọn dẹp và kiểm tra fallback
            output_tmpl_pattern = output_tmpl_pattern.replace("--.", ".").replace("__", "_").strip(" _-.")
            if not output_tmpl_pattern or not output_tmpl_pattern.endswith(f".{desired_ext}"):
                 output_tmpl_pattern = f"downloaded_file_{index}.{desired_ext}" # Tên dự phòng an toàn
            output_tmpl = str(base_folder / output_tmpl_pattern)

            # <<< THÊM MỚI: Xử lý Cookies >>>
            if config.get("use_cookies") and config.get("cookies_file"):
                cookies_path = config["cookies_file"]
                if os.path.exists(cookies_path):
                    self.logger.info(f"[{thread_name}] Sử dụng file cookies: {cookies_path}")
                    cmd.extend(["--cookies", cookies_path])
                else:
                    self.logger.warning(f"[{thread_name}] Đã bật dùng cookies nhưng file không tồn tại: {cookies_path}")
            # <<< KẾT THÚC THÊM MỚI >>>

            cmd.extend(["-o", output_tmpl]) # Thêm tùy chọn đường dẫn output

            # --- Thêm tùy chọn định dạng và --ppa (NẾU LÀ VIDEO và ĐƯỢC CHỌN) ---
            if is_video:
                quality = config.get('v_quality', '1080') # Lấy chất lượng video từ config
                # Format selection (ưu tiên mp4/m4a nếu có thể)
                format_select = "bv*[height<=%s][ext=mp4]+ba[ext=m4a]/bv*[height<=%s]+ba/b[height<=%s]/b" % (quality, quality, quality)
                if quality == 'best':
                     format_select = "bv*+ba/b" # Lấy video + audio tốt nhất
                cmd.extend(["-f", format_select, "--merge-output-format", "mp4"])

                # Kiểm tra checkbox "Tối ưu Mobile"
                optimize_mobile = False
                if hasattr(self, 'optimize_for_mobile_var'):
                    try: optimize_mobile = self.optimize_for_mobile_var.get()
                    except Exception as e_get: self.logger.error(f"Lỗi khi lấy optimize_for_mobile_var: {e_get}")

                if optimize_mobile:
                    # Thêm tùy chọn PPA để ép ffmpeg re-encode tương thích iPhone
                    self.logger.info(f"[{thread_name}] Đã chọn Tối ưu Mobile, thêm PPA cho ffmpeg...")
                    ppa_string = "ffmpeg:-c:v libx264 -preset medium -crf 22 -profile:v main -pix_fmt yuv420p -c:a aac -b:a 192k"
                    cmd.append("--ppa")
                    cmd.append(ppa_string)
                else:
                    # Không tối ưu, chỉ merge (yt-dlp tự xử lý, thường là copy stream)
                    self.logger.info(f"[{thread_name}] Không chọn Tối ưu Mobile, giữ chất lượng gốc (chỉ merge).")

            else: # Nếu là tải Audio
                quality = config.get('a_quality', 'best') # Lấy chất lượng audio
                audio_q_ffmpeg = f"{quality}k" if quality != 'best' and quality.isdigit() else "0" # 0 là tốt nhất cho ffmpeg
                cmd.extend([
                    "-f", "ba/b",  # Chọn luồng audio tốt nhất
                    "-x",          # Trích xuất audio
                    "--audio-format", "mp3", # Định dạng output là mp3
                    "--audio-quality", audio_q_ffmpeg # Chất lượng audio (0=best)
                ])

            # Thêm URL vào cuối cùng
            cmd.append(url)
            self.logger.debug(f"[{thread_name}] Lệnh yt-dlp hoàn chỉnh sẽ chạy: {' '.join(cmd)}")

            # Reset progress bar trước khi bắt đầu
            self.master_app.after(0, lambda: self.update_download_progress(0))

            # --- 3. Thực thi tiến trình yt-dlp (streaming output) ---
            proc = None
            def _set_proc(p):
                nonlocal proc
                proc = p
                try:
                    setattr(self.master_app, 'current_process', p)
                except Exception:
                    pass

            def _clear_proc():
                nonlocal proc
                proc = None
                try:
                    setattr(self.master_app, 'current_process', None)
                except Exception:
                    pass

            # --- 4. Vòng lặp đọc Output từ yt-dlp ---
            progress_regex = re.compile(r"\[download\]\s+(\d{1,3}(?:[.,]\d+)?)%")
            destination_regex = re.compile( r"\[(?:download|Merger|ExtractAudio|ffmpeg)\]\s+(?:Destination:|Merging formats into|Extracting audio to|Deleting original file|Converting video to)\s*(.*)" )
            last_percent = -1.0; is_processing_step = False; potential_output_path = None

            # Đọc từng dòng output cho đến khi tiến trình kết thúc
            for line in ytdlp_stream_output(
                cmd,
                process_name=f"{thread_name}_yt-dlp",
                hide_console_window=True,
                set_current_process=_set_proc,
                clear_current_process=_clear_proc,
            ):
                 if self.master_app.stop_event.is_set(): # Xử lý dừng bởi người dùng
                      self.logger.warning(f"[{thread_name}] Cờ dừng được kích hoạt.")
                      try:
                          if proc and proc.poll() is None: proc.terminate(); self.logger.info(f"[{thread_name}] Đã gửi terminate.")
                      except Exception as term_err: self.logger.warning(f"Lỗi terminate: {term_err}")
                      break # Thoát vòng lặp đọc

                 clean_line = line.strip()
                 if not clean_line: continue # Bỏ qua dòng trống
                 output_lines.append(clean_line) # Lưu lại dòng log để debug nếu cần
                 # Gửi lên UI Log (có thể làm chậm nếu quá nhiều log verbose)
                 self.master_app.after(0, lambda line=clean_line: self.log_download(f"      {line}"))

                 # Phân tích dòng log để tìm đường dẫn file cuối hoặc trạng thái
                 dest_match = destination_regex.search(clean_line)
                 if dest_match:
                    found_path_raw = dest_match.group(1).strip().strip('"')
                    # Kiểm tra nếu là đường dẫn file hợp lệ và không phải file tạm
                    if not any(found_path_raw.endswith(ext) for ext in [".part", ".ytdl", ".temp"]) and os.path.splitext(found_path_raw)[1]:
                         potential_output_path = found_path_raw
                         self.logger.debug(f"Cập nhật path cuối tiềm năng: {potential_output_path}")
                    elif not potential_output_path and any(found_path_raw.endswith(ext) for ext in [".part", ".ytdl", ".temp"]):
                         self.logger.debug(f"Tìm thấy path tạm: {found_path_raw}")

                 # Phát hiện giai đoạn xử lý sau tải (ffmpeg, merge,...)
                 if not is_processing_step and any(tag in clean_line for tag in ["[ExtractAudio]", "[Merger]", "[ffmpeg]"]):
                      is_processing_step = True
                      self.master_app.after(0, lambda: self.update_download_progress(100)) # Xem như download 100%
                      self.master_app.after(0, lambda: self.master_app.update_status("⏳ Đang xử lý (ghép/chuyển đổi)..."))
                      self.logger.debug(f"[{thread_name}] Bắt đầu giai đoạn xử lý sau tải...")
                      continue # Không cần parse % nữa

                 # Cập nhật thanh progress bar nếu đang trong giai đoạn download
                 if not is_processing_step:
                     match = progress_regex.search(clean_line)
                     if match:
                         percent_str = match.group(1).replace(',', '.')
                         try: # Khối try/except định dạng đúng
                             percent = float(percent_str)
                             if abs(percent - last_percent) >= 0.5 or percent >= 99.9:
                                 last_percent = percent
                                 self.master_app.after(0, lambda p=percent: self.update_download_progress(p))
                         except ValueError:
                             pass # Bỏ qua nếu lỗi parse số

            # --- Kết thúc vòng lặp đọc Output ---
            self.logger.info(f"[{thread_name}] Hoàn tất đọc stdout. Chờ tiến trình yt-dlp thoát...")

            # --- 5. Lấy mã trả về ---
            return_code = -97 if proc is None else (proc.returncode if proc.poll() is not None else proc.wait(timeout=1))

            self.master_app.current_process = None # Xóa tham chiếu sau khi xử lý xong

            # --- 6. Xử lý kết quả cuối cùng (PHIÊN BẢN HOÀN CHỈNH) ---
            if self.master_app.stop_event.is_set() or return_code == -100:
                self.master_app.after(0, lambda: self.log_download(f"   ⚠️ Bị dừng."))
                process_result = False
            
            # Ưu tiên kiểm tra sự tồn tại của file output làm điều kiện thành công chính
            
            final_output_path_check = None
            # Cố gắng xác định đường dẫn file cuối cùng bất kể return_code là gì
            if potential_output_path and os.path.exists(potential_output_path) and os.path.getsize(potential_output_path) > 1024:
                final_output_path_check = potential_output_path
            elif os.path.exists(output_tmpl) and os.path.getsize(output_tmpl) > 1024:
                final_output_path_check = output_tmpl
            
            # Nếu tìm thấy file output hợp lệ
            if final_output_path_check:
                if return_code == 0:
                    self.logger.info(f"[{thread_name}] THÀNH CÔNG: yt-dlp thoát với mã 0 và file output hợp lệ: {final_output_path_check}")
                    self.master_app.after(0, lambda: self.log_download(f"   ✔️ Hoàn thành (Mã 0)."))
                else:
                    self.logger.warning(f"[{thread_name}] THÀNH CÔNG (FALLBACK): yt-dlp thoát với mã lỗi {return_code} nhưng đã tạo file thành công: {final_output_path_check}")
                    self.master_app.after(0, lambda: self.log_download(f"   ✔️ Hoàn thành (với fallback của yt-dlp)."))
                
                self.master_app.after(10, lambda: self.update_download_progress(100))
                process_result = True
                output_filepath = final_output_path_check
            
            # Nếu KHÔNG tìm thấy file output nào hợp lệ
            else:
                process_result = False
                full_output_log = "\n".join(output_lines)
                self.logger.error(f"[{thread_name}] THẤT BẠI: Không tìm thấy file output hợp lệ. Mã lỗi yt-dlp: {return_code}. URL: {url}. Log:\n{full_output_log[-2000:]}") # Log 2000 dòng cuối

                # Phân tích lỗi cụ thể để thông báo cho người dùng
                specific_error_msg = None
                full_output_lower = full_output_log.lower()
                if "login required" in full_output_lower or "private video" in full_output_lower or "cookies" in full_output_lower: specific_error_msg = "Yêu cầu đăng nhập hoặc video riêng tư."
                elif "video unavailable" in full_output_lower: specific_error_msg = "Video không tồn tại hoặc đã bị xóa."
                elif "copyright" in full_output_lower: specific_error_msg = "Video bị chặn do vấn đề bản quyền."
                elif "geo-restricted" in full_output_lower or "geo restricted" in full_output_lower: specific_error_msg = "Video bị giới hạn địa lý."
                elif "unsupported url" in full_output_lower: specific_error_msg = "URL không được hỗ trợ."
                elif "fragment" in full_output_lower and "ffmpeg" in full_output_lower: specific_error_msg = "Lỗi ghép file (có thể thiếu ffmpeg?)."
                
                # Tạo thông báo lỗi cho UI
                error_log_msg_ui = f"   ❌ Lỗi tải {'Video' if is_video else 'MP3'} (mã {return_code})"
                if specific_error_msg:
                    error_log_msg_ui += f": {specific_error_msg}"
                self.master_app.after(0, lambda msg=error_log_msg_ui: self.log_download(msg))

        except FileNotFoundError:
             self.logger.error(f"Lỗi FileNotFoundError: Không tìm thấy file thực thi '{YTDLP_PATH}'.")
             self.master_app.after(0, lambda: self.log_download(f"   ❌ Lỗi: Không tìm thấy '{YTDLP_PATH}'.")); process_result = False
             self.master_app.after(0, lambda: self.master_app.update_status(f"❌ Lỗi tải: Không tìm thấy '{YTDLP_PATH}'."))
        except Exception as e:
             import traceback; error_details = traceback.format_exc()
             self.logger.error(f"[{thread_name}] Lỗi không mong đợi trong _execute_ytdlp: {e}\n{error_details}")
             self.master_app.after(0, lambda err=e: self.log_download(f"   ❌ Lỗi không xác định: {err}")); process_result = False
        finally:
            # --- Khối Finally (Đảm bảo dọn dẹp và kết thúc) ---
            # Dọn dẹp file tạm nếu tải thất bại và không phải do người dùng dừng
            if not process_result and not self.master_app.stop_event.is_set():
                self.logger.info(f"[{thread_name}] Tải thất bại. Đang thử dọn dẹp file tạm...")
                try:
                    if base_folder.is_dir():
                        for item in base_folder.iterdir():
                            if item.is_file() and (item.suffix.lower() in ['.part', '.ytdl'] or item.name.endswith('.temp')):
                                self.logger.info(f"Đang xóa file tạm: {item.name}")
                                try: item.unlink()
                                except OSError as del_err: self.logger.warning(f"Không thể xóa {item.name}: {del_err}")
                except Exception as cleanup_err: self.logger.error(f"Lỗi dọn dẹp file tạm: {cleanup_err}")

            # Đảm bảo tiến trình con đã thực sự kết thúc
            if proc and proc.poll() is None: # Kiểm tra lại lần nữa trước khi kill
                self.logger.warning(f"[{thread_name}] Tiến trình yt-dlp vẫn chạy trong finally? Đang kill.")
                try:
                    proc.kill(); proc.wait(timeout=2) # Kill và chờ chút
                    self.logger.info(f"[{thread_name}] Đã kill tiến trình trong finally.")
                except Exception as final_kill_err: self.logger.error(f"Lỗi khi kill tiến trình trong finally: {final_kill_err}")

            # Nếu tải thành công, cập nhật đối tượng tác vụ
            if process_result and task_object_ref is not None:
                if is_video:
                    task_object_ref['downloaded_video_path'] = output_filepath
                    self.logger.info(f"Đã cập nhật 'downloaded_video_path' trong Task Object: {os.path.basename(output_filepath if output_filepath else 'None')}")
                else: # is_audio
                    task_object_ref['downloaded_audio_path'] = output_filepath
                    self.logger.info(f"Đã cập nhật 'downloaded_audio_path' trong Task Object: {os.path.basename(output_filepath if output_filepath else 'None')}")

            self.logger.info(f"[{thread_name}] Hoàn tất _execute_ytdlp. Thành công: {process_result}, Đường dẫn: {output_filepath}")
            # Trả về kết quả (True/False, đường dẫn file hoặc None)
            return (process_result, output_filepath)

    def save_config(self):
        """Lưu cấu hình Download vào master_app.cfg"""
        if not hasattr(self.master_app, 'cfg'):
            self.logger.error("master_app không có thuộc tính cfg")
            return
        
        self.master_app.cfg["download_playlist"] = self.download_playlist_var.get()
        self.master_app.cfg["download_path"] = self.download_path_var.get()
        self.master_app.cfg["download_mode"] = self.download_mode_var.get()
        self.master_app.cfg["download_video_quality"] = self.download_video_quality_var.get()
        self.master_app.cfg["download_audio_quality"] = self.download_audio_quality_var.get()
        self.master_app.cfg["download_sound_enabled"] = self.download_sound_var.get()
        self.master_app.cfg["download_sound_path"] = self.download_sound_path_var.get()
        self.master_app.cfg["download_shutdown_enabled"] = self.download_shutdown_var.get()
        self.master_app.cfg["download_rename_enabled"] = self.download_rename_var.get()
        self.master_app.cfg["download_rename_base_name"] = self.download_rename_box_var.get()
        self.master_app.cfg["download_stop_on_error"] = self.download_stop_on_error_var.get()
        self.master_app.cfg["download_auto_dub_after_sub"] = self.download_auto_dub_after_sub_var.get()
        self.master_app.cfg["auto_upload_after_download"] = self.auto_upload_after_download_var.get()
        self.master_app.cfg["download_use_cookies"] = self.download_use_cookies_var.get()
        self.master_app.cfg["download_cookies_path"] = self.download_cookies_path_var.get()
        
        self.logger.debug("[DownloadTab.save_config] Đã lưu cấu hình download vào master_app.cfg")

    def run_download(self, config_from_start):
        """
        Thực hiện quá trình tải xuống các URL.
        Luôn lấy URL tiếp theo từ đầu self.download_urls_list.
        Xử lý thử lại link lỗi và kiểm tra Sheet tự động khi hàng chờ trống.
        Sử dụng self.globally_completed_urls để không tải lại link đã thành công.
        """

        with keep_awake_helper(self.master_app, "Download media"):

            thread_name = threading.current_thread().name
            self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Bắt đầu (phiên bản động, retry, sheet, global_completed).")

            # Các biến theo dõi cho lượt chạy này của run_download
            successfully_downloaded_video_files_this_run = []
            error_links_encountered_this_run = [] 
            success_count_this_run = 0
            processed_count_this_run = 0
            successfully_created_task_objects_this_run = []
            
            # Cài đặt cho việc kiểm tra Sheet tự động
            last_sheet_check_time = 0 
            sheet_check_interval = config_from_start.get("sheet_check_interval_seconds", 60) # Lấy từ config hoặc mặc định 60s

            MAX_RETRIES_PER_LINK = config_from_start.get("max_retries_per_link", 2) # Lấy từ config hoặc mặc định 2

            attempted_final_sheet_check = False # Giữ nguyên cờ này

            while not self.master_app.stop_event.is_set():
                current_url_to_process = None

                # --- A. XỬ LÝ KHI HÀNG CHỜ TRỐNG HOẶC CHỈ CÓ LINK ĐÃ MAX_RETRIES (BAO GỒM KIỂM TRA SHEET) ---
                # Kiểm tra xem có cần fetch sheet không
                should_fetch_sheet = False
                if not self.download_urls_list: # Hàng chờ trống hoàn toàn
                    should_fetch_sheet = True
                    self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Hàng chờ trống, sẽ xem xét kiểm tra Sheet.")
                else: # Hàng chờ không trống, kiểm tra xem tất cả có phải đã max_retry không
                    all_remaining_are_max_retries = True
                    for url_in_q_check in self.download_urls_list:
                        if self.download_retry_counts.get(url_in_q_check, 0) < MAX_RETRIES_PER_LINK:
                            all_remaining_are_max_retries = False
                            break
                    if all_remaining_are_max_retries:
                        should_fetch_sheet = True
                        self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Hàng chờ chỉ còn các link đã max_retry, sẽ xem xét kiểm tra Sheet.")
                
                if should_fetch_sheet:
                    if self.master_app.disable_auto_sheet_check_var.get():
                        if not self.download_urls_list: # Chỉ thoát nếu hàng chờ thực sự rỗng và không được kiểm tra sheet
                            self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Hàng chờ trống (hoặc chỉ còn link max_retry) và người dùng đã tắt kiểm tra Sheet. Kết thúc tải.")
                            break 
                    else: 
                        current_time = time.time()
                        if (current_time - last_sheet_check_time > sheet_check_interval) or not attempted_final_sheet_check:
                            if not attempted_final_sheet_check:
                                self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Hàng chờ trống/chỉ còn link max_retry, thực hiện kiểm tra Sheet lần cuối/đầu khi rỗng hợp lệ.")
                            else:
                                self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Hàng chờ trống/chỉ còn link max_retry, đến giờ kiểm tra Google Sheet định kỳ...")
                            
                            attempted_final_sheet_check = True 

                            sheet_fetch_done_event = threading.Event()
                            local_links_from_sheet = None
                            local_fetch_success = False
                            local_error_msg = None

                            def after_sheet_fetch_callback(success, links_returned, error_msg):
                                nonlocal local_links_from_sheet, local_fetch_success, local_error_msg
                                local_fetch_success = success
                                if success and links_returned: local_links_from_sheet = links_returned
                                elif not success and error_msg: local_error_msg = error_msg
                                sheet_fetch_done_event.set()
                            
                            self.fetch_links_from_sheet(callback=after_sheet_fetch_callback, auto_triggered=True)
                            
                            self.logger.debug(f"[{thread_name}] RUN_DOWNLOAD: Đang chờ kết quả từ Google Sheet (timeout 30s)...")
                            sheet_fetch_done_event.wait(timeout=30)
                            last_sheet_check_time = time.time() 

                            if not sheet_fetch_done_event.is_set():
                                self.logger.warning(f"[{thread_name}] RUN_DOWNLOAD: Quá thời gian chờ lấy link từ Sheet hoặc callback có vấn đề.")
                            elif local_fetch_success and local_links_from_sheet is not None:
                                newly_added_to_main_list_count = 0
                                for link_fs in local_links_from_sheet:
                                    if link_fs not in self.download_urls_list and \
                                       link_fs not in self.globally_completed_urls: 
                                        self.download_urls_list.append(link_fs)
                                        self.download_retry_counts.pop(link_fs, None) 
                                        newly_added_to_main_list_count +=1
                                    elif link_fs in self.globally_completed_urls:
                                         self.logger.debug(f"[{thread_name}] RUN_DOWNLOAD: Bỏ qua link từ Sheet (đã hoàn thành trước đó): {link_fs[:60]}...")
                                    elif link_fs in self.download_urls_list:
                                         self.logger.debug(f"[{thread_name}] RUN_DOWNLOAD: Bỏ qua link từ Sheet (đã có trong hàng chờ): {link_fs[:60]}...")
                                if newly_added_to_main_list_count > 0:
                                    self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Đã thêm {newly_added_to_main_list_count} link MỚI từ Sheet.")
                                    self.master_app.after(0, self.update_download_queue_display)
                                    attempted_final_sheet_check = False
                                else:
                                    self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Sheet được kiểm tra, không có link thực sự mới.")
                            elif not local_fetch_success:
                                 self.logger.error(f"[{thread_name}] RUN_DOWNLOAD: Lỗi khi tự động lấy link từ Sheet: {local_error_msg}")
                            else: 
                                 self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Không có link nào được trả về từ Sheet.")

                        else: 
                            if not self.download_urls_list:
                                self.logger.debug(f"[{thread_name}] RUN_DOWNLOAD: Hàng chờ rỗng hoàn toàn, chưa đến giờ kiểm tra Sheet định kỳ, tạm dừng 5s.")
                                time.sleep(5) 
                                continue 
                
                # Điều kiện thoát nếu self.download_urls_list rỗng hoàn toàn sau mọi nỗ lực
                if not self.download_urls_list: 
                     self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Hàng chờ rỗng hoàn toàn. Kết thúc tải.")
                     break

                # --- B. CHỌN URL TIẾP THEO TỪ self.download_urls_list ĐỂ XỬ LÝ (ƯU TIÊN LINK MỚI) ---
                current_url_to_process = None
                url_chosen_for_processing_index = -1

                # Ưu tiên 1: Tìm link mới hoàn toàn (retry_count == 0 hoặc chưa có trong retry_counts)
                for i, url_in_q in enumerate(self.download_urls_list):
                    if self.download_retry_counts.get(url_in_q, 0) == 0: # Ưu tiên link chưa thử hoặc retry count là 0
                        url_chosen_for_processing_index = i
                        self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Ưu tiên link mới/chưa thử: '{url_in_q[:50]}...' ở vị trí {i}.")
                        break 
                
                # Ưu tiên 2: Nếu không có link mới, tìm link đã thử nhưng chưa max retries
                if url_chosen_for_processing_index == -1: # Không tìm thấy link mới hoàn toàn
                    for i, url_in_q in enumerate(self.download_urls_list):
                        if self.download_retry_counts.get(url_in_q, 0) < MAX_RETRIES_PER_LINK:
                            url_chosen_for_processing_index = i
                            self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Chọn link đã thử nhưng chưa max retries: '{url_in_q[:50]}...' ở vị trí {i}.")
                            break
                
                if url_chosen_for_processing_index != -1:
                    if url_chosen_for_processing_index > 0:
                        current_url_to_process = self.download_urls_list.pop(url_chosen_for_processing_index)
                        self.download_urls_list.insert(0, current_url_to_process)
                        self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Đã di chuyển link '{current_url_to_process[:50]}...' lên đầu hàng chờ.")
                    else: # url_chosen_for_processing_index == 0 (link hợp lệ đã ở đầu)
                        current_url_to_process = self.download_urls_list[0]
                else:

                    self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Không còn link hợp lệ để thử (tất cả đã lỗi quá {MAX_RETRIES_PER_LINK} lần hoặc hàng chờ trống sau khi lọc). Kết thúc tải.")
                    break 

                if not current_url_to_process:
                     self.logger.error(f"[{thread_name}] RUN_DOWNLOAD: Lỗi logic - Không xác định được current_url_to_process dù đã chọn index. Thoát.")
                     break

                # TẠO ĐỐI TƯỢNG TÁC VỤ CHO URL HIỆN TẠI
                task_object = {
                    'source': current_url_to_process,
                    'identifier': get_identifier_from_source(current_url_to_process),
                    'downloaded_video_path': None,  # Sẽ được cập nhật sau khi tải video
                    'downloaded_audio_path': None,  # Sẽ được cập nhật sau khi tải audio
                }
                self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Đã tạo Task Object với Identifier: '{task_object['identifier']}'")
                
                # --- C. XỬ LÝ URL ĐÃ CHỌN ---
                self.current_download_url = current_url_to_process
                processed_count_this_run += 1
                current_retry_for_url = self.download_retry_counts.get(current_url_to_process, 0)

                self.master_app.after(0, self.update_download_queue_display) # Cập nhật UI ngay khi chọn link
                self.master_app.after(0, lambda url=current_url_to_process, p=processed_count_this_run, retries=current_retry_for_url, total_q=len(self.download_urls_list): \
                    self.master_app.update_status(f"⏳ Đang tải link {p} (Thử {retries+1}, còn {total_q-1} chờ): {url[:45]}..."))
                self.master_app.after(0, lambda: self.update_download_progress(0))
                self.master_app.after(0, lambda url_log=current_url_to_process, retries=current_retry_for_url: \
                    self.log_download(f"\n🔗--- Đang xử lý link (Thử lần {retries+1}): {url_log} ---"))

                loop_start_time = time.time()
                link_overall_success = True
                video_filepath_result = None
                at_least_one_download_attempted = False

                # --- C.1. Tải Video ---
                if config_from_start.get("mode", "video") in ["video", "both"]:
                    at_least_one_download_attempted = True
                    if self.master_app.stop_event.is_set(): link_overall_success = False
                    else:
                        self.master_app.after(0, lambda: self.log_download("   🎬 Đang tải Video..."))
                        video_success, video_filepath_returned = self._execute_ytdlp(current_url_to_process, config_from_start, is_video=True, index=processed_count_this_run, task_object_ref=task_object)
                        if not video_success: link_overall_success = False
                        elif video_filepath_returned: video_filepath_result = video_filepath_returned
                
                # --- C.2. Tải MP3 ---
                should_download_mp3 = (config_from_start.get("mode", "video") in ["mp3", "both"])
                if should_download_mp3 and not self.master_app.stop_event.is_set() and \
                   (config_from_start.get("mode", "video") == "mp3" or link_overall_success): # Chỉ tải MP3 nếu mode là mp3 hoặc video (nếu có) đã thành công
                    at_least_one_download_attempted = True
                    if config_from_start.get("mode", "video") == "both": self.master_app.after(0, lambda: self.update_download_progress(0))
                    self.master_app.after(0, lambda: self.log_download("   🎵 Đang tải MP3..."))
                    mp3_success, _ = self._execute_ytdlp(current_url_to_process, config_from_start, is_video=False, index=processed_count_this_run, task_object_ref=task_object)
                    if not mp3_success: link_overall_success = False
                elif should_download_mp3 and not link_overall_success and config_from_start.get("mode", "video") == "both":
                     self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Chế độ 'both', video lỗi nên bỏ qua tải MP3 cho: {current_url_to_process}")
                     self.master_app.after(0, lambda url_log=current_url_to_process: self.log_download(f"   ⚠️ Video lỗi, bỏ qua MP3 cho: {url_log[:80]}..."))

                if not at_least_one_download_attempted and not self.master_app.stop_event.is_set():
                    link_overall_success = False # Coi như lỗi nếu không có gì được thử tải
                    self.logger.warning(f"[{thread_name}] RUN_DOWNLOAD: Không có tác vụ tải nào cho URL: {current_url_to_process} với chế độ {config_from_start.get('mode', 'video')}")
                    self.master_app.after(0, lambda url_log=current_url_to_process: self.log_download(f"   ⚠️ Không tải gì cho: {url_log[:80]}... (Chế độ: {config_from_start.get('mode', 'video')})"))
                    if current_url_to_process not in error_links_encountered_this_run: 
                        error_links_encountered_this_run.append(current_url_to_process)

                # --- C.3. Xử lý kết quả của link này ---
                if not self.master_app.stop_event.is_set(): 
                    loop_end_time = time.time()
                    duration = loop_end_time - loop_start_time
                    
                    if link_overall_success:
                        success_count_this_run += 1
                        self.master_app.after(0, lambda url_log=current_url_to_process, t=duration: self.log_download(f"   ✅ Hoàn thành Link: {url_log[:80]}... (Thời gian: {t:.2f}s)"))
                        if video_filepath_result and os.path.exists(video_filepath_result):
                            if video_filepath_result not in successfully_downloaded_video_files_this_run:
                                successfully_downloaded_video_files_this_run.append(video_filepath_result)

                        successfully_created_task_objects_this_run.append(task_object)
                        self.globally_completed_urls.add(current_url_to_process) # Đánh dấu đã hoàn thành toàn cục
                        self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Đã thêm '{current_url_to_process[:50]}...' vào globally_completed_urls.")
                        
                        try: # Xóa khỏi hàng chờ và retry_counts
                            if self.download_urls_list and self.download_urls_list[0] == current_url_to_process:
                                self.download_urls_list.pop(0)
                                self.download_retry_counts.pop(current_url_to_process, None)
                                self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Đã xóa URL thành công '{current_url_to_process[:50]}...' và reset retry.")
                            elif current_url_to_process in self.download_urls_list: 
                                self.download_urls_list.remove(current_url_to_process)
                                self.download_retry_counts.pop(current_url_to_process, None)
                                self.logger.warning(f"[{thread_name}] RUN_DOWNLOAD: URL thành công '{current_url_to_process[:50]}...' được xóa (và reset retry) nhưng không từ vị trí đầu.")
                            else: 
                                self.logger.warning(f"[{thread_name}] RUN_DOWNLOAD: URL thành công '{current_url_to_process[:50]}...' không tìm thấy để xóa/reset retry.")
                        except Exception as e_remove:
                            self.logger.error(f"[{thread_name}] RUN_DOWNLOAD: Lỗi khi xóa URL thành công '{current_url_to_process[:50]}...': {e_remove}")
                    
                    else: # link_overall_success is False (và không phải do stop_event)
                        self.master_app.after(0, lambda url_log=current_url_to_process, t=duration: self.log_download(f"   ⚠️ Hoàn thành Link với lỗi: {url_log[:80]}... (Thời gian: {t:.2f}s)"))
                        if current_url_to_process not in error_links_encountered_this_run: 
                             error_links_encountered_this_run.append(current_url_to_process)

                        current_retry_for_url_after_attempt = self.download_retry_counts.get(current_url_to_process, 0) + 1
                        self.download_retry_counts[current_url_to_process] = current_retry_for_url_after_attempt
                        self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: URL '{current_url_to_process[:50]}...' lỗi lần {current_retry_for_url_after_attempt}.")

                        if current_retry_for_url_after_attempt >= MAX_RETRIES_PER_LINK:
                            self.logger.warning(f"[{thread_name}] RUN_DOWNLOAD: URL '{current_url_to_process[:50]}...' đã lỗi {current_retry_for_url_after_attempt} lần. Sẽ không thử lại và giữ nguyên vị trí (sẽ bị bỏ qua ở vòng lặp sau).")
                            self.master_app.after(0, lambda url_log=current_url_to_process: self.log_download(f"   🚫 Link {url_log[:50]}... đã lỗi quá nhiều lần, sẽ không thử lại."))

                        else:
                            if self.download_urls_list and self.download_urls_list[0] == current_url_to_process:
                                if len(self.download_urls_list) > 1: 
                                    try:
                                        failed_url = self.download_urls_list.pop(0)
                                        self.download_urls_list.append(failed_url)
                                        self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Đã chuyển URL lỗi (thử lần {current_retry_for_url_after_attempt}) '{failed_url[:50]}...' xuống cuối.")
                                    except Exception as e_move_failed:
                                        self.logger.error(f"[{thread_name}] RUN_DOWNLOAD: Lỗi khi chuyển URL lỗi '{current_url_to_process[:50]}...': {e_move_failed}")
                                else: 
                                    self.logger.warning(f"[{thread_name}] RUN_DOWNLOAD: URL lỗi '{current_url_to_process[:50]}...' là mục duy nhất (thử {current_retry_for_url_after_attempt}), không di chuyển.")
                        
                        if config_from_start.get("stop_on_error", False):
                            self.master_app.after(0, lambda: self.log_download("\n✋ Đã bật 'Dừng khi lỗi'. Dừng xử lý!"))
                            self.master_app.stop_event.set() 
                
                if self.master_app.stop_event.is_set():
                    self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Phát hiện cờ dừng sau khi xử lý một link, thoát vòng lặp tải.")
                    break 
            
            # ===== KẾT THÚC VÒNG LẶP while not self.stop_event.is_set() =====
            self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Đã thoát vòng lặp tải chính.")

            # --- Khối finally: Dọn dẹp và Hoàn tất ---
            try:
                self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Vào khối finally.")
                self.current_download_url = None
                self.master_app.is_downloading = False 
                self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Đã đặt self.is_downloading = False")
                self.master_app.after(10, self.update_download_queue_display)

                final_message = ""
                should_auto_sub = False
                files_for_sub = [] 

                current_remaining_links_in_master_queue = getattr(self, 'download_urls_list', [])
                
                unique_links_attempted_count = success_count_this_run + len(set(error_links_encountered_this_run))

                if self.master_app.stop_event.is_set():
                    final_message = "\n🛑 Quá trình tải đã bị dừng (bởi người dùng hoặc lỗi)."
                    if current_remaining_links_in_master_queue : 
                         final_message += f"\n   (Còn {len(current_remaining_links_in_master_queue)} link trong hàng chờ chưa xử lý hoàn toàn.)"
                    should_auto_sub = False
                else: 
                    final_message = f"\n🏁 === TỔNG KẾT TẢI ===\n"

                    # --- THÊM THÔNG BÁO VỀ KIỂM TRA SHEET ---
                    if self.master_app.disable_auto_sheet_check_var.get():
                        final_message += "   (Tự động kiểm tra Google Sheet: Đã tắt bởi người dùng)\n"
                    else:
                        final_message += "   (Tự động kiểm tra Google Sheet: Đã bật)\n"
                    # -----------------------------------------

                    final_message += f"   - Tổng số lượt xử lý link trong lượt này: {processed_count_this_run}\n"

                    final_message += f"   - Số link tải thành công trong lượt này: {success_count_this_run}\n"
                    
                    # Thông tin về các link lỗi GẶP PHẢI trong lượt này
                    if error_links_encountered_this_run:
                        final_message += f"   - Số link gặp lỗi trong lượt này: {len(error_links_encountered_this_run)}\n"
                        for err_link in error_links_encountered_this_run[:3]: # Hiển thị tối đa 3 link lỗi cụ thể
                             retry_c_err = self.download_retry_counts.get(err_link, 0)
                             final_message += f"      - {err_link[:80]}... (Đã thử {retry_c_err} lần, tối đa {MAX_RETRIES_PER_LINK})\n"
                        if len(error_links_encountered_this_run) > 3:
                            final_message += f"      ... và {len(error_links_encountered_this_run) - 3} link lỗi khác.\n"

                    # Thông tin về các link CÒN LẠI trong hàng chờ (có thể là link lỗi đã max_retry, hoặc link chưa đến lượt nếu bị dừng)
                    if current_remaining_links_in_master_queue:
                        final_message += f"   - Link còn lại trong hàng chờ cuối cùng: {len(current_remaining_links_in_master_queue)}\n"
                        for rem_link in current_remaining_links_in_master_queue[:3]: 
                            retry_c_rem = self.download_retry_counts.get(rem_link, 0)
                            status_rem = f"(Đã thử {retry_c_rem} lần)" if retry_c_rem > 0 else "(Chưa thử/Đã reset)"
                            if retry_c_rem >= MAX_RETRIES_PER_LINK:
                                status_rem = f"(Đã thử {retry_c_rem} lần - Tối đa)"
                            final_message += f"      - {rem_link[:80]}... {status_rem}\n"
                        if len(current_remaining_links_in_master_queue) > 3:
                            final_message += f"      ... và {len(current_remaining_links_in_master_queue) - 3} link khác.\n"
                    elif not error_links_encountered_this_run and success_count_this_run == processed_count_this_run and processed_count_this_run > 0 : 
                         final_message += f"   🎉 Tất cả {success_count_this_run} link yêu cầu đã được xử lý thành công!\n"
                    elif processed_count_this_run == 0:
                         final_message += f"   ℹ️ Không có link nào được xử lý trong lượt này (hàng chờ có thể đã trống từ đầu).\n"


                    is_auto_sub_request = config_from_start.get("auto_sub_after_download", False)
                    if is_auto_sub_request:

                        verified_video_files = [f for f in successfully_downloaded_video_files_this_run if os.path.exists(f)] #Sửa thành _this_run
                        if verified_video_files:
                            should_auto_sub = True
                            files_for_sub = verified_video_files 
                            final_message += f"\n🔄 Đã tải xong {len(files_for_sub)} file video. Chuẩn bị tự động tạo phụ đề...\n"
                        else:
                            final_message += "\n⚠️ Yêu cầu tự động sub, nhưng không có file video hợp lệ nào được tải thành công để xử lý.\n"
                    else:
                         final_message += "\n(Không yêu cầu tự động sub).\n"

                    if config_from_start.get("do_sound", False) and config_from_start.get("sound_file") and _get_playsound_available(self.master_app):
                       self.master_app.after(100, lambda: self.log_download(" 🔊 Đang phát âm thanh hoàn tất tải..."))
                       play_sound_async(config_from_start["sound_file"]) # Đã sửa ở bước trước

                self.master_app.after(150, lambda msg=final_message: self.log_download(msg))

                final_status_text = "✅ Tải hoàn tất!" 
                if self.master_app.stop_event.is_set(): 
                    final_status_text = "🛑 Đã dừng bởi người dùng/lỗi."
                elif current_remaining_links_in_master_queue: 
                    final_status_text = f"⚠️ Hoàn tất với {len(current_remaining_links_in_master_queue)} link còn lại/lỗi."
                elif should_auto_sub: 
                    final_status_text = f"✅ Tải xong {len(files_for_sub)} video! Đang chuyển sang Sub..."
                
                self.master_app.after(200, lambda text=final_status_text: self.master_app.update_status(text))

                if not should_auto_sub: 
                    self.master_app.after(250, lambda: self.set_download_ui_state(downloading=False))

                if not self.master_app.stop_event.is_set() and not should_auto_sub:
                     self.master_app.after(250, lambda: self.update_download_progress(0))

                # Lấy trạng thái của checkbox Tự động Upload
                is_auto_upload_request = self.auto_upload_after_download_var.get()

                if should_auto_sub:
                    # Ưu tiên chuỗi Sub -> Dub/Upload trước (logic này đã xử lý việc upload sau sub)
                    self.master_app.after(500, self.master_app._trigger_auto_sub, successfully_created_task_objects_this_run, config_from_start.get("and_then_dub", False))
                    self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Gọi _trigger_auto_sub với {len(successfully_created_task_objects_this_run)} task objects...")
                
                # <<< BẮT ĐẦU THAY ĐỔI CHÍNH Ở ĐÂY >>>
                elif is_auto_upload_request and successfully_created_task_objects_this_run:
                    # Nếu chỉ bật Auto Upload (không bật Auto Sub)
                    self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Chuẩn bị thêm {len(successfully_created_task_objects_this_run)} video đã tải vào hàng chờ Upload.")
                    self.master_app.after(0, lambda: self.master_app.update_status(f"✅ Tải xong! Đang thêm vào hàng chờ Upload..."))

                    # Lặp qua các task object đã tạo và thêm vào hàng chờ upload
                    for task_obj in successfully_created_task_objects_this_run:
                        # Việc gọi self.after ở đây sẽ đảm bảo các tác vụ thêm vào hàng chờ được thực hiện tuần tự trên luồng chính
                        self.master_app.after(10, self.master_app._add_completed_video_to_upload_queue, task_obj)
                    
                    # SAU KHI ĐÃ LÊN LỊCH THÊM VÀO HÀNG CHỜ, BÂY GIỜ CHÚNG TA SẼ KÍCH HOẠT QUÁ TRÌNH UPLOAD
                    def start_upload_chain():
                        self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Kích hoạt _start_youtube_batch_upload sau khi đã thêm file từ Download.")
                        # Chuyển sang tab Upload cho người dùng thấy
                        try:
                            upload_tab_value = "📤 Upload YT" 
                            if hasattr(self.master_app, 'view_switcher') and self.master_app.view_switcher.get() != upload_tab_value:
                                self.master_app.view_switcher.set(upload_tab_value)
                                self.master_app.switch_view(upload_tab_value)
                        except Exception as e_switch:
                            self.logger.error(f"[{thread_name}] Lỗi khi tự động chuyển sang tab Upload: {e_switch}")

                        self.master_app._start_youtube_batch_upload()

                    # Lên lịch để bắt đầu chuỗi upload sau một khoảng trễ nhỏ (ví dụ 500ms)
                    # để đảm bảo các tác vụ "thêm vào hàng chờ" đã được thực hiện xong.
                    self.master_app.after(500, start_upload_chain)

                else:
                    # Trường hợp không có chuỗi tự động nào, chỉ dọn dẹp và kết thúc
                    self.master_app.after(250, lambda: self.set_download_ui_state(downloading=False))
                    self.master_app.after(600, self.master_app._check_completion_and_shutdown) 

                self.download_thread = None 
                self.logger.info(f"[{thread_name}] RUN_DOWNLOAD: Đã hoàn tất khối finally và kết thúc.")

            except Exception as e_final_outer: 
                self.logger.critical(f"[{thread_name}] RUN_DOWNLOAD: LỖI NGHIÊM TRỌNG không xử lý được: {e_final_outer}", exc_info=True)
                self.master_app.after(0, lambda: self.set_download_ui_state(downloading=False)) 
                self.master_app.after(0, lambda: self.master_app.update_status(f"❌ Lỗi nghiêm trọng khi tải!"))
                self.master_app.is_downloading = False 
                self.current_download_url = None
                self.download_thread = None
