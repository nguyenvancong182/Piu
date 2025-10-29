# -*- coding: utf-8 -*-
# File: ui/tabs/subtitle_tab.py

import customtkinter as ctk
import os
import logging
from tkinter import filedialog, messagebox

# Import các thành phần UI chung
from config.ui_constants import get_theme_colors
from ui.widgets.tooltip import Tooltip
from ui.widgets.menu_utils import textbox_right_click_menu

# Import các hàm tiện ích
from utils.helpers import open_file_with_default_app
from config.constants import APP_NAME

# Import optional libraries và constants
try:
    from google.cloud import translate_v2 as google_translate
    from google.oauth2 import service_account
    HAS_GOOGLE_CLOUD_TRANSLATE = True
except ImportError:
    HAS_GOOGLE_CLOUD_TRANSLATE = False
    google_translate = None
    service_account = None

try:
    from openai import OpenAI, RateLimitError, AuthenticationError, APIConnectionError, APIStatusError, APITimeoutError
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    OpenAI = None

try:
    from underthesea import sent_tokenize
    HAS_UNDERTHESEA = True
except ImportError:
    HAS_UNDERTHESEA = False
    sent_tokenize = None


class SubtitleTab(ctk.CTkFrame):
    """
    Lớp quản lý toàn bộ giao diện và logic cho Tab Tạo Phụ Đề (Subtitle).
    """

    def __init__(self, master, master_app):
        """
        Khởi tạo frame cho Tab Tạo Phụ Đề.

        Args:
            master (ctk.CTkFrame): Frame cha (main_content_frame từ SubtitleApp).
            master_app (SubtitleApp): Instance của ứng dụng chính (PiuApp).
        """
        super().__init__(master, fg_color="transparent")
        self.master_app = master_app
        self.logger = logging.getLogger(APP_NAME)

        # Khai báo các widget con của tab này (sẽ được gán trong _build_ui)
        # Để tránh AttributeError, khai báo None cho các widget chính
        self.output_display_label = None
        self.choose_output_dir_button = None
        self.branding_settings_button_sub_tab = None
        self.cuda_status_label = None
        self.subtitle_style_settings_button = None
        self.bilingual_checkbox = None
        self.engine_menu = None
        self.target_lang_frame = None
        self.target_lang_menu = None
        self.api_settings_button_translate_tab = None
        self.openai_style_frame = None
        self.openai_style_label = None
        self.openai_style_menu = None
        self.merge_and_pause_frame_ref = None
        self.merge_sub_segmented_button_ref = None
        self.manual_merge_mode_checkbox = None
        self.auto_add_manual_task_checkbox = None
        self.save_in_media_folder_checkbox = None
        self.optimize_whisper_tts_voice_checkbox = None
        self.auto_format_srt_frame = None
        self.chk_auto_format_srt = None
        self.sub_pause_media_options_frame = None
        self.sub_pause_select_folder_button = None
        self.sub_pause_select_media_button = None
        self.sub_pause_selected_media_info_label = None
        self.pause_edit_checkbox = None
        self.continue_merge_button = None
        self.enable_split_checkbox_ref = None
        self.max_chars_entry_ref = None
        self.max_lines_entry_ref = None
        self.split_mode_menu = None
        self.sub_cps_entry = None
        self.enable_block_merging_checkbox = None
        self.merge_time_gap_entry = None
        self.merge_max_len_entry = None
        self.right_panel_sub = None
        self.manual_queue_section = None
        self.queue_section = None
        self.sub_edit_frame = None
        self.ai_edit_button_sub_tab = None
        self.dalle_button_sub_tab = None
        self.imagen_button_sub_tab = None
        self.open_sub_button_ref = None
        self.edit_sub_button_ref = None
        self.save_sub_button_ref = None
        self.sub_clear_content_button = None
        self.subtitle_textbox = None
        self.sub_and_dub_button = None
        self.add_manual_task_button = None
        self.add_button = None
        self.sub_button = None
        self.stop_button = None
        self.open_sub_output_folder_button = None

        # Gọi hàm xây dựng UI
        self._build_ui()

        self.logger.info("SubtitleTab đã được khởi tạo.")

    def _build_ui(self):
        """
        Tạo các thành phần UI cho tab Tạo Phụ Đề.
        (Đây là hàm _create_subtitle_tab cũ, đã được di chuyển sang đây)
        """
        self.logger.debug("Đang tạo UI Chế độ xem Phụ đề (Theme-Aware)...")

        # --- Định nghĩa các màu sắc thích ứng theme ---
        colors = get_theme_colors()
        panel_bg_color = colors["panel_bg"]
        card_bg_color = colors["card_bg"]
        textbox_bg_color = colors["textbox_bg"]
        danger_button_color = colors["danger_button"]
        danger_button_hover_color = colors["danger_button_hover"]
        special_action_button_color = colors["special_action_button"]
        special_action_hover_color = colors["special_action_hover"]

        main_frame_sub = ctk.CTkFrame(self, fg_color="transparent")
        main_frame_sub.pack(fill="both", expand=True)

        main_frame_sub.grid_columnconfigure(0, weight=1, uniform="panelgroup")
        main_frame_sub.grid_columnconfigure(1, weight=2, uniform="panelgroup")
        main_frame_sub.grid_rowconfigure(0, weight=1)

        # --- KHUNG BÊN TRÁI - CONTAINER CỐ ĐỊNH CHIỀU RỘNG ---
        left_panel_container = ctk.CTkFrame(main_frame_sub, fg_color=panel_bg_color, corner_radius=12)
        left_panel_container.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        left_panel_container.pack_propagate(False)

        left_scrollable_content = ctk.CTkScrollableFrame(
            left_panel_container,
            fg_color="transparent"
        )
        left_scrollable_content.pack(expand=True, fill="both", padx=0, pady=0)

        # --- Cụm nút hành động chính ---
        self._create_subtitle_action_buttons_section(left_scrollable_content, danger_button_color, danger_button_hover_color)

        # --- KHUNG CHỨA THƯ MỤC OUTPUT ---
        self._create_subtitle_output_config_section(left_scrollable_content, card_bg_color)

        # --- Khung Cấu hình Whisper ---
        self._create_subtitle_whisper_config_section(left_scrollable_content, card_bg_color)

        # --- KHUNG DỊCH PHỤ ĐỀ ---
        self._create_subtitle_translation_config_section(left_scrollable_content, card_bg_color, special_action_button_color, special_action_hover_color)

        # --- KHUNG GỘP SUB & TÙY CHỌN ---
        self._create_subtitle_merge_options_section(left_scrollable_content, card_bg_color)

        # --- KHUNG CHIA PHỤ ĐỀ ---
        self._create_subtitle_split_config_section(left_scrollable_content, card_bg_color)

        # --- KHUNG BÊN PHẢI (Hàng chờ & Trình chỉnh sửa Phụ đề) ---
        self._create_subtitle_right_panel(main_frame_sub, panel_bg_color, card_bg_color, textbox_bg_color, special_action_button_color, special_action_hover_color)

        # --- KHUNG MỚI: TÙY CHỈNH NHỊP ĐIỆU & TỐC ĐỘ ĐỌC (BỐ CỤC GRID - CÂN ĐỐI) ---
        self._create_subtitle_pacing_section(left_scrollable_content, card_bg_color)

        self.logger.debug("Tạo UI Chế độ xem Phụ đề hoàn tất (đã cập nhật màu sắc tương thích theme).")

    # ========================================================================
    # UI CREATION METHODS - Di chuyển từ Piu.py
    # ========================================================================

    def _create_subtitle_action_buttons_section(self, parent_frame, danger_button_color, danger_button_hover_color):
        """
        Create action buttons section for Subtitle tab.
        
        Args:
            parent_frame: Parent frame to add buttons to
            danger_button_color: Color tuple for danger button
            danger_button_hover_color: Hover color tuple for danger button
        """
        action_buttons_main_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        action_buttons_main_frame.pack(pady=10, padx=10, fill="x")

        btn_row_1_sub = ctk.CTkFrame(action_buttons_main_frame, fg_color="transparent")
        btn_row_1_sub.pack(fill="x", pady=(0, 5))

        self.sub_and_dub_button = ctk.CTkButton(
            btn_row_1_sub, text="🎤 Sub & Dub", height=35,
            font=("Segoe UI", 13, "bold"), command=self.master_app._handle_sub_and_dub_button_action
        )
        self.sub_and_dub_button.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.add_manual_task_button = ctk.CTkButton(
            btn_row_1_sub, text="➕ Thêm File (TC)", height=35,
            font=("Segoe UI", 13, "bold"), command=self.master_app._add_manual_sub_task_to_queue
        )
        # Không pack ngay, để _on_toggle_manual_merge_mode quản lý hiển thị
        
        self.add_button = ctk.CTkButton(btn_row_1_sub, text="➕ Thêm File (Sub)",
                                        height=35, font=("Segoe UI", 13, "bold"),
                                        command=self.master_app.add_files_to_queue)
        # Không pack ngay, để _on_toggle_manual_merge_mode quản lý hiển thị

        # Hàng 2: Bắt đầu SUB (chiếm cả hàng)
        self.sub_button = ctk.CTkButton(action_buttons_main_frame, text="🎬 Bắt đầu SUB",
                                        height=45, font=("Segoe UI", 15, "bold"),
                                        command=self.master_app._handle_start_sub_button_action
                                        )
        self.sub_button.pack(fill="x", pady=5)

        # Hàng 3: Chứa nút "Dừng Sub" (trái) và "Mở Thư Mục Sub" (phải)
        btn_row_3_controls = ctk.CTkFrame(action_buttons_main_frame, fg_color="transparent")
        btn_row_3_controls.pack(fill="x", pady=(5, 0))
        btn_row_3_controls.grid_columnconfigure((0, 1), weight=1)
        
        self.stop_button = ctk.CTkButton(
            btn_row_3_controls, text="🛑 Dừng Sub", height=35, font=("Segoe UI", 13, "bold"),
            command=self.master_app.stop_processing,
            fg_color=danger_button_color,
            hover_color=danger_button_hover_color,
            state=ctk.DISABLED, border_width=0
        )
        self.stop_button.grid(row=0, column=0, padx=(0, 2), pady=0, sticky="ew")

        self.open_sub_output_folder_button = ctk.CTkButton(
            btn_row_3_controls, text="📂 Mở Thư Mục Sub", height=35,
            font=("Segoe UI", 13, "bold"), command=self.open_subtitle_tab_output_folder,
            border_width=0
        )
        self.open_sub_output_folder_button.grid(row=0, column=1, padx=(3, 0), pady=0, sticky="ew")

    def _create_subtitle_output_config_section(self, parent_frame, card_bg_color):
        """
        Create output configuration section for Subtitle tab.
        
        Args:
            parent_frame: Parent frame to add section to
            card_bg_color: Background color tuple for the card frame
        """
        out_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        out_frame.pack(fill="x", padx=10, pady=(2, 2))

        ctk.CTkLabel(out_frame, text="📁 Thư mục lưu Sub/Video Gộp:", font=("Poppins", 13)).pack(anchor="w", padx=10, pady=(5,2))
        
        self.output_display_label = ctk.CTkLabel(out_frame, textvariable=self.master_app.output_path_var, anchor="w", wraplength=300, font=("Segoe UI", 10), text_color=("gray30", "gray70"))
        self.output_display_label.pack(fill="x", padx=10, pady=(0, 3))
        
        buttons_container_frame = ctk.CTkFrame(out_frame, fg_color="transparent")
        buttons_container_frame.pack(fill="x", padx=10, pady=(5,10))
        buttons_container_frame.grid_columnconfigure((0, 1), weight=1)

        self.choose_output_dir_button = ctk.CTkButton(
            buttons_container_frame, text="Chọn Output", height=35,
            font=("Poppins", 12), command=self.choose_output_dir
        )
        self.choose_output_dir_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.branding_settings_button_sub_tab = ctk.CTkButton(
            buttons_container_frame, text="🖼 Logo/Intro", height=35,
            font=("Poppins", 12), command=self.master_app.open_branding_settings_window
        )
        self.branding_settings_button_sub_tab.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        if hasattr(self.master_app, 'output_path_var') and hasattr(self, 'output_display_label'):
            self.master_app.output_path_var.trace_add("write", lambda *a: self.output_display_label.configure(text=self.master_app.output_path_var.get() or "Chưa chọn"))
            self.output_display_label.configure(text=self.master_app.output_path_var.get() or "Chưa chọn")

    def _create_subtitle_whisper_config_section(self, parent_frame, card_bg_color):
        """
        Create Whisper configuration section for Subtitle tab.
        
        Args:
            parent_frame: Parent frame to add section to
            card_bg_color: Background color tuple for the card frame
        """
        whisper_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        whisper_config_frame.pack(fill="x", padx=10, pady=2)
        
        title_cuda_frame = ctk.CTkFrame(whisper_config_frame, fg_color="transparent")
        title_cuda_frame.pack(fill="x", padx=10, pady=(5, 5))
        title_cuda_frame.grid_columnconfigure(0, weight=0); title_cuda_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(title_cuda_frame, text="⚙️ Whisper", font=("Poppins", 13, "bold")).grid(row=0, column=0, sticky="w")
        if not hasattr(self, 'cuda_status_label') or self.cuda_status_label is None:
             self.cuda_status_label = ctk.CTkLabel(title_cuda_frame, text="CUDA: Đang kiểm tra...", font=("Poppins", 11), text_color="gray")
        elif self.cuda_status_label.master != title_cuda_frame: 
            self.cuda_status_label.master = title_cuda_frame
        self.cuda_status_label.grid(row=0, column=1, sticky="e", padx=(0, 5))
        
        whisper_options_grid = ctk.CTkFrame(whisper_config_frame, fg_color="transparent")
        whisper_options_grid.pack(fill="x", padx=10, pady=(0, 10))
        whisper_options_grid.grid_columnconfigure(1, weight=1); whisper_options_grid.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(whisper_options_grid, text="Model:", font=("Poppins", 12), anchor='w').grid(row=0, column=0, padx=(0,5), pady=(0,5), sticky="w")
        model_menu = ctk.CTkOptionMenu(whisper_options_grid, variable=self.master_app.model_var, values=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"])
        model_menu.grid(row=0, column=1, columnspan=3, padx=(0,0), pady=(0,5), sticky="ew")
        
        ctk.CTkLabel(whisper_options_grid, text="Ngôn ngữ:", font=("Poppins", 12), anchor='w').grid(row=1, column=0, padx=(0,5), pady=(5,0), sticky="w")
        lang_menu = ctk.CTkOptionMenu(whisper_options_grid, variable=self.master_app.source_lang_var, values=["auto", "en", "vi", "ja", "zh", "ko", "fr", "de", "es", "it", "th", "ru", "pt", "hi"])
        lang_menu.grid(row=1, column=1, padx=(0,10), pady=(5,0), sticky="ew")
        
        ctk.CTkLabel(whisper_options_grid, text="Định dạng:", font=("Poppins", 12), anchor='w').grid(row=1, column=2, padx=(5,5), pady=(5,0), sticky="w")
        format_menu = ctk.CTkOptionMenu(whisper_options_grid, variable=self.master_app.format_var, values=["srt", "vtt", "txt"])
        format_menu.grid(row=1, column=3, padx=(0,0), pady=(5,0), sticky="ew")

        style_button_frame_sub_tab = ctk.CTkFrame(whisper_config_frame, fg_color="transparent")
        style_button_frame_sub_tab.pack(fill="x", padx=10, pady=(10, 10))
        self.subtitle_style_settings_button = ctk.CTkButton(
            style_button_frame_sub_tab, text="🎨 Tùy chỉnh Kiểu Phụ đề (Hardsub)...",
            height=35, font=("Poppins", 12), command=self.master_app.open_subtitle_style_settings_window
        )
        self.subtitle_style_settings_button.pack(fill="x", expand=True)

    def _create_subtitle_translation_config_section(self, parent_frame, card_bg_color, special_action_button_color, special_action_hover_color):
        """
        Create translation configuration section for Subtitle tab.
        
        Args:
            parent_frame: Parent frame to add section to
            card_bg_color: Background color tuple
            special_action_button_color: Color for special buttons
            special_action_hover_color: Hover color for special buttons
        """
        translate_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        translate_frame.pack(fill="x", padx=10, pady=(0, 2))
        
        header_translate_frame = ctk.CTkFrame(translate_frame, fg_color="transparent")
        header_translate_frame.pack(fill="x", padx=10, pady=(5, 5))
        header_translate_frame.grid_columnconfigure(0, weight=1); header_translate_frame.grid_columnconfigure(1, weight=0)
        
        ctk.CTkLabel(header_translate_frame, text="🌐 Dịch Phụ Đề", font=("Poppins", 13, "bold"), anchor="w").grid(row=0, column=0, sticky="w")
        self.bilingual_checkbox = ctk.CTkCheckBox(header_translate_frame, text="Tạo phụ đề song ngữ", variable=self.master_app.bilingual_var, checkbox_height=20, checkbox_width=20, font=("Poppins", 12))
        self.bilingual_checkbox.grid(row=0, column=1, sticky="e", padx=(5, 0))
        
        engine_frame = ctk.CTkFrame(translate_frame, fg_color="transparent")
        engine_frame.pack(fill="x", padx=10, pady=(0, 5))
        engine_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(engine_frame, text="Dịch bằng:", font=("Poppins", 12), anchor='w').grid(row=0, column=0, padx=(0,5), sticky="w")
        
        engine_options = ["Không dịch"]
        if HAS_GOOGLE_CLOUD_TRANSLATE: engine_options.append("Google Cloud API (Paid)")
        if HAS_OPENAI: engine_options.append("ChatGPT API (Paid)")
        if self.master_app.translation_engine_var.get() not in engine_options: 
            self.master_app.translation_engine_var.set("Không dịch")
        
        self.engine_menu = ctk.CTkOptionMenu(engine_frame, variable=self.master_app.translation_engine_var, values=engine_options, command=self.master_app.on_engine_change)
        self.engine_menu.grid(row=0, column=1, sticky="ew")
        
        self.target_lang_frame = ctk.CTkFrame(translate_frame, fg_color="transparent")
        self.target_lang_frame.pack(fill="x", padx=10, pady=0)
        self.target_lang_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.target_lang_frame, text="Dịch sang:", font=("Poppins", 12), anchor='w').grid(row=0, column=0, padx=(0,5), pady=(5,5), sticky="w")
        self.target_lang_menu = ctk.CTkOptionMenu(self.target_lang_frame, variable=self.master_app.target_lang_var, values=["vi", "en", "ja", "zh-cn", "fr", "ko", "de", "es"])
        self.target_lang_menu.grid(row=0, column=1, padx=(0,10), pady=(5,5), sticky="ew")
        
        api_button_height = self.engine_menu.cget("height")
        self.api_settings_button_translate_tab = ctk.CTkButton(self.target_lang_frame, text="🔑 API Keys...", font=("Poppins", 11), height=api_button_height, width=120, command=self.master_app.open_api_settings_window, fg_color=special_action_button_color, hover_color=special_action_hover_color)
        self.api_settings_button_translate_tab.grid(row=0, column=2, padx=(0,0), pady=(5,5), sticky="e")
        
        self.openai_style_frame = ctk.CTkFrame(translate_frame, fg_color="transparent")
        self.openai_style_frame.grid_columnconfigure(1, weight=1)
        self.openai_style_label = ctk.CTkLabel(self.openai_style_frame, text="Phong cách (GPT):", font=("Poppins", 12), anchor='w')
        self.openai_style_label.grid(row=0, column=0, padx=(0,5), pady=(5,5), sticky="w")
        self.openai_style_menu = ctk.CTkOptionMenu(self.openai_style_frame, variable=self.master_app.openai_translation_style_var, values=self.master_app.OPENAI_TRANSLATION_STYLES)
        self.openai_style_menu.grid(row=0, column=1, columnspan=2, padx=0, pady=(5,5), sticky="ew")

    def _create_subtitle_merge_options_section(self, parent_frame, card_bg_color):
        """
        Create merge options section for Subtitle tab.
        
        Args:
            parent_frame: Parent frame to add section to
            card_bg_color: Background color tuple
        """
        self.merge_and_pause_frame_ref = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        self.merge_and_pause_frame_ref.pack(fill="x", padx=10, pady=(0, 2))

        ctk.CTkLabel(self.merge_and_pause_frame_ref, text="🎬 Gộp Sub & Tùy chọn", font=("Poppins", 13, "bold")).pack(pady=(5,5), padx=10, anchor="w")
        self.merge_sub_segmented_button_ref = ctk.CTkSegmentedButton(self.merge_and_pause_frame_ref, values=["Không gộp", "Hard-sub", "Soft-sub"], variable=self.master_app.merge_sub_var, font=("Poppins", 12), corner_radius=8)
        self.merge_sub_segmented_button_ref.pack(fill="x", padx=10, pady=(0, 10))
        
        self.manual_merge_mode_checkbox = ctk.CTkCheckBox(self.merge_and_pause_frame_ref, text="🛠 Ghép Sub Thủ Công (Bỏ qua Whisper)", variable=self.master_app.manual_merge_mode_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20)
        self.manual_merge_mode_checkbox.pack(anchor="w", padx=10, pady=(2, 2))
        self.auto_add_manual_task_checkbox = ctk.CTkCheckBox(self.merge_and_pause_frame_ref, text="🔄 Tự động thêm vào hàng chờ (TC)", variable=self.master_app.auto_add_manual_sub_task_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20)
        self.auto_add_manual_task_checkbox.pack(anchor="w", padx=10, pady=(2, 2))
        
        self.save_in_media_folder_checkbox = ctk.CTkCheckBox(
            self.merge_and_pause_frame_ref,
            text="Lưu vào thư mục của media (TC)",
            variable=self.master_app.save_in_media_folder_var,
            font=("Poppins", 12),
            checkbox_height=20,
            checkbox_width=20
        )
        self.save_in_media_folder_checkbox.pack(anchor="w", padx=10, pady=(2, 2))
        self.optimize_whisper_tts_voice_checkbox = ctk.CTkCheckBox(self.merge_and_pause_frame_ref, text="🎤 Tối ưu giọng đọc Whisper", variable=self.master_app.optimize_whisper_tts_voice_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20, command=self.master_app._on_toggle_optimize_whisper_tts_voice)
        self.optimize_whisper_tts_voice_checkbox.pack(anchor="w", padx=10, pady=(2, 2))
        self.auto_format_srt_frame = ctk.CTkFrame(self.merge_and_pause_frame_ref, fg_color="transparent")
        self.auto_format_srt_frame.pack(fill="x", padx=10, pady=(0, 2))
        self.chk_auto_format_srt = ctk.CTkCheckBox(self.auto_format_srt_frame, text="🔄 Tự động định dạng Text sang SRT", variable=self.master_app.auto_format_plain_text_to_srt_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20)
        self.chk_auto_format_srt.pack(anchor="w", padx=0, pady=0)
                
        self.sub_pause_media_options_frame = ctk.CTkFrame(self.merge_and_pause_frame_ref, fg_color="transparent")
        self.sub_pause_media_options_frame.grid_columnconfigure((0, 1), weight=1)

        self.sub_pause_select_folder_button = ctk.CTkButton(self.sub_pause_media_options_frame, text="🖼 Thư mục Ảnh...", font=("Poppins", 12), height=30, command=self.master_app._sub_pause_handle_select_folder)
        self.sub_pause_select_folder_button.grid(row=0, column=0, padx=(0, 5), pady=2, sticky="ew")

        self.sub_pause_select_media_button = ctk.CTkButton(self.sub_pause_media_options_frame, text="🎬 Chọn Video/Ảnh...", font=("Poppins", 12), height=30, command=self.master_app._sub_pause_handle_select_media)
        self.sub_pause_select_media_button.grid(row=0, column=1, padx=(5, 0), pady=2, sticky="ew")

        self.sub_pause_selected_media_info_label = ctk.CTkLabel(self.sub_pause_media_options_frame, text="", font=("Segoe UI", 10), text_color="gray", wraplength=300)
        self.sub_pause_selected_media_info_label.grid(row=1, column=0, columnspan=2, padx=0, pady=(2, 5), sticky="ew")
        
        self.pause_edit_checkbox = ctk.CTkCheckBox(self.merge_and_pause_frame_ref, text="🔨 Dừng lại để chỉnh sửa Sub trước khi Gộp", variable=self.master_app.pause_for_edit_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20)
        self.pause_edit_checkbox.pack(anchor="w", padx=10, pady=(2, 2)) 
        self.continue_merge_button = ctk.CTkButton(self.merge_and_pause_frame_ref, text="▶ Tiếp tục Gộp Sub", height=35, font=("Poppins", 13, "bold"), command=self.master_app.resume_paused_task, state=ctk.DISABLED, fg_color="teal", hover_color="darkcyan")
        self.continue_merge_button.pack(fill="x", padx=10, pady=(2, 2))

    def _create_subtitle_split_config_section(self, parent_frame, card_bg_color):
        """
        Create split configuration section for Subtitle tab.
        
        Args:
            parent_frame: Parent frame to add section to
            card_bg_color: Background color tuple
        """
        split_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        split_frame.pack(fill="x", padx=10, pady=(0, 10))
        split_row = ctk.CTkFrame(split_frame, fg_color="transparent")
        split_row.pack(fill="x", padx=10, pady=(5, 10))
        self.enable_split_checkbox_ref = ctk.CTkCheckBox(split_row, text="Chia dòng:", variable=self.master_app.enable_split_var, checkbox_height=20, checkbox_width=20, font=("Poppins", 12))
        self.enable_split_checkbox_ref.grid(row=0, column=0, sticky="w", padx=(0, 10))
        ctk.CTkLabel(split_row, text="Ký tự:", font=("Poppins", 11)).grid(row=0, column=1)
        self.max_chars_entry_ref = ctk.CTkEntry(split_row, textvariable=self.master_app.max_chars_var, width=40)
        self.max_chars_entry_ref.grid(row=0, column=2, padx=(2, 8))
        ctk.CTkLabel(split_row, text="Số dòng:", font=("Poppins", 11)).grid(row=0, column=3)
        self.max_lines_entry_ref = ctk.CTkEntry(split_row, textvariable=self.master_app.max_lines_var, width=40)
        self.max_lines_entry_ref.grid(row=0, column=4, padx=(2, 0))
        split_mode_frame = ctk.CTkFrame(split_frame, fg_color="transparent")
        split_mode_frame.pack(fill="x", padx=10, pady=(0, 10))
        split_mode_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(split_mode_frame, text="Cách chia:", font=("Poppins", 11)).grid(row=0, column=0, padx=(0, 10), sticky="w")
        split_mode_options = ["sentence", "char"]
        if HAS_UNDERTHESEA: split_mode_options.insert(0, "underthesea (Tiếng Việt)")
        self.split_mode_menu = ctk.CTkOptionMenu(split_mode_frame, variable=self.master_app.split_mode_var, values=split_mode_options)
        self.split_mode_menu.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(split_mode_frame, text="Ký tự/giây (Timing):", font=("Poppins", 11)).grid(row=1, column=0, padx=(0, 10), pady=(5,0), sticky="w")
        self.sub_cps_entry = ctk.CTkEntry(split_mode_frame, textvariable=self.master_app.sub_cps_for_timing_var, width=80)
        self.sub_cps_entry.grid(row=1, column=1, pady=(5,0), sticky="w")
        block_merge_options_frame = ctk.CTkFrame(split_frame, fg_color="transparent")
        block_merge_options_frame.pack(fill="x", padx=10, pady=(5, 5))
        block_merge_options_frame.grid_columnconfigure(1, weight=1, minsize=50)
        block_merge_options_frame.grid_columnconfigure(3, weight=1, minsize=50)
        self.enable_block_merging_checkbox = ctk.CTkCheckBox(block_merge_options_frame, text="Bật gộp khối tự động", variable=self.master_app.enable_block_merging_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20, command=self.master_app._toggle_block_merge_options_state)
        self.enable_block_merging_checkbox.grid(row=0, column=0, columnspan=4, sticky="w", padx=0, pady=(0, 5))
        ctk.CTkLabel(block_merge_options_frame, text="TG nghỉ (ms):", font=("Poppins", 10)).grid(row=1, column=0, sticky="w", padx=(0,2), pady=(0,5))
        self.merge_time_gap_entry = ctk.CTkEntry(block_merge_options_frame, textvariable=self.master_app.merge_max_time_gap_var, width=50)
        self.merge_time_gap_entry.grid(row=1, column=1, sticky="ew", padx=(0,5), pady=(0,5))
        ctk.CTkLabel(block_merge_options_frame, text="Độ dài khối max (ký tự):", font=("Poppins", 10)).grid(row=1, column=2, sticky="w", padx=(5,2), pady=(0,5))
        self.merge_max_len_entry = ctk.CTkEntry(block_merge_options_frame, textvariable=self.master_app.merge_curr_max_len_normal_var, width=50)
        self.merge_max_len_entry.grid(row=1, column=3, sticky="ew", padx=(0,0), pady=(0,5))

    def _create_subtitle_right_panel(self, main_frame, panel_bg_color, card_bg_color, textbox_bg_color, special_action_button_color, special_action_hover_color):
        """
        Create right panel for Subtitle tab (queue and editor).
        
        Args:
            main_frame: Main frame containing the panel
            panel_bg_color: Background color for panel
            card_bg_color: Background color for card
            textbox_bg_color: Background color for textbox
            special_action_button_color: Color for special buttons
            special_action_hover_color: Hover color for special buttons
        """
        self.right_panel_sub = ctk.CTkFrame(main_frame, fg_color=panel_bg_color, corner_radius=12)
        self.right_panel_sub.grid(row=0, column=1, pady=0, sticky="nsew")

        self.manual_queue_section = ctk.CTkScrollableFrame(self.right_panel_sub, label_text="📋 Hàng chờ Ghép Thủ Công", label_font=("Poppins", 14, "bold"), height=150)
        self.queue_section = ctk.CTkScrollableFrame(self.right_panel_sub, label_text="📋 Hàng chờ (Sub Tự động)", label_font=("Poppins", 14, "bold"), height=150)
        # Không pack ngay ở đây, để _on_toggle_manual_merge_mode quản lý việc hiển thị

        self.sub_edit_frame = ctk.CTkFrame(self.right_panel_sub, fg_color="transparent")
        self.sub_edit_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.sub_edit_frame.grid_rowconfigure(1, weight=1)
        self.sub_edit_frame.grid_columnconfigure(0, weight=1)

        sub_header = ctk.CTkFrame(self.sub_edit_frame, fg_color="transparent")
        sub_header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(sub_header, text="📝 Nội dung phụ đề:", font=("Poppins", 15, "bold")).pack(side="left", padx=(0,10))

        buttons_container_sub_tab = ctk.CTkFrame(sub_header, fg_color=card_bg_color, corner_radius=6) 
        buttons_container_sub_tab.pack(side="right", fill="x", expand=True, padx=(5,0))

        num_sub_header_buttons = 7
        for i in range(num_sub_header_buttons):
            buttons_container_sub_tab.grid_columnconfigure(i, weight=1)

        button_height_sub = 28
        button_font_style_sub = ("Poppins", 11)

        self.ai_edit_button_sub_tab = ctk.CTkButton(
            buttons_container_sub_tab, text="✨ Biên tập (AI)", height=button_height_sub, font=button_font_style_sub,
            command=lambda: self.master_app._show_ai_script_editing_popup(self.subtitle_textbox, "subtitle"),
            fg_color=special_action_button_color, hover_color=special_action_hover_color
        )
        self.ai_edit_button_sub_tab.grid(row=0, column=0, padx=2, pady=2, sticky="ew")

        self.dalle_button_sub_tab = ctk.CTkButton(
            buttons_container_sub_tab, text="🎨 Tạo Ảnh AI", height=button_height_sub, font=button_font_style_sub,
            command=self.master_app._show_dalle_image_generation_popup,
            fg_color=special_action_button_color, hover_color=special_action_hover_color
        )
        self.dalle_button_sub_tab.grid(row=0, column=1, padx=2, pady=2, sticky="ew")

        self.imagen_button_sub_tab = ctk.CTkButton(
            buttons_container_sub_tab, text="🖼 Ảnh(Imagen)", height=button_height_sub, font=button_font_style_sub,
            command=self.master_app.open_imagen_settings_window,
            fg_color=special_action_button_color, hover_color=special_action_hover_color
        )
        self.imagen_button_sub_tab.grid(row=0, column=2, padx=2, pady=2, sticky="ew")

        self.open_sub_button_ref = ctk.CTkButton(buttons_container_sub_tab, text="📂 Mở Sub...", height=button_height_sub, font=button_font_style_sub, command=self.master_app.load_old_sub_file)
        self.open_sub_button_ref.grid(row=0, column=3, padx=2, pady=2, sticky="ew")

        self.edit_sub_button_ref = ctk.CTkButton(buttons_container_sub_tab, text="📝 Sửa Sub", height=button_height_sub, font=button_font_style_sub, command=self.master_app.enable_sub_editing)
        self.edit_sub_button_ref.grid(row=0, column=4, padx=2, pady=2, sticky="ew")

        self.save_sub_button_ref = ctk.CTkButton(buttons_container_sub_tab, text="💾 Lưu Sub", height=button_height_sub, font=button_font_style_sub, command=self.master_app.save_edited_sub)
        self.save_sub_button_ref.grid(row=0, column=5, padx=2, pady=2, sticky="ew")

        self.sub_clear_content_button = ctk.CTkButton(
            buttons_container_sub_tab, text="🗑 Xóa Nội dung", height=button_height_sub, font=button_font_style_sub, command=self.master_app.clear_subtitle_textbox_content
        )
        self.sub_clear_content_button.grid(row=0, column=6, padx=(2,0), pady=2, sticky="ew")

        self.subtitle_textbox = ctk.CTkTextbox(
            self.sub_edit_frame, font=("Segoe UI", 13), wrap="word", state="normal",
            fg_color=textbox_bg_color, border_width=1
        )
        self.subtitle_textbox.grid(row=1, column=0, sticky="nsew", padx=0, pady=(2,0))
        self.subtitle_textbox.bind("<Button-3>", textbox_right_click_menu)
        if hasattr(self.subtitle_textbox, 'bind'): 
            self.subtitle_textbox.bind("<<Paste>>", self.master_app.handle_paste_and_format_srt)
        
        self.subtitle_textbox.configure(state="normal")
        self.subtitle_textbox.insert("1.0", self.master_app.subtitle_textbox_placeholder) 
        
        self.after(150, lambda: self.master_app.on_engine_change(self.master_app.translation_engine_var.get()))
        self.after(150, lambda: self.master_app._toggle_block_merge_options_state())

    def _create_subtitle_pacing_section(self, parent_frame, card_bg_color):
        """
        Create pacing configuration section for Subtitle tab.
        
        Args:
            parent_frame: Parent frame to add section to
            card_bg_color: Background color tuple
        """
        pacing_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        pacing_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(pacing_frame, text="⏱ Nhịp điệu & Tốc độ Đọc (Nâng cao)", font=("Poppins", 13, "bold")).pack(pady=(5,5), padx=10, anchor="w")

        pacing_grid = ctk.CTkFrame(pacing_frame, fg_color="transparent")
        pacing_grid.pack(fill="x", padx=10, pady=(0, 10))
        
        pacing_grid.grid_columnconfigure(0, weight=0)
        pacing_grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(pacing_grid, text="Nghỉ sau dấu phẩy (ms):", font=("Poppins", 11)).grid(row=0, column=0, sticky="w", pady=2, padx=(0, 5))
        pause_medium_entry = ctk.CTkEntry(pacing_grid, textvariable=self.master_app.sub_pacing_pause_medium_ms_var)
        pause_medium_entry.grid(row=0, column=1, sticky="ew", pady=2)
        Tooltip(pause_medium_entry, "Thời gian nghỉ (mili giây) sau các dấu câu như , ; :")

        ctk.CTkLabel(pacing_grid, text="Nghỉ sau dấu chấm (ms):", font=("Poppins", 11)).grid(row=1, column=0, sticky="w", pady=2, padx=(0, 5))
        pause_period_entry = ctk.CTkEntry(pacing_grid, textvariable=self.master_app.sub_pacing_pause_period_ms_var)
        pause_period_entry.grid(row=1, column=1, sticky="ew", pady=2)
        Tooltip(pause_period_entry, "Thời gian nghỉ (mili giây) sau các dấu câu như . ...")

        ctk.CTkLabel(pacing_grid, text="Nghỉ sau dấu hỏi (ms):", font=("Poppins", 11)).grid(row=2, column=0, sticky="w", pady=2, padx=(0, 5))
        pause_question_entry = ctk.CTkEntry(pacing_grid, textvariable=self.master_app.sub_pacing_pause_question_ms_var)
        pause_question_entry.grid(row=2, column=1, sticky="ew", pady=2)
        Tooltip(pause_question_entry, "Thời gian nghỉ (mili giây) sau các dấu câu như ? !")

        ctk.CTkLabel(pacing_grid, text="Ngưỡng câu dài (ký tự):", font=("Poppins", 11)).grid(row=3, column=0, sticky="w", pady=2, padx=(0, 5))
        long_sentence_entry = ctk.CTkEntry(pacing_grid, textvariable=self.master_app.sub_pacing_long_sentence_threshold_var)
        long_sentence_entry.grid(row=3, column=1, sticky="ew", pady=2)
        Tooltip(long_sentence_entry, "Số ký tự để coi một câu là 'dài' và tăng tốc độ đọc.")

        ctk.CTkLabel(pacing_grid, text="Hệ số tăng tốc:", font=("Poppins", 11)).grid(row=4, column=0, sticky="w", pady=2, padx=(0, 5))
        fast_cps_multiplier_entry = ctk.CTkEntry(pacing_grid, textvariable=self.master_app.sub_pacing_fast_cps_multiplier_var)
        fast_cps_multiplier_entry.grid(row=4, column=1, sticky="ew", pady=2)
        Tooltip(fast_cps_multiplier_entry, "Hệ số nhân với tốc độ đọc (CPS) cho câu dài. Ví dụ: 1.1 = nhanh hơn 10%.")

    # ========================================================================
    # HELPER METHODS - Di chuyển từ Piu.py
    # ========================================================================

    def open_subtitle_tab_output_folder(self):
        """Mở thư mục output đã được cấu hình cho tab Tạo Phụ Đề."""
        self.logger.info("[UI SubTab] Yêu cầu mở thư mục output của tab Sub.")
        current_path = self.master_app.output_path_var.get()
        if current_path and os.path.isdir(current_path):
            open_file_with_default_app(current_path)
        elif current_path:
            messagebox.showwarning("Đường dẫn không hợp lệ", 
                                   f"Đường dẫn đã cấu hình không phải là một thư mục hợp lệ:\n{current_path}", 
                                   parent=self.master_app)
        else:
            messagebox.showwarning("Chưa chọn thư mục", 
                                   "Vui lòng chọn 'Thư mục lưu Sub/Video Gộp' trước.", 
                                   parent=self.master_app)

    def choose_output_dir(self):
        """ Mở hộp thoại để chọn thư mục output """
        path = filedialog.askdirectory(initialdir=self.master_app.output_path_var.get() or os.getcwd())
        if path:
            self.master_app.output_path_var.set(path) # Tự động lưu do trace

