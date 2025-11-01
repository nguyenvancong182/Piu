# -*- coding: utf-8 -*-
# File: ui/tabs/youtube_upload_tab.py

import customtkinter as ctk
import os
import logging
import threading
import time
import json
import shutil
import random
import re
from contextlib import contextmanager

# Import các thành phần UI chung
from config.ui_constants import get_theme_colors
from ui.widgets.tooltip import Tooltip

# Import các hàm tiện ích
from utils.helpers import get_default_downloads_folder, get_identifier_from_source, play_sound_async, sanitize_youtube_text, normalize_string_for_comparison
from ui.utils.ui_helpers import update_path_label
from config.constants import (
    APP_NAME, YOUTUBE_CATEGORIES, YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, 
    TOKEN_FILENAME, YOUTUBE_CATEGORY_NAVIGATION_ORDER
)
from config.settings import get_config_path
from tkinter import filedialog, messagebox

# Import các service và utilities
from services.google_api_service import get_google_api_service
from services.youtube_browser_upload_service import click_with_fallback, YOUTUBE_LOCATORS
from services.youtube_service import YouTubeService
from utils.keep_awake import KeepAwakeManager
from utils.system_utils import cleanup_stale_chrome_processes
from utils.logging_utils import log_failed_task

# Selenium imports (optional)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException,
        ElementClickInterceptedException,
        StaleElementReferenceException,
        WebDriverException,
        NoSuchWindowException,
        NoSuchElementException
    )
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_SELENIUM = True
except ImportError:
    webdriver = None
    Service = None
    By = None
    Keys = None
    ActionChains = None
    WebDriverWait = None
    EC = None
    ChromeDriverManager = None
    HAS_SELENIUM = False

# Google API imports
try:
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    HAS_GOOGLE_API = True
except ImportError:
    MediaFileUpload = None
    HttpError = None
    HAS_GOOGLE_API = False


class YouTubeUploadTab(ctk.CTkFrame):
    """
    Lớp quản lý toàn bộ giao diện cho Tab Upload YouTube.
    """

    def __init__(self, master, master_app):
        """
        Khởi tạo frame cho Tab Upload YouTube.

        Args:
            master (ctk.CTkFrame): Frame cha (main_content_frame từ SubtitleApp).
            master_app (SubtitleApp): Instance của ứng dụng chính (PiuApp).
        """
        super().__init__(master, fg_color="transparent")
        self.master_app = master_app
        self.logger = logging.getLogger(APP_NAME)

        # ========================================================================
        # BIẾN TRẠNG THÁI (State) - Di chuyển từ Piu.py
        # ========================================================================
        
        # Biến video và thông tin
        self.youtube_video_path_var = ctk.StringVar(value="") # Đường dẫn video đã chọn để upload
        self.youtube_title_var = ctk.StringVar(value=self.master_app.cfg.get("youtube_last_title", ""))      # Tiêu đề video
        self.youtube_description_var = ctk.StringVar(value="") # Mô tả video
        self.youtube_tags_var = ctk.StringVar(value=self.master_app.cfg.get("youtube_last_tags", ""))       # Thẻ tag (cách nhau bởi dấu phẩy)
        self.youtube_playlist_var = ctk.StringVar(value=self.master_app.cfg.get("youtube_playlist_name", "")) # Biến mới cho tên danh sách phát
        
        # YouTube upload queue - delegate to YouTubeService
        # Keep for backward compatibility with existing code
        self.youtube_upload_queue = self.master_app.youtube_service.queue  # Reference to service queue
        self.youtube_currently_processing_task_id = None # Theo dõi ID của tác vụ đang chạy (sync với service)
        
        # Auto-fill và metadata
        self.youtube_autofill_var = ctk.BooleanVar(value=self.master_app.cfg.get("youtube_autofill_enabled", False))
        self.metadata_auto_increment_thumb_var = ctk.BooleanVar(value=self.master_app.cfg.get("metadata_auto_increment_thumb", True))
        
        # Trạng thái riêng tư và danh mục
        self.youtube_privacy_status_var = ctk.StringVar(value=self.master_app.cfg.get("youtube_default_privacy", "private"))
        self.youtube_category_id_var = ctk.StringVar(value=self.master_app.cfg.get("youtube_default_category_id", '2'))
        
        # Trạng thái upload
        self.is_uploading_youtube = False # Cờ theo dõi trạng thái upload YouTube
        
        # Biến cho checkbox "Upload lên YouTube sau khi hoàn tất chuỗi tự động"
        self.auto_upload_to_youtube_var = ctk.BooleanVar(value=self.master_app.cfg.get("auto_upload_to_youtube", False))
        self.youtube_thumbnail_path_var = ctk.StringVar(value="") # Đường dẫn file thumbnail
        self.youtube_fetch_metadata_var = ctk.BooleanVar(value=self.master_app.cfg.get("youtube_fetch_metadata_enabled", False))
        
        # Thêm các biến MỚI cho phương pháp upload trình duyệt
        self.youtube_upload_method_var = ctk.StringVar(value=self.master_app.cfg.get("youtube_upload_method", "api")) # "api" hoặc "browser"
        self.chrome_portable_path_var = ctk.StringVar(value=self.master_app.cfg.get("chrome_portable_path", ""))
        self.chromedriver_path_var = ctk.StringVar(value=self.master_app.cfg.get("chromedriver_path", ""))
        self.youtube_headless_var = ctk.BooleanVar(value=self.master_app.cfg.get("youtube_run_headless", True)) # Mặc định là True (ẩn)
        
        # BIẾN MỚI CHO MÀN HÌNH KẾT THÚC VÀ THẺ
        self.youtube_add_end_screen_var = ctk.BooleanVar(value=self.master_app.cfg.get("youtube_add_end_screen", False))
        self.youtube_add_cards_var = ctk.BooleanVar(value=self.master_app.cfg.get("youtube_add_cards", False))

        # Khai báo các widget con của tab này (sẽ được gán trong _build_ui)
        # Action buttons
        self.youtube_select_video_button = None
        self.youtube_start_upload_button = None
        self.youtube_stop_upload_button = None
        self.youtube_add_to_queue_button = None
        
        # Auto upload
        self.auto_upload_checkbox = None
        
        # Thumbnail
        self.youtube_thumbnail_path_display_label = None
        self.youtube_select_thumbnail_button = None
        
        # Video info
        self.youtube_video_path_display_label = None
        self.youtube_fetch_metadata_checkbox = None
        self.youtube_autofill_checkbox = None
        self.youtube_title_entry = None
        self.youtube_description_textbox = None
        self.youtube_tags_entry = None
        self.youtube_playlist_entry = None
        self.youtube_privacy_optionmenu = None
        self.youtube_category_display_var = None
        self.youtube_category_optionmenu = None
        self.youtube_add_end_screen_checkbox = None
        self.youtube_add_cards_checkbox = None
        
        # Upload method
        self.upload_method_radio_api = None
        self.upload_method_radio_browser = None
        self.chrome_portable_config_frame = None
        self.headless_checkbox = None
        self.chrome_portable_path_display_label = None
        self.chromedriver_path_display_label = None
        
        # Right panel
        self.youtube_queue_display_frame = None
        self.manage_metadata_button = None
        self.youtube_clear_log_button = None
        self.youtube_log_textbox = None
        self.youtube_log_textbox_placeholder = "[Log và trạng thái upload YouTube sẽ hiển thị ở đây.]"
        self.youtube_progress_bar = None

        # Gọi hàm xây dựng UI
        self._build_ui()

        self.logger.info("YouTubeUploadTab đã được khởi tạo.")

    def _build_ui(self):
        """
        Tạo các thành phần UI cho tab Upload YouTube.
        (Đây là hàm _create_youtube_upload_tab cũ, đã được di chuyển sang đây)
        """
        self.logger.debug("[YouTubeUploadUI] Đang tạo UI cho tab Upload YouTube...")

        colors = get_theme_colors()
        panel_bg_color = colors["panel_bg"]
        card_bg_color = colors["card_bg"]
        textbox_bg_color = colors["textbox_bg"]
        danger_button_color = colors["danger_button"]
        danger_button_hover_color = colors["danger_button_hover"]
        special_action_button_color = colors["special_action_button"]
        special_action_hover_color = colors["special_action_hover"]

        main_frame_upload = ctk.CTkFrame(self, fg_color="transparent")
        main_frame_upload.pack(fill="both", expand=True)
        
        main_frame_upload.grid_columnconfigure(0, weight=1, uniform="panelgroup")
        main_frame_upload.grid_columnconfigure(1, weight=2, uniform="panelgroup")
        main_frame_upload.grid_rowconfigure(0, weight=1)

        left_panel_upload_container = ctk.CTkFrame(main_frame_upload, fg_color=panel_bg_color, corner_radius=12)
        left_panel_upload_container.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        left_panel_upload_container.pack_propagate(False)

        left_upload_scrollable_content = ctk.CTkScrollableFrame(
            left_panel_upload_container,
            fg_color="transparent"
        )
        left_upload_scrollable_content.pack(expand=True, fill="both", padx=0, pady=0)

        # === CỤM NÚT HÀNH ĐỘNG CHÍNH (UPLOAD) ===
        self._create_youtube_action_buttons_section(left_upload_scrollable_content, danger_button_color, danger_button_hover_color)

        # Auto-upload checkbox
        self._create_youtube_auto_upload_section(left_upload_scrollable_content, card_bg_color)

        # Video information section
        self._create_youtube_video_info_section(left_upload_scrollable_content, card_bg_color)

        # Thumbnail selection (nằm dưới checkbox "Thêm MH kết thúc" và trên "Phương thức Upload")
        self._create_youtube_thumbnail_section(left_upload_scrollable_content, card_bg_color)

        # Upload method section
        self._create_youtube_upload_method_section(left_upload_scrollable_content, card_bg_color)

        # Right panel with queue, log, and progress
        self._create_youtube_right_panel(main_frame_upload, panel_bg_color, textbox_bg_color)
        
        self.logger.debug("[YouTubeUploadUI] Tạo UI cho tab Upload YouTube hoàn tất.")
        self.master_app.after(100, self._update_youtube_ui_state, False)

    # ========================================================================
    # UI CREATION METHODS - Di chuyển từ Piu.py
    # ========================================================================

    def _create_youtube_action_buttons_section(self, parent_frame, danger_button_color, danger_button_hover_color):
        """
        Create action buttons section for YouTube upload tab.
        
        Args:
            parent_frame: Parent frame to add buttons to
            danger_button_color: Color tuple for danger button
            danger_button_hover_color: Hover color tuple for danger button
            
        Returns:
            Frame containing action buttons
        """
        action_buttons_main_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        action_buttons_main_frame.pack(pady=10, padx=10, fill="x")
        action_buttons_main_frame.grid_columnconfigure((0, 1), weight=1)

        self.youtube_select_video_button = ctk.CTkButton(
            action_buttons_main_frame, text="📁 Chọn Video Upload...", height=38, font=("Segoe UI", 14, "bold"),
            command=self._select_youtube_video_file
        )
        self.youtube_select_video_button.grid(row=0, column=0, columnspan=2, pady=5, sticky="ew")

        self.youtube_start_upload_button = ctk.CTkButton(
            action_buttons_main_frame, text="📤 Bắt đầu Upload Hàng loạt", height=45, font=("Segoe UI", 15, "bold"),
            command=self._start_youtube_batch_upload 
        )
        self.youtube_start_upload_button.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        self.youtube_stop_upload_button = ctk.CTkButton(
            action_buttons_main_frame, text="🛑 Dừng Upload", height=35, font=("Segoe UI", 13, "bold"),
            command=self._stop_youtube_upload, fg_color=danger_button_color, hover_color=danger_button_hover_color,
            state=ctk.DISABLED, border_width=0
        )
        self.youtube_stop_upload_button.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="ew")
        
        self.youtube_add_to_queue_button = ctk.CTkButton(
            action_buttons_main_frame, text="➕ Thêm Hàng Chờ", height=35, font=("Segoe UI", 13, "bold"),
            command=self._add_youtube_task_to_queue
        )
        self.youtube_add_to_queue_button.grid(row=2, column=1, padx=(5, 0), pady=5, sticky="ew")
        
        return action_buttons_main_frame

    def _create_youtube_auto_upload_section(self, parent_frame, card_bg_color):
        """
        Create auto-upload checkbox section for YouTube upload tab.
        
        Args:
            parent_frame: Parent frame to add section to
            card_bg_color: Background color tuple for the card frame
        """
        auto_upload_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        auto_upload_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.auto_upload_checkbox = ctk.CTkCheckBox(
            auto_upload_frame,
            text="🚀Tự động Upload (Sau chuỗi tự động hoàn tất)",
            variable=self.auto_upload_to_youtube_var,
            font=("Segoe UI", 12, "bold"),
            checkbox_height=18, checkbox_width=18,
            command=self.master_app.save_current_config 
        )
        self.auto_upload_checkbox.pack(pady=10, padx=10, anchor="w")

    def _create_youtube_thumbnail_section(self, parent_frame, card_bg_color):
        """
        Create thumbnail selection section for YouTube upload tab.
        
        Args:
            parent_frame: Parent frame to add section to
            card_bg_color: Background color tuple for the card frame
        """
        thumbnail_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        thumbnail_frame.pack(fill="x", padx=10, pady=(0, 10))
        thumbnail_frame.grid_columnconfigure(0, weight=1)
        thumbnail_frame.grid_columnconfigure(1, weight=0, minsize=110)
        
        ctk.CTkLabel(thumbnail_frame, text="🖼 Ảnh Thumbnail (Tùy chọn):", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(5,2), sticky="w")
        self.youtube_thumbnail_path_display_label = ctk.CTkLabel(thumbnail_frame, text="(Chưa chọn ảnh)", wraplength=200, anchor="w", text_color=("gray30", "gray70"), font=("Segoe UI", 10))
        self.youtube_thumbnail_path_display_label.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")
        self.youtube_select_thumbnail_button = ctk.CTkButton(thumbnail_frame, text="Chọn Ảnh...", width=110, command=self._select_youtube_thumbnail)
        self.youtube_select_thumbnail_button.grid(row=1, column=1, padx=10, pady=(0,10), sticky="e")

    def _create_youtube_video_info_section(self, parent_frame, card_bg_color):
        """
        Create video information section for YouTube upload.
        
        Args:
            parent_frame: Parent frame to add section to
            card_bg_color: Background color for card frames
        """
        video_info_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        video_info_frame.pack(fill="x", padx=10, pady=(5, 10))
      
        ctk.CTkLabel(video_info_frame, text="🎬 Thông tin Video:", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=10, pady=(5,2))
        ctk.CTkLabel(video_info_frame, text="Đường dẫn Video:", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        self.youtube_video_path_display_label = ctk.CTkLabel(video_info_frame, textvariable=self.youtube_video_path_var, wraplength=340, anchor="w", text_color=("gray30", "gray70"), font=("Segoe UI", 10))
        self.youtube_video_path_display_label.pack(fill="x", padx=10, pady=(0, 5))
        self.youtube_video_path_var.trace_add("write", lambda *a: self._update_youtube_path_label_display())
        
        # Title header with metadata checkboxes
        title_header_frame = ctk.CTkFrame(video_info_frame, fg_color="transparent")
        title_header_frame.pack(fill="x", padx=10, pady=(2,0))
        title_header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(title_header_frame, text="Tiêu đề:", anchor="w", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w")
        
        # Fetch metadata checkbox
        self.youtube_fetch_metadata_checkbox = ctk.CTkCheckBox(
            title_header_frame, text="Lấy metadata",
            variable=self.youtube_fetch_metadata_var, font=("Segoe UI", 11),
            checkbox_height=18, checkbox_width=18,
            command=lambda: self._on_metadata_checkbox_toggled('fetch')
        )
        self.youtube_fetch_metadata_checkbox.grid(row=0, column=1, padx=(0, 5), sticky="e")
        Tooltip(self.youtube_fetch_metadata_checkbox, "Khi chọn video, tự động điền thông tin từ file Master Metadata (nếu có)")
        
        # Autofill checkbox
        self.youtube_autofill_checkbox = ctk.CTkCheckBox(
            title_header_frame, text="Lấy theo tên file",
            variable=self.youtube_autofill_var, font=("Segoe UI", 11),
            checkbox_height=18, checkbox_width=18,
            command=lambda: self._on_metadata_checkbox_toggled('autofill')
        )
        self.youtube_autofill_checkbox.grid(row=0, column=2, sticky="e")
        Tooltip(self.youtube_autofill_checkbox, "Khi chọn video, tự động điền Tiêu đề bằng tên file video")
        
        self.youtube_title_entry = ctk.CTkEntry(video_info_frame, textvariable=self.youtube_title_var, font=("Segoe UI", 12))
        self.youtube_title_entry.pack(fill="x", padx=10, pady=(0,5))
        
        ctk.CTkLabel(video_info_frame, text="Mô tả:", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        self.youtube_description_textbox = ctk.CTkTextbox(video_info_frame, height=80, wrap="word", font=("Segoe UI", 12))
        self.youtube_description_textbox.pack(fill="x", padx=10, pady=(0,5))
        saved_description = self.master_app.cfg.get("youtube_last_description", "")
        if saved_description:
            self.youtube_description_textbox.insert("1.0", saved_description)
            
        ctk.CTkLabel(video_info_frame, text="Thẻ tag (phân cách bởi dấu phẩy):", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        self.youtube_tags_entry = ctk.CTkEntry(video_info_frame, textvariable=self.youtube_tags_var, font=("Segoe UI", 12))
        self.youtube_tags_entry.pack(fill="x", padx=10, pady=(0,5))
        
        ctk.CTkLabel(video_info_frame, text="Danh sách phát (nhập chính xác tên):", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        self.youtube_playlist_entry = ctk.CTkEntry(video_info_frame, textvariable=self.youtube_playlist_var, font=("Segoe UI", 12))
        self.youtube_playlist_entry.pack(fill="x", padx=10, pady=(0,5))
        
        ctk.CTkLabel(video_info_frame, text="Trạng thái riêng tư:", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        privacy_options = ["private", "unlisted", "public"]
        self.youtube_privacy_optionmenu = ctk.CTkOptionMenu(video_info_frame, variable=self.youtube_privacy_status_var, values=privacy_options)
        self.youtube_privacy_optionmenu.pack(fill="x", padx=10, pady=(0,10))

        ctk.CTkLabel(video_info_frame, text="Danh mục Video:", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        # Get category name from ID
        self.youtube_category_display_var = ctk.StringVar(
            value=YOUTUBE_CATEGORIES.get(self.youtube_category_id_var.get(), "Giải trí")
        )
        # Function called when user selects a menu item
        def on_category_select(selected_display_name):
            # Find ID corresponding to selected name and update main variable
            for cat_id, cat_name in YOUTUBE_CATEGORIES.items():
                if cat_name == selected_display_name:
                    self.youtube_category_id_var.set(cat_id)
                    break
        
        self.youtube_category_optionmenu = ctk.CTkOptionMenu(
            video_info_frame, 
            variable=self.youtube_category_display_var,
            values=list(YOUTUBE_CATEGORIES.values()),
            command=on_category_select
        )
        self.youtube_category_optionmenu.pack(fill="x", padx=10, pady=(0,10))

        # Frame containing options for Video Elements (End Screen, Cards)
        video_elements_frame = ctk.CTkFrame(video_info_frame, fg_color="transparent")
        video_elements_frame.pack(fill="x", padx=10, pady=(0, 10))
        video_elements_frame.grid_columnconfigure((0, 1), weight=1)

        self.youtube_add_end_screen_checkbox = ctk.CTkCheckBox(
            video_elements_frame,
            text="Thêm MH kết thúc",
            variable=self.youtube_add_end_screen_var,
            font=("Segoe UI", 11),
            checkbox_height=18, checkbox_width=18,
            command=self.master_app.save_current_config
        )
        self.youtube_add_end_screen_checkbox.grid(row=0, column=0, sticky="w")
        Tooltip(self.youtube_add_end_screen_checkbox, "Tự động thêm Màn hình kết thúc bằng cách 'Nhập từ video gần nhất'.")

        self.youtube_add_cards_checkbox = ctk.CTkCheckBox(
            video_elements_frame,
            text="Thêm Thẻ video",
            variable=self.youtube_add_cards_var,
            font=("Segoe UI", 11),
            checkbox_height=18, checkbox_width=18,
            command=self.master_app.save_current_config
        )
        self.youtube_add_cards_checkbox.grid(row=0, column=1, sticky="e")
        Tooltip(self.youtube_add_cards_checkbox, "Tự động thêm một Thẻ gợi ý video gần nhất.")

    def _create_youtube_upload_method_section(self, parent_frame, card_bg_color):
        """
        Create upload method section with API and Browser options.
        
        Args:
            parent_frame: Parent frame to add section to
            card_bg_color: Background color for card frames
        """
        upload_method_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        upload_method_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(upload_method_frame, text="Phương thức Upload:", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=10, pady=(5,2))
        self.upload_method_radio_api = ctk.CTkRadioButton(
            upload_method_frame, text="API (Mặc định)", variable=self.youtube_upload_method_var, value="api",
            command=lambda: self._on_upload_method_changed(self.youtube_upload_method_var.get()), 
            font=("Segoe UI", 12)
        )
        self.upload_method_radio_api.pack(anchor="w", padx=10, pady=5)
        self.upload_method_radio_browser = ctk.CTkRadioButton(
            upload_method_frame, text="Trình duyệt (Chrome Portable)", variable=self.youtube_upload_method_var, value="browser",
            command=lambda: self._on_upload_method_changed(self.youtube_upload_method_var.get()), 
            font=("Segoe UI", 12)
        )
        self.upload_method_radio_browser.pack(anchor="w", padx=10, pady=5)

        self.chrome_portable_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)

        # Small frame containing checkbox for better alignment
        headless_frame = ctk.CTkFrame(self.chrome_portable_config_frame, fg_color="transparent")
        headless_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.headless_checkbox = ctk.CTkCheckBox(
            headless_frame,
            text="Ẩn trình duyệt khi upload (Headless Mode)",
            variable=self.youtube_headless_var,
            font=("Segoe UI", 12)
        )
        self.headless_checkbox.pack(anchor="w")

        ctk.CTkLabel(self.chrome_portable_config_frame, text="Cấu hình Chrome Portable:", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=10, pady=(5,2))
        chrome_portable_path_frame = ctk.CTkFrame(self.chrome_portable_config_frame, fg_color="transparent")
        chrome_portable_path_frame.pack(fill="x", padx=10, pady=(5,0))
        chrome_portable_path_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(chrome_portable_path_frame, text="Đường dẫn Chrome.exe:", anchor="w", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w")
        self.chrome_portable_path_display_label = ctk.CTkLabel(chrome_portable_path_frame, textvariable=self.chrome_portable_path_var, wraplength=200, anchor="w", text_color=("gray30", "gray70"), font=("Segoe UI", 10))
        self.chrome_portable_path_display_label.grid(row=1, column=0, padx=(0,5), sticky="ew")
        chrome_portable_browse_button = ctk.CTkButton(chrome_portable_path_frame, text="Duyệt...", width=80, command=self._browse_chrome_portable_path)
        chrome_portable_browse_button.grid(row=1, column=1, sticky="e")
        
        chromedriver_path_frame = ctk.CTkFrame(self.chrome_portable_config_frame, fg_color="transparent")
        chromedriver_path_frame.pack(fill="x", padx=10, pady=(5,10))
        chromedriver_path_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(chromedriver_path_frame, text="Đường dẫn ChromeDriver.exe:", anchor="w", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w")
        self.chromedriver_path_display_label = ctk.CTkLabel(chromedriver_path_frame, textvariable=self.chromedriver_path_var, wraplength=200, anchor="w", text_color=("gray30", "gray70"), font=("Segoe UI", 10))
        self.chromedriver_path_display_label.grid(row=1, column=0, padx=(0,5), sticky="ew")
        chromedriver_browse_button = ctk.CTkButton(chromedriver_path_frame, text="Duyệt...", width=80, command=self._browse_chromedriver_path)
        chromedriver_browse_button.grid(row=1, column=1, sticky="e")
        self.master_app.after(100, self._on_upload_method_changed, self.youtube_upload_method_var.get())

    def _create_youtube_right_panel(self, main_frame, panel_bg_color, textbox_bg_color):
        """
        Create right panel with queue, log, and progress bar.
        
        Args:
            main_frame: Main frame to add panel to
            panel_bg_color: Background color for panel
            textbox_bg_color: Background color for textbox
        """
        right_panel_upload = ctk.CTkFrame(main_frame, fg_color=panel_bg_color, corner_radius=12)
        right_panel_upload.grid(row=0, column=1, pady=0, sticky="nsew")
        
        self.youtube_queue_display_frame = ctk.CTkScrollableFrame(
            right_panel_upload,
            label_text="📋 Hàng chờ Upload",
            label_font=("Poppins", 14, "bold"),
            height=200 
        )
        self.youtube_queue_display_frame.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(self.youtube_queue_display_frame, text="[Hàng chờ upload trống]", font=("Segoe UI", 11), text_color="gray").pack(pady=20)
        
        log_section_frame_upload = ctk.CTkFrame(right_panel_upload, fg_color="transparent")
        log_section_frame_upload.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        log_section_frame_upload.grid_rowconfigure(1, weight=1)
        log_section_frame_upload.grid_columnconfigure(0, weight=1)

        # Log header with buttons
        log_header_upload = ctk.CTkFrame(log_section_frame_upload, fg_color="transparent")
        log_header_upload.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        log_header_upload.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(log_header_upload, text="📜 Log Upload:", font=("Poppins", 15, "bold")).grid(row=0, column=0, sticky="w")

        header_buttons_container = ctk.CTkFrame(log_header_upload, fg_color="transparent")
        header_buttons_container.grid(row=0, column=2, sticky="e")

        self.manage_metadata_button = ctk.CTkButton(
            header_buttons_container, text="🗂 Quản lý Metadata...",
            height=28, font=("Poppins", 11),
            command=self.master_app._open_metadata_manager
        )
        self.manage_metadata_button.pack(side="left", padx=(0, 5))

        self.youtube_clear_log_button = ctk.CTkButton(
            header_buttons_container, text="Clear Log",
            height=28, font=("Poppins", 11),
            command=self._clear_youtube_log
        )
        self.youtube_clear_log_button.pack(side="left", padx=(0, 0))

        self.youtube_log_textbox = ctk.CTkTextbox(log_section_frame_upload, wrap="word", font=("Consolas", 12), state="disabled", fg_color=textbox_bg_color, border_width=1)
        self.youtube_log_textbox.grid(row=1, column=0, sticky="nsew", padx=0, pady=(2,0))
        self.youtube_log_textbox.configure(state="normal")
        self.youtube_log_textbox.insert("1.0", self.youtube_log_textbox_placeholder)
        self.youtube_log_textbox.configure(state="disabled")
        
        self.youtube_progress_bar = ctk.CTkProgressBar(right_panel_upload, orientation="horizontal", height=15, mode="determinate")
        self.youtube_progress_bar.pack(fill="x", padx=10, pady=(5, 10), side="bottom")
        self.youtube_progress_bar.configure(
            progress_color=("#10B981", "#34D399"),
            fg_color=("#D4D8DB", "#4A4D50")
        )
        self.youtube_progress_bar.set(1.0)

    # ========================================================================
    # UI HELPER METHODS - Di chuyển từ Piu.py
    # ========================================================================

    def _update_youtube_path_label_display(self):
        """Cập nhật label hiển thị đường dẫn video đã chọn."""
        path = self.youtube_video_path_var.get()
        if hasattr(self, 'youtube_video_path_display_label') and self.youtube_video_path_display_label.winfo_exists():
            display_text = os.path.basename(path) if path else "(Chưa chọn video)"
            self.youtube_video_path_display_label.configure(text=display_text)

            # Nếu path có giá trị, tự động điền Tiêu đề mặc định (nếu Tiêu đề đang trống)
            if path and not self.youtube_title_var.get().strip():
                # Tiêu đề mặc định là tên file (bỏ đuôi mở rộng)
                default_title = os.path.splitext(os.path.basename(path))[0]
                self.youtube_title_var.set(default_title)
                self.logger.info(f"[YouTubeUI] Tự động điền tiêu đề: '{default_title}'")

            # Sau khi cập nhật, kiểm tra lại trạng thái các nút upload
            self._update_youtube_ui_state(self.is_uploading_youtube)

    def _perform_autofill_if_needed(self):
        """
        Kiểm tra xem checkbox autofill có được bật không VÀ có file video hợp lệ không.
        Nếu có, sẽ tự động điền tiêu đề. Hàm này an toàn để gọi bất cứ lúc nào.
        """
        # Chỉ thực hiện nếu checkbox đang được bật
        if not (hasattr(self, 'youtube_autofill_var') and self.youtube_autofill_var.get()):
            return

        video_path = self.youtube_video_path_var.get()
        
        # Nếu không có đường dẫn video thì không làm gì cả (và không bỏ tick checkbox)
        if not video_path or not os.path.exists(video_path):
            return

        # Nếu có đủ điều kiện, thực hiện điền tiêu đề
        self.logger.info("[YouTubeUI] Autofill được kích hoạt sau khi chọn file.")
        default_title = os.path.splitext(os.path.basename(video_path))[0]
        self.youtube_title_var.set(default_title)
        self.master_app.update_status(f"✅ Đã tự động điền tiêu đề từ tên file.")

    def _clear_youtube_log(self):
        """Xóa nội dung trong ô log upload YouTube."""
        if hasattr(self, 'youtube_log_textbox') and self.youtube_log_textbox.winfo_exists():
            self.youtube_log_textbox.configure(state="normal")
            self.youtube_log_textbox.delete("1.0", "end")
            self.youtube_log_textbox.insert("1.0", self.youtube_log_textbox_placeholder)
            self.youtube_log_textbox.configure(state="disabled")
            self.logger.info("[YouTubeUI] Đã xóa log upload YouTube.")

    def _log_youtube_upload(self, message):
        """Ghi log vào ô upload log YouTube (thread-safe)."""
        if hasattr(self, 'youtube_log_textbox') and self.youtube_log_textbox.winfo_exists():
            if not message.endswith('\n'):
                message += '\n'
            self.master_app.after(0, lambda: self.youtube_log_textbox.configure(state="normal"))
            self.master_app.after(0, lambda: self.youtube_log_textbox.insert("end", message))
            self.master_app.after(0, lambda: self.youtube_log_textbox.see("end"))
            self.master_app.after(0, lambda: self.youtube_log_textbox.configure(state="disabled"))
        else:
            self.logger.info(f"[YouTubeLogFallback] {message.strip()}")

    def _update_youtube_progress(self, value):
        """Cập nhật thanh tiến trình upload YouTube (thread-safe). Giá trị từ 0 đến 100."""
        if hasattr(self, 'youtube_progress_bar') and self.youtube_progress_bar.winfo_exists():
            self.master_app.after(0, lambda: self.youtube_progress_bar.set(float(value) / 100.0))
        else:
            self.logger.warning("[_update_youtube_progress] youtube_progress_bar không tồn tại hoặc chưa được hiển thị khi cập nhật.")

    # ========================================================================
    # LOGIC FUNCTIONS - Di chuyển từ Piu.py
    # ========================================================================

    def _select_youtube_video_file(self):
        """
        Mở dialog chọn file video để upload lên YouTube.
        Cập nhật đường dẫn và gọi hàm tự động điền thông tin.
        """
        self.logger.info("[YouTubeUpload] Nút 'Chọn Video Upload' được nhấn.")

        initial_dir = os.path.dirname(self.youtube_video_path_var.get()) if self.youtube_video_path_var.get() and os.path.exists(os.path.dirname(self.youtube_video_path_var.get())) else \
                      (self.master_app.dub_output_path_var.get() if hasattr(self.master_app, 'dub_output_path_var') and self.master_app.dub_output_path_var.get() else get_default_downloads_folder())

        file_path = filedialog.askopenfilename(
            title="Chọn Video để Tải lên YouTube",
            filetypes=[
                ("Video Files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv"),
                ("All Files", "*.*")
            ],
            initialdir=initial_dir,
            parent=self
        )

        if file_path:
            self.youtube_video_path_var.set(file_path)
            self.logger.info(f"[YouTubeUpload] Đã chọn video: {os.path.basename(file_path)}")
            
            # Gọi hàm xử lý tự động điền thông tin tập trung
            self._autofill_youtube_fields()
            
            self._update_youtube_ui_state(False)
        else:
            self.logger.info("[YouTubeUpload] Người dùng đã hủy chọn video.")
            if not self.youtube_video_path_var.get():
                if hasattr(self, 'youtube_video_path_display_label') and self.youtube_video_path_display_label.winfo_exists():
                    self.youtube_video_path_display_label.configure(text="(Chưa chọn video)")
            
            self._update_youtube_ui_state(False)

    def _select_youtube_thumbnail(self):
        """Mở dialog để chọn file ảnh cho thumbnail."""
        file_path = filedialog.askopenfilename(
            title="Chọn Ảnh Thumbnail (tỷ lệ 16:9)",
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png"),
                ("All Files", "*.*")
            ],
            parent=self
        )
        if file_path and os.path.exists(file_path):
            self.youtube_thumbnail_path_var.set(file_path)
            # Cập nhật label hiển thị
            if hasattr(self, 'youtube_thumbnail_path_display_label') and self.youtube_thumbnail_path_display_label.winfo_exists():
                self.youtube_thumbnail_path_display_label.configure(text=os.path.basename(file_path), text_color=("#0B8457", "lightgreen"))
            self.master_app.update_status(f"Đã chọn thumbnail: {os.path.basename(file_path)}")
        elif not file_path:
            # Nếu người dùng hủy và chưa có gì được chọn, reset lại
            if not self.youtube_thumbnail_path_var.get():
                if hasattr(self, 'youtube_thumbnail_path_display_label') and self.youtube_thumbnail_path_display_label.winfo_exists():
                    self.youtube_thumbnail_path_display_label.configure(text="(Chưa chọn ảnh)", text_color=("gray30", "gray70"))
            self.logger.info("Người dùng hủy chọn thumbnail.")
        else:
            messagebox.showwarning("File không tồn tại", f"File ảnh '{file_path}' không tồn tại.", parent=self)
            self.youtube_thumbnail_path_var.set("")
            if hasattr(self, 'youtube_thumbnail_path_display_label') and self.youtube_thumbnail_path_display_label.winfo_exists():
                self.youtube_thumbnail_path_display_label.configure(text="(File không tồn tại!)", text_color="red")

    def _browse_chrome_portable_path(self):
        """Mở dialog chọn đường dẫn đến Chrome.exe của Chrome Portable."""
        initial_dir = os.path.dirname(self.chrome_portable_path_var.get()) if self.chrome_portable_path_var.get() else os.path.expanduser("~")
        file_path = filedialog.askopenfilename(
            title="Chọn Chrome.exe (trong thư mục Chrome Portable)",
            initialdir=initial_dir,
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")],
            parent=self
        )
        if file_path:
            self.chrome_portable_path_var.set(file_path)
            if hasattr(self, 'chrome_portable_path_display_label') and self.chrome_portable_path_display_label.winfo_exists():
                update_path_label(self.chrome_portable_path_display_label, file_path)
            self.master_app.cfg["chrome_portable_path"] = file_path # Lưu vào config
            self.master_app.save_current_config()

    def _browse_chromedriver_path(self):
        """Mở dialog chọn đường dẫn đến chromedriver.exe."""
        initial_dir = os.path.dirname(self.chromedriver_path_var.get()) if self.chromedriver_path_var.get() else os.path.expanduser("~")
        file_path = filedialog.askopenfilename(
            title="Chọn chromedriver.exe",
            initialdir=initial_dir,
            filetypes=[("Executable files", "chromedriver.exe"), ("All files", "*.*")],
            parent=self
        )
        if file_path:
            self.chromedriver_path_var.set(file_path)
            if hasattr(self, 'chromedriver_path_display_label') and self.chromedriver_path_display_label.winfo_exists():
                update_path_label(self.chromedriver_path_display_label, file_path)
            self.master_app.cfg["chromedriver_path"] = file_path # Lưu vào config
            self.master_app.save_current_config()

    def _on_upload_method_changed(self, selected_method):
        """
        Xử lý khi người dùng thay đổi phương thức upload (API hoặc Trình duyệt).
        Hiển thị hoặc ẩn khung cấu hình Chrome Portable.
        """
        self.logger.info(f"Phương thức Upload YouTube thay đổi thành: {selected_method}")
        
        if selected_method == "browser":
            if hasattr(self, 'chrome_portable_config_frame') and hasattr(self, 'upload_method_radio_browser'):
                self.chrome_portable_config_frame.pack(fill="x", padx=10, pady=(0, 10), after=self.upload_method_radio_browser.master)
            # Cập nhật hiển thị label cho đường dẫn hiện tại
            if hasattr(self, 'chrome_portable_path_display_label'):
                update_path_label(self.chrome_portable_path_display_label, self.chrome_portable_path_var.get())
            if hasattr(self, 'chromedriver_path_display_label'):
                update_path_label(self.chromedriver_path_display_label, self.chromedriver_path_var.get())
            self.master_app.update_status("📤 YouTube: Đã chọn upload qua Trình duyệt.")
        else:
            if hasattr(self, 'chrome_portable_config_frame'):
                self.chrome_portable_config_frame.pack_forget()
            self.master_app.update_status("📤 YouTube: Đã chọn upload qua API.")
        
        # Lưu lại lựa chọn vào config
        self.master_app.cfg["youtube_upload_method"] = selected_method
        self.master_app.save_current_config()
        # Cập nhật trạng thái của nút "Bắt đầu Upload"
        self._update_youtube_ui_state(self.is_uploading_youtube)

    def _get_youtube_description(self):
        """Lấy nội dung mô tả từ textbox YouTube upload."""
        if hasattr(self, 'youtube_description_textbox') and self.youtube_description_textbox and self.youtube_description_textbox.winfo_exists():
            return self.youtube_description_textbox.get("1.0", "end-1c").strip()
        return ""

    def _add_youtube_task_to_queue(self):
        """Thu thập thông tin từ UI, tạo một task và thêm vào hàng chờ upload."""
        log_prefix = "[YouTubeQueue]"
        
        # 1. Lấy và xác thực thông tin
        video_path = self.youtube_video_path_var.get().strip()
        title = self.youtube_title_var.get().strip()
        
        if not video_path or not os.path.exists(video_path):
            messagebox.showwarning("Thiếu Video", "Vui lòng chọn một file video hợp lệ.", parent=self)
            return
        if not title:
            messagebox.showwarning("Thiếu Tiêu đề", "Vui lòng nhập tiêu đề cho video.", parent=self)
            return

        # 2. Thêm vào hàng chờ qua YouTubeService
        task_data = self.master_app.youtube_service.add_task_to_queue(
            video_path=video_path,
            title=title,
            description=self._get_youtube_description(),
            tags_str=self.youtube_tags_var.get().strip(),
            playlist_name=self.youtube_playlist_var.get().strip(),
            thumbnail_path=self.youtube_thumbnail_path_var.get().strip(),
            privacy_status=self.youtube_privacy_status_var.get(),
            category_id=self.youtube_category_id_var.get()
        )
        
        # 3. Reset các ô nhập liệu để chuẩn bị cho tác vụ tiếp theo
        self.youtube_video_path_var.set("")
        self.youtube_title_var.set("")
        self.youtube_thumbnail_path_var.set("")
        
        if hasattr(self, 'youtube_thumbnail_path_display_label') and self.youtube_thumbnail_path_display_label and self.youtube_thumbnail_path_display_label.winfo_exists():
            self.youtube_thumbnail_path_display_label.configure(text="(Chưa chọn ảnh)", text_color=("gray30", "gray70"))        
        self.update_youtube_queue_display()
        self.master_app.update_status(f"✅ Đã thêm '{title[:30]}...' vào hàng chờ upload.")

    def update_youtube_queue_display(self):
        """Cập nhật giao diện của hàng chờ upload YouTube."""
        if not hasattr(self, 'youtube_queue_display_frame') or not self.youtube_queue_display_frame.winfo_exists():
            return

        for widget in self.youtube_queue_display_frame.winfo_children():
            if widget.winfo_exists(): # Thêm kiểm tra cho từng widget con nữa cho an toàn
                widget.destroy()

        # Lấy tác vụ đang xử lý để hiển thị riêng (từ service)
        self.youtube_currently_processing_task_id = self.master_app.youtube_service.currently_processing_task_id
        processing_task = self.master_app.youtube_service.get_current_task()
        
        # Hiển thị tác vụ đang xử lý
        if processing_task:
            frame = ctk.CTkFrame(self.youtube_queue_display_frame, fg_color="#006933", corner_radius=5)
            frame.pack(fill="x", pady=(2, 5), padx=2)
            
            label_text = f"▶ ĐANG UPLOAD:\n   {processing_task['title']}"
            
            label_widget = ctk.CTkLabel(frame, text=label_text, font=("Poppins", 11, "bold"), justify="left", anchor='w', text_color="white")
            label_widget.pack(side="left", padx=5, pady=3, fill="x")
            Tooltip(label_widget, text=processing_task['title'])

        # Hiển thị các tác vụ đang chờ (từ service)
        waiting_tasks = self.master_app.youtube_service.get_waiting_tasks()

        if not waiting_tasks and not processing_task:
            ctk.CTkLabel(self.youtube_queue_display_frame, text="[Hàng chờ upload trống]", font=("Segoe UI", 11), text_color="gray").pack(pady=20)
            self._update_youtube_ui_state(False) # Cập nhật lại nút Start Upload
            return

        for index, task in enumerate(waiting_tasks):
            item_frame = ctk.CTkFrame(self.youtube_queue_display_frame, fg_color="transparent")
            item_frame.pack(fill="x", padx=2, pady=(1,2))
            
            info_text = f"{index + 1}. {task['title']}"
            if task.get('status') != 'Chờ xử lý':
                info_text += f" [{task['status']}]"

            label_widget = ctk.CTkLabel(item_frame, text=info_text, anchor="w", font=("Segoe UI", 10))
            label_widget.pack(side="left", padx=(5, 0), expand=True, fill="x")
            Tooltip(label_widget, text=task['title'])

            # Frame nhỏ để chứa các nút điều khiển
            controls_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            controls_frame.pack(side="right", padx=(5, 5))

            # Nút Xóa
            button_state = ctk.DISABLED if self.is_uploading_youtube else ctk.NORMAL
            del_button = ctk.CTkButton(
                controls_frame, text="✕",
                width=28, height=28,
                font=("Segoe UI", 12, "bold"),
                fg_color="#E74C3C", hover_color="#C0392B",
                command=lambda task_id=task['id']: self._remove_youtube_task_from_queue(task_id),
                state=button_state
            )
            del_button.pack()

    def _remove_youtube_task_from_queue(self, task_id_to_remove):
        """Xóa một tác vụ khỏi hàng chờ upload YouTube dựa trên ID."""
        if self.is_uploading_youtube:
            messagebox.showwarning("Đang xử lý", "Không thể xóa tác vụ khi đang upload.", parent=self)
            return

        # Xóa qua YouTubeService
        removed = self.master_app.youtube_service.remove_task_from_queue(task_id_to_remove)
        
        if removed:
            self.update_youtube_queue_display() # Cập nhật lại giao diện
            self.master_app.update_status("ℹ️ Đã xóa 1 tác vụ khỏi hàng chờ upload.")
            
            # Hẹn giờ 4 giây (4000ms) sau sẽ gọi hàm reset status (giống code gốc)
            if hasattr(self.master_app, '_reset_status_to_default'):
                self.master_app.after(4000, self.master_app._reset_status_to_default)
        else:
            self.logger.warning(f"Không tìm thấy tác vụ upload với ID '{task_id_to_remove}' để xóa.")

    def _autofill_youtube_fields(self):
        """
        [REFACTORED] Tự động điền các trường thông tin YouTube dựa trên checkbox nào đang được bật.
        Sử dụng MetadataService để xử lý business logic, chỉ xử lý UI callbacks ở đây.
        """
        video_path = self.youtube_video_path_var.get()
        if not video_path or not os.path.exists(video_path):
            return # Không làm gì nếu chưa có video được chọn

        # Đồng bộ state từ Piu.py sang MetadataService
        master_metadata_cache = self.master_app.master_metadata_cache if hasattr(self.master_app, 'master_metadata_cache') else {}
        self.master_app.metadata_service.cache = master_metadata_cache

        # Ưu tiên 1: Lấy từ Master Metadata
        if self.youtube_fetch_metadata_var.get():
            # Gọi MetadataService để autofill
            filled_fields = self.master_app.metadata_service.autofill_youtube_fields(file_path=video_path)
            
            if filled_fields.get('title') or filled_fields.get('description') or filled_fields.get('tags'):
                # Có metadata - điền vào UI
                self.youtube_title_var.set(filled_fields.get('title', ''))
                self.youtube_tags_var.set(filled_fields.get('tags', ''))
                self.youtube_playlist_var.set(filled_fields.get('playlist', ''))
                self.youtube_thumbnail_path_var.set(filled_fields.get('thumbnail', ''))
                
                if hasattr(self, 'youtube_description_textbox') and self.youtube_description_textbox and self.youtube_description_textbox.winfo_exists():
                    self.youtube_description_textbox.delete("1.0", "end")
                    self.youtube_description_textbox.insert("1.0", filled_fields.get('description', ''))
                
                # Cập nhật label hiển thị thumbnail
                thumb_path = filled_fields.get('thumbnail', '')
                if hasattr(self, 'youtube_thumbnail_path_display_label') and self.youtube_thumbnail_path_display_label and self.youtube_thumbnail_path_display_label.winfo_exists():
                    if thumb_path and os.path.exists(thumb_path):
                        self.youtube_thumbnail_path_display_label.configure(text=os.path.basename(thumb_path), text_color=("gray10", "lightgreen"))
                    else:
                        self.youtube_thumbnail_path_display_label.configure(text="(Chưa có ảnh trong metadata)", text_color=("gray30", "gray70"))

                identifier = get_identifier_from_source(video_path)
                self.master_app.update_status(f"✅ Đã tự động điền thông tin từ Master Metadata cho '{identifier}'.")
                self.logger.info(f"[Autofill] Đã áp dụng thành công metadata cho key '{identifier}'.")
            else:
                # Không tìm thấy metadata
                identifier = get_identifier_from_source(video_path)
                self.master_app.update_status(f"⚠️ Không tìm thấy metadata cho '{identifier}'.")
                self.logger.warning(f"[Autofill] Không tìm thấy metadata cho key '{identifier}' trong cache.")

        # Ưu tiên 2: Lấy theo tên file (chỉ chạy nếu ưu tiên 1 không được chọn)
        elif self.youtube_autofill_var.get():
            # Gọi MetadataService để lấy title từ filename
            default_title = self.master_app.metadata_service.get_title_from_filename(video_path)
            self.youtube_title_var.set(default_title)
            self.master_app.update_status("✅ Đã tự động điền tiêu đề từ tên file.")

    def _on_metadata_checkbox_toggled(self, source):
        """
        Xử lý khi một trong các checkbox metadata được nhấn,
        đảm bảo chúng loại trừ lẫn nhau và cập nhật UI.
        """
        # Ngăn chặn thay đổi nếu đang upload
        if self.is_uploading_youtube:
            return

        if source == 'fetch' and self.youtube_fetch_metadata_var.get():
            self.youtube_autofill_var.set(False)
        elif source == 'autofill' and self.youtube_autofill_var.get():
            self.youtube_fetch_metadata_var.set(False)

        # Sau khi thay đổi trạng thái, gọi hàm áp dụng logic
        self._autofill_youtube_fields()
        # Lưu lại cài đặt
        self.master_app.save_current_config()

    def _update_youtube_ui_state(self, is_uploading: bool, *, silent: bool = False):
        """
        Cập nhật trạng thái của các nút và trường nhập liệu trên tab Upload YouTube.
        Nếu silent=True: KHÔNG cập nhật status_label để tránh ghi đè thông điệp '✅ Hoàn tất...' ở cuối batch.
        """
        self.logger.debug(f"[YouTubeUploadUI] Cập nhật trạng thái UI, is_uploading={is_uploading}, silent={silent}")
        self.is_uploading_youtube = is_uploading
        
        # Kiểm Tra Bản Quyền
        is_app_active = self.master_app._is_app_fully_activated() if hasattr(self.master_app, '_is_app_fully_activated') else True

        # Xác định trạng thái mục tiêu cho các control
        can_interact = is_app_active and not is_uploading
        target_state_normal = "normal" if can_interact else "disabled"

        # --- Nút Upload ---
        if hasattr(self, 'youtube_start_upload_button') and self.youtube_start_upload_button.winfo_exists():
            if is_uploading:
                self.youtube_start_upload_button.configure(state="disabled", text="📤 Đang Upload...")
            elif not is_app_active:
                self.youtube_start_upload_button.configure(state="disabled", text="🔒 Kích hoạt (Upload)")
            else:
                # Chỉ bật khi hàng chờ có tác vụ
                if getattr(self.master_app, "youtube_service", None) and self.master_app.youtube_service.queue:
                    try:
                        qlen = len(self.master_app.youtube_service.queue)
                    except Exception:
                        qlen = 0
                    self.youtube_start_upload_button.configure(state="normal", text=f"📤 Bắt đầu Upload ({qlen} video)")
                else:
                    self.youtube_start_upload_button.configure(state="disabled", text="📤 Bắt đầu Upload Hàng loạt")

        # --- Nút Dừng ---
        if hasattr(self, 'youtube_stop_upload_button') and self.youtube_stop_upload_button.winfo_exists():
            self.youtube_stop_upload_button.configure(state="normal" if is_uploading else "disabled")

        # --- Nút Chọn Video ---
        if hasattr(self, 'youtube_select_video_button') and self.youtube_select_video_button.winfo_exists():
            if not is_app_active:
                self.youtube_select_video_button.configure(state="disabled", text="🔒 Kích hoạt")
            else:
                self.youtube_select_video_button.configure(state=target_state_normal, text="📁 Chọn Video Upload...")

        # --- Các trường nhập liệu ---
        if hasattr(self, 'youtube_title_entry') and self.youtube_title_entry and self.youtube_title_entry.winfo_exists():
            self.youtube_title_entry.configure(state=target_state_normal)
        if hasattr(self, 'youtube_tags_entry') and self.youtube_tags_entry and self.youtube_tags_entry.winfo_exists():
            self.youtube_tags_entry.configure(state=target_state_normal)
        if hasattr(self, 'youtube_privacy_optionmenu') and self.youtube_privacy_optionmenu and self.youtube_privacy_optionmenu.winfo_exists():
            self.youtube_privacy_optionmenu.configure(state=target_state_normal)
        if hasattr(self, 'youtube_description_textbox') and self.youtube_description_textbox and self.youtube_description_textbox.winfo_exists():
            self.youtube_description_textbox.configure(state=target_state_normal)

        # --- Nút Clear Log ---
        if hasattr(self, 'youtube_clear_log_button') and self.youtube_clear_log_button.winfo_exists():
            self.youtube_clear_log_button.configure(state=target_state_normal)

        # --- Checkbox Tự động Upload ---
        if hasattr(self, 'auto_upload_checkbox') and self.auto_upload_checkbox.winfo_exists():
            self.auto_upload_checkbox.configure(state=target_state_normal)

        # --- Progressbar: chế độ & an toàn không bị kẹt ---
        try:
            if hasattr(self, 'youtube_progress_bar') and self.youtube_progress_bar.winfo_exists():
                if is_uploading:
                    # Bắt đầu upload: đảm bảo indeterminate + chạy animation
                    self.youtube_progress_bar.stop()              # reset vòng lặp nếu có
                    self.youtube_progress_bar.configure(mode="indeterminate")
                    self.youtube_progress_bar.set(0)              # thanh trống (không % cụ thể)
                    try:
                        # CTkProgressBar: start() không nhận tham số; nếu bạn dùng ttk thì start(10) = 10ms/step
                        self.youtube_progress_bar.start()
                    except Exception:
                        pass
                else:
                    # Không upload: dừng, chuyển determinate, về 0
                    self.youtube_progress_bar.stop()
                    self.youtube_progress_bar.configure(mode="determinate")
                    self.youtube_progress_bar.set(0)
        except Exception as e:
            self.logger.debug(f"[YouTubeUploadUI] Progressbar cleanup skipped: {e}")

        # --- Cập nhật thanh trạng thái (tuỳ theo silent) ---
        if not silent:
            if is_uploading:
                # Thông điệp mặc định khi đang upload (nếu nơi khác chưa set cụ thể)
                self.master_app.update_status("📤 Đang upload lên YouTube...")
            else:
                if not is_app_active:
                    self.master_app.update_status("⛔ Yêu cầu Kích hoạt (YouTube Upload)")
                else:
                    # Kiểm tra input cơ bản để gợi ý 'sẵn sàng'
                    has_path = False
                    has_title = False
                    try:
                        has_path = bool(self.youtube_video_path_var.get().strip())
                    except Exception:
                        pass
                    try:
                        has_title = bool(self.youtube_title_var.get().strip())
                    except Exception:
                        pass
                    if has_path and has_title:
                        self.master_app.update_status("✅ YouTube: Sẵn sàng upload.")
                    else:
                        self.master_app.update_status("ℹ️ YouTube: Đang chờ chọn video/nhập thông tin.")

    def _start_youtube_batch_upload(self):
        """Bắt đầu quá trình xử lý hàng loạt các tác vụ trong hàng chờ upload."""
        if hasattr(self.master_app, 'is_chain_handoff'):
            self.master_app.is_chain_handoff = False
        self.logger.info("[YouTubeUploadStart] Đã gỡ khóa is_chain_handoff. Quá trình upload chính thức bắt đầu.")
        
        if self.is_uploading_youtube:
            messagebox.showwarning("Đang bận", "Đang trong quá trình upload hàng loạt.", parent=self)
            return
        if not self.master_app.youtube_service.queue:
            messagebox.showinfo("Hàng chờ trống", "Vui lòng thêm ít nhất một video vào hàng chờ upload.", parent=self)
            return

        self.logger.info(f"--- BẮT ĐẦU UPLOAD HÀNG LOẠT ({len(self.master_app.youtube_service.queue)} tác vụ) ---")
        
        # Bắt đầu batch qua service
        first_task_id = self.master_app.youtube_service.queue[0]['id'] if self.master_app.youtube_service.queue else None
        self.master_app.youtube_service.start_batch(first_task_id=first_task_id)
        
        # Sync với Piu state
        self.is_uploading_youtube = self.master_app.youtube_service.is_uploading
        self.youtube_currently_processing_task_id = self.master_app.youtube_service.currently_processing_task_id
        if hasattr(self.master_app, 'download_view_frame'):
            self.master_app.shutdown_requested_by_task = self.master_app.download_view_frame.download_shutdown_var.get()
        if hasattr(self.master_app, 'start_time'):
            self.master_app.start_time = time.time()
        if hasattr(self.master_app, 'update_time_realtime'):
            self.master_app.update_time_realtime()
        self.master_app.stop_event.clear()
        
        # Kiểm tra phương thức upload và cài đặt thanh tiến trình tương ứng
        upload_method = self.youtube_upload_method_var.get()
        if hasattr(self, 'youtube_progress_bar') and self.youtube_progress_bar.winfo_exists():
            if upload_method == "browser":
                self.logger.info("Chế độ Upload Trình duyệt: Đặt thanh tiến trình sang 'indeterminate'.")
                self.youtube_progress_bar.configure(mode="indeterminate")
                self.youtube_progress_bar.start()
            else: # Chế độ API
                self.logger.info("Chế độ Upload API: Đặt thanh tiến trình sang 'determinate'.")
                self.youtube_progress_bar.configure(mode="determinate")
                self.youtube_progress_bar.set(0) # Bắt đầu từ 0%

        self._update_youtube_ui_state(True)
        self.master_app.update_status(f"Bắt đầu upload hàng loạt {len(self.master_app.youtube_service.queue)} video...")
        
        # Bắt đầu xử lý với tác vụ đầu tiên trong hàng chờ
        self._process_next_youtube_task()

    def _process_next_youtube_task(self):
        """Lấy tác vụ tiếp theo từ hàng chờ upload và bắt đầu xử lý."""
        if self.master_app.stop_event.is_set():
            self.logger.info("Yêu cầu dừng được phát hiện. Kết thúc hàng loạt upload.")
            self._on_youtube_batch_finished(stopped=True)
            return

        if not self.master_app.youtube_service.queue:
            self.logger.info("Hàng chờ upload trống. Hoàn tất hàng loạt.")
            self._on_youtube_batch_finished(stopped=False)
            return
        
        # Lấy task đầu tiên từ queue (giống code gốc)
        # Lưu ý: Task sẽ được xóa khỏi queue trong _handle_youtube_upload_completion sau khi upload xong
        task = self.master_app.youtube_service.queue[0]
        
        # Set current_task (giống code gốc - luôn set khi lấy task mới)
        self.master_app.youtube_service.set_current_task(task['id'])
        
        # Sync với Piu state và tab state
        self.youtube_currently_processing_task_id = task['id']
        self.update_youtube_queue_display() 

        self.logger.info(f"Đang xử lý tác vụ upload: '{task['title']}' (ID: {task['id']})")
        
        # THAY ĐỔI: Lấy tags_str một cách an toàn, mặc định là chuỗi rỗng nếu nó là None
        tags_str_from_task = task.get('tags_str') or "" 
        tags = [tag.strip() for tag in tags_str_from_task.split(',') if tag.strip()]
        
        # Quyết định luồng sẽ gọi (API hoặc Trình duyệt)
        upload_method = self.youtube_upload_method_var.get()
        if upload_method == "api":
            thread = threading.Thread(
                target=self._perform_youtube_upload_thread,
                args=(task['video_path'], task['title'], task['description'], tags, task['privacy_status'], True, task['thumbnail_path'], task['playlist_name'], task['category_id']),
                daemon=True, name="YouTubeAPIUploadWorker"
            )
            thread.start()
        elif upload_method == "browser":
            thread = threading.Thread(
                target=self._upload_video_via_browser_thread,
                args=(task['video_path'], task['title'], task['description'], tags, task['privacy_status'], task['playlist_name'], task['thumbnail_path'], task['category_id']),
                daemon=True, name="YouTubeBrowserUploadWorker"
            )
            thread.start()

    def _stop_youtube_upload(self):
        """
        Dừng quá trình upload YouTube đang diễn ra.
        """
        self.logger.warning("[YouTubeUpload] Người dùng yêu cầu dừng upload YouTube.")
        self.master_app.stop_event.set() # Dùng chung stop_event cho việc dừng các luồng dài
        
        # Dừng batch qua service
        self.master_app.youtube_service.stop_batch()
        self.is_uploading_youtube = self.master_app.youtube_service.is_uploading

        # Cố gắng dừng tiến trình ffmpeg/gapi-client nếu có
        if hasattr(self.master_app, 'current_process') and self.master_app.current_process and self.master_app.current_process.poll() is None:
            self.logger.info(f"[YouTubeUpload] Đang cố gắng dừng tiến trình con (PID: {self.master_app.current_process.pid})...")
            try:
                self.master_app.current_process.terminate()
                self.master_app.current_process.wait(timeout=1.0)
            except Exception as e:
                self.logger.warning(f"[YouTubeUpload] Lỗi khi dừng tiến trình con: {e}")
            finally:
                self.master_app.current_process = None

        self.master_app.update_status("🛑 Đang yêu cầu dừng upload YouTube...")
        # Cập nhật UI sẽ được xử lý trong _handle_youtube_upload_completion khi luồng dừng hẳn

    def _handle_youtube_upload_completion(self, success, video_id, error_message, is_chained_upload):
        """
        v4 (ngắn gọn): UI còn thì cập nhật bằng after(); UI chết thì vẫn advance batch.
        KHÔNG return sớm chỉ vì UI đã bị phá hủy.
        """
        log_prefix = "[YouTubeUploadCompletion_v4_Short]"
        # Lấy task_id từ tab state (giống code gốc - lấy từ biến trực tiếp)
        # Tab state là nguồn chân lý vì nó được set trong _process_next_youtube_task
        task_id = getattr(self, 'youtube_currently_processing_task_id', None)
        if not task_id:
            # Fallback: thử lấy từ service nếu tab state không có
            task_id = self.master_app.youtube_service.currently_processing_task_id
        self.logger.info(f"{log_prefix} Tác vụ (ID: {task_id}) hoàn tất. Success: {success}, VideoID: {video_id}, Error: {error_message}")

        # Cập nhật trạng thái task (bộ nhớ, không đụng UI)
        if task_id:
            try:
                t = self.master_app.youtube_service.get_task_by_id(task_id)
                if t:
                    t['status'] = 'Hoàn thành ✅' if success else 'Lỗi ❌'
                    t['video_id'] = video_id
            except Exception:
                pass

        # Log kết quả
        try:
            if success:
                self._log_youtube_upload(f"✅ Tải lên '{video_id}' thành công!")
            else:
                self._log_youtube_upload(f"❌ Tải lên thất bại: {error_message}")
        except Exception:
            pass

        # UI còn không?
        try:
            ui_alive = (not getattr(self.master_app, "_is_shutting_down", False)) and bool(self.master_app.winfo_exists())
        except Exception:
            ui_alive = False

        def _update_and_proceed():
            # Xóa task đã xong khỏi hàng đợi (qua service)
            if task_id:
                self.master_app.youtube_service.remove_task_from_queue(task_id)
            self.master_app.youtube_service.set_current_task(None)
            
            # Sync với Piu state
            self.youtube_currently_processing_task_id = self.master_app.youtube_service.currently_processing_task_id

            # Cập nhật UI nếu còn, tránh TclError
            if ui_alive:
                try:
                    self.update_youtube_queue_display()
                except Exception as e:
                    self.logger.debug(f"{log_prefix} Bỏ qua update UI: {e}")

            # Tiến hành tác vụ tiếp theo / kết thúc
            try:
                if not self.master_app.stop_event.is_set():
                    if self.master_app.youtube_service.queue:
                        self._process_next_youtube_task()
                    else:
                        self._on_youtube_batch_finished(stopped=False)
                else:
                    self._on_youtube_batch_finished(stopped=True)
            except Exception as e:
                self.logger.error(f"{log_prefix} Lỗi khi advance batch: {e}", exc_info=True)
                # Dù lỗi, vẫn cố kết thúc batch để không treo
                try:
                    self._on_youtube_batch_finished(stopped=False)
                except Exception:
                    pass

        if ui_alive:
            # UI còn → cập nhật/advance trên main thread
            self.master_app.after(100, _update_and_proceed)
        else:
            # UI đã đóng → vẫn advance ở nền, không treo batch
            self.logger.warning("[YouTubeUploadCompletion] UI đã đóng. Bỏ qua UI, vẫn advance batch.")
            threading.Thread(target=_update_and_proceed, daemon=True).start()

    def _on_youtube_batch_finished(self, stopped=False):
        """Được gọi khi tất cả các tác vụ trong hàng chờ upload đã hoàn thành hoặc bị dừng."""
        # Hoàn thành batch qua service (service sẽ chặn duplicate calls)
        self.master_app.youtube_service.finish_batch(stopped=stopped)
        
        # Sync với Piu state
        self.is_uploading_youtube = self.master_app.youtube_service.is_uploading
        self.youtube_currently_processing_task_id = self.master_app.youtube_service.currently_processing_task_id
        if hasattr(self.master_app, 'start_time'):
            self.master_app.start_time = None

        # Progress bar/UI cleanup an toàn
        try:
            if hasattr(self, "youtube_progress_bar") and self.youtube_progress_bar.winfo_exists():
                self.youtube_progress_bar.stop()
                self.youtube_progress_bar.configure(mode="determinate")
                self.youtube_progress_bar.set(0)
        except Exception as e:
            self.logger.debug(f"[BatchFinished] Progress bar cleanup skipped: {e}")

        try:
            self._update_youtube_ui_state(False, silent=True)
            self.update_youtube_queue_display()
        except Exception as e:
            self.logger.debug(f"[BatchFinished] UI state update skipped: {e}")

        # Đọc cờ "tắt máy khi xong"
        should_shutdown = False
        try:
            if hasattr(self.master_app, "shutdown_after_tasks_var"):
                should_shutdown = bool(self.master_app.shutdown_after_tasks_var.get())
        except Exception:
            pass

        # Trạng thái cuối
        if stopped:
            self.master_app.update_status("🛑 Hàng loạt upload đã dừng.")
        else:
            self.master_app.update_status("✅ Hoàn tất tất cả tác vụ upload!")

        # 👉👉 GỌI CHECK SHUTDOWN TRƯỚC POPUP (để lệnh tắt máy chạy ngay)
        try:
            if hasattr(self.master_app, '_check_completion_and_shutdown'):
                self.master_app._check_completion_and_shutdown()
        except Exception as e:
            self.logger.debug(f"[BatchFinished] check_completion_and_shutdown error: {e}")

        # Nếu đang bật tắt máy thì KHÔNG hiện popup (tránh chặn)
        if not should_shutdown:
            # Phát âm thanh (nếu có)
            try:
                if (hasattr(self.master_app, "download_view_frame") and hasattr(self.master_app.download_view_frame, "download_sound_var") and self.master_app.download_view_frame.download_sound_var.get()
                    and hasattr(self.master_app.download_view_frame, "download_sound_path_var") and self.master_app.download_view_frame.download_sound_path_var.get()
                    and os.path.isfile(self.master_app.download_view_frame.download_sound_path_var.get())):
                    play_sound_async(self.master_app.download_view_frame.download_sound_path_var.get())
            except Exception as e:
                self.logger.debug(f"[BatchFinished] play_sound skipped: {e}")

            # Popup thông báo (không bắt buộc)
            try:
                messagebox.showinfo("Hoàn thành", "Đã upload xong tất cả các video trong hàng chờ.", parent=self)
            except Exception as e:
                self.logger.debug(f"[BatchFinished] showinfo skipped: {e}")

    def save_config(self):
        """Lưu cấu hình YouTube Upload vào master_app.cfg"""
        if not hasattr(self.master_app, 'cfg'):
            self.logger.error("master_app không có thuộc tính cfg")
            return
        
        # Lưu các cấu hình YouTube
        self.master_app.cfg["youtube_last_title"] = self.youtube_title_var.get()
        self.master_app.cfg["youtube_last_tags"] = self.youtube_tags_var.get()
        self.master_app.cfg["youtube_playlist_name"] = self.youtube_playlist_var.get()
        self.master_app.cfg["youtube_autofill_enabled"] = self.youtube_autofill_var.get()
        self.master_app.cfg["metadata_auto_increment_thumb"] = self.metadata_auto_increment_thumb_var.get()
        self.master_app.cfg["youtube_default_privacy"] = self.youtube_privacy_status_var.get()
        self.master_app.cfg["youtube_default_category_id"] = self.youtube_category_id_var.get()
        self.master_app.cfg["auto_upload_to_youtube"] = self.auto_upload_to_youtube_var.get()
        self.master_app.cfg["youtube_fetch_metadata_enabled"] = self.youtube_fetch_metadata_var.get()
        self.master_app.cfg["youtube_upload_method"] = self.youtube_upload_method_var.get()
        self.master_app.cfg["chrome_portable_path"] = self.chrome_portable_path_var.get()
        self.master_app.cfg["chromedriver_path"] = self.chromedriver_path_var.get()
        self.master_app.cfg["youtube_run_headless"] = self.youtube_headless_var.get()
        self.master_app.cfg["youtube_add_end_screen"] = self.youtube_add_end_screen_var.get()
        self.master_app.cfg["youtube_add_cards"] = self.youtube_add_cards_var.get()
        
        self.logger.debug("[YouTubeUploadTab.save_config] Đã lưu cấu hình YouTube Upload vào master_app.cfg")

    # ========================================================================
    # THREAD UPLOAD FUNCTIONS - Di chuyển từ Piu.py
    # ========================================================================

    def _keep_awake(self, reason: str = "Processing"):
        """Context manager: giữ máy không Sleep trong khối lệnh."""
        @contextmanager
        def _keep_awake_impl():
            if hasattr(self.master_app, 'KEEP_AWAKE'):
                tk = self.master_app.KEEP_AWAKE.acquire(reason)
                try:
                    yield
                finally:
                    self.master_app.KEEP_AWAKE.release(tk)
            else:
                # Fallback: tạo instance riêng nếu master_app không có
                manager = KeepAwakeManager()
                tk = manager.acquire(reason)
                try:
                    yield
                finally:
                    manager.release(tk)
        return _keep_awake_impl()

    def _perform_youtube_upload_thread(self, video_path, title, description, tags, privacy_status, is_chained_upload, thumbnail_path, playlist_name, category_id):
        """
        (PHIÊN BẢN 1.2 - HOÀN CHỈNH VỚI XỬ LÝ LỖI API)
        Luồng worker thực hiện tải video lên YouTube, cập nhật tiến trình, tải thumbnail và xử lý lỗi chi tiết.
        """
        worker_log_prefix = f"[YouTubeUploadWorker_V1.2]"
        logging.info(f"{worker_log_prefix} Bắt đầu tải lên video: '{os.path.basename(video_path)}'")

        upload_success_final = False
        error_message_final = None
        uploaded_video_id_final = None
        service = None # Khai báo service ở scope ngoài để khối except có thể dùng

        try:
            if self.master_app.stop_event.is_set():
                raise InterruptedError("Đã dừng bởi người dùng trước khi upload.")

            service = get_google_api_service(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION)
            
            if service is None:
                raise RuntimeError("Không thể xác thực với Google API cho YouTube.")

            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Tệp video không tồn tại: {os.path.basename(video_path)}")

            # Bắt đầu với các trường bắt buộc trong snippet
            snippet = {
                'title': title,
                'categoryId': category_id
            }
            
            # Chỉ thêm các trường tùy chọn nếu chúng có giá trị (không phải None)
            if description is not None:
                snippet['description'] = description
            
            # 'tags' đã là một list, nếu nó rỗng (không có tag) thì sẽ không có vấn đề
            if tags:
                snippet['tags'] = tags
            
            # Xây dựng đối tượng 'body' cuối cùng từ các phần đã chuẩn bị
            body = {
                'snippet': snippet,
                'status': { 
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False 
                }
            }

            self._log_youtube_upload(f"Bắt đầu tải lên: '{os.path.basename(video_path)}'")
            self._log_youtube_upload(f"Tiêu đề: '{title}'")

            media_body = MediaFileUpload(video_path, chunksize=(1024*1024), resumable=True) # Sửa -1 thành 1MB
            request = service.videos().insert(part=",".join(body.keys()), body=body, media_body=media_body)
            response_from_api = None
            self._log_youtube_upload("Đang tải lên video...")
            self._update_youtube_progress(0)

            while response_from_api is None:
                if self.master_app.stop_event.is_set():
                    raise InterruptedError("Quá trình tải lên bị dừng bởi người dùng.")

                try:
                    status, response_from_api = request.next_chunk()
                    if status:
                        # Lấy số byte đã tải và tổng kích thước để tính %
                        bytes_uploaded = status.resumable_progress
                        total_size = status.total_size
                        if total_size > 0:
                            percent_complete = int((bytes_uploaded / total_size) * 100)
                            self._update_youtube_progress(percent_complete)
                            self.master_app.after(0, lambda p=percent_complete: self.master_app.update_status(f"📤 Đang Upload: {p}% - {os.path.basename(video_path)}"))
                        
                except HttpError as e_chunk:
                    error_content_chunk = e_chunk.content.decode('utf-8', 'replace')
                    if "uploadLimitExceeded" in error_content_chunk:
                        raise HttpError(e_chunk.resp, e_chunk.content, uri=e_chunk.uri) # Ném lại lỗi để khối except bên ngoài bắt
                    logging.error(f"{worker_log_prefix} Lỗi khi upload chunk: {e_chunk}. Sẽ thử lại sau 5 giây.")
                    self._log_youtube_upload(f"Lỗi mạng khi đang upload, đang thử kết nối lại...")
                    time.sleep(5)
                    continue

            if response_from_api and not self.master_app.stop_event.is_set():
                uploaded_video_id_final = response_from_api.get('id')
                if uploaded_video_id_final:
                    upload_success_final = True
                    self._log_youtube_upload(f"✅ Tải lên video thành công! ID: {uploaded_video_id_final}")
                    self._log_youtube_upload(f"Link video: https://youtu.be/{uploaded_video_id_final}")

                    # 1. Tải lên thumbnail nếu có (qua service)
                    if thumbnail_path and os.path.exists(thumbnail_path):
                        self.master_app.youtube_service.upload_thumbnail(service, uploaded_video_id_final, thumbnail_path, log_callback=self._log_youtube_upload)
                    else:
                        logging.info("Không có thumbnail được cung cấp hoặc file không tồn tại.")

                    # 2. Thêm vào danh sách phát nếu có (qua service)
                    if playlist_name:
                        # Initialize cache if not exists
                        if not hasattr(self.master_app, 'playlist_cache'):
                            self.master_app.playlist_cache = {}
                        playlist_id_found = self.master_app.youtube_service.get_playlist_id(service, playlist_name, self.master_app.playlist_cache)
                        if playlist_id_found:
                            self.master_app.youtube_service.add_to_playlist(service, uploaded_video_id_final, playlist_id_found, log_callback=self._log_youtube_upload)
                        else:
                            self._log_youtube_upload(f"⚠️ Không tìm thấy ID cho danh sách phát '{playlist_name}', bỏ qua.")
                    else:
                        logging.info("Không có tên danh sách phát được cung cấp.")
                else:
                    error_message_final = "Tải lên thành công nhưng không nhận được ID video."
            elif not error_message_final:
                error_message_final = "Tải lên không thành công hoặc không có phản hồi."            

            if not upload_success_final:
                logging.error(f"{worker_log_prefix} {error_message_final}")

        except InterruptedError as e_known:
            error_message_final = str(e_known)
            logging.warning(f"{worker_log_prefix} {error_message_final}")
        except (FileNotFoundError, RuntimeError) as e_known:
             error_message_final = str(e_known)
             logging.error(f"{worker_log_prefix} {error_message_final}", exc_info=True)
        
        ### BẮT ĐẦU KHỐI XỬ LÝ LỖI HTTP NÂNG CAO ###
        except HttpError as e_http:
            error_content = e_http.content.decode('utf-8', 'replace') if hasattr(e_http, 'content') else ""
            error_details_parsed = ""
            try:
                error_json = json.loads(error_content)
                error_details_parsed = error_json.get('error', {}).get('message', 'Không có chi tiết lỗi cụ thể từ API.')
            except json.JSONDecodeError:
                error_details_parsed = f"Phản hồi lỗi không phải JSON: {error_content[:100]}..."

            if e_http.resp.status == 401:
                error_message_final = (f"Lỗi Xác thực (401): Thông tin đăng nhập không hợp lệ hoặc đã hết hạn.\n\n"
                                       f"Gợi ý: Thử xóa file 'token.json' và chạy lại ứng dụng để xác thực lại tài khoản Google.")
                token_path_to_delete = os.path.join(os.path.dirname(get_config_path()), TOKEN_FILENAME)
                if os.path.exists(token_path_to_delete):
                    try:
                        os.remove(token_path_to_delete)
                        logging.info(f"{worker_log_prefix} Đã tự động xóa file token.json do lỗi 401: {token_path_to_delete}")
                    except OSError as del_err:
                        logging.warning(f"{worker_log_prefix} Không thể tự động xóa token.json: {del_err}")

            elif e_http.resp.status == 403 or "uploadLimitExceeded" in error_content:
                reason = "không rõ"
                if "uploadLimitExceeded" in error_content:
                    reason = "Đã vượt quá giới hạn upload video trong ngày của YouTube. Vui lòng xác minh tài khoản hoặc chờ 24 giờ."
                elif "forbidden" in error_content.lower():
                    reason = "Không có quyền thực hiện hành động này. Hãy đảm bảo API YouTube Data v3 đã được bật trong Google Cloud Console và tài khoản của bạn có quyền upload."
                error_message_final = f"Lỗi Quyền truy cập (403): {reason}\nChi tiết: {error_details_parsed}"
            
            else:
                error_message_final = f"Lỗi Google API (Mã: {e_http.resp.status}): {error_details_parsed}"

            logging.error(f"{worker_log_prefix} {error_message_final}", exc_info=False)
        ### KẾT THÚC KHỐI XỬ LÝ LỖI HTTP NÂNG CAO ###
        
        except Exception as e_general:
            if not error_message_final: error_message_final = f"Lỗi không mong muốn: {e_general}"
            logging.critical(f"{worker_log_prefix} {error_message_final}", exc_info=True)
        
        finally:
            self.master_app.after(0, self._handle_youtube_upload_completion, 
                           upload_success_final, 
                           uploaded_video_id_final, 
                           error_message_final, 
                           is_chained_upload)

# ======================================================================================
# PHIÊN BẢN 9.6 - TÍCH HỢP HÀM CLICK MẠNH MẼ
# ======================================================================================

# Phương thức click "tối thượng" với 3 lớp fallback và cơ chế chống Stale Element
# Method _click_with_fallback đã được extracted vào services/youtube_browser_upload_service.py

# Hàm upload đã được cập nhật để sử dụng hàm click mới        
    def _upload_video_via_browser_thread(self, video_path, title, description, tags, privacy_status, playlist_name, thumbnail_path_from_task, category_id):
        """
        Luồng worker thực hiện upload qua trình duyệt.
        >>> PHIÊN BẢN 9.10: Nâng cấp chọn Thẻ video để lấy ngẫu nhiên 1 trong TẤT CẢ các playlist có sẵn. <<<
        >>> SỬA LỖI v9.8: Đã sửa tất cả các lệnh click để truyền LOCATOR thay vì ELEMENT. <<<
        """
        import random
        
        with self._keep_awake("Upload YouTube via browser"):  # <<< GIỮ MÁY THỨC TRONG SUỐT QUÁ TRÌNH UP

            worker_log_prefix = "[BrowserUploadWorker_v9.8_FixedCalls]"
            logging.info(f"{worker_log_prefix} Bắt đầu upload video '{os.path.basename(video_path)}' qua trình duyệt.")

            # --- Phần khởi tạo driver giữ nguyên ---
            # (Giữ nguyên toàn bộ phần khởi tạo driver và các cấu hình của bạn)
            chrome_portable_exe_path = self.chrome_portable_path_var.get() if hasattr(self, 'chrome_portable_path_var') else ""
            chromedriver_exe_path = self.chromedriver_path_var.get() if hasattr(self, 'chromedriver_path_var') else ""

            if not chrome_portable_exe_path or not os.path.exists(chrome_portable_exe_path):
                error_msg = "Đường dẫn Chrome Portable không hợp lệ hoặc không tìm thấy. Vui lòng cấu hình lại trong tab 'Upload YT'."
                logging.error(f"{worker_log_prefix} {error_msg}")
                self.master_app.after(0, lambda: messagebox.showerror("Lỗi Cấu Hình", error_msg, parent=self))
                self._handle_youtube_upload_completion(False, None, error_msg, False)
                return

            if not chromedriver_exe_path or not os.path.exists(chromedriver_exe_path):
                logging.warning(f"{worker_log_prefix} ChromeDriver không hợp lệ hoặc không tìm thấy. Thử tự động tải...")
                try:
                    chromedriver_exe_path = ChromeDriverManager().install()
                    if hasattr(self, 'chromedriver_path_var'):
                        self.chromedriver_path_var.set(chromedriver_exe_path)
                    self.master_app.save_current_config()
                    logging.info(f"{worker_log_prefix} Đã tự động tải ChromeDriver thành công: {chromedriver_exe_path}")
                except Exception as e_chromedriver_dl:
                    error_msg = f"Không thể tìm hoặc tự động tải ChromeDriver. Lỗi: {e_chromedriver_dl}.\n\nVui lòng tải ChromeDriver thủ công..."
                    logging.error(f"{worker_log_prefix} {error_msg}")
                    self.master_app.after(0, lambda: messagebox.showerror("Lỗi ChromeDriver", error_msg, parent=self))
                    self._handle_youtube_upload_completion(False, None, error_msg, False)
                    return

            driver = None
            service = None
            max_driver_init_retries = 3
            driver_init_delay_seconds = 5
            config_directory = os.path.dirname(get_config_path())
            user_data_dir_for_chrome = os.path.join(config_directory, "ChromeProfile")

            cleanup_stale_chrome_processes(user_data_dir_for_chrome)
            time.sleep(1)

            for attempt in range(max_driver_init_retries):
                try:
                    logging.info(f"{worker_log_prefix} Đang khởi tạo WebDriver (thử lần {attempt + 1}/{max_driver_init_retries})...")
                    chrome_options = webdriver.ChromeOptions()
                    chrome_options.binary_location = chrome_portable_exe_path                
                    # 1. Giả mạo User-Agent của một trình duyệt Chrome thật trên Windows
                    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                    chrome_options.add_argument(f'user-agent={user_agent}')
                    
                    # 2. Các cờ để vô hiệu hóa tính năng tự động hóa mà trang web có thể phát hiện
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    chrome_options.add_experimental_option('useAutomationExtension', False)
                    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

                    # <<< THAY ĐỔI 1: Luôn thiết lập kích thước cửa sổ cho headless mode >>>
                    if hasattr(self, 'youtube_headless_var') and self.youtube_headless_var.get():
                        logging.info(f"{worker_log_prefix} Chạy ở chế độ không đầu (headless) với kích thước cửa sổ 1920x1080.")
                        chrome_options.add_argument("--headless=new")
                        chrome_options.add_argument("--window-size=1920,1080") # Rất quan trọng!
                    else:
                        logging.info(f"{worker_log_prefix} Chạy ở chế độ có giao diện.")        

                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--disable-gpu")
                    chrome_options.add_argument("--disable-extensions")
                    chrome_options.add_argument("--disable-infobars")
                    chrome_options.add_argument("--disable-browser-side-navigation")
                    chrome_options.add_argument("--disable-features=RendererCodeIntegrity")
                    chrome_options.add_argument("--disable-background-networking")
                    chrome_options.add_argument("--disable-default-apps")
                    chrome_options.add_argument("--disable-sync")
                    chrome_options.add_argument("--no-default-browser-check")
                    chrome_options.add_argument("--disable-popup-blocking")
                    chrome_options.add_argument("--ignore-certificate-errors")
                    chrome_options.add_argument("--remote-debugging-port=9222")
                    chrome_options.add_argument("--log-level=3")
                    prefs = {"profile.default_content_setting_values.notifications": 2}
                    chrome_options.add_experimental_option("prefs", prefs)
                    os.makedirs(user_data_dir_for_chrome, exist_ok=True)
                    chrome_options.add_argument(f"user-data-dir={user_data_dir_for_chrome}")
                    logging.info(f"{worker_log_prefix} Sử dụng User Data Directory: {user_data_dir_for_chrome}")
                    service = Service(chromedriver_exe_path, log_path=os.path.join(config_directory, "chromedriver.log"))
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    logging.info(f"{worker_log_prefix} WebDriver đã khởi động thành công.")
                    break
                except Exception as e_driver_init:
                    logging.error(f"{worker_log_prefix} Lỗi khi khởi tạo WebDriver (thử lần {attempt + 1}): {e_driver_init}", exc_info=False)
                    if os.path.exists(user_data_dir_for_chrome):
                        try:
                            shutil.rmtree(user_data_dir_for_chrome)
                            logging.warning(f"{worker_log_prefix} Đã xóa thư mục User Data Directory.")
                        except Exception as e_rm:
                            logging.error(f"{worker_log_prefix} Lỗi khi xóa thư mục profile: {e_rm}")
                    if attempt < max_driver_init_retries - 1:
                        time.sleep(driver_init_delay_seconds)
                    else:
                        error_msg_init = f"Không thể khởi động trình duyệt Chrome sau {max_driver_init_retries} lần thử."
                        self.master_app.after(0, lambda: messagebox.showerror("Lỗi Khởi Tạo Trình Duyệt", f"{error_msg_init}\n\nChi tiết: {e_driver_init}", parent=self))
                        self._handle_youtube_upload_completion(False, None, error_msg_init, False)
                        return
            
            if driver is None:
                self._handle_youtube_upload_completion(False, None, "WebDriver không khởi tạo được.", False)
                return

            # --- CẬP NHẬT LOCATORS: THÊM ID CHO LINK VIDEO ---
            # Use YOUTUBE_LOCATORS from service
            YOUTUBE_LOCATORS = self.master_app.youtube_service.get_youtube_locators() or {
                # --- Các locators không đổi ---
                "title": (By.XPATH, "//div[@aria-label='Thêm tiêu đề để mô tả video của bạn (nhập ký tự @ để đề cập tên một kênh)' or @aria-label='Add a title that describes your video (type @ to mention a channel)']"),
                "description": (By.XPATH, "//div[@aria-label='Giới thiệu về video của bạn cho người xem (nhập ký tự @ để đề cập tên một kênh)' or @aria-label='Tell viewers about your video (type @ to mention a channel)']"),
                "not_for_kids": (By.NAME, "VIDEO_MADE_FOR_KIDS_NOT_MFK"),
                "next_button": (By.ID, "next-button"),
                "done_button": (By.ID, "done-button"),
                "video_url_link": (By.XPATH, "//a[contains(@href, 'youtu.be/') or contains(@href, '/shorts/')]"),
                "privacy_private_radio": (By.CSS_SELECTOR, "tp-yt-paper-radio-button[name='PRIVATE']"),
                "privacy_unlisted_radio": (By.CSS_SELECTOR, "tp-yt-paper-radio-button[name='UNLISTED']"),
                "privacy_public_radio": (By.CSS_SELECTOR, "tp-yt-paper-radio-button[name='PUBLIC']"),
                "thumbnail_file_input": (By.XPATH, "//input[@id='file-loader']"),
                "tags_container": (By.ID, "tags-container"),
                "tags_input": (By.ID, "text-input"),
                "uploading_popup": (By.XPATH, "//ytcp-dialog[.//h1[contains(text(), 'Tải video lên') or contains(text(), 'Uploading video')]]"),
                "alternative_upload_popup": (By.CSS_SELECTOR, "ytcp-multi-progress-monitor"),
                "add_cards_button": (By.ID, "cards-button"),
                "cards_editor_dialog": (By.ID, "dialog"),
                "ALL_PLAYLISTS_IN_LIST": (By.XPATH, "//ytcp-entity-card"),
                "cards_editor_save_button": (By.ID, "save-button"),
                "cards_editor_save_button_ENABLED": (By.CSS_SELECTOR, "ytcp-button#save-button:not([disabled])"),
                "ENDSCREEN_VIDEO_TIMELINE_TRACK": (By.ID, "VIDEO_THUMBNAILS"),
                "RETRY_BUTTON_IN_EDITOR": (By.ID, "error-retry-button"),

                # --- CÁC LOCATORS ĐÃ ĐƯỢC CẬP NHẬT ĐA NGÔN NGỮ ---
                "show_more_button": (By.XPATH, "//ytcp-button[.//div[contains(text(),'Hiện thêm') or contains(text(), 'Show more')]]"),

                "CARD_TYPE_PLAYLIST": (By.XPATH, "//div[contains(@class, 'info-card-type-option-container') and .//span[contains(text(), 'Danh sách phát') or contains(text(), 'Playlist')]]"),
                
                "SELECTED_PLAYLIST_NAME_IN_CARD_EDITOR": (By.XPATH, "//div[@id='label-container']//div[contains(@class, 'entityName') and (contains(., 'Danh sách phát:') or contains(., 'Playlist:'))]"),

                "add_end_screen_button": (By.XPATH, "//ytcp-button[@id='endscreens-button']"),

                "endscreen_template_1vid_1sub": (By.XPATH, "//div[@aria-label='1 video, 1 đăng ký' or @aria-label='1 video, 1 subscribe']"),

                "save_button_on_main_page_ENABLED": (By.XPATH, "//ytcp-button[@id='save-button' and not(@disabled)]"),

                # Nút này rất quan trọng, đã được cập nhật
                "DISCARD_CHANGES_BUTTON": (By.XPATH, "//ytcp-button-shape[.//div[contains(text(), 'Hủy thay đổi') or contains(text(), 'Discard changes')]]//button"),

                # Dialog editor End screen (đa ngôn ngữ, CHỈ khi đang mở)
                "ENDSCREEN_EDITOR_DIALOG": (
                    By.XPATH,
                    "//ytcp-dialog[@opened and .//h1[contains(., 'Màn hình kết thúc') or contains(., 'End screen')]]"
                ),

                # Dialog editor Cards (đa ngôn ngữ, CHỈ khi đang mở)
                "CARDS_EDITOR_DIALOG": (
                    By.XPATH,
                    "//ytcp-dialog[@opened and .//h1[contains(., 'Thẻ') or contains(., 'Cards')]]"
                ),

                # Bất kỳ dialog editor chung (fallback, CHỈ khi đang mở)
                "EDITOR_DIALOG_ANY": (
                    By.CSS_SELECTOR,
                    "ytcp-dialog[opened], tp-yt-paper-dialog[opened]"
                ),
                
            }

            try:
                # BƯỚC 1: ĐIỀU HƯỚNG VÀ TẢI FILE VIDEO LÊN
                self.master_app.after(0, lambda: self.master_app.update_status(f"📤 Trình duyệt: Đang mở trang upload..."))
                driver.get("https://www.youtube.com/upload")
                self._log_youtube_upload("Đã mở trang YouTube Studio...")
                self.master_app.after(0, lambda: self.master_app.update_status(f"📤 Trình duyệt: Đang gửi tệp video..."))
                file_input_element = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
                file_input_element.send_keys(os.path.abspath(video_path))
                logging.info(f"{worker_log_prefix} Đã gửi tệp video. Đang chờ xác định giao diện upload...")
                self.master_app.after(0, lambda: self.master_app.update_status(f"📤 Trình duyệt: Đã gửi tệp, đang chờ giao diện..."))

                # Khởi tạo biến ở đây để tránh lỗi UnboundLocalError
                uploaded_video_id = None

                try:
                    # Chờ 60 giây để MỘT TRONG HAI giao diện xuất hiện
                    wait = WebDriverWait(driver, 60)
                    
                    condition_normal_page = EC.presence_of_element_located(YOUTUBE_LOCATORS["title"])
                    condition_alternative_popup = EC.presence_of_element_located(YOUTUBE_LOCATORS["alternative_upload_popup"])
                    
                    wait.until(EC.any_of(condition_normal_page, condition_alternative_popup))
                    logging.info(f"{worker_log_prefix} Đã phát hiện một giao diện upload.")

                    try:
                        # Thử tìm popup nhỏ trước
                        alt_popup = driver.find_element(*YOUTUBE_LOCATORS["alternative_upload_popup"])
                        
                        logging.warning(f"{worker_log_prefix} ⚠️ ĐÃ PHÁT HIỆN GIAO DIỆN UPLOAD NHỎ (MINI UPLOADER).")
                        
                        log_message_for_failed_task = f"Bỏ qua (Gặp popup nhỏ): {os.path.basename(video_path)}"
                        log_failed_task(log_message_for_failed_task)
                        
                        self._log_youtube_upload("⚠️ Lỗi Giao Diện: YouTube hiển thị popup upload nhỏ. Tác vụ sẽ được coi là thành công nhưng không thể điền chi tiết (mô tả, playlist, v.v.).")
                        
                        self.master_app.after(0, lambda: self.master_app.update_status(f"ℹ️ Trình duyệt: Gặp giao diện nhỏ, kết thúc sớm."))
                        
                        time.sleep(5)
                        # SỬA LỖI 1: Truyền LOCATOR vào
                        click_with_fallback(driver, (By.ID, "close-button"))
                        
                        self._handle_youtube_upload_completion(True, None, "Phát hiện popup upload nhỏ, coi như thành công.", False)
                        return

                    except NoSuchElementException: # Bây giờ Python đã biết NoSuchElementException là gì
                        logging.info(f"{worker_log_prefix} ✅ Đã xác nhận giao diện upload đầy đủ. Tiếp tục quy trình...")
                        self._log_youtube_upload("Gặp giao diện upload đầy đủ, tiếp tục điền thông tin.")

                except TimeoutException:
                    error_msg_no_ui = "Sau khi gửi file, không có giao diện upload nào của YouTube xuất hiện."
                    logging.error(f"{worker_log_prefix} {error_msg_no_ui}")
                    self._handle_youtube_upload_completion(False, None, error_msg_no_ui, False)
                    return

                # LẤY LINK NGAY LẬP TỨC --- >>>
                try:
                    # Chờ cho đến khi thẻ <a> chứa link video xuất hiện.
                    video_link_element = WebDriverWait(driver, 120).until(
                        EC.presence_of_element_located(YOUTUBE_LOCATORS["video_url_link"])
                    )
                    
                    # Lấy URL và trích xuất ID
                    video_url = video_link_element.get_attribute("href")
                    # Cập nhật regex để khớp với 'youtu.be' hoặc 'http://googleusercontent.com/youtube.com/6'
                    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', video_url)
                    if match:
                        uploaded_video_id = match.group(1)
                        logging.info(f"{worker_log_prefix} ✅ LẤY LINK THÀNH CÔNG! Video ID: {uploaded_video_id}")
                        self._log_youtube_upload(f"Lấy được link video sớm: {video_url}")
                    else:
                        logging.warning(f"{worker_log_prefix} Đã tìm thấy thẻ link nhưng không trích xuất được ID từ URL: {video_url}")
                
                except Exception as e_get_link:
                    # Nếu không lấy được link ở bước này, tác vụ sẽ thất bại vì đây là bước quan trọng.
                    logging.error(f"{worker_log_prefix} Không thể lấy link video sau khi tải tệp lên. Hủy tác vụ. Lỗi: {e_get_link}")
                    self._handle_youtube_upload_completion(False, None, "Không thể lấy link video từ YouTube Studio.", False)
                    return # Thoát khỏi hàm ngay lập tức

                # BƯỚC 2: TIẾP TỤC ĐIỀN THÔNG TIN VÀ CHUYỂN TRANG
                self.master_app.after(0, lambda: self.master_app.update_status(f"🖋 Trình duyệt: Đang điền tiêu đề..."))
                
                # SỬA LỖI 2: Dùng hàm click mới để lấy element
                title_element = click_with_fallback(driver, YOUTUBE_LOCATORS["title"], timeout=60)
                time.sleep(0.5)
                title_element.send_keys(Keys.CONTROL + "a")
                title_element.send_keys(Keys.DELETE)
                time.sleep(0.5)
                # --- LÀM SẠCH TIÊU ĐỀ TRƯỚC KHI GỬI ---
                cleaned_title = sanitize_youtube_text(title, max_length=100) # Giới hạn 100 ký tự
                title_element.send_keys(cleaned_title)
                self._log_youtube_upload(f"🖋 Đã điền tiêu đề video.")
                logging.info(f"{worker_log_prefix} Đã điền tiêu đề.")
                
                self.master_app.after(0, lambda: self.master_app.update_status(f"🖋 Trình duyệt: Đang điền mô tả..."))
                if description is not None:
                    # SỬA LỖI 3: Dùng hàm click mới để lấy element
                    description_element = click_with_fallback(driver, YOUTUBE_LOCATORS["description"])
                    time.sleep(0.5)
                    description_element.send_keys(Keys.CONTROL + "a")
                    description_element.send_keys(Keys.DELETE)
                    time.sleep(0.5)
                    # --- LÀM SẠCH MÔ TẢ TRƯỚC KHI GỬI ---
                    cleaned_description = sanitize_youtube_text(description, max_length=5000) # Giới hạn 5000 ký tự
                    # Fix: Remove non-BMP characters for ChromeDriver compatibility
                    cleaned_description = ''.join(c for c in cleaned_description if ord(c) < 0x10000)
                    description_element.send_keys(cleaned_description)
                    self._log_youtube_upload(f"🖋 Đã điền mô tả video.")
                    logging.info(f"{worker_log_prefix} Đã điền mô tả.")
                else:
                    self._log_youtube_upload(f"🖋 Bỏ qua điền mô tả.")
                    logging.info(f"{worker_log_prefix} Bỏ qua điền mô tả (để YouTube dùng mặc định).")

                self.master_app.after(0, lambda: self.master_app.update_status(f"✔ Trình duyệt: Đang chọn 'Không dành cho trẻ em'..."))
                # SỬA LỖI 4: Truyền LOCATOR vào
                click_with_fallback(driver, YOUTUBE_LOCATORS["not_for_kids"], timeout=30)
                logging.info(f"{worker_log_prefix} Đã chọn 'Không phải nội dung cho trẻ em'.")

                # Upload Thumbnail
                thumbnail_path = thumbnail_path_from_task
                if thumbnail_path and os.path.exists(thumbnail_path):
                    try:
                        self.master_app.after(0, lambda: self.master_app.update_status(f"🖼 Trình duyệt: Đang tải lên thumbnail..."))
                        self._log_youtube_upload("🖼 Đang tìm vị trí upload thumbnail...")
                        thumbnail_input_element = WebDriverWait(driver, 30).until(EC.presence_of_element_located(YOUTUBE_LOCATORS["thumbnail_file_input"]))
                        thumbnail_input_element.send_keys(os.path.abspath(thumbnail_path))
                        logging.info(f"{worker_log_prefix} Đã gửi đường dẫn thumbnail: {os.path.basename(thumbnail_path)}")
                        self._log_youtube_upload(f"✅ Đã tải lên thumbnail.")
                        self.master_app.after(0, lambda: self.master_app.update_status(f"🖼 Trình duyệt: Tải thumbnail xong."))
                        time.sleep(5)
                    except Exception as e_thumb:
                        logging.warning(f"{worker_log_prefix} Lỗi khi upload thumbnail: {e_thumb}")
                        self._log_youtube_upload(f"⚠️ Không thể upload thumbnail.")        

                # DANH SÁCH PHÁT
                if playlist_name:
                    try:
                        self._log_youtube_upload(f"🎶 Đang tìm danh sách phát: '{playlist_name}'...")
                        self.master_app.after(0, lambda: self.master_app.update_status(f"🎶 Đang tìm playlist: {playlist_name}..."))
                        
                        playlist_dropdown_xpath = "//ytcp-dropdown-trigger[@aria-label='Chọn danh sách phát']"
                        # SỬA LỖI 5: Truyền LOCATOR (tuple) vào
                        click_with_fallback(driver, (By.XPATH, playlist_dropdown_xpath), timeout=20)
                        logging.info(f"{worker_log_prefix} Đã click vào dropdown danh sách phát.")
                        time.sleep(2)

                        all_playlist_items_selector = "li.row"
                        all_items = WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, all_playlist_items_selector)))
                        logging.info(f"{worker_log_prefix} Đã tìm thấy {len(all_items)} mục trong danh sách phát.")

                        found_playlist = False
                        for item in all_items:
                            try:
                                playlist_label_element = item.find_element(By.CSS_SELECTOR, "span.label-text")
                                playlist_label_text_from_web = playlist_label_element.get_attribute('textContent').strip()
                                playlist_name_from_task = playlist_name.strip()
                                normalized_web_text = normalize_string_for_comparison(playlist_label_text_from_web)
                                normalized_task_text = normalize_string_for_comparison(playlist_name_from_task)
                                
                                logging.info(f"NORMALIZED: So sánh '{normalized_web_text}' VỚI '{normalized_task_text}'")

                                if normalized_web_text and normalized_web_text == normalized_task_text:
                                    logging.info(f"{worker_log_prefix} >>> ĐÃ TÌM THẤY '{playlist_label_text_from_web}'! Đang click...")
                                    checkbox_to_click = item.find_element(By.TAG_NAME, "ytcp-checkbox-lit")
                                    # SỬA LỖI 6: Dùng JS click cho element con (vì _click_with_fallback yêu cầu locator)
                                    driver.execute_script("arguments[0].click();", checkbox_to_click)
                                    found_playlist = True
                                    break
                            except Exception as e_find_playlist_item:
                                logging.warning(f"Lỗi nhỏ khi duyệt qua một mục playlist: {e_find_playlist_item}")
                                continue
                        
                        if not found_playlist:
                            raise Exception(f"Không tìm thấy danh sách phát có tên '{playlist_name}' trong danh sách.")

                        time.sleep(1)
                        done_button_xpath = "//ytcp-button[.//div[text()='Xong']]"
                        # SỬA LỖI 7: Truyền LOCATOR (tuple) vào
                        click_with_fallback(driver, (By.XPATH, done_button_xpath), timeout=10)
                        logging.info(f"{worker_log_prefix} Đã click nút 'Xong' sau khi chọn danh sách phát.")
                        self._log_youtube_upload(f"✅ Đã chọn danh sách phát: '{playlist_name}'.")
                        self.master_app.after(0, lambda: self.master_app.update_status(f"🎶 Trình duyệt: Đã chọn xong playlist."))

                    except Exception as e_playlist:
                        logging.warning(f"{worker_log_prefix} Lỗi khi chọn danh sách phát: {e_playlist}", exc_info=False)
                        self._log_youtube_upload(f"⚠️ Không tìm thấy hoặc không thể chọn danh sách phát: '{playlist_name}'.")
                        try:
                            from selenium.webdriver.common.action_chains import ActionChains
                            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                            logging.info(f"{worker_log_prefix} Đã thử nhấn Escape để đóng dialog playlist.")
                        except Exception:
                            pass

                # BƯỚC 1: CLICK "HIỆN THÊM"
                try:
                    self.master_app.after(0, lambda: self.master_app.update_status(f"... Đang tìm nút 'Hiện thêm'..."))
                    self._log_youtube_upload("🔎 Đang tìm nút 'Hiện thêm'...")
                    # SỬA LỖI 8: Truyền LOCATOR vào (hàm click mới đã tự cuộn)
                    click_with_fallback(driver, YOUTUBE_LOCATORS["show_more_button"], timeout=20)
                    logging.info(f"{worker_log_prefix} Đã click 'Hiện thêm'.")
                    self.master_app.after(0, lambda: self.master_app.update_status(f"✅ Đã nhấn 'Hiện thêm'."))
                    time.sleep(1.5)
                except Exception as e_show_more:
                    logging.warning(f"{worker_log_prefix} Không tìm thấy hoặc không click được nút 'Hiện thêm': {e_show_more}")
                    self._log_youtube_upload("⚠️ Không tìm thấy nút 'Hiện thêm'.")

                # --- BƯỚC 2: CHỌN DANH MỤC VIDEO (TÍCH HỢP 2 PHƯƠNG PHÁP) ---
                if category_id and category_id in YOUTUBE_CATEGORIES:
                    category_name_to_select = YOUTUBE_CATEGORIES[category_id]
                    
                    try:
                        # --- CÁC BƯỚC CHUNG ---
                        self.master_app.after(0, lambda: self.master_app.update_status(f"... Đang chọn danh mục..."))
                        self._log_youtube_upload(f"🏷 Bắt đầu quá trình chọn danh mục: '{category_name_to_select}'")

                        # Click để mở dropdown (dùng chung cho cả 2 phương pháp)
                        category_dropdown_trigger_xpath = "//ytcp-form-select[@id='category']//ytcp-dropdown-trigger"
                        # SỬA LỖI 9: Truyền LOCATOR (tuple) vào
                        click_with_fallback(driver, (By.XPATH, category_dropdown_trigger_xpath), timeout=15)
                        logging.info(f"{worker_log_prefix} Đã click mở dropdown danh mục.")
                        
                        time.sleep(1.5)

                        # --- THỬ PHƯƠNG PHÁP 1: TÌM THEO VĂN BẢN (ƯU TIÊN) ---
                        try:
                            logging.info(f"{worker_log_prefix} Đang thử Phương pháp 1: Tìm theo văn bản...")
                            
                            category_item_xpath = f"//tp-yt-paper-listbox//yt-formatted-string[normalize-space(.)='{category_name_to_select}']"
                            # SỬA LỖI 10: Truyền LOCATOR (tuple) vào
                            click_with_fallback(driver, (By.XPATH, category_item_xpath), timeout=10)
                            
                            logging.info(f"{worker_log_prefix} ✅ Phương pháp 1 THÀNH CÔNG: Đã chọn '{category_name_to_select}' bằng văn bản.")

                        # --- NẾU PHƯƠNG PHÁP 1 THẤT BẠI, CHUYỂN SANG PHƯƠNG PHÁP 2: DÙNG BÀN PHÍM ---
                        except Exception as e_text_method:
                            logging.warning(f"{worker_log_prefix} ⚠️ Phương pháp 1 thất bại: {e_text_method}. Chuyển sang Phương pháp 2: Dùng bàn phím.")
                            self._log_youtube_upload(f"Lỗi chọn theo text, đang thử lại bằng bàn phím...")

                            # Tìm thẻ <body> để gửi phím
                            body_element = driver.find_element(By.TAG_NAME, "body")

                            # Lấy số lần nhấn phím từ "bản đồ" điều hướng của bạn
                            number_of_presses = YOUTUBE_CATEGORY_NAVIGATION_ORDER.get(category_id, -1)
                            
                            if number_of_presses == -1:
                                raise Exception(f"Không tìm thấy thứ tự điều hướng bàn phím cho Category ID '{category_id}'.")
                                
                            logging.info(f"{worker_log_prefix} Sẽ nhấn Mũi tên xuống {number_of_presses} lần.")

                            # Gửi các phím mũi tên xuống
                            for _ in range(number_of_presses):
                                body_element.send_keys(Keys.ARROW_DOWN)
                                time.sleep(0.15) # Giữ khoảng nghỉ để ổn định

                            # Gửi phím Enter để chọn
                            body_element.send_keys(Keys.ENTER)
                            logging.info(f"{worker_log_prefix} ✅ Phương pháp 2 THÀNH CÔNG: Đã chọn '{category_name_to_select}' bằng bàn phím.")

                        # --- LOG KẾT QUẢ THÀNH CÔNG CHUNG ---
                        self._log_youtube_upload(f"✅ Đã chọn danh mục: '{category_name_to_select}'.")
                        self.master_app.after(0, lambda: self.master_app.update_status(f"✅ Đã chọn danh mục."))
                        
                        # Chờ cho dropdown đóng lại để xác nhận hành động hoàn tất
                        WebDriverWait(driver, 10).until(
                            EC.invisibility_of_element_located((By.XPATH, "//tp-yt-paper-listbox"))
                        )

                    # --- NẾU CẢ 2 PHƯƠNG PHÁP ĐỀU THẤT BẠI ---
                    except Exception as e_category:
                        logging.critical(f"{worker_log_prefix} LỖI NGHIÊM TRỌNG: Cả 2 phương pháp chọn danh mục đều thất bại. Lỗi: {e_category}", exc_info=True)
                        self._log_youtube_upload(f"❌ Lỗi nghiêm trọng: Không thể chọn danh mục '{category_name_to_select}'.")
                        
                        try:
                            config_directory = os.path.dirname(get_config_path())
                            screenshot_path = os.path.join(config_directory, f"error_screenshot_category_{int(time.time())}.png")
                            driver.save_screenshot(screenshot_path)
                            logging.info(f"Đã lưu ảnh chụp màn hình lỗi tại: {screenshot_path}")
                            self.master_app.after(0, lambda: messagebox.showwarning("Lỗi Chọn Danh Mục",
                                                                       f"Không thể tự động chọn danh mục.\n"
                                                                       f"Ảnh chụp màn hình lỗi đã được lưu tại:\n\n{screenshot_path}\n\n"
                                                                       f"Vui lòng kiểm tra ảnh để xem lỗi và thử lại.", parent=self))
                        except Exception as e_ss:
                            logging.error(f"Không thể chụp ảnh màn hình lỗi: {e_ss}")

                # BƯỚC 3: ĐIỀN THẺ TAG (PHIÊN BẢN KẾT HỢP TỐT NHẤT)
                if tags: # tags là một list
                    try:
                        self.master_app.after(0, lambda: self.master_app.update_status(f"... Đang điền thẻ tags..."))
                        self._log_youtube_upload("🔎 Đang tìm và chờ ô nhập thẻ tags sẵn sàng...")

                        # 1. DÙNG LOGIC CŨ: Tìm container trước để đảm bảo phạm vi chính xác.
                        tags_container = WebDriverWait(driver, 20).until(
                            EC.visibility_of_element_located(YOUTUBE_LOCATORS["tags_container"])
                        )

                        # 2. TÌM Ô INPUT BÊN TRONG CONTAINER VÀ LƯU LẠI THAM CHIẾU (reference).
                        tags_input_field = tags_container.find_element(*YOUTUBE_LOCATORS["tags_input"])

                        # 3. DÙNG HÀM CLICK MẠNH MẼ ĐỂ CLICK VÀO Ô NHẬP LIỆU.
                        click_with_fallback(driver, YOUTUBE_LOCATORS["tags_input"])
                        time.sleep(0.8)
                        
                        self._log_youtube_upload(f"🖋 Đang điền {len(tags)} thẻ tags...")
                        
                        # 4. GỬI KEYS VÀO THAM CHIẾU ỔN ĐỊNH ĐÃ TÌM Ở BƯỚC 2.
                        cleaned_tags = [sanitize_youtube_text(tag, max_length=50) for tag in tags]
                        tags_string = ", ".join([tag for tag in cleaned_tags if tag.strip()])
                        
                        tags_input_field.send_keys(tags_string)
                        time.sleep(0.5)
                        tags_input_field.send_keys(',')
                        
                        logging.info(f"{worker_log_prefix} Đã điền xong các thẻ tags.")
                        self._log_youtube_upload("✅ Đã điền xong thẻ tags.")
                        self.master_app.after(0, lambda: self.master_app.update_status(f"✅ Đã điền xong tags."))

                    except Exception as e_tags:
                        logging.warning(f"{worker_log_prefix} Lỗi khi điền thẻ tags: {e_tags}", exc_info=True)
                        self._log_youtube_upload(f"⚠️ Không thể điền thẻ tags.")

                # === BƯỚC 2: NHẤN "TIẾP THEO" LẦN 1 ĐỂ ĐẾN TRANG "YẾU TỐ VIDEO" ===
                self.master_app.after(0, lambda: self.master_app.update_status(f"➡ Trình duyệt: Chuyển đến trang Yếu tố video..."))
                click_with_fallback(driver, YOUTUBE_LOCATORS["next_button"], timeout=60)

                WebDriverWait(driver, 30).until(EC.element_to_be_clickable(YOUTUBE_LOCATORS["add_end_screen_button"]))
                logging.info(f"{worker_log_prefix} Trang 'Yếu tố video' đã tải xong.")

                # THÊM VÀO: Cho YouTube thời gian để ổn định hoàn toàn
                logging.info(f"{worker_log_prefix} Tạm dừng 2 giây để ổn định trang 'Yếu tố video'...")
                self.master_app.after(0, lambda: self.master_app.update_status(f"Ổn định trang Yếu tố video..."))
                time.sleep(2)

                # === HELPERS (drop-in): Retry/Discard & Dialog visibility/invisibility ===
                # Các key dialog trong YOUTUBE_LOCATORS
                DIALOG_KEYS = ("ENDSCREEN_EDITOR_DIALOG", "CARDS_EDITOR_DIALOG", "EDITOR_DIALOG_ANY")

                def _is_visible(locator) -> bool:
                    """Trả về True nếu có ít nhất 1 element đang HIỂN THỊ (displayed=True)."""
                    try:
                        elems = driver.find_elements(*locator)
                        return any(e.is_displayed() for e in elems)
                    except Exception:
                        return False

                def _wait_dialogs_invisible(timeout_each: int = 15):
                    """Chờ các dialog editor biến mất (ẩn hẳn). Không raise nếu 1 vài cái không kịp tắt."""
                    for key in DIALOG_KEYS:
                        try:
                            WebDriverWait(driver, timeout_each).until(
                                EC.invisibility_of_element_located(YOUTUBE_LOCATORS[key])
                            )
                        except Exception:
                            continue
                    # Lớp đảm bảo cuối: hết mọi dialog đang mở ([@opened]) thì mới coi như đóng xong
                    try:
                        WebDriverWait(driver, 5).until(
                            lambda d: len(d.find_elements(By.CSS_SELECTOR, "ytcp-dialog[opened], tp-yt-paper-dialog[opened]")) == 0
                        )
                    except Exception:
                        pass

                def _overlay_retry_visible() -> bool:
                    """Overlay lỗi (nút 'Thử lại') có đang HIỂN THỊ thật hay không."""
                    try:
                        return _is_visible(YOUTUBE_LOCATORS["RETRY_BUTTON_IN_EDITOR"])
                    except Exception:
                        return False

                def _try_retry_overlay(editor_name: str, max_tries: int = 2) -> bool:
                    """
                    Nếu thấy overlay lỗi, thử bấm 'Thử lại' tối đa max_tries lần.
                    Trả về True nếu overlay đã biến mất; False nếu vẫn còn.
                    """
                    for i in range(max_tries):
                        if not _overlay_retry_visible():
                            return True
                        self._log_youtube_upload(f"ℹ️ {editor_name}: thấy overlay lỗi → nhấn 'Thử lại' (lần {i+1}/{max_tries})")
                        try:
                            click_with_fallback(driver, YOUTUBE_LOCATORS["RETRY_BUTTON_IN_EDITOR"], timeout=5)
                        except Exception:
                            pass
                        # chờ overlay biến mất
                        try:
                            WebDriverWait(driver, 10).until(lambda d: not _overlay_retry_visible())
                            return True
                        except Exception:
                            continue
                    return not _overlay_retry_visible()

                def _discard_and_wait_close(editor_name: str, quick: bool = False):
                    """
                    Đóng editor an toàn:
                    - quick=True: chỉ bấm Discard nếu clickable nhanh; nếu không thì ESC (dùng cho Gate trước Next).
                    - quick=False: bấm Discard với timeout dài hơn; fallback ESC nếu fail.
                    Sau đó luôn chờ dialog biến mất hẳn.
                    """
                    try:
                        self._log_youtube_upload(f"⚠️ {editor_name}: gặp lỗi/overlay → Hủy thay đổi & bỏ qua.")
                        if quick:
                            # chỉ click khi thực sự clickable nhanh, tránh stale
                            try:
                                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(YOUTUBE_LOCATORS["DISCARD_CHANGES_BUTTON"]))
                                click_with_fallback(driver, YOUTUBE_LOCATORS["DISCARD_CHANGES_BUTTON"], timeout=5)
                            except Exception:
                                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                        else:
                            click_with_fallback(driver, YOUTUBE_LOCATORS["DISCARD_CHANGES_BUTTON"], timeout=10)
                    except Exception:
                        # Fallback: nhấn ESC 1–2 lần nếu không bấm được Discard
                        try:
                            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                            time.sleep(0.3)
                            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                        except Exception:
                            pass

                    # Chờ dialog đóng hẳn (không dựa vào //ytve-player)
                    _wait_dialogs_invisible(timeout_each=15)
                    self._log_youtube_upload(f"✅ {editor_name}: dialog đã đóng, tiếp tục.")

                # === Jitter helper: tạo trễ ngẫu nhiên ngắn để chờ UI “chín” ===
                def _jitter(base=0.25, rand=0.35):
                    try:
                        import random, time as _t
                        _t.sleep(base + random.random() * rand)
                    except Exception:
                        time.sleep(base)

                # --- Xử lý Màn hình kết thúc ---
                if hasattr(self, 'youtube_add_end_screen_var') and self.youtube_add_end_screen_var.get():
                    self.master_app.after(0, lambda: self.master_app.update_status(f"➕ Bắt đầu thêm Màn hình kết thúc..."))
                    self._log_youtube_upload("➕ Đang thử thêm Màn hình kết thúc...")
                    try:
                        # 1) Mở editor
                        logging.info(f"{worker_log_prefix} Đang mở trình chỉnh sửa Màn hình kết thúc...")
                        click_with_fallback(driver, YOUTUBE_LOCATORS["add_end_screen_button"], timeout=30)

                        # 2) Chờ 1 trong 3 trạng thái
                        wait_for_editor = WebDriverWait(driver, 120)
                        logging.info(f"{worker_log_prefix} ⏳ Đang chờ Editor tải (thành công) hoặc báo lỗi (thất bại)...")
                        self.master_app.after(0, lambda: self.master_app.update_status(f"⏳ Đang chờ trình chỉnh sửa Màn hình kết thúc tải..."))
                        wait_for_editor.until(EC.any_of(
                            EC.visibility_of_element_located(YOUTUBE_LOCATORS["ENDSCREEN_VIDEO_TIMELINE_TRACK"]),
                            EC.visibility_of_element_located(YOUTUBE_LOCATORS["RETRY_BUTTON_IN_EDITOR"]),
                            EC.element_to_be_clickable(YOUTUBE_LOCATORS["DISCARD_CHANGES_BUTTON"])
                        ))

                        proceed_end = True
                        if _overlay_retry_visible():
                            logging.warning(f"{worker_log_prefix} End screen editor có overlay lỗi (Retry). Thử Retry trước khi bỏ qua.")
                            if not _try_retry_overlay("End screen", max_tries=2):
                                self.master_app.after(0, lambda: self.master_app.update_status(f"⚠ Gặp lỗi editor, bỏ qua Màn hình kết thúc..."))
                                _discard_and_wait_close("End screen")
                                proceed_end = False
                            else:
                                self._log_youtube_upload("✅ Overlay đã hết sau khi Retry. Tiếp tục thao tác End screen.")

                        # 4) Nếu editor sẵn sàng → chọn template + lưu
                        if proceed_end and not _overlay_retry_visible():
                            logging.info(f"{worker_log_prefix} ✅ Editor Màn hình kết thúc sẵn sàng (không overlay).")
                            self.master_app.after(0, lambda: self.master_app.update_status(f"✅ Editor đã tải, đang áp dụng mẫu..."))
                            self._log_youtube_upload("✅ Editor Màn hình kết thúc đã tải, bắt đầu thao tác.")
                            _jitter()

                            WebDriverWait(driver, 20).until(
                                EC.element_to_be_clickable(YOUTUBE_LOCATORS["endscreen_template_1vid_1sub"])
                            )
                            click_with_fallback(driver, YOUTUBE_LOCATORS["endscreen_template_1vid_1sub"], timeout=20)
                            _jitter()

                            self.master_app.after(0, lambda: self.master_app.update_status(f"Đang lưu Màn hình kết thúc..."))
                            save_button_locator = (By.XPATH, "//ytcp-button[@id='save-button' and not(@disabled)]")
                            click_with_fallback(driver, save_button_locator, timeout=60)

                            # Chờ dialog đóng hẳn theo [opened]
                            try:
                                WebDriverWait(driver, 10).until(
                                    lambda d: len(d.find_elements(
                                        By.CSS_SELECTOR, "ytcp-dialog[opened], tp-yt-paper-dialog[opened]"
                                    )) == 0
                                )
                            except Exception:
                                try:
                                    WebDriverWait(driver, 5).until(
                                        EC.invisibility_of_element_located(YOUTUBE_LOCATORS["EDITOR_DIALOG_ANY"])
                                    )
                                except Exception:
                                    pass

                            self.master_app.after(0, lambda: self.master_app.update_status(f"✅ Đã thêm Màn hình kết thúc."))
                            self._log_youtube_upload("✅ Đã thêm Màn hình kết thúc thành công.")

                    except Exception as e_endscreen:
                        logging.error(f"{worker_log_prefix} ❌ Lỗi End screen: {e_endscreen}", exc_info=False)
                        _discard_and_wait_close("End screen")
                        self.master_app.after(0, lambda: self.master_app.update_status(f"❌ Lỗi, bỏ qua Màn hình kết thúc."))
                        self._log_youtube_upload("❌ Bỏ qua Màn hình kết thúc do lỗi.")

                time.sleep(1.0)

                # --- Xử lý Thẻ ---
                if hasattr(self, 'youtube_add_cards_var') and self.youtube_add_cards_var.get():
                    self.master_app.after(0, lambda: self.master_app.update_status(f"➕ Bắt đầu thêm Thẻ..."))
                    self._log_youtube_upload("➕ Đang thử thêm Thẻ...")
                    try:
                        # 1) Mở editor
                        logging.info(f"{worker_log_prefix} Đang mở trình chỉnh sửa Thẻ...")
                        click_with_fallback(driver, YOUTUBE_LOCATORS["add_cards_button"], timeout=30)

                        # 2) Chờ 1 trong 3 trạng thái
                        wait_for_editor = WebDriverWait(driver, 120)
                        logging.info(f"{worker_log_prefix} ⏳ Đang chờ Editor tải (thành công) hoặc báo lỗi (thất bại)...")
                        self.master_app.after(0, lambda: self.master_app.update_status(f"⏳ Đang chờ trình chỉnh sửa Thẻ tải..."))
                        wait_for_editor.until(EC.any_of(
                            EC.visibility_of_element_located(YOUTUBE_LOCATORS["ENDSCREEN_VIDEO_TIMELINE_TRACK"]),
                            EC.visibility_of_element_located(YOUTUBE_LOCATORS["RETRY_BUTTON_IN_EDITOR"]),
                            EC.element_to_be_clickable(YOUTUBE_LOCATORS["DISCARD_CHANGES_BUTTON"])
                        ))

                        proceed_cards = True
                        if _overlay_retry_visible():
                            logging.warning(f"{worker_log_prefix} Cards editor có overlay lỗi (Retry). Thử Retry trước khi bỏ qua.")
                            if not _try_retry_overlay("Cards", max_tries=2):
                                self.master_app.after(0, lambda: self.master_app.update_status(f"⚠️ Gặp lỗi editor, bỏ qua Thẻ..."))
                                _discard_and_wait_close("Cards")
                                proceed_cards = False
                            else:
                                self._log_youtube_upload("✅ Overlay đã hết sau khi Retry. Tiếp tục thao tác Cards.")

                        # 4) Nếu editor sẵn sàng → CHỌN PLAYLIST NGẪU NHIÊN THẬT SỰ + lưu
                        if proceed_cards and not _overlay_retry_visible():
                            logging.info(f"{worker_log_prefix} ✅ Editor Thẻ sẵn sàng (không overlay).")
                            self.master_app.after(0, lambda: self.master_app.update_status(f"✅ Editor đã tải, đang chọn playlist..."))
                            self._log_youtube_upload("✅ Editor Thẻ đã tải, bắt đầu thao tác.")
                            _jitter()

                            WebDriverWait(driver, 20).until(
                                EC.element_to_be_clickable(YOUTUBE_LOCATORS["CARD_TYPE_PLAYLIST"])
                            )
                            click_with_fallback(driver, YOUTUBE_LOCATORS["CARD_TYPE_PLAYLIST"], timeout=20)
                            _jitter()

                            # Lấy danh sách item hiện có trong DOM
                            all_cards = WebDriverWait(driver, 30).until(
                                EC.presence_of_all_elements_located(YOUTUBE_LOCATORS["ALL_PLAYLISTS_IN_LIST"])
                            )

                            # Lọc những item có text hợp lệ, tránh "Tạo danh sách phát"/"Create playlist"
                            valid = []
                            for el in all_cards:
                                try:
                                    txt = el.text.strip()
                                    if not txt:
                                        continue
                                    low = txt.lower()
                                    if ("tạo danh sách" in low) or ("create playlist" in low):
                                        continue
                                    valid.append((el, txt))
                                except Exception:
                                    continue

                            if not valid:
                                raise RuntimeError("Không tìm thấy playlist hợp lệ trong Cards editor.")

                            # Đọc label đang hiển thị (nếu có) để kiểm tra đã đổi sau khi click
                            try:
                                before_label = driver.find_element(*YOUTUBE_LOCATORS["SELECTED_PLAYLIST_NAME_IN_CARD_EDITOR"]) \
                                                     .get_attribute("textContent").strip()
                            except Exception:
                                before_label = None

                            # Thử tối đa 3 lần để đảm bảo chọn khác mặc định
                            import random as _r
                            picked_ok = False
                            for _ in range(3):
                                el, txt = _r.choice(valid)

                                # Scroll vào giữa viewport để tránh element “ngoài tầm”
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'nearest'});", el)
                                    _jitter(0.2, 0.25)
                                except Exception:
                                    pass

                                # Đợi clickable rồi click với fallback
                                try:
                                    WebDriverWait(driver, 10).until(lambda d: el.is_displayed())
                                    try:
                                        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(el))
                                        el.click()
                                    except Exception:
                                        try:
                                            # click vào checkbox/radio con nếu có
                                            sub = None
                                            for sel in ("ytcp-checkbox-lit", "ytcp-radio-button", "ytcp-icon-button"):
                                                try:
                                                    sub = el.find_element(By.CSS_SELECTOR, sel)
                                                    break
                                                except Exception:
                                                    continue
                                            target = sub if sub else el
                                            driver.execute_script("arguments[0].click();", target)
                                        except Exception:
                                            driver.execute_script("arguments[0].click();", el)
                                except Exception:
                                    continue

                                _jitter(0.3, 0.35)

                                # Xác nhận label đã đổi
                                try:
                                    label_el = WebDriverWait(driver, 10).until(
                                        EC.visibility_of_element_located(YOUTUBE_LOCATORS["SELECTED_PLAYLIST_NAME_IN_CARD_EDITOR"])
                                    )
                                    after_label = label_el.get_attribute("textContent").strip()
                                except Exception:
                                    after_label = None

                                # Log gọn, không hiện "Label trước/sau"
                                if (after_label and (after_label != before_label)) or (before_label is None and after_label):
                                    # Đã xác nhận đổi được playlist
                                    self._log_youtube_upload(f"🎲 Chọn playlist: '{txt}' — ✅ đã xác nhận.")
                                    picked_ok = True
                                    break
                                else:
                                    # Chưa xác nhận được, thử tiếp (log ngắn gọn)
                                    self._log_youtube_upload(f"🎲 Chọn playlist: '{txt}' — ⏳ chưa xác nhận, thử lại...")


                                if (after_label and (after_label != before_label)) or (before_label is None and after_label):
                                    picked_ok = True
                                    break

                            if not picked_ok:
                                logging.warning(f"{worker_log_prefix} Không xác nhận được label đổi, vẫn tiếp tục lưu theo lựa chọn hiện tại.")

                            self.master_app.after(0, lambda: self.master_app.update_status(f"Đang lưu Thẻ..."))
                            save_button_element = WebDriverWait(driver, 20).until(
                                EC.element_to_be_clickable(YOUTUBE_LOCATORS["cards_editor_save_button_ENABLED"])
                            )
                            save_button_element.click()
                            _jitter()

                            # Chờ dialog đóng hẳn theo [opened]
                            try:
                                WebDriverWait(driver, 10).until(
                                    lambda d: len(d.find_elements(
                                        By.CSS_SELECTOR, "ytcp-dialog[opened], tp-yt-paper-dialog[opened]"
                                    )) == 0
                                )
                            except Exception:
                                try:
                                    WebDriverWait(driver, 5).until(
                                        EC.invisibility_of_element_located(YOUTUBE_LOCATORS["EDITOR_DIALOG_ANY"])
                                    )
                                except Exception:
                                    pass

                            self.master_app.after(0, lambda: self.master_app.update_status(f"✅ Đã thêm Thẻ."))
                            self._log_youtube_upload("✅ Đã thêm Thẻ thành công.")

                    except Exception as e_cards:
                        logging.error(f"{worker_log_prefix} ❌ Lỗi Thẻ: {e_cards}", exc_info=False)
                        _discard_and_wait_close("Cards")
                        self.master_app.after(0, lambda: self.master_app.update_status(f"❌ Lỗi, bỏ qua Thẻ."))
                        self._log_youtube_upload("❌ Bỏ qua Thẻ do lỗi.")

                # Rời dialog/iframe nếu có
                driver.switch_to.default_content()
                time.sleep(1.0)

                # === BƯỚC TIẾP THEO: NHẤN "TIẾP" 2 LẦN ĐỂ HOÀN TẤT ===
                logging.info(f"{worker_log_prefix} Chuẩn bị nhấn 'Tiếp' 2 lần để hoàn tất...")
                self._log_youtube_upload("➡ Chuẩn bị chuyển qua các bước cuối cùng...")

                for i in range(2):  # (1) Yếu tố -> Kiểm tra, (2) Kiểm tra -> Chế độ hiển thị
                    if self.master_app.stop_event.is_set():
                        raise InterruptedError("Dừng bởi người dùng.")

                    log_message = f"Chuyển đến trang Kiểm tra..." if i == 0 else f"Chuyển đến trang Chế độ hiển thị..."
                    self.master_app.after(0, lambda i=i, msg=log_message: self.master_app.update_status(f"➡ {msg} ({i+1}/2)"))

                    self._log_youtube_upload(f"➡ Đang nhấn 'Tiếp' để {log_message.lower()}")
                    try:
                        click_with_fallback(driver, YOUTUBE_LOCATORS["next_button"], timeout=60)
                        logging.info(f"{worker_log_prefix} Đã nhấn nút 'Tiếp' thành công (lần lặp {i+1}).")
                        time.sleep(2.5)  # Chờ trang mới tải xong
                    except Exception as e_click_next:
                        logging.error(f"{worker_log_prefix} Lỗi khi nhấn nút 'Tiếp' ở lần lặp {i+1}: {e_click_next}")
                        raise RuntimeError(f"Không thể nhấn nút 'Tiếp' ở bước chuyển trang thứ {i+1}.")

                # === CHỌN QUYỀN RIÊNG TƯ VÀ XUẤT BẢN ===        
                self.master_app.after(0, lambda: self.master_app.update_status(f"🔒 Đang cài đặt quyền riêng tư..."))
                self._log_youtube_upload(f"🔒 Đang chọn quyền riêng tư: {privacy_status}.")
                target_privacy_locator = YOUTUBE_LOCATORS.get(f"privacy_{privacy_status.lower()}_radio")

                if target_privacy_locator:
                    click_with_fallback(driver, target_privacy_locator, timeout=30)
                    logging.info(f"{worker_log_prefix} Đã chọn quyền riêng tư: {privacy_status}.")

                # --- BƯỚC 5: NHẤN XUẤT BẢN ---
                self.master_app.after(0, lambda: self.master_app.update_status(f"🚀 Chuẩn bị xuất bản video..."))
                self._log_youtube_upload("🚀 Đang nhấn nút Xuất bản/Lưu cuối cùng...")
                click_with_fallback(driver, YOUTUBE_LOCATORS["done_button"], timeout=30)
                logging.info(f"{worker_log_prefix} Đã click nút 'Xuất bản'.")
                self.master_app.after(0, lambda: self.master_app.update_status(f"🚀 Đã nhấn 'Xuất bản'. Đang chờ xác nhận..."))

                # --- BƯỚC 6: XÁC NHẬN CUỐI CÙNG (GUARD 1h) ---
                try:
                    GUARD_SECS = int(getattr(self.master_app, "youtube_final_guard_seconds", 3600))
                    deadline_ts = time.time() + GUARD_SECS

                    logging.info(f"{worker_log_prefix} Đang kiểm tra sự xuất hiện của popup 'Tải lên' (chờ 7 giây)...")

                    try:
                        # 1) Thấy popup "Tải video lên" → chờ biến mất nhưng không quá GUARD_SECS
                        WebDriverWait(driver, 7).until(
                            EC.visibility_of_element_located(YOUTUBE_LOCATORS["uploading_popup"])
                        )
                        logging.info(f"{worker_log_prefix} Đã phát hiện popup 'Tải lên'. Chờ biến mất (tối đa {GUARD_SECS}s)...")
                        self.master_app.after(0, lambda: self.master_app.update_status("📤 Trình duyệt: Video đang được tải lên server YouTube..."))

                        while True:
                            if hasattr(self.master_app, "stop_event") and self.master_app.stop_event.is_set():
                                raise InterruptedError("Dừng bởi người dùng trong khi chờ popup biến mất.")

                            remaining = deadline_ts - time.time()
                            if remaining <= 0:
                                logging.warning(f"{worker_log_prefix} ⏱ Hết thời gian guard {GUARD_SECS}s. Auto-continue.")
                                self._handle_youtube_upload_completion(True, uploaded_video_id, "⏱ Quá 1h — auto-continue.", False)
                                return

                            per_try = min(remaining, 30)
                            try:
                                WebDriverWait(driver, per_try).until(
                                    EC.invisibility_of_element_located(YOUTUBE_LOCATORS["uploading_popup"])
                                )
                                logging.info(f"{worker_log_prefix} ✅ Popup 'Tải lên' đã biến mất. Upload thành công!")
                                self._handle_youtube_upload_completion(True, uploaded_video_id, None, False)
                                return
                            except TimeoutException:
                                continue

                    except TimeoutException:
                        # 2) Không thấy popup trong 7s → video ngắn/redirect nhanh → coi như OK
                        logging.info(f"{worker_log_prefix} ✅ Không thấy popup 'Tải lên' sau 7s. Giả định upload đã hoàn tất.")
                        self._handle_youtube_upload_completion(True, uploaded_video_id, None, False)
                        return

                except (StaleElementReferenceException, NoSuchWindowException, WebDriverException) as e:
                    logging.info(f"{worker_log_prefix} ✅ UI đổi/đóng trong khi chờ ({type(e).__name__}). Giả định đã hoàn tất.")
                    self._handle_youtube_upload_completion(True, uploaded_video_id, None, False)
                    return        

                # Thêm một khoảng nghỉ ngắn để đảm bảo mọi thứ ổn định trước khi đóng trình duyệt
                logging.info(f"{worker_log_prefix} Tạm dừng 2 giây trước khi đóng trình duyệt.")
                time.sleep(2)        

            except InterruptedError as ie:
                logging.warning(f"{worker_log_prefix} Tác vụ bị dừng: {ie}")
                self._handle_youtube_upload_completion(False, uploaded_video_id, f"Đã dừng bởi người dùng: {ie}", False)
            except Exception as e_upload_browser:
                # Bắt tất cả các lỗi khác, bao gồm cả TimeoutException nếu CẢ HAI điều kiện đều không xảy ra.
                error_msg_final = f"Lỗi không xác định khi upload qua trình duyệt: {type(e_upload_browser).__name__} - {e_upload_browser}"
                logging.critical(f"{worker_log_prefix} {error_msg_final}", exc_info=True)
                try:
                    if driver:
                        screenshot_path = os.path.join(config_directory, f"error_screenshot_{int(time.time())}.png")
                        driver.save_screenshot(screenshot_path)
                        error_msg_final += f"\n\nẢnh chụp màn hình lỗi đã được lưu tại:\n{screenshot_path}"
                except Exception as e_ss:
                    logging.error(f"{worker_log_prefix} Không thể chụp ảnh màn hình lỗi: {e_ss}")
                self._handle_youtube_upload_completion(False, uploaded_video_id, error_msg_final, False)

            finally:
                if driver:
                    try:
                        import threading  # chỉ threading, KHÔNG import os ở đây
                        quit_err = {"e": None}
                        def _q():
                            try:
                                driver.quit()
                            except Exception as _e:
                                quit_err["e"] = _e
                        t = threading.Thread(target=_q, daemon=True)
                        t.start()
                        t.join(8)  # chờ tối đa 8s

                        if t.is_alive():
                            logging.warning(f"{worker_log_prefix} driver.quit() quá 8s -> kill chromedriver.")
                            try:
                                if service and hasattr(service, "process") and service.process:
                                    service.process.kill()
                            except Exception as kill_e:
                                logging.warning(f"{worker_log_prefix} Không thể kill service process: {kill_e}")
                    except Exception as e_quit:
                        logging.error(f"{worker_log_prefix} Lỗi khi đóng trình duyệt: {e_quit}")