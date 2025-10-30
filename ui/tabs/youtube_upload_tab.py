# -*- coding: utf-8 -*-
# File: ui/tabs/youtube_upload_tab.py

import customtkinter as ctk
import os
import logging

# Import các thành phần UI chung
from config.ui_constants import get_theme_colors
from ui.widgets.tooltip import Tooltip

# Import các hàm tiện ích
from utils.helpers import get_default_downloads_folder
from config.constants import APP_NAME, YOUTUBE_CATEGORIES


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

        # Thumbnail selection
        self._create_youtube_thumbnail_section(left_upload_scrollable_content, card_bg_color)

        # Video information section
        self._create_youtube_video_info_section(left_upload_scrollable_content, card_bg_color)

        # Upload method section
        self._create_youtube_upload_method_section(left_upload_scrollable_content, card_bg_color)

        # Right panel with queue, log, and progress
        self._create_youtube_right_panel(main_frame_upload, panel_bg_color, textbox_bg_color)
        
        self.logger.debug("[YouTubeUploadUI] Tạo UI cho tab Upload YouTube hoàn tất.")
        self.master_app.after(100, self.master_app._update_youtube_ui_state, False)

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
            command=self.master_app._select_youtube_video_file
        )
        self.youtube_select_video_button.grid(row=0, column=0, columnspan=2, pady=5, sticky="ew")

        self.youtube_start_upload_button = ctk.CTkButton(
            action_buttons_main_frame, text="📤 Bắt đầu Upload Hàng loạt", height=45, font=("Segoe UI", 15, "bold"),
            command=self.master_app._start_youtube_batch_upload 
        )
        self.youtube_start_upload_button.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        self.youtube_stop_upload_button = ctk.CTkButton(
            action_buttons_main_frame, text="🛑 Dừng Upload", height=35, font=("Segoe UI", 13, "bold"),
            command=self.master_app._stop_youtube_upload, fg_color=danger_button_color, hover_color=danger_button_hover_color,
            state=ctk.DISABLED, border_width=0
        )
        self.youtube_stop_upload_button.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="ew")
        
        self.youtube_add_to_queue_button = ctk.CTkButton(
            action_buttons_main_frame, text="➕ Thêm Hàng Chờ", height=35, font=("Segoe UI", 13, "bold"),
            command=self.master_app._add_youtube_task_to_queue
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
            variable=self.master_app.auto_upload_to_youtube_var,
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
        self.youtube_select_thumbnail_button = ctk.CTkButton(thumbnail_frame, text="Chọn Ảnh...", width=110, command=self.master_app._select_youtube_thumbnail)
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
        self.youtube_video_path_display_label = ctk.CTkLabel(video_info_frame, textvariable=self.master_app.youtube_video_path_var, wraplength=340, anchor="w", text_color=("gray30", "gray70"), font=("Segoe UI", 10))
        self.youtube_video_path_display_label.pack(fill="x", padx=10, pady=(0, 5))
        self.master_app.youtube_video_path_var.trace_add("write", lambda *a: self._update_youtube_path_label_display())
        
        # Title header with metadata checkboxes
        title_header_frame = ctk.CTkFrame(video_info_frame, fg_color="transparent")
        title_header_frame.pack(fill="x", padx=10, pady=(2,0))
        title_header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(title_header_frame, text="Tiêu đề:", anchor="w", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w")
        
        # Fetch metadata checkbox
        self.youtube_fetch_metadata_checkbox = ctk.CTkCheckBox(
            title_header_frame, text="Lấy metadata",
            variable=self.master_app.youtube_fetch_metadata_var, font=("Segoe UI", 11),
            checkbox_height=18, checkbox_width=18,
            command=lambda: self.master_app._on_metadata_checkbox_toggled('fetch')
        )
        self.youtube_fetch_metadata_checkbox.grid(row=0, column=1, padx=(0, 5), sticky="e")
        Tooltip(self.youtube_fetch_metadata_checkbox, "Khi chọn video, tự động điền thông tin từ file Master Metadata (nếu có)")
        
        # Autofill checkbox
        self.youtube_autofill_checkbox = ctk.CTkCheckBox(
            title_header_frame, text="Lấy theo tên file",
            variable=self.master_app.youtube_autofill_var, font=("Segoe UI", 11),
            checkbox_height=18, checkbox_width=18,
            command=lambda: self.master_app._on_metadata_checkbox_toggled('autofill')
        )
        self.youtube_autofill_checkbox.grid(row=0, column=2, sticky="e")
        Tooltip(self.youtube_autofill_checkbox, "Khi chọn video, tự động điền Tiêu đề bằng tên file video")
        
        self.youtube_title_entry = ctk.CTkEntry(video_info_frame, textvariable=self.master_app.youtube_title_var, font=("Segoe UI", 12))
        self.youtube_title_entry.pack(fill="x", padx=10, pady=(0,5))
        
        ctk.CTkLabel(video_info_frame, text="Mô tả:", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        self.youtube_description_textbox = ctk.CTkTextbox(video_info_frame, height=80, wrap="word", font=("Segoe UI", 12))
        self.youtube_description_textbox.pack(fill="x", padx=10, pady=(0,5))
        saved_description = self.master_app.cfg.get("youtube_last_description", "")
        if saved_description:
            self.youtube_description_textbox.insert("1.0", saved_description)
            
        ctk.CTkLabel(video_info_frame, text="Thẻ tag (phân cách bởi dấu phẩy):", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        self.youtube_tags_entry = ctk.CTkEntry(video_info_frame, textvariable=self.master_app.youtube_tags_var, font=("Segoe UI", 12))
        self.youtube_tags_entry.pack(fill="x", padx=10, pady=(0,5))
        
        ctk.CTkLabel(video_info_frame, text="Danh sách phát (nhập chính xác tên):", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        self.youtube_playlist_entry = ctk.CTkEntry(video_info_frame, textvariable=self.master_app.youtube_playlist_var, font=("Segoe UI", 12))
        self.youtube_playlist_entry.pack(fill="x", padx=10, pady=(0,5))
        
        ctk.CTkLabel(video_info_frame, text="Trạng thái riêng tư:", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        privacy_options = ["private", "unlisted", "public"]
        self.youtube_privacy_optionmenu = ctk.CTkOptionMenu(video_info_frame, variable=self.master_app.youtube_privacy_status_var, values=privacy_options)
        self.youtube_privacy_optionmenu.pack(fill="x", padx=10, pady=(0,10))

        ctk.CTkLabel(video_info_frame, text="Danh mục Video:", anchor="w", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=(2,0))
        # Get category name from ID
        self.youtube_category_display_var = ctk.StringVar(
            value=YOUTUBE_CATEGORIES.get(self.master_app.youtube_category_id_var.get(), "Giải trí")
        )
        # Function called when user selects a menu item
        def on_category_select(selected_display_name):
            # Find ID corresponding to selected name and update main variable
            for cat_id, cat_name in YOUTUBE_CATEGORIES.items():
                if cat_name == selected_display_name:
                    self.master_app.youtube_category_id_var.set(cat_id)
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
            variable=self.master_app.youtube_add_end_screen_var,
            font=("Segoe UI", 11),
            checkbox_height=18, checkbox_width=18,
            command=self.master_app.save_current_config
        )
        self.youtube_add_end_screen_checkbox.grid(row=0, column=0, sticky="w")
        Tooltip(self.youtube_add_end_screen_checkbox, "Tự động thêm Màn hình kết thúc bằng cách 'Nhập từ video gần nhất'.")

        self.youtube_add_cards_checkbox = ctk.CTkCheckBox(
            video_elements_frame,
            text="Thêm Thẻ video",
            variable=self.master_app.youtube_add_cards_var,
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
            upload_method_frame, text="API (Mặc định)", variable=self.master_app.youtube_upload_method_var, value="api",
            command=lambda: self.master_app._on_upload_method_changed(self.master_app.youtube_upload_method_var.get()), 
            font=("Segoe UI", 12)
        )
        self.upload_method_radio_api.pack(anchor="w", padx=10, pady=5)
        self.upload_method_radio_browser = ctk.CTkRadioButton(
            upload_method_frame, text="Trình duyệt (Chrome Portable)", variable=self.master_app.youtube_upload_method_var, value="browser",
            command=lambda: self.master_app._on_upload_method_changed(self.master_app.youtube_upload_method_var.get()), 
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
            variable=self.master_app.youtube_headless_var,
            font=("Segoe UI", 12)
        )
        self.headless_checkbox.pack(anchor="w")

        ctk.CTkLabel(self.chrome_portable_config_frame, text="Cấu hình Chrome Portable:", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=10, pady=(5,2))
        chrome_portable_path_frame = ctk.CTkFrame(self.chrome_portable_config_frame, fg_color="transparent")
        chrome_portable_path_frame.pack(fill="x", padx=10, pady=(5,0))
        chrome_portable_path_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(chrome_portable_path_frame, text="Đường dẫn Chrome.exe:", anchor="w", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w")
        self.chrome_portable_path_display_label = ctk.CTkLabel(chrome_portable_path_frame, textvariable=self.master_app.chrome_portable_path_var, wraplength=200, anchor="w", text_color=("gray30", "gray70"), font=("Segoe UI", 10))
        self.chrome_portable_path_display_label.grid(row=1, column=0, padx=(0,5), sticky="ew")
        chrome_portable_browse_button = ctk.CTkButton(chrome_portable_path_frame, text="Duyệt...", width=80, command=self.master_app._browse_chrome_portable_path)
        chrome_portable_browse_button.grid(row=1, column=1, sticky="e")
        
        chromedriver_path_frame = ctk.CTkFrame(self.chrome_portable_config_frame, fg_color="transparent")
        chromedriver_path_frame.pack(fill="x", padx=10, pady=(5,10))
        chromedriver_path_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(chromedriver_path_frame, text="Đường dẫn ChromeDriver.exe:", anchor="w", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w")
        self.chromedriver_path_display_label = ctk.CTkLabel(chromedriver_path_frame, textvariable=self.master_app.chromedriver_path_var, wraplength=200, anchor="w", text_color=("gray30", "gray70"), font=("Segoe UI", 10))
        self.chromedriver_path_display_label.grid(row=1, column=0, padx=(0,5), sticky="ew")
        chromedriver_browse_button = ctk.CTkButton(chromedriver_path_frame, text="Duyệt...", width=80, command=self.master_app._browse_chromedriver_path)
        chromedriver_browse_button.grid(row=1, column=1, sticky="e")
        self.master_app.after(100, self.master_app._on_upload_method_changed, self.master_app.youtube_upload_method_var.get())

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
        path = self.master_app.youtube_video_path_var.get()
        if hasattr(self, 'youtube_video_path_display_label') and self.youtube_video_path_display_label.winfo_exists():
            display_text = os.path.basename(path) if path else "(Chưa chọn video)"
            self.youtube_video_path_display_label.configure(text=display_text)

            # Nếu path có giá trị, tự động điền Tiêu đề mặc định (nếu Tiêu đề đang trống)
            if path and not self.master_app.youtube_title_var.get().strip():
                # Tiêu đề mặc định là tên file (bỏ đuôi mở rộng)
                default_title = os.path.splitext(os.path.basename(path))[0]
                self.master_app.youtube_title_var.set(default_title)
                self.logger.info(f"[YouTubeUI] Tự động điền tiêu đề: '{default_title}'")

            # Sau khi cập nhật, kiểm tra lại trạng thái các nút upload
            self.master_app._update_youtube_ui_state(self.master_app.is_uploading_youtube)

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

