# -*- coding: utf-8 -*-
# File: ui/tabs/subtitle_tab.py

import customtkinter as ctk
import os
import logging
import threading
import time
import re
import json
import uuid
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from contextlib import contextmanager

# Import các thành phần UI chung
from config.ui_constants import get_theme_colors
from ui.widgets.tooltip import Tooltip
from ui.widgets.menu_utils import textbox_right_click_menu

# Import các hàm tiện ích
from utils.helpers import (open_file_with_default_app, get_default_downloads_folder, 
                          safe_int, create_safe_filename, parse_color_string_to_tuple,
                          play_sound_async)
from utils.srt_utils import format_srt_data_to_string, extract_dialogue_from_srt_string
from utils.ffmpeg_utils import find_ffprobe
from config.constants import APP_NAME
from utils.keep_awake import KeepAwakeManager
from services.ffmpeg_service import run_ffmpeg_command as ffmpeg_run_command

# Import playsound và định nghĩa PLAYSOUND_AVAILABLE
try:
    from playsound import playsound
    PLAYSOUND_AVAILABLE = True
except ImportError:
    logging.warning("Thư viện 'playsound' chưa được cài đặt. Chức năng phát nhạc khi tải xong sẽ không hoạt động.")
    PLAYSOUND_AVAILABLE = False
    playsound = None

# Import pysubs2
try:
    import pysubs2
    HAS_PYSUBS2 = True
except ImportError:
    HAS_PYSUBS2 = False
    pysubs2 = None

# Helper để sử dụng keep_awake
@contextmanager
def keep_awake(reason: str = "Processing"):
    """Helper context manager cho keep_awake"""
    keeper = KeepAwakeManager()
    tk = keeper.acquire(reason)
    try:
        yield
    finally:
        keeper.release(tk)

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

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    whisper = None


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

        # ====================================================================
        # BIẾN STATE - Di chuyển từ Piu.py
        # ====================================================================
        
        # --- Biến Model & Queue ---
        self.whisper_model = None
        self.loaded_model_name = None
        self.is_loading_model = False
        self.is_loading_model_for_timer = False
        self.file_queue = []
        self.current_file = None
        self.current_srt_path = None
        self.manual_sub_queue = []  # Hàng chờ chính cho các tác vụ ghép thủ công
        self.last_loaded_script_path = None
        self.allow_edit_sub = True
        self.sub_pause_selected_media_path = None
        self.is_subbing = False
        self.is_gpt_processing_script = False
        self.is_gemini_processing = False
        
        # --- Biến Language & Options ---
        self.source_lang_var = ctk.StringVar(value=self.master_app.cfg.get("language", "auto"))
        self.merge_sub_var = ctk.StringVar(value=self.master_app.cfg.get("merge_mode", "Không gộp"))
        self.bilingual_var = ctk.BooleanVar(value=self.master_app.cfg.get("bilingual", False))
        self.target_lang_var = ctk.StringVar(value=self.master_app.cfg.get("target_lang", "vi"))
        self.enable_split_var = ctk.BooleanVar(value=self.master_app.cfg.get("split", True))
        self.max_chars_var = ctk.StringVar(value=str(self.master_app.cfg.get("max_chars", 90)))
        self.max_lines_var = ctk.StringVar(value=str(self.master_app.cfg.get("max_lines", 1)))
        self.sub_cps_for_timing_var = ctk.StringVar(value=str(self.master_app.cfg.get("sub_cps_for_timing", 17)))
        self.is_actively_paused_for_edit = False
        self.HAS_UNDERTHESEA_LIB = globals().get('HAS_UNDERTHESEA', False)
        
        # --- Biến Pacing (Advanced) ---
        self.sub_pacing_pause_medium_ms_var = ctk.StringVar(
            value=str(self.master_app.cfg.get("sub_pacing_pause_medium_ms", 150))
        )
        self.sub_pacing_pause_period_ms_var = ctk.StringVar(
            value=str(self.master_app.cfg.get("sub_pacing_pause_period_ms", 300))
        )
        self.sub_pacing_pause_question_ms_var = ctk.StringVar(
            value=str(self.master_app.cfg.get("sub_pacing_pause_question_ms", 450))
        )
        self.sub_pacing_long_sentence_threshold_var = ctk.StringVar(
            value=str(self.master_app.cfg.get("sub_pacing_long_sentence_threshold", 55))
        )
        self.sub_pacing_fast_cps_multiplier_var = ctk.StringVar(
            value=str(self.master_app.cfg.get("sub_pacing_fast_cps_multiplier", 1.1))
        )
        
        # --- Biến Style (Font, Color, Outline) ---
        self.sub_style_font_name_var = ctk.StringVar(value=self.master_app.cfg.get("sub_style_font_name", "Arial"))
        self.sub_style_font_size_var = ctk.IntVar(value=self.master_app.cfg.get("sub_style_font_size", 60))
        self.sub_style_font_bold_var = ctk.BooleanVar(value=self.master_app.cfg.get("sub_style_font_bold", True))
        self.sub_style_text_color_rgb_str_var = ctk.StringVar(value=self.master_app.cfg.get("sub_style_text_color_rgb_str", "255,255,255"))
        self.sub_style_text_opacity_percent_var = ctk.IntVar(value=self.master_app.cfg.get("sub_style_text_opacity_percent", 100))
        self.sub_style_background_mode_var = ctk.StringVar(value=self.master_app.cfg.get("sub_style_background_mode", "Đổ Bóng"))
        self.sub_style_bg_color_rgb_str_var = ctk.StringVar(value=self.master_app.cfg.get("sub_style_bg_color_rgb_str", "0,0,0"))
        self.sub_style_bg_box_actual_opacity_percent_var = ctk.IntVar(value=self.master_app.cfg.get("sub_style_bg_box_actual_opacity_percent", 75))
        self.sub_style_outline_enabled_var = ctk.BooleanVar(value=self.master_app.cfg.get("sub_style_outline_enabled", False))
        self.sub_style_outline_size_var = ctk.DoubleVar(value=self.master_app.cfg.get("sub_style_outline_size", 2.0))
        self.sub_style_outline_color_rgb_str_var = ctk.StringVar(value=self.master_app.cfg.get("sub_style_outline_color_rgb_str", "0,0,0"))
        self.sub_style_outline_opacity_percent_var = ctk.IntVar(value=self.master_app.cfg.get("sub_style_outline_opacity_percent", 100))
        self.sub_style_marginv_var = ctk.IntVar(value=self.master_app.cfg.get("margin_v", 60))
        
        # --- Biến FFmpeg cho Slideshow ---
        self.ffmpeg_encoder_var = ctk.StringVar(value=self.master_app.cfg.get("ffmpeg_encoder", "libx264"))
        self.ffmpeg_preset_var = ctk.StringVar(value=self.master_app.cfg.get("ffmpeg_preset", "veryfast"))
        self.ffmpeg_crf_var = ctk.StringVar(value=str(self.master_app.cfg.get("ffmpeg_crf", "23")))
        
        # --- Font Caching ---
        self.system_fonts_cache = []
        self.fonts_are_loading = False
        
        # --- Cấu hình Split Mode ---
        _initial_split_modes = ["sentence", "char"]
        if HAS_UNDERTHESEA:
            _initial_split_modes.append("underthesea (Tiếng Việt)")
        saved_split_mode_on_init = self.master_app.cfg.get("split_mode", _initial_split_modes[0])
        if saved_split_mode_on_init not in _initial_split_modes:
            self.logger.warning(f"Split mode đã lưu trong config '{saved_split_mode_on_init}' không khả dụng khi khởi tạo. Đặt lại về '{_initial_split_modes[0]}'.")
            self.split_mode_var = ctk.StringVar(value=_initial_split_modes[0])
        else:
            self.split_mode_var = ctk.StringVar(value=saved_split_mode_on_init)
        
        # --- Biến Block Merging ---
        self.enable_block_merging_var = ctk.BooleanVar(value=self.master_app.cfg.get("enable_block_merging", False))
        self.merge_max_time_gap_var = ctk.StringVar(value=str(self.master_app.cfg.get("merge_max_time_gap_ms", 369)))
        self.merge_curr_max_len_normal_var = ctk.StringVar(value=str(self.master_app.cfg.get("merge_curr_max_len", 36)))
        
        # --- Biến Pause for Edit ---
        self.pause_for_edit_var = ctk.BooleanVar(value=self.master_app.cfg.get("pause_for_edit", False))
        self.continue_merge_event = threading.Event()
        
        # --- Biến Manual Merge ---
        self.manual_merge_mode_var = ctk.BooleanVar(value=self.master_app.cfg.get("manual_merge_mode", False))
        self.manual_merge_mode_var.trace_add("write", lambda *args: self._on_toggle_manual_merge_mode())
        
        # --- Biến khác ---
        self.auto_format_plain_text_to_srt_var = ctk.BooleanVar(value=self.master_app.cfg.get("auto_format_plain_text_to_srt", False))
        self.auto_add_manual_sub_task_var = ctk.BooleanVar(value=self.master_app.cfg.get("auto_add_manual_sub_task", True))
        self.save_in_media_folder_var = ctk.BooleanVar(value=self.master_app.cfg.get("save_in_media_folder", False))
        self.optimize_whisper_tts_voice_var = ctk.BooleanVar(value=self.master_app.cfg.get("optimize_whisper_tts_voice", False))
        self.subtitle_textbox_placeholder = "[Nội dung phụ đề sẽ hiển thị ở đây sau khi được tạo hoặc tải.\nỞ chế độ 'Ghép Sub Thủ Công', bạn có thể '📂 Mở Sub...' hoặc '📝 Sửa Sub' để nhập/dán trực tiếp.]"
        self.min_duration_per_segment_ms = 999
        self.translate_batch_first_api_error_msg_shown = False
        self.translate_batch_accumulated_api_error_details = None
        self.manual_sub_then_dub_active = False
        self.current_manual_merge_srt_path = None
        
        # --- Biến GPT/Gemini Undo & Rewrite ---
        self.gemini_undo_buffer = {}
        self.last_gemini_parameters_used = {}
        self.gpt_undo_buffer = {}
        self.last_gpt_parameters_used = {}
        
        # --- Biến Chain Processing ---
        self.files_for_chained_dubbing = []
        
        # --- Biến Output & Model ---
        self.output_path_var = ctk.StringVar(value=self.master_app.cfg.get("output_path", get_default_downloads_folder()))
        self.model_var = ctk.StringVar(value=self.master_app.cfg.get("model", "medium"))
        self.format_var = ctk.StringVar(value=self.master_app.cfg.get("format", "srt"))

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
            font=("Segoe UI", 13, "bold"), command=self._on_sub_and_dub_clicked
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
        
        self.output_display_label = ctk.CTkLabel(out_frame, textvariable=self.output_path_var, anchor="w", wraplength=300, font=("Segoe UI", 10), text_color=("gray30", "gray70"))
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

        if hasattr(self, 'output_path_var') and hasattr(self, 'output_display_label'):
            self.output_path_var.trace_add("write", lambda *a: self.output_display_label.configure(text=self.output_path_var.get() or "Chưa chọn"))
            self.output_display_label.configure(text=self.output_path_var.get() or "Chưa chọn")

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
        model_menu = ctk.CTkOptionMenu(whisper_options_grid, variable=self.model_var, values=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"])
        model_menu.grid(row=0, column=1, columnspan=3, padx=(0,0), pady=(0,5), sticky="ew")
        
        ctk.CTkLabel(whisper_options_grid, text="Ngôn ngữ:", font=("Poppins", 12), anchor='w').grid(row=1, column=0, padx=(0,5), pady=(5,0), sticky="w")
        lang_menu = ctk.CTkOptionMenu(whisper_options_grid, variable=self.source_lang_var, values=["auto", "en", "vi", "ja", "zh", "ko", "fr", "de", "es", "it", "th", "ru", "pt", "hi"])
        lang_menu.grid(row=1, column=1, padx=(0,10), pady=(5,0), sticky="ew")
        
        ctk.CTkLabel(whisper_options_grid, text="Định dạng:", font=("Poppins", 12), anchor='w').grid(row=1, column=2, padx=(5,5), pady=(5,0), sticky="w")
        format_menu = ctk.CTkOptionMenu(whisper_options_grid, variable=self.format_var, values=["srt", "vtt", "txt"])
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
        self.bilingual_checkbox = ctk.CTkCheckBox(header_translate_frame, text="Tạo phụ đề song ngữ", variable=self.bilingual_var, checkbox_height=20, checkbox_width=20, font=("Poppins", 12))
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
        self.target_lang_menu = ctk.CTkOptionMenu(self.target_lang_frame, variable=self.target_lang_var, values=["vi", "en", "ja", "zh-cn", "fr", "ko", "de", "es"])
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
        self.merge_sub_segmented_button_ref = ctk.CTkSegmentedButton(self.merge_and_pause_frame_ref, values=["Không gộp", "Hard-sub", "Soft-sub"], variable=self.merge_sub_var, font=("Poppins", 12), corner_radius=8)
        self.merge_sub_segmented_button_ref.pack(fill="x", padx=10, pady=(0, 10))
        
        self.manual_merge_mode_checkbox = ctk.CTkCheckBox(self.merge_and_pause_frame_ref, text="🛠 Ghép Sub Thủ Công (Bỏ qua Whisper)", variable=self.manual_merge_mode_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20)
        self.manual_merge_mode_checkbox.pack(anchor="w", padx=10, pady=(2, 2))
        self.auto_add_manual_task_checkbox = ctk.CTkCheckBox(self.merge_and_pause_frame_ref, text="🔄 Tự động thêm vào hàng chờ (TC)", variable=self.auto_add_manual_sub_task_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20)
        self.auto_add_manual_task_checkbox.pack(anchor="w", padx=10, pady=(2, 2))
        
        self.save_in_media_folder_checkbox = ctk.CTkCheckBox(
            self.merge_and_pause_frame_ref,
            text="Lưu vào thư mục của media (TC)",
            variable=self.save_in_media_folder_var,
            font=("Poppins", 12),
            checkbox_height=20,
            checkbox_width=20
        )
        self.save_in_media_folder_checkbox.pack(anchor="w", padx=10, pady=(2, 2))
        self.optimize_whisper_tts_voice_checkbox = ctk.CTkCheckBox(self.merge_and_pause_frame_ref, text="🎤 Tối ưu giọng đọc Whisper", variable=self.optimize_whisper_tts_voice_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20, command=self._on_toggle_optimize_whisper_tts_voice)
        self.optimize_whisper_tts_voice_checkbox.pack(anchor="w", padx=10, pady=(2, 2))
        self.auto_format_srt_frame = ctk.CTkFrame(self.merge_and_pause_frame_ref, fg_color="transparent")
        self.auto_format_srt_frame.pack(fill="x", padx=10, pady=(0, 2))
        self.chk_auto_format_srt = ctk.CTkCheckBox(self.auto_format_srt_frame, text="🔄 Tự động định dạng Text sang SRT", variable=self.auto_format_plain_text_to_srt_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20)
        self.chk_auto_format_srt.pack(anchor="w", padx=0, pady=0)
                
        self.sub_pause_media_options_frame = ctk.CTkFrame(self.merge_and_pause_frame_ref, fg_color="transparent")
        self.sub_pause_media_options_frame.grid_columnconfigure((0, 1), weight=1)

        self.sub_pause_select_folder_button = ctk.CTkButton(self.sub_pause_media_options_frame, text="🖼 Thư mục Ảnh...", font=("Poppins", 12), height=30, command=self.master_app._sub_pause_handle_select_folder)
        self.sub_pause_select_folder_button.grid(row=0, column=0, padx=(0, 5), pady=2, sticky="ew")

        self.sub_pause_select_media_button = ctk.CTkButton(self.sub_pause_media_options_frame, text="🎬 Chọn Video/Ảnh...", font=("Poppins", 12), height=30, command=self.master_app._sub_pause_handle_select_media)
        self.sub_pause_select_media_button.grid(row=0, column=1, padx=(5, 0), pady=2, sticky="ew")

        self.sub_pause_selected_media_info_label = ctk.CTkLabel(self.sub_pause_media_options_frame, text="", font=("Segoe UI", 10), text_color="gray", wraplength=300)
        self.sub_pause_selected_media_info_label.grid(row=1, column=0, columnspan=2, padx=0, pady=(2, 5), sticky="ew")
        
        self.pause_edit_checkbox = ctk.CTkCheckBox(self.merge_and_pause_frame_ref, text="🔨 Dừng lại để chỉnh sửa Sub trước khi Gộp", variable=self.pause_for_edit_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20)
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
        self.enable_split_checkbox_ref = ctk.CTkCheckBox(split_row, text="Chia dòng:", variable=self.enable_split_var, checkbox_height=20, checkbox_width=20, font=("Poppins", 12))
        self.enable_split_checkbox_ref.grid(row=0, column=0, sticky="w", padx=(0, 10))
        ctk.CTkLabel(split_row, text="Ký tự:", font=("Poppins", 11)).grid(row=0, column=1)
        self.max_chars_entry_ref = ctk.CTkEntry(split_row, textvariable=self.max_chars_var, width=40)
        self.max_chars_entry_ref.grid(row=0, column=2, padx=(2, 8))
        ctk.CTkLabel(split_row, text="Số dòng:", font=("Poppins", 11)).grid(row=0, column=3)
        self.max_lines_entry_ref = ctk.CTkEntry(split_row, textvariable=self.max_lines_var, width=40)
        self.max_lines_entry_ref.grid(row=0, column=4, padx=(2, 0))
        split_mode_frame = ctk.CTkFrame(split_frame, fg_color="transparent")
        split_mode_frame.pack(fill="x", padx=10, pady=(0, 10))
        split_mode_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(split_mode_frame, text="Cách chia:", font=("Poppins", 11)).grid(row=0, column=0, padx=(0, 10), sticky="w")
        split_mode_options = ["sentence", "char"]
        if HAS_UNDERTHESEA: split_mode_options.insert(0, "underthesea (Tiếng Việt)")
        self.split_mode_menu = ctk.CTkOptionMenu(split_mode_frame, variable=self.split_mode_var, values=split_mode_options)
        self.split_mode_menu.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(split_mode_frame, text="Ký tự/giây (Timing):", font=("Poppins", 11)).grid(row=1, column=0, padx=(0, 10), pady=(5,0), sticky="w")
        self.sub_cps_entry = ctk.CTkEntry(split_mode_frame, textvariable=self.sub_cps_for_timing_var, width=80)
        self.sub_cps_entry.grid(row=1, column=1, pady=(5,0), sticky="w")
        block_merge_options_frame = ctk.CTkFrame(split_frame, fg_color="transparent")
        block_merge_options_frame.pack(fill="x", padx=10, pady=(5, 5))
        block_merge_options_frame.grid_columnconfigure(1, weight=1, minsize=50)
        block_merge_options_frame.grid_columnconfigure(3, weight=1, minsize=50)
        self.enable_block_merging_checkbox = ctk.CTkCheckBox(block_merge_options_frame, text="Bật gộp khối tự động", variable=self.enable_block_merging_var, font=("Poppins", 12), checkbox_height=20, checkbox_width=20, command=self.master_app._toggle_block_merge_options_state)
        self.enable_block_merging_checkbox.grid(row=0, column=0, columnspan=4, sticky="w", padx=0, pady=(0, 5))
        ctk.CTkLabel(block_merge_options_frame, text="TG nghỉ (ms):", font=("Poppins", 10)).grid(row=1, column=0, sticky="w", padx=(0,2), pady=(0,5))
        self.merge_time_gap_entry = ctk.CTkEntry(block_merge_options_frame, textvariable=self.merge_max_time_gap_var, width=50)
        self.merge_time_gap_entry.grid(row=1, column=1, sticky="ew", padx=(0,5), pady=(0,5))
        ctk.CTkLabel(block_merge_options_frame, text="Độ dài khối max (ký tự):", font=("Poppins", 10)).grid(row=1, column=2, sticky="w", padx=(5,2), pady=(0,5))
        self.merge_max_len_entry = ctk.CTkEntry(block_merge_options_frame, textvariable=self.merge_curr_max_len_normal_var, width=50)
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

        self.open_sub_button_ref = ctk.CTkButton(buttons_container_sub_tab, text="📂 Mở Sub...", height=button_height_sub, font=button_font_style_sub, command=self.load_old_sub_file)
        self.open_sub_button_ref.grid(row=0, column=3, padx=2, pady=2, sticky="ew")

        self.edit_sub_button_ref = ctk.CTkButton(buttons_container_sub_tab, text="📝 Sửa Sub", height=button_height_sub, font=button_font_style_sub, command=self.enable_sub_editing)
        self.edit_sub_button_ref.grid(row=0, column=4, padx=2, pady=2, sticky="ew")

        self.save_sub_button_ref = ctk.CTkButton(buttons_container_sub_tab, text="💾 Lưu Sub", height=button_height_sub, font=button_font_style_sub, command=self.save_edited_sub)
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

    def _on_sub_and_dub_clicked(self):
        """Chuyển sang tab Dubbing và đưa nội dung phụ đề hiện tại sang ô kịch bản TM."""
        try:
            current_text = ""
            if hasattr(self, "subtitle_textbox") and self.subtitle_textbox is not None:
                current_text = self.subtitle_textbox.get("1.0", "end-1c").strip()
        except Exception:
            current_text = ""

        # Gọi handler hiện có để thực hiện chuyển tab/logic liên quan
        try:
            if hasattr(self.master_app, "_handle_sub_and_dub_button_action"):
                self.master_app._handle_sub_and_dub_button_action()
        except Exception:
            pass

        # Sau khi UI đổi tab, điền text vào ô dubbing (nếu sẵn sàng)
        def _populate_when_ready():
            try:
                dub_tb = getattr(self.master_app, "dub_script_textbox", None)
                if dub_tb and current_text:
                    try:
                        dub_tb.configure(state="normal")
                    except Exception:
                        pass
                    dub_tb.delete("1.0", "end")
                    dub_tb.insert("1.0", current_text)
                    if hasattr(self.master_app, "_update_dub_script_controls_state"):
                        self.master_app._update_dub_script_controls_state()
                    if hasattr(self.master_app, "_update_dub_start_batch_button_state"):
                        self.master_app._update_dub_start_batch_button_state()
                    if hasattr(self.master_app, "update_dub_queue_display"):
                        self.master_app.update_dub_queue_display()

                # Ensure Stop button is enabled so user can cancel the Sub&Dub chain immediately
                dub_stop_btn = getattr(self.master_app, "dub_stop_button", None)
                if dub_stop_btn is not None:
                    try:
                        dub_stop_btn.configure(state="normal")
                    except Exception:
                        pass
            except Exception:
                pass

        # Đợi UI khởi tạo xong tab Dubbing rồi mới set nội dung
        self.master_app.after(200, _populate_when_ready)

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
        pause_medium_entry = ctk.CTkEntry(pacing_grid, textvariable=self.sub_pacing_pause_medium_ms_var)
        pause_medium_entry.grid(row=0, column=1, sticky="ew", pady=2)
        Tooltip(pause_medium_entry, "Thời gian nghỉ (mili giây) sau các dấu câu như , ; :")

        ctk.CTkLabel(pacing_grid, text="Nghỉ sau dấu chấm (ms):", font=("Poppins", 11)).grid(row=1, column=0, sticky="w", pady=2, padx=(0, 5))
        pause_period_entry = ctk.CTkEntry(pacing_grid, textvariable=self.sub_pacing_pause_period_ms_var)
        pause_period_entry.grid(row=1, column=1, sticky="ew", pady=2)
        Tooltip(pause_period_entry, "Thời gian nghỉ (mili giây) sau các dấu câu như . ...")

        ctk.CTkLabel(pacing_grid, text="Nghỉ sau dấu hỏi (ms):", font=("Poppins", 11)).grid(row=2, column=0, sticky="w", pady=2, padx=(0, 5))
        pause_question_entry = ctk.CTkEntry(pacing_grid, textvariable=self.sub_pacing_pause_question_ms_var)
        pause_question_entry.grid(row=2, column=1, sticky="ew", pady=2)
        Tooltip(pause_question_entry, "Thời gian nghỉ (mili giây) sau các dấu câu như ? !")

        ctk.CTkLabel(pacing_grid, text="Ngưỡng câu dài (ký tự):", font=("Poppins", 11)).grid(row=3, column=0, sticky="w", pady=2, padx=(0, 5))
        long_sentence_entry = ctk.CTkEntry(pacing_grid, textvariable=self.sub_pacing_long_sentence_threshold_var)
        long_sentence_entry.grid(row=3, column=1, sticky="ew", pady=2)
        Tooltip(long_sentence_entry, "Số ký tự để coi một câu là 'dài' và tăng tốc độ đọc.")

        ctk.CTkLabel(pacing_grid, text="Hệ số tăng tốc:", font=("Poppins", 11)).grid(row=4, column=0, sticky="w", pady=2, padx=(0, 5))
        fast_cps_multiplier_entry = ctk.CTkEntry(pacing_grid, textvariable=self.sub_pacing_fast_cps_multiplier_var)
        fast_cps_multiplier_entry.grid(row=4, column=1, sticky="ew", pady=2)
        Tooltip(fast_cps_multiplier_entry, "Hệ số nhân với tốc độ đọc (CPS) cho câu dài. Ví dụ: 1.1 = nhanh hơn 10%.")

    # ========================================================================
    # HELPER METHODS - Di chuyển từ Piu.py
    # ========================================================================

    def open_subtitle_tab_output_folder(self):
        """Mở thư mục output đã được cấu hình cho tab Tạo Phụ Đề."""
        self.logger.info("[UI SubTab] Yêu cầu mở thư mục output của tab Sub.")
        current_path = self.output_path_var.get()
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
        path = filedialog.askdirectory(initialdir=self.output_path_var.get() or os.getcwd())
        if path:
            self.output_path_var.set(path) # Tự động lưu do trace

    # ========================================================================
    # PHASE 2.2: WHISPER FUNCTIONS - ✅ HOÀN THÀNH
    # ========================================================================
    # Đã di chuyển 7 hàm Whisper (~291 dòng)
    
    # ========================================================================
    # TODO: CÁC HÀM CẦN DI CHUYỂN TỪ Piu.py - PHASE 2.3+
    # ========================================================================
    # Còn ước tính ~40-50 hàm cần copy từ Piu.py
    #
    # PHASE 2.3: GPT/GEMINI FUNCTIONS (14 hàm)
    # =========================================
    # Gemini:
    # 1. _trigger_gemini_script_processing_with_chain    (2567) - Chain trigger
    # 2. _execute_gemini_script_editing_thread_for_chain (2647) - Chain worker
    # 3. _handle_gemini_script_editing_result_for_chain  (2705) - Chain handler
    # 4. _execute_gemini_scene_division_thread           (2880) - Scene division
    # 5. _handle_gemini_scene_division_result            (2977) - Scene division handler
    # 6. _trigger_gemini_script_processing               (3338) - Single trigger
    # 7. _execute_gemini_script_editing_thread           (3391) - Single worker
    # 8. _handle_gemini_script_editing_result            (3426) - Single handler
    #
    # GPT:
    # 9. _trigger_gpt_script_processing_from_popup       (3967) - Trigger
    # 10. _execute_gpt_script_editing_thread             (4061) - Worker
    # 11. _execute_gpt_scene_division_thread             (4236) - Scene division
    # 12. _execute_gpt_single_summary_prompt_thread      (4373) - Summary
    # 13. _handle_gpt_scene_division_result              (4491) - Handler
    # 14. _handle_gpt_script_editing_result              (4538) - Handler
    #
    #
    # PHASE 2.4: TRANSLATION FUNCTIONS (3 hàm)
    # =========================================
    # 1. translate_subtitle_file      (12334) - Main wrapper
    # 2. translate_google_cloud       (12161) - Google Cloud Translate
    # 3. translate_openai             (12258) - OpenAI Translate
    #
    # PHASE 2.5: MERGE/BURN FUNCTIONS (2 hàm)
    # =========================================
    # 1. burn_sub_to_video            (12535) - Hardcode subtitles
    # 2. merge_sub_as_soft_sub        (12745) - Softcode subtitles
    #
    # PHASE 2.6: EDIT & MANUAL MERGE FUNCTIONS (5 hàm)
    # ==================================================
    # 1. _on_toggle_manual_merge_mode     (7787) - Toggle mode
    # 2. load_old_sub_file                (9848) - Load subtitle file
    # 3. save_edited_sub                  (9938) - Save edited subtitle
    # 4. enable_sub_editing               (9928) - Enable editing
    # 5. _execute_manual_merge_threaded   (8380) - Manual merge worker
    #
    # LƯU Ý:
    # - Hầu hết GPT/Gemini đã sử dụng AIService (được refactor trước đó)
    # - Nhiều hàm có callback/threading phức tạp
    # - Bạn có thể copy từng nhóm (Gemini trước, GPT sau, rồi Translation, Merge, Edit)
    # ========================================================================

    # Hàm logic: Chạy model Whisper để tạo phụ đề từ file media    
    def run_whisper_engine(self, input_file, model_name, fmt, lang, output_dir):
        """
        [REFACTORED] Chạy Whisper transcription bằng model đã được load.
        Sử dụng ModelService để xử lý business logic, chỉ xử lý UI/logging ở đây.
        """
        # Kiểm tra các điều kiện cần thiết
        if not self.master_app.model_service.is_model_loaded():
            current_expected_model = self.model_var.get()
            logging.error(f"Model Whisper '{current_expected_model}' chưa được load.")
            raise RuntimeError(f"Model Whisper '{current_expected_model}' chưa được load.")
        
        # Đồng bộ state từ ModelService
        self.whisper_model = self.master_app.model_service.current_model
        self.loaded_model_name = self.master_app.model_service.model_name
        self.loaded_model_device = self.master_app.model_service.device
            
        # Ghi log chi tiết về tác vụ sắp thực hiện
        use_fp16 = (self.loaded_model_device == 'cuda')
        logging.info(
            f"[{threading.current_thread().name}] "
            f"Đang chạy Whisper transcribe (Model: '{self.loaded_model_name}' "
            f"trên Device: {self.loaded_model_device}, "
            f"fp16: {use_fp16}, lang: {lang}) "
            f"trên file: {os.path.basename(input_file)}"
        )
        
        # Định dạng và lưu file output
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        sub_name = f"{base_name}.{fmt}"
        sub_path = os.path.join(output_dir, sub_name)
        
        try:
            # Gọi ModelService để transcribe và save
            saved_path = self.master_app.model_service.transcribe_and_save(
                audio_path=input_file,
                output_path=sub_path,
                output_format=fmt,
                language=lang if lang != "auto" else None,
                fp16=use_fp16,
                patience=2.0,
                beam_size=5,
                no_speech_threshold=0.45,
                logprob_threshold=-0.8
            )
            
            logging.info(f"[{threading.current_thread().name}] Đã ghi file phụ đề: {saved_path}")
            return saved_path
            
        except Exception as e:
            logging.error(f"[{threading.current_thread().name}] Lỗi trong quá trình transcribe/ghi file: {e}", exc_info=True)
            raise

# Hàm tối ưu giọng đọc cho whisper TTS
    def _on_toggle_optimize_whisper_tts_voice(self):
        logging.info(f"Checkbox 'Tối ưu giọng đọc cho TTS' thay đổi trạng thái: {self.optimize_whisper_tts_voice_var.get()}")
        # TODO: Thêm logic xử lý khi checkbox này thay đổi (ví dụ: lưu config, cập nhật UI khác nếu cần)
        if hasattr(self, 'save_config'):
            self.save_config() # Lưu trạng thái mới của checkbox vào config
        # Gọi hàm cập nhật UI chung của tab Sub để nó có thể vô hiệu hóa checkbox này khi ở Manual Mode
        if hasattr(self, '_set_subtitle_tab_ui_state'):
            self._set_subtitle_tab_ui_state(self.is_subbing)    

# Hàm logic: Xác định thiết bị (device) nên dùng để tải model Whisper
    def _determine_target_device(self):
        """
        [REFACTORED] Xác định device nên dùng ('cuda' hoặc 'cpu').
        Sử dụng ModelService để xác định device, đồng bộ state với Piu.py.
        """
        selected_model = self.model_var.get()
        device = self.master_app.model_service.get_recommended_device(selected_model)
        
        # Đồng bộ state với master_app
        # Note: cuda_status và gpu_vram_mb không cần lưu ở SubtitleTab vì đã có trong master_app
        return device                

# Hàm Tải model Whisper nếu cần, dựa trên tên model VÀ thiết bị đích. ---
    def load_whisper_model_if_needed(self, force_reload=False, callback=None):
        """
        Tải model Whisper nếu cần, dựa trên tên model VÀ thiết bị đích.
        PHIÊN BẢN HOÀN CHỈNH: Tích hợp với chuỗi khởi động tuần tự và có thông báo chi tiết.
        """
        if not HAS_WHISPER:
            logging.error("Không thể tải model Whisper: thư viện whisper chưa được cài đặt.")
            if callback: callback() # Phải gọi callback để không làm kẹt chuỗi khởi động
            return

        if self.is_loading_model:
            logging.info("Đang trong quá trình tải model Whisper khác. Bỏ qua yêu cầu mới.")
            # Không gọi callback ở đây vì một luồng khác đang chạy và sẽ chịu trách nhiệm gọi callback của nó.
            return

        target_model = self.model_var.get()
        target_device = self._determine_target_device()

        should_load = (
            force_reload or
            self.whisper_model is None or
            self.loaded_model_name != target_model or
            self.loaded_model_device != target_device
        )

        if should_load:
            logging.info(f"Cần tải/load lại model '{target_model}' lên device '{target_device}'.")

            self.is_loading_model = True
            self.is_loading_model_for_timer = True
            if self.master_app.start_time is None: # Chỉ đặt start_time nếu chưa có tác vụ nào khác đang chạy
                self.master_app.start_time = time.time()

            # --- Logic hiển thị thông báo chi tiết ---
            whisper_model_sizes = {
                "tiny": "~72MB", "base": "~142MB", "small": "~466MB",
                "medium": "~1.42GB", "large": "~2.85GB", 
                "large-v1": "~2.85GB", "large-v2": "~2.85GB", "large-v3": "~2.85GB"
            }
            size_estimate = whisper_model_sizes.get(target_model, "")

            # Tạo thông báo ngắn gọn cho thanh status chính sau này
            status_message_for_timer = f"⏳ Tải model: {target_model} ({size_estimate})..."
            self.master_app._last_status_text = status_message_for_timer # Lưu lại để đồng hồ sử dụng

            # Tạo thông báo đầy đủ cho màn hình chờ
            status_message_for_splash = (
                f"🧠 Đang chuẩn bị mô hình Trí tuệ nhân tạo...\n"
                f"Tải model: {target_model} ({size_estimate})\n"
                f"(Việc này có thể mất vài phút ở lần đầu)"
            )
            
            # Cập nhật trực tiếp lên màn hình chờ nếu nó vẫn còn
            if hasattr(self.master_app, 'splash') and self.master_app.splash and self.master_app.splash.winfo_exists():
                # Hàm update_status trong SplashScreen đã có hiệu ứng fade
                self.master_app.splash.update_status(status_message_for_timer) 
            
            logging.info(status_message_for_splash.replace('\n', ' '))
            # --- Kết thúc logic thông báo ---

            self.master_app.after(1000, self.master_app.update_time_realtime)

            sub_button = self.sub_button if hasattr(self, 'sub_button') else None
            if sub_button and sub_button.winfo_exists():
                try:
                    sub_button.configure(state="disabled", text=f"Đang tải {target_model}...")
                except Exception as e:
                    logging.warning(f"Không thể vô hiệu hóa nút Sub: {e}")

            thread = threading.Thread(
                target=self._load_whisper_model_thread,
                args=(target_model, target_device, callback), # Truyền callback vào luồng
                daemon=True,
                name=f"WhisperLoad_{target_model}_{target_device}"
            )
            thread.start()
        
        elif callback:
            # Rất quan trọng: Nếu không cần tải, vẫn phải gọi callback để chuỗi khởi động tiếp tục!
            logging.info(f"Model '{target_model}' trên device '{target_device}' đã sẵn sàng. Bỏ qua tải và tiếp tục chuỗi.")
            if hasattr(self.master_app, 'mark_startup_task_done'):
                self.master_app.mark_startup_task_done('ai_model')
            callback()     

# Hàm logic (chạy trong luồng): Tải model Whisper lên thiết bị cụ thể
    def _load_whisper_model_thread(self, target_model, target_device, callback=None):
        """
        [REFACTORED] Tải model Whisper an toàn cho GUI.
        Sử dụng ModelService để xử lý business logic, chỉ xử lý UI callbacks ở đây.
        """
        with keep_awake(f"Loading Whisper model {target_model}"):
            try:
                # Báo UI
                self.master_app.after(0, lambda tm=target_model, td=target_device:
                           self.master_app.update_status(f"⏳ Đang tải/nạp model: {tm} ({td})... (Có thể mất vài phút)"))
                logging.info(f"[LoadModelThread] Bắt đầu tải/nạp model Whisper: {target_model} lên device {target_device}")

                # Gọi ModelService để load model
                loaded_model, loaded_model_name, actual_device, error_message = self.master_app.model_service.load_model(
                    model_name=target_model,
                    device=target_device,
                    force_reload=False,
                    stop_event=lambda: self.master_app.stop_event.is_set()
                )
                
                # Đồng bộ state với Piu.py
                if loaded_model:
                    target_device = actual_device  # Update với device thực tế đã dùng
                    logging.info(f"[LoadModelThread] Model '{loaded_model_name}' loaded on '{actual_device}' successfully.")
                
                # Cập nhật về luồng chính
                self.master_app.after(0, self._update_loaded_model, loaded_model, loaded_model_name, actual_device, callback)

            except Exception as e:
                logging.error(f"[LoadModelThread] Lỗi tải model Whisper '{target_model}': {e}", exc_info=True)
                error_msg = f"Đã xảy ra lỗi khi tải model '{target_model}': {e}"
                self.master_app.after(0, lambda err=error_msg, tm=target_model, td=target_device: messagebox.showerror(
                    "Lỗi Tải Model",
                    f"Đã xảy ra lỗi khi tải model '{tm}' lên thiết bị '{td}':\n{err}",
                    parent=self.master_app
                ))
                self.master_app.after(0, self._update_loaded_model, None, None, None, callback)

            finally:
                # Luôn trả UI về trạng thái bình thường
                self.master_app.after(0, self._reset_model_loading_ui)
                self.master_app.after(0, lambda: setattr(self, "is_loading_model", False))
                self.master_app.after(0, lambda: setattr(self.master_app.model_service, "is_loading_model", False))
                logging.debug(f"[LoadModelThread] Hoàn tất luồng tải cho model '{target_model}' device '{target_device}'.") 

    # Hàm callback: Cập nhật trạng thái model Whisper đã được tải (chạy trên luồng chính)
    def _update_loaded_model(self, model_object, model_name, loaded_device, callback=None):
        """
        [REFACTORED] Callback để cập nhật trạng thái model, device.
        Đồng bộ state giữa ModelService và Piu.py.
        """
        # Đồng bộ state với Piu.py
        self.whisper_model = model_object
        self.loaded_model_name = model_name
        self.loaded_model_device = loaded_device
        
        # Đồng bộ state với ModelService (để đảm bảo đồng nhất)
        if model_object:
            self.master_app.model_service.current_model = model_object
            self.master_app.model_service.model_name = model_name
            self.master_app.model_service.device = loaded_device
        
        # Tắt cờ timer ngay khi có kết quả
        self.is_loading_model_for_timer = False
        logging.debug("Đã đặt is_loading_model_for_timer = False trong _update_loaded_model.")

        if model_object and loaded_device:
            logging.info(f"Đã tải thành công model Whisper '{model_name}' lên device '{loaded_device}'.")
            self.master_app.update_status(f"✅ Model '{model_name}' ({loaded_device}) đã sẵn sàng.")
            if hasattr(self.master_app, 'mark_startup_task_done'):
                self.master_app.mark_startup_task_done('model')
        else:
            # Xử lý khi load lỗi
            logging.warning("Model Whisper chưa được tải hoặc có lỗi.")
            self.master_app.update_status("⚠️ Model chưa được tải hoặc có lỗi khi tải.")
            self.whisper_model = None
            self.loaded_model_name = None
            self.loaded_model_device = None

        # --- THAY ĐỔI QUAN TRỌNG NHẤT ---
        # Thay vì gọi _reset_model_loading_ui, gọi hàm quản lý UI chính của tab
        if hasattr(self, '_set_subtitle_tab_ui_state'):
            # Gọi sau một chút để đảm bảo các thay đổi biến ở trên đã hoàn tất
            self.master_app.after(50, lambda: self._set_subtitle_tab_ui_state(subbing_active=False))
            logging.info("Đã lên lịch _set_subtitle_tab_ui_state(False) để khôi phục toàn bộ UI tab Sub.")
        else:
            # Fallback nếu hàm chính không tồn tại (hiếm)
            logging.error("Không tìm thấy hàm _set_subtitle_tab_ui_state để khôi phục UI.")
            if hasattr(self, '_reset_model_loading_ui'):
                self.master_app.after(50, self._reset_model_loading_ui)

        # Gọi callback (nếu có) để tiếp tục chuỗi khởi động
        if callback:
            callback()

    # Hàm tiện ích UI: Khôi phục trạng thái giao diện sau khi tải model xong (hoặc lỗi)
    def _reset_model_loading_ui(self):
        """Khôi phục trạng thái UI sau khi tải model xong (hoặc lỗi)."""
        logging.debug("Đang khôi phục UI sau khi tải model...")

        # TẮT CỜ CHO ĐỒNG HỒ
        was_loading_model_for_timer = self.is_loading_model_for_timer # Lưu trạng thái cũ
        self.is_loading_model_for_timer = False
        logging.debug("Đã đặt self.is_loading_model_for_timer = False")

        # Kích hoạt lại nút Sub
        is_app_active = self.master_app._is_app_fully_activated() if hasattr(self.master_app, '_is_app_fully_activated') else True

        sub_button = self.sub_button if hasattr(self, 'sub_button') else None
        if sub_button and sub_button.winfo_exists():
             try:
                 # Chỉ bật lại nút Sub nếu không có tác vụ subbing nào khác đang chạy
                 if not self.is_subbing:
                     current_state_sub_btn = "normal" if is_app_active else "disabled"
                     button_text_sub_btn = "▶️ Bắt đầu SUB" if is_app_active else "🔒 Kích hoạt (Sub)"
                     # Kiểm tra xem có ở manual mode không
                     if self.manual_merge_mode_var.get():
                         button_text_sub_btn = "🔨 Bắt đầu Ghép Thủ Công"
                         current_state_sub_btn = "normal" # Ở manual mode, nút này nên bật nếu không subbing

                     sub_button.configure(state=current_state_sub_btn, text=button_text_sub_btn)
                     logging.debug(f"Đã khôi phục nút Sub về trạng thái: {current_state_sub_btn}")
                 else:
                     logging.debug("Nút Sub không được bật lại vì is_subbing vẫn True (có thể tác vụ sub khác đang chờ).")
             except Exception as e:
                 logging.warning(f"Không thể khôi phục nút Sub: {e}")

        # (MỚI) Kiểm tra và reset start_time nếu không còn tác vụ nào khác dùng timer
        if was_loading_model_for_timer: # Chỉ kiểm tra nếu nó vừa mới được tắt
            all_other_timer_tasks_stopped_after_model = not (
                self.master_app.is_downloading or
                self.is_subbing or
                # self.is_loading_model_for_timer is now False
                self.master_app.dub_is_processing or
                self.master_app.is_creating_slideshow or
                self.is_gpt_processing_script or
                self.master_app.is_dalle_processing
            )
            if all_other_timer_tasks_stopped_after_model:
                if self.master_app.start_time is not None:
                    self.master_app.start_time = None
                    logging.info("Tải model hoàn tất/lỗi. Không còn tác vụ nào khác dùng timer, đã reset self.start_time.")
                    # Cập nhật status nếu không có gì khác đang chạy
                    # Hàm check_if_fully_ready cũng có thể xử lý việc này
                    if not (self.is_subbing or self.master_app.is_downloading or self.master_app.dub_is_processing):
                        self.master_app.after(100, lambda: self.master_app.update_status("✅ Piu đã xử lý xong. Ứng dụng đã sẵn sàng!"))
            else:
                logging.info("Tải model hoàn tất/lỗi. Vẫn còn tác vụ khác dùng timer, self.start_time KHÔNG được reset bởi _reset_model_loading_ui.")   


# Hàm trigger cho chuỗi Gemini -> Imagen -> Dub
    def _trigger_gemini_script_processing_with_chain(self, target_textbox_widget, context, user_prompt,
                                                         trigger_imagen_chain_flag=False,
                                                         trigger_dub_chain_flag=False,
                                                         input_script_override=None,
                                                         base_filename_for_chain=None): # <<< THÊM THAM SỐ MỚI NÀY VÀO ĐÂY
        ## Hàm này có cấu trúc rất giống với hàm trigger của GPT
        log_prefix = f"[GeminiChainTrigger:{context}]"

        # <<< THÊM DÒNG NÀY ĐỂ RESET HÀNG CHỜ >>>
        # Điều này đảm bảo tác vụ đơn lẻ không bị ảnh hưởng bởi các lô chạy trước
        if not input_script_override: # Chỉ reset nếu đây là tác vụ đơn lẻ, không phải một phần của lô AI
            self.files_for_chained_dubbing = []
        
        self.master_app.stop_event.clear()
        logging.info(f"{log_prefix} Đã xóa (clear) self.stop_event để chuẩn bị cho chuỗi tác vụ mới.")        
        logging.info(f"{log_prefix} Kích hoạt chuỗi Gemini -> Imagen. Prompt: '{user_prompt[:50]}...', TriggerImagen: {trigger_imagen_chain_flag}, TriggerDub: {trigger_dub_chain_flag}")

        ## 1. Kiểm tra API Key (Giữ nguyên code cũ của bạn)
        if not self.master_app.gemini_key_var.get():
            messagebox.showerror("Thiếu API Key", "Vui lòng cấu hình Gemini API Key trong Cài đặt API Keys.", parent=self.master_app)
            return

        ## 2. Lấy nội dung script hiện tại
        script_content = ""
        text_in_widget_before = ""
        
        if input_script_override is not None:
            # Nếu đang chạy hàng loạt, sử dụng kịch bản được truyền vào
            script_content = input_script_override
            logging.info(f"{log_prefix} Sử dụng kịch bản được truyền vào từ chế độ hàng loạt (dài {len(script_content)} chars).")
            # Vẫn lấy nội dung widget để có thể hoàn tác về trạng thái trước khi bắt đầu lô
            if target_textbox_widget and target_textbox_widget.winfo_exists():
                text_in_widget_before = target_textbox_widget.get("1.0", "end-1c")
        else:
            # Nếu chạy đơn lẻ, lấy kịch bản từ textbox như cũ
            if target_textbox_widget and target_textbox_widget.winfo_exists():
                text_in_widget_before = target_textbox_widget.get("1.0", "end-1c")
                temp_content = text_in_widget_before.strip()
                if not self._is_textbox_content_invalid_for_script(temp_content):
                    script_content = temp_content

        ## 3. Lưu trạng thái để Hoàn tác (Undo) và Viết lại (Giữ nguyên code cũ của bạn)
        self.gemini_undo_buffer[context] = {"original_text": text_in_widget_before}
        self.last_gemini_parameters_used[context] = {
            "prompt": user_prompt,
            "input_script_for_this_prompt": script_content
        }
        logging.info(f"{log_prefix} Đã lưu trạng thái Undo và Rewrite cho Gemini.")

        ## 4. Cập nhật giao diện (Giữ nguyên code cũ của bạn)
        self.is_gemini_processing = True 
        self.master_app.start_time = time.time()
        self.master_app._set_subtitle_tab_ui_state(True)
        self.master_app.update_queue_display() # Gọi để hiển thị mục "ĐANG XỬ LÝ..."
        self.master_app.update_status(f"💎 Gemini đang tạo kịch bản...")
        self.master_app.update_time_realtime()
        
        if hasattr(self, 'ai_edit_button_sub_tab'): self.ai_edit_button_sub_tab.configure(state="disabled", text="AI Đang chạy...")
        if hasattr(self, 'ai_edit_dub_script_button'): self.ai_edit_dub_script_button.configure(state="disabled", text="AI Đang chạy...")

        selected_model = self.master_app.gemini_model_for_script_editing_var.get()
        logging.info(f"{log_prefix} Model Gemini được chọn cho chuỗi tự động: {selected_model}")

        # Lấy thông tin Dàn diễn viên từ config đã lưu
        character_sheet_text = self.master_app.cfg.get("imagen_last_character_sheet", "")
        logging.info(f"{log_prefix} Lấy được character_sheet từ config (dài {len(character_sheet_text)} chars) để truyền cho luồng.")

        thread = threading.Thread(
            target=self._execute_gemini_script_editing_thread_for_chain,
            args=(script_content, user_prompt, selected_model, target_textbox_widget, context,
                  trigger_imagen_chain_flag, trigger_dub_chain_flag, character_sheet_text, # Giữ nguyên dòng này
                  base_filename_for_chain), 
            daemon=True,
            name=f"GeminiChainThread_{context}"
        )
        thread.start()
        logging.info(f"{log_prefix} Đã khởi động luồng xử lý nền cho chuỗi Gemini (đã bao gồm character_sheet).")


# <<<--- THÊM HÀM MỚI NÀY VÀO BÊN DƯỚI HÀM TRIGGER BẠN VỪA TẠO Ở BƯỚC 2 ---<<<
    def _execute_gemini_script_editing_thread_for_chain(self, script_content, user_instruction, selected_model, target_widget, context,
                                                    trigger_imagen_chain_flag, trigger_dub_chain_flag, character_sheet_text,
                                                    base_filename_for_chain): # <<< THÊM VÀO ĐÂY
        """
        [REFACTORED] (Worker) Tách lời thoại, gọi API Gemini, và truyền dữ liệu nhân vật đi tiếp.
        Sử dụng AIService để xử lý business logic, chỉ xử lý UI callbacks ở đây.
        """
        log_prefix = f"[GeminiChainExec_v2:{context}]"
        logging.info(f"{log_prefix} Bắt đầu xử lý kịch bản với Gemini...")

        # Lấy API key
        gemini_api_key = self.master_app.gemini_key_var.get()
        if not gemini_api_key:
            error_message = "Lỗi: Vui lòng nhập Gemini API Key trong Cài đặt."
            self.master_app.after(0, self._handle_gemini_script_editing_result_for_chain,
                      None, error_message, target_widget, context,
                      trigger_imagen_chain_flag, trigger_dub_chain_flag,
                      selected_model, script_content, character_sheet_text,
                      base_filename_for_chain)
            return

        # Gọi AI Service để xử lý (SRT extraction đã được xử lý trong AIService)
        try:
            processed_script, error_message = self.master_app.ai_service.process_script_with_gemini(
                script_content=script_content,
                user_instruction=user_instruction,
                api_key=gemini_api_key,
                model_name=selected_model,
                stop_event=lambda: self.master_app.stop_event.is_set(),
                max_retries=2,  # Chain có thể cần retry nhanh hơn
                retry_delay_seconds=15
            )
            
            # Track API call nếu thành công
            if processed_script:
                self.master_app._track_api_call(service_name="gemini_calls", units=1)

        except Exception as e:
            error_message = f"Lỗi nghiêm trọng khi sử dụng AI Service: {type(e).__name__} - {e}"
            logging.error(f"{log_prefix} {error_message}", exc_info=True)
            processed_script = None
            
        # --- BƯỚC 3: GỌI HÀM HANDLER VÀ TRUYỀN `character_sheet_text` ĐI TIẾP ---
        self.master_app.after(0, self._handle_gemini_script_editing_result_for_chain,
                   processed_script,
                   error_message,
                   target_widget,
                   context,
                   trigger_imagen_chain_flag,
                   trigger_dub_chain_flag,
                   selected_model,
                   script_content,
                   character_sheet_text,
                   base_filename_for_chain) # <<< THÊM VÀO CUỐI CÙNG 


# Hàm xử lý kết quả từ Gemini
    def _handle_gemini_script_editing_result_for_chain(self, processed_script, error_message, target_widget, context,
                                                       trigger_imagen_chain_flag, trigger_dub_chain_flag, selected_model,
                                                       original_input_script, character_sheet_text,
                                                       base_filename_for_chain): # <<< THÊM VÀO ĐÂY
        
        log_prefix = f"[HandleGeminiChainResult_v8:{context}]"

        # --- KHỐI 1: KIỂM TRA LỆNH DỪNG TỪ NGƯỜI DÙNG ---
        if self.master_app.stop_event.is_set():
            logging.warning(f"{log_prefix} Phát hiện stop_event. Hủy bỏ xử lý kết quả và thực hiện dọn dẹp đầy đủ.")
            
            # Nếu đang trong một lô AI, gọi hàm dọn dẹp của lô đó
            if self.is_ai_batch_processing:
                self._on_ai_batch_finished(stopped=True)
            else: 
                # Nếu là tác vụ đơn lẻ, thực hiện dọn dẹp tại chỗ
                
                # 1. Reset cờ xử lý của chính nó
                self.is_gemini_processing = False
                self.is_gpt_processing_script = False # Reset cả các cờ liên quan
                self.is_creating_slideshow = False
                self.is_dalle_processing = False
                self.is_imagen_processing = False
                self.is_subbing = False # Đảm bảo cờ sub (dùng cho hardsub) cũng được reset

                # 2. Gọi hàm kiểm tra hoàn thành chung để reset đồng hồ
                self._check_completion_and_shutdown()
                
                # 3. Cập nhật lại toàn bộ giao diện của tab Subtitle về trạng thái chờ
                #    Đây là bước quan trọng nhất để kích hoạt lại các nút
                self._set_subtitle_tab_ui_state(False)
                
                # 4. Cập nhật thanh trạng thái với thông báo cuối cùng
                self.update_status("🛑 Tác vụ đã được dừng.")
                
            return # Dừng hàm tại đây, không xử lý gì thêm

        # --- KHỐI 2: KIỂM TRA LỖI TỪ KẾT QUẢ CỦA AI ---
        if error_message or not processed_script:
            is_user_stop = "Đã dừng bởi người dùng" in (error_message or "")
            error_to_show = error_message or "Gemini không trả về kết quả kịch bản."
            logging.error(f"{log_prefix} Lỗi tạo kịch bản từ Gemini: {error_to_show}")
            
            final_status_msg = f"🛑 Đã dừng bởi người dùng." if is_user_stop else f"❌ Lỗi Gemini: {error_to_show[:60]}..."
            self.update_status(final_status_msg)

            if not is_user_stop:
                messagebox.showerror("Lỗi Gemini API", error_to_show, parent=self)
            
            self.is_gemini_processing = False
            self._check_completion_and_shutdown()
            # <<< THÊM DÒNG NÀY ĐỂ ĐẢM BẢO UI CŨNG ĐƯỢC RESET KHI CÓ LỖI >>>
            self._set_subtitle_tab_ui_state(False)
            return

        logging.info(f"{log_prefix} Tạo kịch bản thành công. Bắt đầu xử lý timing...")
        
        is_original_srt = re.match(r"^\d+\s*[\r\n]+\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->", original_input_script.strip(), re.MULTILINE) is not None

        final_script_for_display = processed_script
        script_for_chain_timing = processed_script 

        split_config_from_ui = {
            "split_enabled": self.enable_split_var.get(),
            "mode": self.split_mode_var.get(),
            "max_chars": safe_int(self.max_chars_var.get(), 90),
            "max_lines": safe_int(self.max_lines_var.get(), 1),
            "DEFAULT_CPS_FOR_TIMING": safe_int(self.sub_cps_for_timing_var.get(), 17),
            "PAUSE_BETWEEN_SEGMENTS_MS_FOR_TIMING": 1, 
            "ABSOLUTE_MIN_DURATION_PER_CHUNK_MS": self.min_duration_per_segment_ms
        }
        logging.info(f"{log_prefix} Cấu hình chia dòng lấy từ UI: {split_config_from_ui}")

        if is_original_srt:
            logging.info(f"{log_prefix} Input gốc là SRT. Sẽ bảo toàn timing.")
            self.update_status("💎 Gemini đã sửa xong. Đang ánh xạ lại timing gốc...")
            
            original_srt_data = self._parse_plain_text_to_srt_data(original_input_script, force_plain_text_processing=False)
            
            if original_srt_data:
                new_text_segments = self._parse_plain_text_to_srt_data(
                    processed_script, 
                    force_plain_text_processing=True, 
                    split_config_override=split_config_from_ui
                )

                final_mapped_data = self._map_optimized_segments_to_original_srt_timings(new_text_segments, original_srt_data)
                
                if final_mapped_data:
                    final_srt_string = format_srt_data_to_string(final_mapped_data)
                    final_script_for_display = final_srt_string
                    script_for_chain_timing = final_srt_string
                    logging.info(f"{log_prefix} Ánh xạ timing thành công.")
                else:
                    logging.warning(f"{log_prefix} Ánh xạ timing thất bại.")
            else:
                logging.warning(f"{log_prefix} Không parse được dữ liệu timing từ SRT gốc.")

        else:
            logging.info(f"{log_prefix} Input gốc là Plain Text. Sẽ tạo timing mới.")
            self.update_status("💎 Gemini đã tạo kịch bản. Đang ước tính timing...")

            srt_data_content = self._parse_plain_text_to_srt_data(
                processed_script, 
                force_plain_text_processing=True, 
                split_config_override=split_config_from_ui
            )
            
            if srt_data_content:
                srt_output_string = format_srt_data_to_string(srt_data_content)
                final_script_for_display = srt_output_string
                script_for_chain_timing = srt_output_string
                logging.info(f"{log_prefix} Tạo SRT và timing mới thành công.")
            else:
                logging.warning(f"{log_prefix} Không tạo được dữ liệu SRT.")
        
        if target_widget and target_widget.winfo_exists():
            target_widget.configure(state="normal")
            target_widget.delete("1.0", "end")
            target_widget.insert("1.0", final_script_for_display)

        # --- SỬA LỖI Ở ĐÂY ---
        if not trigger_imagen_chain_flag:
            self.update_status("✅ Gemini đã biên tập xong kịch bản.")
            messagebox.showinfo("Hoàn thành", "Gemini đã xử lý và cập nhật nội dung kịch bản.", parent=self)
            
            # THÊM KHỐI CODE KHÔI PHỤC NÚT VÀO ĐÂY
            is_app_active = self._is_app_fully_activated()

            if is_app_active:
                if hasattr(self, 'ai_edit_button_sub_tab') and self.ai_edit_button_sub_tab.winfo_exists():
                    self.ai_edit_button_sub_tab.configure(state="normal", text="✨ Biên tập (AI)")
                if hasattr(self, 'ai_edit_dub_script_button') and self.ai_edit_dub_script_button.winfo_exists():
                    self.ai_edit_dub_script_button.configure(state="normal", text="✨ Biên tập (AI)")
            logging.info(f"{log_prefix} Đã khôi phục các nút Biên tập AI (chuỗi ngắn).")
            # KẾT THÚC KHỐI CODE THÊM

            self.is_gemini_processing = False
            self._set_subtitle_tab_ui_state(False)
            self._check_completion_and_shutdown()
            return
        
        # Logic tiếp tục chuỗi Imagen (giữ nguyên)
        logging.info(f"{log_prefix} Bắt đầu bước 2: Yêu cầu Gemini tạo prompt cho Imagen...")
        self.update_status("💎 Gemini tạo kịch bản xong! Chuẩn bị yêu cầu Gemini chia cảnh...")

        try:
            num_images = int(self.cfg.get("imagen_last_num_images", "1"))
            # <<< THÊM DÒNG NÀY ĐỂ ĐỌC CÀI ĐẶT MỚI >>>
            auto_split_scenes = self.cfg.get("imagen_auto_split_scenes", True)
        except (ValueError, TypeError):
            num_images = 1
            auto_split_scenes = True # Mặc định an toàn
        
        thread = threading.Thread(
            target=self._execute_gemini_scene_division_thread,
            args=(
                processed_script,
                script_for_chain_timing,
                num_images,
                selected_model,
                target_widget,
                context,
                trigger_dub_chain_flag,
                character_sheet_text,
                base_filename_for_chain,
                auto_split_scenes 
            ),
            daemon=True,
            name=f"GeminiSceneDivisionThread_{context}"
        )
        thread.start()

# <<<--- THÊM HÀM MỚI NÀY VÀO BÊN DƯỚI HÀM VỪA TẠO Ở BƯỚC 4 ---<<<
    def _execute_gemini_scene_division_thread(self, script_content, formatted_srt_for_slideshow, num_images, selected_model, target_widget, context, trigger_dub_chain_flag, character_sheet_text,
                                              base_filename_for_chain, auto_split_scenes):
        """
        [REFACTORED] Yêu cầu Gemini phân tích kịch bản, tạo prompt JSON và tuân thủ giới hạn thời gian tối thiểu cho mỗi cảnh.
        Sử dụng AIService để xử lý business logic, chỉ xử lý UI callbacks ở đây.
        """
        worker_log_prefix = f"[{threading.current_thread().name}_GeminiSceneDivision_v13_TimeLimit]"
        logging.info(f"{worker_log_prefix} Bắt đầu chia kịch bản và tạo {num_images} cặp scene/prompt.")

        # Lấy API key
        gemini_api_key = self.gemini_key_var.get()
        if not gemini_api_key:
            error_message = "Lỗi: Vui lòng nhập Gemini API Key trong Cài đặt."
            self.master_app.after(0, self._handle_gemini_scene_division_result,
                      None, error_message, formatted_srt_for_slideshow, script_content,
                      target_widget, context, trigger_dub_chain_flag, base_filename_for_chain)
            return

        # Lấy các config parameters
        saved_style_name = self.cfg.get("imagen_last_style", "Mặc định (AI tự do)")
        style_prompt_fragment = None
        try:
            from ui.popups.imagen_settings import ImagenSettingsWindow
            style_prompt_fragment = ImagenSettingsWindow.IMAGEN_ART_STYLES.get(saved_style_name, "")
        except:
            style_prompt_fragment = ""

        # Tính toán min_duration_seconds từ UI
        min_duration_seconds = 0
        min_duration_setting = self.imagen_min_scene_duration_var.get()
        duration_map = {"15 giây": 15, "30 giây": 30, "1 phút": 60, "2 phút": 120, "3 phút": 180}
        for key, value in duration_map.items():
            if key in min_duration_setting:
                min_duration_seconds = value
                break
        
        # Tính tổng thời lượng kịch bản từ SRT (bê nguyên code từ file gốc)
        total_duration_seconds = 0.0
        if min_duration_seconds > 0 and formatted_srt_for_slideshow:
            # Tính tổng thời lượng kịch bản gốc
            total_duration_ms = 0
            original_timed_segments = self._parse_plain_text_to_srt_data(formatted_srt_for_slideshow)
            if original_timed_segments:
                total_duration_ms = original_timed_segments[-1]['end_ms'] - original_timed_segments[0]['start_ms']
            
            if total_duration_ms > 0:
                total_duration_seconds = total_duration_ms / 1000.0
                logging.info(f"{worker_log_prefix} Áp dụng giới hạn thời gian: Tối thiểu {min_duration_seconds}s/cảnh. Tổng thời lượng kịch bản: {total_duration_seconds:.2f}s.")
                
        # Gọi AI Service để xử lý
        try:
            gemini_response_text, error_message = self.master_app.ai_service.divide_scene_with_gemini(
                script_content=script_content,
                num_images=num_images,
                api_key=gemini_api_key,
                model_name=selected_model,
                character_sheet_text=character_sheet_text,
                formatted_srt_for_timing=formatted_srt_for_slideshow,
                min_scene_duration_seconds=min_duration_seconds,
                total_duration_seconds=total_duration_seconds,  # Truyền thêm tổng thời lượng đã tính
                auto_split_scenes=auto_split_scenes,
                art_style_name=saved_style_name,
                art_style_prompt=style_prompt_fragment,
                cfg=self.cfg,
                stop_event=lambda: self.master_app.stop_event.is_set(),
                max_retries=2,
                retry_delay_seconds=15.0
            )
            
            # Track API call nếu thành công
            if gemini_response_text:
                self.master_app._track_api_call(service_name="gemini_calls", units=1)
                
        except Exception as e:
            error_message = f"Lỗi nghiêm trọng khi sử dụng AI Service: {type(e).__name__} - {e}"
            logging.error(f"{worker_log_prefix} {error_message}", exc_info=True)
            gemini_response_text = None

        # Gọi hàm xử lý kết quả ở luồng chính
        self.master_app.after(0, self._handle_gemini_scene_division_result,
                   gemini_response_text,
                   error_message,
                   formatted_srt_for_slideshow,
                   script_content,
                   target_widget,
                   context,
                   trigger_dub_chain_flag,
                   base_filename_for_chain)   

    def _handle_gemini_scene_division_result(self, gemini_response_text, error_message,
                                             script_for_slideshow_timing, original_plain_text_for_dub,
                                             target_widget, context, trigger_dub_chain_flag,
                                             base_filename_for_chain):
        """
        (PHIÊN BẢN 7.0 - TÁI CẤU TRÚC & CỨU HỘ JSON)
        Xử lý kết quả từ Gemini, "cứu hộ" từng khối JSON hợp lệ, và xử lý lỗi nhất quán qua các hàm helper.
        """
        log_prefix = f"[HandleGeminiSceneResult_v7_Salvage]"

        # --- BƯỚC 1: XỬ LÝ LỖI MẠNG HOẶC KẾT QUẢ RỖNG ---
        if error_message or not gemini_response_text:
            error_to_show = error_message or "Gemini không tạo được prompt ảnh nào."
            if self._is_in_any_batch_queue():
                self._handle_batch_error_and_continue("Lỗi Chuỗi AI (Hàng loạt)", error_to_show)
                return

            else:
                self.is_gemini_processing = False
                messagebox.showerror("Lỗi Gemini Chia Cảnh", f"Đã xảy ra lỗi:\n\n{error_to_show}", parent=self)
                self._check_completion_and_shutdown()
            return

        try:
            # === BƯỚC 2: PARSE JSON MẠNH MẼ - "CỨU HỘ" TỪNG KHỐI RIÊNG LẺ ===
            logging.debug(f"{log_prefix} Phản hồi thô từ Gemini:\n{gemini_response_text}")

            potential_json_blocks = re.findall(r'\{.*?\}', gemini_response_text, re.DOTALL)
            if not potential_json_blocks:
                raise json.JSONDecodeError("Không tìm thấy khối văn bản nào có dạng {...} trong phản hồi.", gemini_response_text, 0)

            logging.info(f"{log_prefix} Tìm thấy {len(potential_json_blocks)} khối JSON tiềm năng. Bắt đầu parse...")
            
            scene_data_list, parsing_errors = [], []
            for block_str in potential_json_blocks:
                try:
                    cleaned_block_str = ''.join(c for c in block_str if c.isprintable() or c in '\n\r\t')
                    parsed_data = json.loads(cleaned_block_str)
                    if isinstance(parsed_data, dict):
                        scene_data_list.append(parsed_data)
                except json.JSONDecodeError as e:
                    parsing_errors.append(f"Lỗi parse khối: {e} | Khối: '{block_str}'")

            if parsing_errors:
                logging.warning(f"{log_prefix} Đã bỏ qua {len(parsing_errors)} khối JSON bị lỗi.")

            if not scene_data_list:
                raise ValueError("Không 'cứu hộ' được bất kỳ khối JSON hợp lệ nào.")

            # === BƯỚC 3: XÁC THỰC VÀ TRÍCH XUẤT DỮ LIỆU ===
            scene_scripts = [item.get("scene_script", "").strip() for item in scene_data_list]
            image_prompts = [item.get("image_prompt", "").strip() for item in scene_data_list]
            valid_pairs = [(s, p) for s, p in zip(scene_scripts, image_prompts) if s and p]
            
            if not valid_pairs:
                raise ValueError("Không có cặp scene/prompt hợp lệ nào trong các khối JSON đã parse.")

            final_scene_scripts = [pair[0] for pair in valid_pairs]
            final_image_prompts = [pair[1] for pair in valid_pairs]
            logging.info(f"{log_prefix} Đã 'cứu hộ' thành công {len(final_image_prompts)} cặp scene/prompt.")

            # === BƯỚC 4: TÍNH TOÁN THỜI LƯỢNG VÀ CHUẨN BỊ TẠO ẢNH ===
            image_durations_seconds = self._calculate_durations_for_scenes(final_scene_scripts)
            if not image_durations_seconds or len(image_durations_seconds) != len(final_image_prompts):
                raise ValueError("Không thể tính toán thời lượng hoặc số lượng không khớp.")

            logging.info(f"{log_prefix} Chuẩn bị gọi Imagen với {len(final_image_prompts)} prompt.")
            self.update_status(f"✅ Gemini đã chia cảnh & tính thời lượng. Chuẩn bị vẽ {len(final_image_prompts)} ảnh...")
            
            # Phần chuẩn bị payload và gọi bước tiếp theo giữ nguyên
            output_folder = self.cfg.get("imagen_last_output_folder", get_default_downloads_folder())
            safe_base_name = create_safe_filename(base_filename_for_chain, max_length=80) if base_filename_for_chain else f"ai_chain_{uuid.uuid4().hex[:6]}"
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_folder_name = f"Imagen_{safe_base_name}_{timestamp_str}"
            temp_imagen_output_folder = os.path.join(output_folder, new_folder_name)
            os.makedirs(temp_imagen_output_folder, exist_ok=True)

            payload_for_next_steps = {
                "image_prompts": final_image_prompts,
                "image_durations_seconds": image_durations_seconds,
                "original_plain_text_for_dub": original_plain_text_for_dub,
                "original_full_srt_for_hardsub": script_for_slideshow_timing 
            }

            self.master_app.after(100, self._handle_image_generation_and_slideshow,
                       payload_for_next_steps, temp_imagen_output_folder, target_widget,
                       context, trigger_dub_chain_flag, "Imagen 3", "Gemini",
                       base_filename_for_chain, temp_imagen_output_folder)

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            # === XỬ LÝ LỖI TẬP TRUNG ===
            # Tất cả các lỗi từ parse JSON, validation, tính toán thời lượng sẽ được xử lý ở đây
            error_to_show = f"Lỗi trong quá trình xử lý kết quả Gemini: {e}"
            if self._is_in_any_batch_queue():
                self._handle_batch_error_and_continue("Lỗi Xử lý Dữ liệu (Hàng loạt)", error_to_show, gemini_response_text)
            else:
                self.is_gemini_processing = False
                messagebox.showerror("Lỗi Xử lý Kết quả AI", error_to_show, parent=self)
                self._check_completion_and_shutdown()
            return               

# Hàm kích hoạt: Lấy text, lấy prompt
    def _trigger_gemini_script_processing(self, target_textbox_widget, context, user_prompt_from_popup):
        """
        Hàm kích hoạt: Lấy text, prompt, và bắt đầu luồng xử lý Gemini.
        ĐÃ SỬA: Tương tác với các nút AI hợp nhất.
        """
        self.stop_event.clear()
        logging.info(f"[GeminiTrigger:{context}] Đã xóa (clear) self.stop_event.")

        log_prefix = f"[GeminiTrigger:{context}]"
        logging.info(f"{log_prefix} Kích hoạt biên tập Gemini với prompt: '{user_prompt_from_popup[:50]}...'")

        gemini_key = self.gemini_key_var.get()
        if not gemini_key:
            messagebox.showerror("Thiếu API Key", "Vui lòng cấu hình Gemini API Key.", parent=self)
            return

        script_content = ""
        text_in_widget_before = ""
        if target_textbox_widget and target_textbox_widget.winfo_exists():
            text_in_widget_before = target_textbox_widget.get("1.0", "end-1c")
            temp_content = text_in_widget_before.strip()
            if not self._is_textbox_content_invalid_for_script(temp_content):
                script_content = temp_content

        # Lưu trạng thái để Hoàn tác (Undo) và Viết lại
        self.gemini_undo_buffer[context] = {"original_text": text_in_widget_before}
        self.last_gemini_parameters_used[context] = {
            "prompt": user_prompt_from_popup,
            "input_script_for_this_prompt": script_content
        }

        # Cập nhật UI
        self.is_gemini_processing = True
        self.start_time = time.time()
        self.update_status(f"💎 Gemini đang xử lý: '{user_prompt_from_popup[:30]}...'")
        self.update_time_realtime()

        # <<< SỬA Ở ĐÂY: Vô hiệu hóa các nút hợp nhất >>>
        if hasattr(self, 'ai_edit_button_sub_tab') and self.ai_edit_button_sub_tab.winfo_exists():
            self.ai_edit_button_sub_tab.configure(state="disabled", text="AI Đang chạy...")
        if hasattr(self, 'ai_edit_dub_script_button') and self.ai_edit_dub_script_button.winfo_exists():
            self.ai_edit_dub_script_button.configure(state="disabled", text="AI Đang chạy...")
        
        # Bắt đầu luồng
        thread = threading.Thread(
            target=self._execute_gemini_script_editing_thread,
            args=(script_content, user_prompt_from_popup, target_textbox_widget, context),
            daemon=True,
            name=f"GeminiEditThread_{context}"
        )
        thread.start()      


    def _execute_gemini_script_editing_thread(self, script_content, user_instruction, target_widget, context):
        """
        [REFACTORED] Hàm worker (chạy trong luồng): Gọi API Gemini và xử lý phản hồi.
        Sử dụng AIService để xử lý business logic, chỉ xử lý UI callbacks ở đây.
        """
        log_prefix = f"[GeminiExec_v2:{context}]"
        logging.info(f"{log_prefix} Bắt đầu xử lý kịch bản với Gemini...")

        # Lấy API key
        gemini_api_key = self.gemini_key_var.get()
        if not gemini_api_key:
            error_message = "Lỗi: Vui lòng nhập Gemini API Key."
            self.master_app.after(0, self._handle_gemini_script_editing_result, None, error_message, target_widget, context)
            return

        # Gọi AI Service để xử lý
        try:
            processed_script, error_message = self.master_app.ai_service.process_script_with_gemini(
                script_content=script_content,
                user_instruction=user_instruction,
                api_key=gemini_api_key,
                model_name=None,  # Auto-select
                stop_event=lambda: self.master_app.stop_event.is_set(),
                max_retries=3,
                retry_delay_seconds=20
            )
            
        except Exception as e:
            error_message = f"Lỗi nghiêm trọng khi sử dụng AI Service: {type(e).__name__} - {e}"
            logging.error(f"{log_prefix} {error_message}", exc_info=True)
            processed_script = None

        # Gọi hàm callback trên luồng chính để cập nhật UI
        self.master_app.after(0, self._handle_gemini_script_editing_result, processed_script, error_message, target_widget, context)
        
 
    def _handle_gemini_script_editing_result(self, processed_script, error_message, target_widget, context):
        """
        Hàm callback: Cập nhật UI sau khi có kết quả từ Gemini.
        ĐÃ SỬA: Tương tác với các nút AI hợp nhất.
        """
        log_prefix = f"[GeminiResult:{context}]"
        self.is_gemini_processing = False
        
        # Luôn kiểm tra trạng thái kích hoạt của app và key trước khi bật lại nút
        is_app_active = self._is_app_fully_activated()
        
        if is_app_active:
            if hasattr(self, 'ai_edit_button_sub_tab') and self.ai_edit_button_sub_tab.winfo_exists():
                self.ai_edit_button_sub_tab.configure(state="normal", text="✨ Biên tập (AI)")
            if hasattr(self, 'ai_edit_dub_script_button') and self.ai_edit_dub_script_button.winfo_exists():
                self.ai_edit_dub_script_button.configure(state="normal", text="✨ Biên tập (AI)")

        # Xử lý lỗi và cập nhật textbox
        if error_message:
            logging.error(f"{log_prefix} Xử lý thất bại: {error_message}")
            self.update_status(f"❌ Lỗi Gemini: {error_message[:60]}...")
            messagebox.showerror("Lỗi Gemini API", error_message, parent=self)
        elif processed_script is not None:
            logging.info(f"{log_prefix} Xử lý thành công. Cập nhật textbox.")
            if target_widget.winfo_exists():
                target_widget.configure(state="normal")
                target_widget.delete("1.0", "end")
                target_widget.insert("1.0", processed_script)
            self.update_status("✅ Gemini đã biên tập xong kịch bản.")
            messagebox.showinfo("Hoàn thành", "Gemini đã xử lý và cập nhật nội dung kịch bản.", parent=self)
        else:
            logging.warning(f"{log_prefix} Xử lý không thành công nhưng không có lỗi cụ thể.")
            self.update_status("⚠️ Lỗi không xác định từ Gemini.")
            messagebox.showwarning("Lỗi", "Gemini không trả về kết quả.", parent=self)

        # Reset timer nếu không có tác vụ nào khác đang chạy
        self._check_completion_and_shutdown()        



#---------------------------------------------------------------------------------------
#Hàm này sẽ được gọi bởi nút "Bắt đầu Xử lý GPT trong popup.
    def _trigger_gpt_script_processing_from_popup(self, script_content_to_process_param, user_prompt, selected_model,
                                                  target_textbox_widget, calling_button_context,
                                                  trigger_dalle_chain_flag=False,
                                                  trigger_dub_chain_flag=False,
                                                  base_filename_for_chain=None): # <<< THÊM VÀO ĐÂY
        log_prefix = f"[GPTScriptTrigger:{calling_button_context}]"
        self.stop_event.clear()

        current_text_in_widget_at_trigger = ""
        if target_textbox_widget and target_textbox_widget.winfo_exists():
            current_text_in_widget_at_trigger = target_textbox_widget.get("1.0", "end-1c").strip()

        logging.debug(f"{log_prefix} DEBUG_TRIGGER: current_text_in_widget_at_trigger (stripped) = '{current_text_in_widget_at_trigger}'")

        actual_script_content_for_gpt = ""
        action_type_log = "tạo mới"

        is_placeholder_content = False
        if calling_button_context == "subtitle":
            defined_placeholder = getattr(self, 'subtitle_textbox_placeholder', "###MISSING_SUB_PLACEHOLDER###").strip()
            logging.debug(f"{log_prefix} DEBUG_TRIGGER (subtitle): Comparing with placeholder: '{defined_placeholder}'")
            if current_text_in_widget_at_trigger == defined_placeholder or not current_text_in_widget_at_trigger.strip(): # Thêm kiểm tra rỗng
                is_placeholder_content = True
                logging.debug(f"{log_prefix} Phát hiện placeholder hoặc rỗng trong subtitle_textbox.")
        elif calling_button_context == "dubbing":
            if self._is_textbox_content_invalid_for_script(current_text_in_widget_at_trigger):
                is_placeholder_content = True
                logging.debug(f"{log_prefix} Phát hiện placeholder/nội dung không hợp lệ trong dub_script_textbox (theo _is_textbox_content_invalid_for_script).")

        if not is_placeholder_content and current_text_in_widget_at_trigger:
            actual_script_content_for_gpt = current_text_in_widget_at_trigger
            action_type_log = "biên tập"
        else:
            actual_script_content_for_gpt = ""
            action_type_log = "tạo mới"

        logging.info(f"{log_prefix} Kích hoạt {action_type_log} script. Model: {selected_model}, Prompt: '{user_prompt[:50]}...'")
        logging.debug(f"{log_prefix} Nội dung thực tế sẽ gửi cho GPT (actual_script_content_for_gpt) là: '{actual_script_content_for_gpt[:100].replace(chr(10),' ')}...'")

        text_in_widget_before_gpt = ""
        if target_textbox_widget and target_textbox_widget.winfo_exists():
            text_in_widget_before_gpt = target_textbox_widget.get("1.0", "end-1c")

        self.gpt_undo_buffer[calling_button_context] = {
            "original_text": text_in_widget_before_gpt,
            "target_widget": target_textbox_widget
        }
        logging.info(f"{log_prefix} Đã lưu trạng thái Undo cho context '{calling_button_context}'.")

        self.last_gpt_parameters_used[calling_button_context] = {
            "prompt": user_prompt,
            "model": selected_model,
            "input_script_for_this_prompt": actual_script_content_for_gpt
        }
        logging.info(f"{log_prefix} Đã lưu tham số (prompt, model, input_script) cho context '{calling_button_context}' để Rewrite.")
        # <<< CODE LƯU PROMPT VÀO CONFIG >>>
        config_key_for_prompt = f"last_used_gpt_prompt_{calling_button_context}"
        self.master_app.cfg[config_key_for_prompt] = user_prompt # Lưu prompt vào self.cfg
        logging.info(f"{log_prefix} Đã cập nhật self.cfg['{config_key_for_prompt}'] với prompt: '{user_prompt[:50]}...'")
        self.master_app.save_current_config() # Gọi hàm lưu toàn bộ config ra file JSON

        # <<< SỬA Ở ĐÂY: Vô hiệu hóa các nút hợp nhất >>>
        if hasattr(self, 'ai_edit_button_sub_tab') and self.ai_edit_button_sub_tab.winfo_exists():
            self.ai_edit_button_sub_tab.configure(state="disabled", text="AI Đang chạy...")
        if hasattr(self, 'ai_edit_dub_script_button') and self.ai_edit_dub_script_button.winfo_exists():
            self.ai_edit_dub_script_button.configure(state="disabled", text="AI Đang chạy...")

        self.is_gpt_processing_script = True 
        self.master_app.start_time = time.time()      
        self.master_app._set_subtitle_tab_ui_state(subbing_active=False)        
        status_message_gpt_starts = f"🤖 GPT ({selected_model}) đang xử lý..."
        self.master_app.update_status(status_message_gpt_starts)
        self.master_app.update_time_realtime()

        if target_textbox_widget and target_textbox_widget.winfo_exists():
            target_textbox_widget.configure(state="disabled")
            if calling_button_context == "subtitle":
                self.allow_edit_sub = False

        # Tạo và bắt đầu luồng
        thread = threading.Thread(
            target=self._execute_gpt_script_editing_thread,
            args=(actual_script_content_for_gpt, user_prompt, selected_model,
                  target_textbox_widget, calling_button_context,
                  trigger_dalle_chain_flag,
                  trigger_dub_chain_flag,
                  base_filename_for_chain),
            daemon=True,
            name=f"GPTScriptEditThread_{selected_model}_{calling_button_context}"
        )
        thread.start()        


# Hàm logic chính cho chức năng biên tập GPT
    def _execute_gpt_script_editing_thread(self, script_content_to_process, user_instruction, selected_model,
                                           target_textbox_widget, calling_button_context,
                                           trigger_dalle_chain_flag=False,
                                           trigger_dub_chain_flag=False,
                                           base_filename_for_chain=None): 
        """
        [REFACTORED] Hàm logic chính cho chức năng biên tập GPT.
        Sử dụng AIService để xử lý business logic, chỉ xử lý UI callbacks ở đây.
        """
        log_prefix = f"[GPTScriptExec:{selected_model}:{calling_button_context}]"

        action_type_log = "tạo mới kịch bản" if not script_content_to_process.strip() else "biên tập kịch bản hiện có"
        logging.info(f"{log_prefix} Bắt đầu {action_type_log}. Instruction: '{user_instruction[:50]}...'")
        
        # Lấy API key
        api_key = self.openai_key_var.get()
        if not api_key:
            error_message_detail = "Lỗi cấu hình: OpenAI API Key bị thiếu. Vui lòng kiểm tra trong 'Cài đặt API Keys'."
            logging.error(f"{log_prefix} {error_message_detail}")
            self.master_app.after(0, self._handle_gpt_script_editing_result, None, error_message_detail, 
                      target_textbox_widget, calling_button_context,
                      trigger_dalle_chain_flag, trigger_dub_chain_flag, base_filename_for_chain)
            return

        # Gọi AI Service để xử lý
        try:
            processed_script_content, error_message_detail = self.master_app.ai_service.process_script_with_gpt(
                script_content=script_content_to_process,
                user_instruction=user_instruction,
                api_key=api_key,
                model_name=selected_model,
                stop_event=lambda: self.stop_event.is_set()
            )
            
        except Exception as e:
            error_message_detail = f"Lỗi nghiêm trọng khi sử dụng AI Service: {type(e).__name__} - {e}"
            logging.error(f"{log_prefix} {error_message_detail}", exc_info=True)
            processed_script_content = None

        # Gọi hàm callback trên luồng chính để cập nhật UI
        self.master_app.after(0, self._handle_gpt_script_editing_result,
                   processed_script_content,
                   error_message_detail,
                   target_textbox_widget,
                   calling_button_context,
                   trigger_dalle_chain_flag,
                   trigger_dub_chain_flag,
                   base_filename_for_chain) # <<< THÊM VÀO ĐÂY        


#  Hàm mới để yêu cầu GPT chia kịch bản và tạo DALL-E prompts
    def _execute_gpt_scene_division_thread(self,
                                           script_content_for_gpt_analysis, # Script để GPT phân tích (có thể là SRT)
                                           num_images_to_generate,
                                           selected_gpt_model,
                                           original_plain_gpt_text_for_dub, # Text thuần gốc từ GPT
                                           original_gpt_context,
                                           original_target_widget,
                                           original_trigger_dub_chain_flag):
        """
        [REFACTORED] Chạy trong luồng: Gọi GPT để chia kịch bản thành các phân cảnh và tạo ra các DALL-E prompt tương ứng.
        Sử dụng AIService để xử lý business logic, chỉ xử lý UI callbacks ở đây.
        original_plain_gpt_text_for_dub là text thuần gốc từ GPT, được truyền qua để dùng cho bước thuyết minh sau này.
        """
        worker_log_prefix = f"[GPT_SceneDivision_{selected_gpt_model}]"
        logging.info(f"{worker_log_prefix} Bắt đầu chia kịch bản (input: '{script_content_for_gpt_analysis[:50].replace(chr(10),' ')}...') và tạo {num_images_to_generate} DALL-E prompts.")
        logging.info(f"{worker_log_prefix}   Plain text gốc đi kèm (cho dub): '{original_plain_gpt_text_for_dub[:50].replace(chr(10),' ')}...'")

        # Lấy API key
        api_key = self.openai_key_var.get()
        if not api_key:
            error_message_division = "Lỗi cấu hình: OpenAI API Key bị thiếu."
            self.master_app.after(0, self._handle_gpt_scene_division_result,
                      None, error_message_division, script_content_for_gpt_analysis,
                      original_plain_gpt_text_for_dub, original_gpt_context,
                      original_target_widget, original_trigger_dub_chain_flag)
            return

        # Gọi AI Service để xử lý
        try:
            list_of_dalle_prompts, error_message_division = self.master_app.ai_service.divide_scene_with_gpt(
                script_content=script_content_for_gpt_analysis,
                num_images=num_images_to_generate,
                api_key=api_key,
                model_name=selected_gpt_model,
                character_sheet_text="",  # GPT scene division doesn't use character sheet
                stop_event=lambda: self.stop_event.is_set()
            )
            
            if error_message_division and not list_of_dalle_prompts:
                # Có lỗi và không có kết quả nào
                logging.error(f"{worker_log_prefix} {error_message_division}")
            elif list_of_dalle_prompts:
                # Có kết quả (có thể ít hơn số lượng yêu cầu)
                if len(list_of_dalle_prompts) != num_images_to_generate:
                    logging.warning(f"{worker_log_prefix} GPT trả về {len(list_of_dalle_prompts)} prompts, nhưng yêu cầu là {num_images_to_generate}. Sẽ cố gắng sử dụng các prompt có được.")
                logging.info(f"{worker_log_prefix} Đã trích xuất được {len(list_of_dalle_prompts)} DALL-E prompt(s).")
                
        except Exception as e:
            error_message_division = f"Lỗi nghiêm trọng khi sử dụng AI Service: {type(e).__name__} - {e}"
            logging.error(f"{worker_log_prefix} {error_message_division}", exc_info=True)
            list_of_dalle_prompts = None

        finally:
            # Gọi hàm callback trên luồng chính để xử lý kết quả
            # Truyền original_plain_gpt_text_for_dub thay cho original_processed_script cũ
            # và script_content_for_gpt_analysis (là script đã dùng để chia cảnh)
            self.master_app.after(0, self._handle_gpt_scene_division_result, #
                       list_of_dalle_prompts if list_of_dalle_prompts else None,  #
                       error_message_division, #
                       script_content_for_gpt_analysis,    # Script đã dùng để chia cảnh (có thể là SRT hoặc plain text)
                       original_plain_gpt_text_for_dub,    # Text thuần gốc từ GPT
                       original_gpt_context,  #
                       original_target_widget,  #
                       original_trigger_dub_chain_flag) #
            logging.debug(f"{worker_log_prefix} Đã lên lịch callback _handle_gpt_scene_division_result.") #                   


# Hàm Gọi API của GPT với một prompt yêu cầu GPT tóm tắt văn bản đó và tạo ra một prompt DALL-E duy nhất, tổng quát, an toàn cho toàn bộ kịch bản.
    def _execute_gpt_single_summary_prompt_thread(self,
                                                  original_plain_script_text, # Text thuần để GPT tóm tắt
                                                  selected_gpt_model,
                                                  # Các tham số này được truyền thẳng cho callback
                                                  script_for_slideshow_timing_callback, # Là script_for_scene_division từ hàm gọi
                                                  original_plain_gpt_text_for_dub_callback, # Là original_plain_gpt_text_for_dub từ hàm gọi
                                                  original_gpt_context_callback,
                                                  original_target_widget_callback,
                                                  original_trigger_dub_chain_flag_callback):
        """
        Chạy trong luồng: Gọi GPT để tóm tắt kịch bản và tạo MỘT prompt DALL-E chung.
        """
        worker_log_prefix = f"[GPTSingleSummaryPrompt_{selected_gpt_model}]"
        logging.info(f"{worker_log_prefix} Bắt đầu tóm tắt và tạo 1 prompt DALL-E chung từ plain text (dài {len(original_plain_script_text)} chars): '{original_plain_script_text[:50].replace(chr(10),' ')}...'")

        single_dalle_prompt = None
        error_message_summary = None

        try:
            if not HAS_OPENAI or OpenAI is None:
                error_message_summary = "Lỗi nghiêm trọng: Thư viện OpenAI không khả dụng (cho tóm tắt)."
                logging.critical(f"{worker_log_prefix} {error_message_summary}")
                # Callback sẽ được gọi trong finally
                return

            api_key = self.openai_key_var.get()
            if not api_key:
                error_message_summary = "Lỗi cấu hình: OpenAI API Key bị thiếu (cho tóm tắt)."
                logging.error(f"{worker_log_prefix} {error_message_summary}")
                return # Callback sẽ được gọi trong finally

            client = OpenAI(api_key=api_key, timeout=180.0) # Timeout 3 phút

            system_message_content = (
                "Bạn là một trợ lý AI xuất sắc trong việc tóm tắt nội dung văn bản và tạo mô tả hình ảnh an toàn, tổng quát, phù hợp với mọi đối tượng, với mục tiêu tạo ra hình ảnh chân thực và sắc nét. "
                "Nhiệm vụ của bạn là đọc hiểu toàn bộ kịch bản được cung cấp, tóm tắt ý chính của nó, và sau đó tạo ra MỘT prompt DALL-E DUY NHẤT (bằng tiếng Anh, ngắn gọn, súc tích, tối đa khoảng 40-60 từ). "
                "Prompt DALL-E này phải mang tính đại diện cho toàn bộ câu chuyện hoặc chủ đề chính của kịch bản, phù hợp để tạo một hình ảnh minh họa chung. "

                # --- HƯỚNG DẪN PHONG CÁCH MỚI ---
                "QUAN TRỌNG VỀ PHONG CÁCH ẢNH: "
                "1. Ưu tiên phong cách TẢ THỰC, CHI TIẾT CAO, như ảnh chụp chất lượng cao hoặc render 3D điện ảnh. Hình ảnh cần SẮC NÉT, RÕ RÀNG, với nhiều chi tiết tinh xảo. "
                "2. TRỪ KHI KỊCH BẢN GỐC YÊU CẦU RÕ RÀNG một phong cách khác (ví dụ: 'hoạt hình', 'anime', 'tranh vẽ'), hãy MẶC ĐỊNH hướng tới phong cách CHÂN THỰC 3D. Hạn chế tối đa việc tạo ra các prompt gợi ý tranh vẽ 2D, hoạt hình, hoặc anime nếu không được yêu cầu cụ thể. "
                "3. Để đạt được điều này, hãy cân nhắc sử dụng các từ khóa mô tả phong cách trong DALL-E prompt (bằng tiếng Anh) như: 'photorealistic', 'hyperrealistic', 'highly detailed', 'sharp focus', '3D render', 'cinematic lighting', 'Unreal Engine 5 style', 'V-Ray render', 'octane render', 'detailed skin texture', 'intricate details', 'professional photography', '8K resolution' (DALL-E sẽ hiểu ý đồ về độ chi tiết). "
                # --- KẾT THÚC HƯỚNG DẪN PHONG CÁCH MỚI ---

                "QUAN TRỌNG VỀ AN TOÀN NỘI DUNG: Prompt DALL-E phải TUÂN THỦ NGHIÊM NGẶT chính sách nội dung của OpenAI. "
                "TRÁNH TUYỆT ĐỐI các mô tả có thể bị coi là bạo lực, người lớn, thù địch, tự hại, hoặc lừa đảo. Ưu tiên sự an toàn và tích cực. "
                "Không mô tả các hành động cụ thể có thể bị cấm. Tập trung vào cảm xúc, bối cảnh tổng thể, và các yếu tố hình ảnh trung tính. "
                "Nếu kịch bản gốc không phải tiếng Anh, hãy dịch các yếu tố hình ảnh quan trọng sang tiếng Anh cho prompt DALL-E, đồng thời đảm bảo tính an toàn và phong cách chân thực của nội dung đã dịch. "
                "Chỉ trả về duy nhất prompt DALL-E đó, không có bất kỳ giải thích hay định dạng nào khác. "
                "ĐẶC BIỆT LƯU Ý: Các prompt DALL-E mà bạn tạo ra phải hướng dẫn DALL-E KHÔNG ĐƯỢC VIẾT BẤT KỲ CHỮ, KÝ TỰ, HAY VĂN BẢN nào lên hình ảnh được tạo ra. Hình ảnh cuối cùng phải hoàn toàn không có chữ. Nếu cần, hãy thêm các cụm từ như 'no text', 'text-free', 'image only, no writing', 'avoid typography', 'typography-free' vào cuối mỗi DALL-E prompt để nhấn mạnh yêu cầu này."
            )
            
            user_message_content = (
                f"Dưới đây là toàn bộ kịch bản cần xử lý:\n\n"
                f"```script\n{original_plain_script_text}\n```\n\n"
                f"Dựa vào kịch bản trên, hãy tóm tắt ý chính và tạo ra MỘT prompt DALL-E DUY NHẤT (bằng tiếng Anh, an toàn, tổng quát) để minh họa cho toàn bộ kịch bản này. "
                f"Chỉ trả về duy nhất prompt DALL-E đó."
            )
            
            logging.info(f"{worker_log_prefix} Đang gửi yêu cầu đến model '{selected_gpt_model}' để tạo 1 prompt DALL-E tóm tắt...")
            
            response = client.chat.completions.create(
                model=selected_gpt_model,
                messages=[
                    {"role": "system", "content": system_message_content},
                    {"role": "user", "content": user_message_content}
                ],
                temperature=0.3, # Nhiệt độ thấp hơn để prompt ít bay bổng, tập trung hơn
            )
            
            gpt_response_content = response.choices[0].message.content.strip()
            # Loại bỏ dấu ngoặc kép hoặc các ký tự không mong muốn nếu có
            cleaned_prompt = gpt_response_content.replace('"', '').replace("'", "").strip()

            if cleaned_prompt:
                single_dalle_prompt = cleaned_prompt
                logging.info(f"{worker_log_prefix} GPT đã tạo prompt DALL-E tóm tắt: '{single_dalle_prompt}'")
            else:
                error_message_summary = "GPT không trả về prompt DALL-E tóm tắt nào hoặc prompt rỗng."
                logging.warning(f"{worker_log_prefix} {error_message_summary}. Phản hồi gốc: {gpt_response_content}")

        except RateLimitError as e_rate:
            error_message_summary = f"Lỗi Giới hạn Yêu cầu (Rate Limit) từ OpenAI khi tạo prompt tóm tắt. Chi tiết: {str(e_rate)}"
            logging.warning(f"{worker_log_prefix} {error_message_summary}")
        except AuthenticationError as e_auth:
            error_message_summary = f"Lỗi Xác thực OpenAI khi tạo prompt tóm tắt: API Key không hợp lệ/hết hạn. Chi tiết: {str(e_auth)}"
            logging.error(f"{worker_log_prefix} {error_message_summary}")
        except APIConnectionError as e_conn:
            error_message_summary = f"Lỗi Kết nối đến server OpenAI khi tạo prompt tóm tắt. Chi tiết: {str(e_conn)}"
            logging.error(f"{worker_log_prefix} {error_message_summary}")
        except APITimeoutError as e_timeout:
            error_message_summary = f"Lỗi Timeout với OpenAI khi tạo prompt tóm tắt. Chi tiết: {str(e_timeout)}"
            logging.error(f"{worker_log_prefix} {error_message_summary}")
        except APIStatusError as e_status:
            status_code = e_status.status_code if hasattr(e_status, 'status_code') else 'N/A'
            err_msg_from_api = e_status.message if hasattr(e_status, 'message') else str(e_status)
            error_message_summary = f"Lỗi từ API OpenAI (Mã trạng thái: {status_code}) khi tạo prompt tóm tắt: {err_msg_from_api}"
            logging.error(f"{worker_log_prefix} {error_message_summary}")
        except Exception as e_general:
            error_message_summary = f"Lỗi không mong muốn khi GPT tạo prompt tóm tắt: {type(e_general).__name__} - {str(e_general)}"
            logging.error(f"{worker_log_prefix} {error_message_summary}", exc_info=True)

        finally:
            prompts_for_callback = [single_dalle_prompt] if single_dalle_prompt else []
            # Gọi lại hàm _handle_gpt_scene_division_result với danh sách chỉ chứa 1 prompt (hoặc rỗng nếu lỗi)
            self.master_app.after(0, self._handle_gpt_scene_division_result,
                       prompts_for_callback,
                       error_message_summary,
                       script_for_slideshow_timing_callback,    # Truyền lại script dùng cho slideshow timing
                       original_plain_gpt_text_for_dub_callback, # Truyền lại plain text gốc
                       original_gpt_context_callback,
                       original_target_widget_callback,
                       original_trigger_dub_chain_flag_callback)
            logging.debug(f"{worker_log_prefix} Đã lên lịch callback _handle_gpt_scene_division_result (từ summary thread).")


# Thêm hàm này vào lớp SubtitleApp
    def _handle_gpt_scene_division_result(self, 
                                          list_of_dalle_prompts, 
                                          error_message,
                                          script_for_slideshow_timing,        # << Đổi tên cho rõ (đây là script_content_for_gpt_analysis từ bước trước)
                                          original_plain_gpt_text_for_dub,  # << THAM SỐ MỚI
                                          original_gpt_context, 
                                          original_target_widget, 
                                          original_trigger_dub_chain_flag):
        log_prefix_callback = f"[GPT_SceneDivision_Result:{original_gpt_context}]"
        logging.info(f"{log_prefix_callback} Nhận kết quả chia cảnh. Số prompts: {len(list_of_dalle_prompts) if list_of_dalle_prompts else 0}, Lỗi: {error_message}")
        logging.info(f"{log_prefix_callback}   script_for_slideshow_timing (có thể là SRT, dài {len(script_for_slideshow_timing)} chars): '{script_for_slideshow_timing[:50].replace(chr(10),' ')}...'")
        logging.info(f"{log_prefix_callback}   original_plain_gpt_text_for_dub (dài {len(original_plain_gpt_text_for_dub)} chars): '{original_plain_gpt_text_for_dub[:50].replace(chr(10),' ')}...'")

        if error_message or not list_of_dalle_prompts:
            # ... (phần xử lý lỗi của bạn giữ nguyên) ...
            final_error = error_message or "GPT không tạo được DALL-E prompt nào."
            logging.error(f"{log_prefix_callback} {final_error}")
            self.update_status(f"❌ Lỗi GPT (chia cảnh): {final_error[:60]}...")
            messagebox.showerror(f"Lỗi GPT Chia Cảnh ({original_gpt_context.capitalize()})",
                                 f"Đã xảy ra lỗi khi yêu cầu GPT chia cảnh và tạo DALL-E prompts:\n\n{final_error}",
                                 parent=self)
            # Reset lại các nút liên quan 
            button_to_enable = None; button_text_default = "🤖 GPT"
            if original_gpt_context == "subtitle":
                if hasattr(self, 'gpt_edit_script_button_main_tab'): button_to_enable = self.gpt_edit_script_button_main_tab
            elif original_gpt_context == "dubbing":
                if hasattr(self, 'gpt_edit_dub_script_button'): button_to_enable = self.gpt_edit_dub_script_button
            if button_to_enable and button_to_enable.winfo_exists():
                button_to_enable.configure(state=ctk.NORMAL, text=button_text_default)
            if hasattr(self, 'is_gpt_processing_script'): self.is_gpt_processing_script = False
            return

        logging.info(f"{log_prefix_callback} Thành công! Có {len(list_of_dalle_prompts)} DALL-E prompts. Chuẩn bị gọi DALL-E...")
        self.update_status(f"✅ GPT đã tạo {len(list_of_dalle_prompts)} prompt ảnh. Chuẩn bị vẽ...")

        # Sửa hàm _start_gpt_dalle_slideshow_chain_multiple_prompts để nhận thêm original_plain_gpt_text_for_dub
        self.master_app.after(100, self._start_gpt_dalle_slideshow_chain_multiple_prompts,
                   list_of_dalle_prompts,
                   script_for_slideshow_timing,       # Dùng cho timing slideshow
                   original_plain_gpt_text_for_dub, 
                   None,
                   original_gpt_context,
                   original_target_widget,
                   original_trigger_dub_chain_flag)            


# Hàm được gọi sau khi biên tập GPT hoàn thành
    def _handle_gpt_script_editing_result(self, processed_script, error_message,
                                          target_textbox_widget, calling_button_context,
                                          trigger_dalle_chain_flag=False,
                                          trigger_dub_chain_flag=False,
                                          base_filename_for_chain=None):
        log_prefix = f"[GPTScriptResult:{calling_button_context}]"
        self.is_gpt_processing_script = False 

        # Chỉ bật lại nút nếu không có chuỗi DALL-E tiếp theo
        if not trigger_dalle_chain_flag:
            is_app_active = self._is_app_fully_activated()
            
            if is_app_active:
                if hasattr(self, 'ai_edit_button_sub_tab') and self.ai_edit_button_sub_tab.winfo_exists():
                    self.ai_edit_button_sub_tab.configure(state="normal", text="✨ Biên tập (AI)")
                if hasattr(self, 'ai_edit_dub_script_button') and self.ai_edit_dub_script_button.winfo_exists():
                    self.ai_edit_dub_script_button.configure(state="normal", text="✨ Biên tập (AI)")
        # Cập nhật log này để bao gồm cả cờ mới
        logging.info(f"{log_prefix} GIÁ TRỊ CỦA trigger_dalle_chain_flag LÀ: {trigger_dalle_chain_flag}, trigger_dub_chain_flag LÀ: {trigger_dub_chain_flag}")

        # Xử lý trường hợp người dùng chủ động dừng
        if error_message and "Đã dừng bởi người dùng" in error_message:
            self.is_gpt_processing_script = False # Đặt lại cờ
            # Cập nhật trạng thái
            self.update_status(f"🛑 Tác vụ GPT ({calling_button_context}) đã được dừng.")
            # Đảm bảo textbox có thể tương tác lại được
            if target_textbox_widget and target_textbox_widget.winfo_exists():
                target_textbox_widget.configure(state="normal")
            # Đảm bảo các nút được reset về trạng thái chờ
            if hasattr(self, '_set_subtitle_tab_ui_state'):
                self._set_subtitle_tab_ui_state(subbing_active=False)
            logging.info(f"{log_prefix} Đã xử lý xong yêu cầu dừng của người dùng.")
            return # Thoát khỏi hàm sớm

        self.is_gpt_processing_script = False 

        button_to_enable = None
        button_text_default = "🤖 GPT"
        if calling_button_context == "subtitle":
            if hasattr(self, 'gpt_edit_script_button_main_tab'):
                button_to_enable = self.gpt_edit_script_button_main_tab
        elif calling_button_context == "dubbing":
            if hasattr(self, 'gpt_edit_dub_script_button'):
                button_to_enable = self.gpt_edit_dub_script_button
        
        if button_to_enable and button_to_enable.winfo_exists():
            button_to_enable.configure(state=ctk.NORMAL, text=button_text_default)

        if target_textbox_widget and target_textbox_widget.winfo_exists():
            target_textbox_widget.configure(state="normal")

        if error_message:
            logging.error(f"{log_prefix} Lỗi từ GPT: {error_message}")
            self.update_status(f"❌ Lỗi GPT ({calling_button_context}): {error_message[:50]}...")
            messagebox.showerror(f"Lỗi Xử Lý GPT ({calling_button_context.capitalize()})",
                                 f"Đã xảy ra lỗi khi yêu cầu GPT xử lý kịch bản:\n\n{error_message}\n\nNội dung kịch bản chưa được thay đổi.",
                                 parent=self)
            # Đảm bảo textbox ở trạng thái 'normal' ngay cả khi có lỗi để người dùng có thể sửa
            if target_textbox_widget and target_textbox_widget.winfo_exists():
                 target_textbox_widget.configure(state="normal")
            return 

        elif processed_script is not None: 
            logging.info(f"{log_prefix} GPT xử lý thành công. Context: {calling_button_context}.")
            
            final_script_for_display = processed_script 
            srt_data_content_for_dub_update = None # Sẽ dùng cho context "dubbing"

            if calling_button_context == "subtitle":
                original_plain_gpt_text = processed_script  # Lưu lại text thuần túy gốc từ GPT
                script_for_chain_timing = original_plain_gpt_text # Mặc định nếu không có gì thay đổi
                final_script_for_display_sub_tab = original_plain_gpt_text # Cho textbox tab Subtitle

                # Kiểm tra checkbox "Tự động định dạng Text sang SRT" của tab Subtitle
                subtitle_textbox = getattr(self.subtitle_view_frame, 'subtitle_textbox', None) if hasattr(self, 'subtitle_view_frame') else None
                auto_format_sub_on = (hasattr(self, 'auto_format_plain_text_to_srt_var') and
                                     self.auto_format_plain_text_to_srt_var.get() and
                                     target_textbox_widget == subtitle_textbox)

                if auto_format_sub_on:
                    logging.info(f"{log_prefix} Checkbox 'AutoFormat SRT (Subtitle)' BẬT. Tạo SRT theo rule Subtitle.")
                    gpt_split_cfg_sub = { # Cấu hình của tab Subtitle
                        "split_enabled": self.enable_split_var.get(),
                        "mode": self.split_mode_var.get(),
                        "max_chars": safe_int(self.max_chars_var.get(), 90),
                        "max_lines": safe_int(self.max_lines_var.get(), 1),
                        "DEFAULT_CPS_FOR_TIMING": safe_int(self.sub_cps_for_timing_var.get(), 17),
                        "PAUSE_BETWEEN_SEGMENTS_MS_FOR_TIMING": 1, 
                        "ABSOLUTE_MIN_DURATION_PER_CHUNK_MS": self.min_duration_per_segment_ms
                    } # Đảm bảo dấu } ở đúng vị trí
                    gpt_srt_data_content_sub = self._parse_plain_text_to_srt_data(
                        original_plain_gpt_text,
                        force_plain_text_processing=True,
                        split_config_override=gpt_split_cfg_sub
                    )
                    if gpt_srt_data_content_sub:
                        srt_output_from_sub_rules = format_srt_data_to_string(gpt_srt_data_content_sub)
                        final_script_for_display_sub_tab = srt_output_from_sub_rules # Hiển thị SRT trên tab Sub
                        script_for_chain_timing = srt_output_from_sub_rules       # Dùng SRT này cho chain timing
                        logging.info(f"{log_prefix} Đã tạo SRT theo rule Subtitle. final_script_for_display_sub_tab và script_for_chain_timing được cập nhật.")
                    else:
                        logging.warning(f"{log_prefix} Không tạo được SRT từ rule Subtitle. Giữ nguyên plain text cho hiển thị và chain timing.")
                
                # Nếu chuỗi DALL-E/Dub được kích hoạt VÀ "AutoFormat SRT (Subtitle)" TẮT,
                # chúng ta vẫn cần tạo một SRT cơ bản cho chain timing.
                elif trigger_dalle_chain_flag and not auto_format_sub_on: # Dùng elif ở đây là đúng
                    logging.info(f"{log_prefix} Chain DALL-E/Dub kích hoạt và 'AutoFormat SRT (Subtitle)' TẮT. Tạo SRT cơ bản cho chain timing từ plain text gốc.")
                    basic_timing_config = {
                        "split_enabled": True, 
                        "mode": "sentence",    
                        "max_chars": 90,       
                        "max_lines": 1,        
                        "DEFAULT_CPS_FOR_TIMING": safe_int(self.sub_cps_for_timing_var.get(), 17),
                        "PAUSE_BETWEEN_SEGMENTS_MS_FOR_TIMING": 1, # Đảm bảo dấu phẩy
                        "ABSOLUTE_MIN_DURATION_PER_CHUNK_MS": self.min_duration_per_segment_ms
                    } # Đảm bảo dấu }
                    basic_srt_data_for_chain = self._parse_plain_text_to_srt_data(
                        original_plain_gpt_text,
                        force_plain_text_processing=True,
                        split_config_override=basic_timing_config
                    )
                    if basic_srt_data_for_chain:
                        script_for_chain_timing = format_srt_data_to_string(basic_srt_data_for_chain)
                        logging.info(f"{log_prefix} Đã tạo SRT cơ bản cho chain timing. script_for_chain_timing được cập nhật.")
                    else:
                        logging.warning(f"{log_prefix} Không tạo được SRT cơ bản cho chain timing. script_for_chain_timing vẫn là plain text.")
                    # final_script_for_display_sub_tab vẫn là original_plain_gpt_text vì auto_format_sub_on TẮT

                # Cập nhật textbox của tab Subtitle với final_script_for_display_sub_tab
                if target_textbox_widget and target_textbox_widget.winfo_exists():
                    target_textbox_widget.delete("1.0", "end")
                    target_textbox_widget.insert("1.0", final_script_for_display_sub_tab)
                    self.allow_edit_sub = True
                
                # Kích hoạt chuỗi DALL-E nếu cần
                if trigger_dalle_chain_flag:
                    logging.info(f"{log_prefix} Cờ trigger_dalle_chain_flag=True. Bắt đầu chuỗi GPT chia cảnh -> DALL-E.")
                    logging.info(f"{log_prefix}   Truyền script_for_chain_timing (dài {len(script_for_chain_timing)} chars): '{script_for_chain_timing[:100].replace(chr(10),' ')}...'")
                    logging.info(f"{log_prefix}   Truyền original_plain_gpt_text (dài {len(original_plain_gpt_text)} chars): '{original_plain_gpt_text[:100].replace(chr(10),' ')}...'")
                    
                    self.update_status(f"🤖 GPT tạo kịch bản xong! Chuẩn bị yêu cầu GPT chia cảnh...")
                    
                    self.master_app.after(100, self._initiate_gpt_scene_division,
                               script_for_chain_timing,
                               original_plain_gpt_text,
                               calling_button_context, 
                               target_textbox_widget, 
                               trigger_dub_chain_flag,
                               base_filename_for_chain)
                    return            
            
            elif calling_button_context == "dubbing":
                # Khởi tạo final_script_for_display bằng output thuần từ GPT
                final_script_for_display = processed_script 
                srt_data_content_for_dub_update = None # Sẽ lưu trữ kết quả parse

                if hasattr(self, 'auto_format_plain_text_to_srt_dub_var') and \
                   self.auto_format_plain_text_to_srt_dub_var.get() and \
                   target_textbox_widget == self.dub_script_textbox:
                    
                    logging.info(f"{log_prefix} Checkbox 'AutoFormat SRT (Dubbing)' BẬT. Thử chuyển đổi output GPT.")
                    gpt_split_cfg_dub = {
                        "split_enabled": self.enable_split_var.get(),
                        "mode": self.split_mode_var.get(),
                        "max_chars": safe_int(self.max_chars_var.get(), 90),
                        "max_lines": safe_int(self.max_lines_var.get(), 1),
                        "DEFAULT_CPS_FOR_TIMING": safe_int(self.sub_cps_for_timing_var.get(), 17),
                        "PAUSE_BETWEEN_SEGMENTS_MS_FOR_TIMING": 1,
                        "ABSOLUTE_MIN_DURATION_PER_CHUNK_MS": self.min_duration_per_segment_ms
                    }

                    temp_parsed_data = self._parse_plain_text_to_srt_data(
                        processed_script, 
                        force_plain_text_processing=True,
                        split_config_override=gpt_split_cfg_dub
                    )
                    if temp_parsed_data: # Nếu parse thành công và có nội dung
                        srt_string_from_gpt_dub = format_srt_data_to_string(temp_parsed_data)
                        final_script_for_display = srt_string_from_gpt_dub
                        srt_data_content_for_dub_update = temp_parsed_data # Đây là dữ liệu SRT thực sự
                        logging.info(f"{log_prefix} Đã chuyển đổi output GPT (Dubbing) sang SRT. Số mục: {len(srt_data_content_for_dub_update)}")
                    else: # Parse không thành công hoặc trả về rỗng
                        logging.warning(f"{log_prefix} Không thể chuyển đổi output GPT (Dubbing) sang SRT cấu trúc. Giữ nguyên plain text.")
                        # final_script_for_display vẫn là processed_script (plain text)
                        # Cần parse plain text này để lấy srt_data_content_for_dub_update cho dub_temp_srt_data_for_queue
                        srt_data_content_for_dub_update = self._parse_plain_text_to_srt_data(
                            final_script_for_display, force_plain_text_processing=True, split_config_override=None
                        )
                        logging.info(f"{log_prefix} Đã parse lại plain text từ GPT (Dubbing) cho srt_data_content_for_dub_update. Số mục: {len(srt_data_content_for_dub_update if srt_data_content_for_dub_update else [])}")
                
                else: # Checkbox AutoFormat (Dubbing) không được tick
                    logging.info(f"{log_prefix} Checkbox 'AutoFormat SRT (Dubbing)' TẮT. Parse output GPT như plain text.")
                    srt_data_content_for_dub_update = self._parse_plain_text_to_srt_data(
                        final_script_for_display, force_plain_text_processing=True, split_config_override=None
                    )
                    logging.info(f"{log_prefix} Đã parse plain text từ GPT (Dubbing) cho srt_data_content_for_dub_update (checkbox tắt). Số mục: {len(srt_data_content_for_dub_update if srt_data_content_for_dub_update else [])}")

                # Cập nhật self.dub_temp_srt_data_for_queue với dữ liệu đã parse (SRT hoặc plain text đã ước lượng thời gian)
                self.dub_temp_srt_data_for_queue = srt_data_content_for_dub_update if srt_data_content_for_dub_update else []
                
                # Cập nhật textbox dubbing
                if target_textbox_widget and target_textbox_widget.winfo_exists(): # chính là self.dub_script_textbox
                    target_textbox_widget.configure(state="normal") 
                    target_textbox_widget.delete("1.0", "end")      
                    
                    # Chỉ insert nếu final_script_for_display thực sự có nội dung sau khi strip
                    # Nếu nó rỗng, textbox sẽ trống, và _update_dub_script_controls_state sẽ xử lý placeholder
                    if final_script_for_display and final_script_for_display.strip():
                        target_textbox_widget.insert("1.0", final_script_for_display)
                        logging.debug(f"{log_prefix} Đã insert nội dung vào dub_script_textbox: '{final_script_for_display[:50]}...'")
                    else:
                        logging.debug(f"{log_prefix} final_script_for_display rỗng hoặc chỉ chứa khoảng trắng. dub_script_textbox sẽ trống.")
                
                # Gọi các hàm cập nhật UI sau khi textbox đã ổn định
                self._update_dub_script_controls_state() 
                if hasattr(self, '_check_can_add_to_dub_queue'):
                    self._check_can_add_to_dub_queue()
                logging.debug(f"{log_prefix} Đã gọi _update_dub_script_controls_state và _check_can_add_to_dub_queue.")

                    

            # Xử lý chung sau khi đã cập nhật textbox (nếu không có DALL-E chain được trigger)
            if not trigger_dalle_chain_flag: 
                self.update_status(f"✅ GPT đã biên tập xong kịch bản ({calling_button_context}).")
                try:
                    play_sound_on_gpt_task_complete = self.download_view_frame.download_sound_var.get() if hasattr(self, 'download_view_frame') else False
                    sound_file_to_play_gpt = self.download_view_frame.download_sound_path_var.get() if hasattr(self, 'download_view_frame') else ""
                    if play_sound_on_gpt_task_complete and sound_file_to_play_gpt and \
                       os.path.isfile(sound_file_to_play_gpt) and PLAYSOUND_AVAILABLE:
                        play_sound_async(sound_file_to_play_gpt)
                except Exception as e_play_gpt_sound:
                    logging.error(f"{log_prefix} Lỗi khi thử phát âm thanh sau GPT: {e_play_gpt_sound}")

                messagebox.showinfo("Hoàn thành GPT",
                                    f"GPT đã xử lý và cập nhật nội dung kịch bản ({calling_button_context.capitalize()}).",
                                    parent=self)
        else: # processed_script is None (và không có lỗi)
            logging.warning(f"{log_prefix} GPT không trả về nội dung và không báo lỗi.")
            self.update_status(f"⚠️ GPT không trả về nội dung ({calling_button_context}).")
            messagebox.showwarning("Không có kết quả", 
                                   f"GPT không trả về nội dung nào cho yêu cầu của bạn ({calling_button_context.capitalize()}).\n"
                                   "Vui lòng thử lại hoặc thay đổi yêu cầu.", 
                                   parent=self)

        # Đảm bảo textbox ở trạng thái 'normal' nếu không có lỗi và không có chuỗi DALL-E
        if target_textbox_widget and target_textbox_widget.winfo_exists() and not error_message and not (trigger_dalle_chain_flag and calling_button_context == "subtitle"):
             target_textbox_widget.configure(state="normal")
        elif target_textbox_widget and target_textbox_widget.winfo_exists() and error_message:
             target_textbox_widget.configure(state="normal")            


# Hàm logic: Dịch một file phụ đề (SRT/VTT)
    def translate_subtitle_file(self, input_srt, output_srt, target_lang="vi", bilingual=False):
        """
        Dịch file phụ đề sử dụng engine được chọn, bao gồm kiểm tra điều kiện.
        Hàm này sẽ raise ValueError nếu engine được chọn không sẵn sàng.
        """
        selected_engine = self.master_app.translation_engine_var.get()
        base_input_name = os.path.basename(input_srt) # Lấy tên file để log
        logging.info(f"Bắt đầu kiểm tra và dịch file '{base_input_name}' bằng engine: {selected_engine}")

        # --- KIỂM TRA ĐIỀU KIỆN TIÊN QUYẾT CHO ENGINE ---
        if selected_engine == "Không dịch":
            logging.info("Người dùng chọn 'Không dịch', bỏ qua bước dịch.")
            return 

        elif "Google Cloud API" in selected_engine:
            key_path = self.google_key_path_var.get()
            if not HAS_GOOGLE_CLOUD_TRANSLATE:
                msg = "Thư viện Google Cloud Translate chưa được cài đặt.\nVui lòng cài đặt: pip install google-cloud-translate"
                logging.error(msg)
                messagebox.showerror("Lỗi Thư viện", msg, parent=self)
                raise ValueError("Thiếu thư viện Google Cloud Translate")
            if not key_path or not os.path.exists(key_path):
                msg = "Vui lòng cấu hình đường dẫn file JSON Key cho Google Cloud trong 'Cài đặt API Keys'."
                logging.error(msg)
                messagebox.showerror("Thiếu Cấu hình Google Key", msg, parent=self)
                raise ValueError("Thiếu hoặc sai cấu hình Google Cloud Key")
            logging.info("Điều kiện Google Cloud API hợp lệ.")

        elif "ChatGPT API" in selected_engine:
            api_key = self.openai_key_var.get()
            if not HAS_OPENAI:
                msg = "Thư viện OpenAI chưa được cài đặt.\nVui lòng cài đặt: pip install openai"
                logging.error(msg)
                messagebox.showerror("Lỗi Thư viện", msg, parent=self)
                raise ValueError("Thiếu thư viện OpenAI")
            if not api_key:
                msg = "Vui lòng cấu hình OpenAI API Key trong 'Cài đặt API Keys'."
                logging.error(msg)
                messagebox.showerror("Thiếu Cấu hình OpenAI Key", msg, parent=self)
                raise ValueError("Thiếu cấu hình OpenAI Key")
            logging.info("Điều kiện OpenAI API hợp lệ.")

        else: # Trường hợp engine không xác định (lỗi logic đâu đó)
             msg = f"Engine dịch không xác định: '{selected_engine}'. Không thể dịch."
             logging.error(msg)
             messagebox.showerror("Lỗi Engine", msg, parent=self)
             raise ValueError("Engine dịch không xác định")

        # --- KẾT THÚC KIỂM TRA ĐIỀU KIỆN ---

        # --- Nếu vượt qua kiểm tra, tiến hành đọc và dịch file ---
        logging.info(f"Bắt đầu đọc và xử lý file '{base_input_name}'...")
        try:
            with open(input_srt, "r", encoding="utf-8") as f:
                lines = f.readlines()
            logging.debug(f"Đã đọc {len(lines)} dòng từ file input.")
        except Exception as e:
            logging.error(f"Lỗi đọc file phụ đề để dịch '{input_srt}': {e}", exc_info=True)
            # Ném lại lỗi để luồng cha xử lý
            raise IOError(f"Lỗi đọc file phụ đề để dịch: {e}")

        output_lines = []
        block = []
        processed_blocks = 0
        # Lặp qua các dòng để xử lý từng khối
        for line in lines:
            # Kiểm tra dừng giữa các khối
            if self.master_app.stop_event.is_set():
                logging.warning("Yêu cầu dừng trong quá trình xử lý khối phụ đề.")
                raise InterruptedError("Dừng bởi người dùng khi đang dịch file.")

            if line.strip() == "": # Kết thúc một khối
                if block:
                    # Gọi _translate_block đã sửa (không cần truyền translator nữa)
                    translated_block_lines = self._translate_block(block, target_lang, bilingual)
                    output_lines.extend(translated_block_lines)
                    processed_blocks += 1
                    logging.debug(f"Đã xử lý xong khối {processed_blocks}")
                # output_lines.append("\n") # Không cần thêm dòng trống ở đây vì _translate_block đã xử lý
                block = [] # Bắt đầu khối mới
            else:
                block.append(line.strip() + "\n") # Thêm lại ký tự xuống dòng chuẩn

        # Xử lý khối cuối cùng nếu file không kết thúc bằng dòng trống
        if block:
            logging.debug("Đang xử lý khối cuối cùng...")
            translated_block_lines = self._translate_block(block, target_lang, bilingual)
            output_lines.extend(translated_block_lines)
            processed_blocks += 1
            logging.debug(f"Đã xử lý xong khối cuối cùng (Tổng cộng: {processed_blocks}).")

        # --- Ghi kết quả ra file output ---
        try:
            # Đảm bảo file output kết thúc bằng một dòng trống (theo chuẩn SRT/VTT)
            final_output_content = "".join(output_lines)
            # Xóa các dòng trống thừa ở cuối và đảm bảo có 1 dòng trống cuối
            final_output_content = final_output_content.rstrip() + "\n\n"

            with open(output_srt, "w", encoding="utf-8") as f:
                f.write(final_output_content)
            logging.info(f"Đã lưu phụ đề đã dịch thành công vào: {output_srt}")
        except Exception as e:
            logging.error(f"Lỗi ghi file phụ đề đã dịch '{output_srt}': {e}", exc_info=True)
            # Ném lại lỗi để luồng cha xử lý
            raise IOError(f"Lỗi ghi file phụ đề đã dịch: {e}")                 



# Hàm logic: Dịch văn bản bằng Google Cloud Translate API
    def translate_google_cloud(self, text_list, target_lang_code, source_lang_code=None):
        """
        Dịch một danh sách các chuỗi văn bản bằng Google Cloud Translate API v2.

        Args:
            text_list (list): Danh sách các chuỗi cần dịch.
            target_lang_code (str): Mã ngôn ngữ đích (ví dụ: 'en', 'vi').
            source_lang_code (str, optional): Mã ngôn ngữ nguồn. Mặc định là None (tự động phát hiện).

        Returns:
            list or None: Danh sách các chuỗi đã dịch, hoặc None nếu có lỗi nghiêm trọng.
                          Nếu lỗi xảy ra với một vài dòng, có thể trả về list chứa dòng lỗi đó.
        """
        # Kiểm tra xem thư viện có tồn tại không
        if not HAS_GOOGLE_CLOUD_TRANSLATE or google_translate is None or service_account is None:
            logging.error("Thư viện Google Cloud Translate không khả dụng để gọi API.")
            # Không cần hiện messagebox ở đây vì đã có kiểm tra trước khi gọi
            return None

        # Lấy đường dẫn file key từ biến cấu hình
        key_path = self.google_key_path_var.get()
        if not key_path or not os.path.exists(key_path):
            logging.error("Đường dẫn file key Google Cloud không hợp lệ hoặc bị thiếu trong cấu hình.")
            # Thông báo lỗi cho người dùng một lần duy nhất nếu họ cố dịch mà thiếu key
            self.master_app.after(0, lambda: messagebox.showerror("Thiếu Key Google Cloud",
                                                       "Vui lòng cấu hình đường dẫn đến file JSON key của Google Service Account trong 'Cài đặt API Keys' trước khi sử dụng tính năng này.",
                                                       parent=self))
            return None # Trả về None để hàm gọi biết là lỗi

        try:
            # Load credentials từ file JSON đã cấu hình
            credentials = service_account.Credentials.from_service_account_file(key_path)
            # Khởi tạo Google Translate client
            translate_client = google_translate.Client(credentials=credentials)

            # Ghi log về yêu cầu dịch
            logging.info(f"Đang gửi {len(text_list)} dòng tới Google Cloud API để dịch sang '{target_lang_code}'...")
            if source_lang_code:
                logging.info(f"  (Ngôn ngữ nguồn được chỉ định: '{source_lang_code}')")
            else:
                logging.info("  (Ngôn ngữ nguồn: Tự động phát hiện)")

            results = translate_client.translate(
                values=text_list, # Tham số values thay vì text_list ở một số phiên bản
                target_language=target_lang_code,
                source_language=source_lang_code if source_lang_code and source_lang_code != 'auto' else None
            )

            # Trích xuất kết quả
            translated_texts = [result['translatedText'] for result in results]
            logging.info(f"Google Cloud API đã dịch thành công {len(translated_texts)} dòng.")
            # <-- BẮT ĐẦU THÊM MỚI -->
            total_chars_translated = sum(len(text) for text in text_list)
            self._track_api_call(service_name="google_translate_chars", units=total_chars_translated)

            # Kiểm tra xem số lượng kết quả có khớp không (phòng trường hợp lạ)
            if len(translated_texts) != len(text_list):
                 logging.warning(f"Số lượng dòng trả về ({len(translated_texts)}) từ Google Cloud không khớp với số lượng gửi đi ({len(text_list)})!")
                 return None

            return translated_texts # Trả về danh sách các dòng đã dịch

        except Exception as e:
            # Xử lý các lỗi có thể xảy ra khi gọi API
            logging.error(f"Lỗi khi gọi Google Cloud Translate API: {e}", exc_info=True)

            # === BẮT ĐẦU LOGIC KIỂM SOÁT POPUP LỖI API DỊCH ===
            should_show_translate_popup_now = False
            # Kiểm tra xem có phải đang trong quá trình subbing không (để biết là batch hay không)
            is_batch_subbing = hasattr(self, 'is_subbing') and self.is_subbing

            if not is_batch_subbing: # Nếu không phải batch (ví dụ: một lệnh gọi API đơn lẻ không rõ ngữ cảnh)
                should_show_translate_popup_now = True
            elif is_batch_subbing: # Nếu đang xử lý batch sub
                if not self.translate_batch_first_api_error_msg_shown:
                    self.translate_batch_first_api_error_msg_shown = True
                    self.translate_batch_accumulated_api_error_details = str(e)
                    should_show_translate_popup_now = True
                else:
                    logging.warning(f"Lỗi API Google Translate tiếp theo, popup đã bị chặn cho batch này: {e}")
            
            if should_show_translate_popup_now:
                 parent_window = self # Vì đây là method của SubtitleApp
                 self.master_app.after(0, lambda err=str(e), p=parent_window: messagebox.showerror("Lỗi Google API (Dịch)",
                                                                       f"Đã xảy ra lỗi khi liên lạc với Google Cloud Translation:\n{err}",
                                                                       parent=p))
            # === KẾT THÚC LOGIC KIỂM SOÁT POPUP LỖI API DỊCH ===
            return None # Trả về None để báo hiệu lỗi dịch
            
            # Hiển thị lỗi cho người dùng qua luồng chính
            self.master_app.after(0, lambda err=str(e): messagebox.showerror("Lỗi Google API",
                                                                   f"Đã xảy ra lỗi khi liên lạc với Google Cloud Translation:\n{err}",
                                                                   parent=self))
            return None # Trả về None để báo hiệu lỗi    


# Hàm logic: Dịch văn bản bằng OpenAI (ChatGPT) API
    def translate_openai(self, text_list, target_lang, source_lang=None):
        """
        Dịch một danh sách các chuỗi văn bản bằng OpenAI API (ChatGPT),
        có hỗ trợ lựa chọn phong cách dịch.
        
        [REFACTORED] Sử dụng AIService để xử lý translation logic.

        Args:
            text_list (list): Danh sách các chuỗi cần dịch.
            target_lang (str): Tên ngôn ngữ đích (ví dụ: 'Vietnamese', 'English').
            source_lang (str, optional): Tên/Mã ngôn ngữ nguồn. Mặc định là None (không chỉ định).

        Returns:
            list or None: Danh sách các chuỗi đã dịch (hoặc gốc nếu lỗi),
                          hoặc None nếu có lỗi nghiêm trọng (thiếu key/thư viện).
        """
        # Lấy API key
        api_key = self.openai_key_var.get()
        if not api_key:
            logging.error("OpenAI API Key bị thiếu trong cấu hình.")
            self.master_app.after(0, lambda: messagebox.showerror("Thiếu Key OpenAI",
                                                       "Vui lòng cấu hình OpenAI API Key trong 'Cài đặt API Keys'.",
                                                       parent=self))
            return None

        # Lấy phong cách dịch đã chọn
        selected_style = "Mặc định (trung tính)"
        try:
            if hasattr(self, 'openai_translation_style_var'):
                selected_style = self.openai_translation_style_var.get()
                logging.info(f"Sẽ yêu cầu dịch OpenAI với phong cách: '{selected_style}'")
            else:
                logging.warning("Không tìm thấy biến openai_translation_style_var. Sử dụng phong cách mặc định.")
        except Exception as e_get_style:
            logging.error(f"Lỗi khi lấy phong cách dịch OpenAI: {e_get_style}. Sử dụng phong cách mặc định.")

        # Gọi AI Service để dịch
        try:
            translated_texts, error_message = self.ai_service.translate_with_openai(
                text_list=text_list,
                target_lang=target_lang,
                api_key=api_key,
                source_lang=source_lang,
                translation_style=selected_style,
                model_name="gpt-3.5-turbo",
                stop_event=lambda: self.stop_event.is_set()
            )
            
            if error_message:
                logging.error(f"Lỗi khi dịch OpenAI: {error_message}")
                # Nếu có lỗi nhưng vẫn có một phần kết quả, trả về phần đó
                if translated_texts:
                    return translated_texts
                # Nếu lỗi nghiêm trọng, hiển thị messagebox
                self.master_app.after(0, lambda err=error_message: messagebox.showerror("Lỗi OpenAI API",
                                                                           f"Đã xảy ra lỗi khi liên lạc với OpenAI:\n{err}",
                                                                       parent=self))
                return None

        except Exception as e:
            logging.error(f"Lỗi nghiêm trọng khi sử dụng AI Service: {e}", exc_info=True)
            self.master_app.after(0, lambda err=str(e): messagebox.showerror("Lỗi AI Service",
                                                                  f"Đã xảy ra lỗi khi gọi AI Service:\n{err}",
                                                                  parent=self))
            return None      


# Hàm logic: Gắn cứng (hardsub) phụ đề vào video bằng FFmpeg
    def burn_sub_to_video(self, input_video, input_sub_path_srt, output_video, cfg_snapshot):
        logging.info(f"[HardsubBurning] Bắt đầu Hardsub cho: {os.path.basename(input_video)}")
        logging.info(f"[HardsubBurning] cfg_snapshot nhận được: {json.dumps(cfg_snapshot, indent=2, ensure_ascii=False)}")

        # HẰNG SỐ THAM CHIẾU
        REFERENCE_VIDEO_HEIGHT_FOR_SCALING = 1080
        logging.info(f"[HardsubStyleDebug] Sử dụng REFERENCE_VIDEO_HEIGHT_FOR_SCALING: {REFERENCE_VIDEO_HEIGHT_FOR_SCALING}px")


        temp_ass_file_path = None
        try:
            subs_srt = pysubs2.load(input_sub_path_srt, encoding="utf-8")
            config_source = cfg_snapshot

            # --- Lấy thông tin kích thước video cho PlayRes và tính toán font ---
            video_width_for_ass = 1920  # Mặc định
            video_height_for_ass = 1080 # Mặc định
            ffprobe_exec_ass = find_ffprobe() # Hàm find_ffprobe() của bạn
            if ffprobe_exec_ass:
                try:
                    cmd_probe_res_ass = [ffprobe_exec_ass, "-v", "error", "-select_streams", "v:0",
                                         "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0",
                                         os.path.abspath(input_video)]
                    startupinfo_probe = None; creationflags_probe = 0
                    if sys.platform == "win32":
                        startupinfo_probe = subprocess.STARTUPINFO(); startupinfo_probe.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo_probe.wShowWindow = subprocess.SW_HIDE; creationflags_probe = subprocess.CREATE_NO_WINDOW
                    probe_res_ass = subprocess.run(cmd_probe_res_ass, capture_output=True, text=True, timeout=10,
                                                   startupinfo=startupinfo_probe, creationflags=creationflags_probe, check=False)
                    if probe_res_ass.returncode == 0 and probe_res_ass.stdout.strip():
                        w_h_ass = probe_res_ass.stdout.strip().split('x')
                        if len(w_h_ass) == 2 and w_h_ass[0].isdigit() and w_h_ass[1].isdigit():
                            video_width_for_ass = int(w_h_ass[0]); video_height_for_ass = int(w_h_ass[1])
                            logging.info(f"[HardsubASSInfo] Lấy được kích thước video cho PlayRes: {video_width_for_ass}x{video_height_for_ass}")
                        else: logging.warning(f"[HardsubASSInfo] ffprobe trả về định dạng không mong muốn: '{probe_res_ass.stdout.strip()}'.")
                    else: logging.warning(f"[HardsubASSInfo] ffprobe không lấy được kích thước (Code: {probe_res_ass.returncode}).")
                except Exception as e_probe_ass: logging.warning(f"[HardsubASSInfo] Lỗi ffprobe: {e_probe_ass}.")
            else: logging.warning("[HardsubASSInfo] Không tìm thấy ffprobe cho PlayRes.")

            # --- Tính toán scaled_font_size ---
            config_font_size = float(config_source.get("sub_style_font_size", 60))
            reference_height = float(REFERENCE_VIDEO_HEIGHT_FOR_SCALING) # Sử dụng hằng số đã định nghĩa
            actual_video_height_for_scaling = float(video_height_for_ass)

            if reference_height > 0 and actual_video_height_for_scaling > 0:
                scaled_font_size = (config_font_size / reference_height) * actual_video_height_for_scaling
            else:
                scaled_font_size = config_font_size # Fallback
                logging.warning(f"[HardsubStyleDebug] Lỗi reference_height ({reference_height}) hoặc actual_video_height ({actual_video_height_for_scaling}) không hợp lệ. Dùng config_font_size.")

            logging.info(f"[HardsubStyleDebug] ConfigFontSize: {config_font_size}, RefHeight: {reference_height}, ActualVidHeight: {actual_video_height_for_scaling}, ScaledFontSize for SSAStyle: {scaled_font_size:.2f}")
            # --- Kết thúc tính toán scaled_font_size ---

            piu_style = pysubs2.SSAStyle()
            piu_style.fontname = config_source.get("sub_style_font_name", "Arial")
            piu_style.fontsize = scaled_font_size # <<<< SỬ DỤNG FONT SIZE ĐÃ TÍNH TOÁN >>>>
            piu_style.bold = config_source.get("sub_style_font_bold", True)

            text_color_str = config_source.get("sub_style_text_color_rgb_str", "255,255,255")
            style_primary_color_rgb = parse_color_string_to_tuple(text_color_str, (255,255,255))
            primary_color_opacity_percent = config_source.get("sub_style_text_opacity_percent", 100)
            primary_transparency_decimal = (100.0 - primary_color_opacity_percent) / 100.0
            style_primary_color_alpha_pysubs2 = int(round(255 * primary_transparency_decimal))

            piu_style.primarycolor = pysubs2.Color(r=style_primary_color_rgb[0], g=style_primary_color_rgb[1], b=style_primary_color_rgb[2], a=style_primary_color_alpha_pysubs2)

            enable_outline_cfg = config_source.get("sub_style_outline_enabled", False)
            enable_background_box_cfg = config_source.get("sub_style_bg_box_enabled", False)

            logging.info(f"[HardsubStyleDebug] Style từ cfg_snapshot cho '{os.path.basename(input_video)}':")
            logging.info(f"[HardsubStyleDebug]   FontName: {piu_style.fontname}, ScaledFontSize: {piu_style.fontsize:.2f}, Bold: {piu_style.bold}") # Log scaled font size
            logging.info(f"[HardsubStyleDebug]   TextColorRGB: {style_primary_color_rgb}, TextAlphaPysubs2: {style_primary_color_alpha_pysubs2}")
            logging.info(f"[HardsubStyleDebug]   EnableOutline Checkbox: {enable_outline_cfg}")
            logging.info(f"[HardsubStyleDebug]   EnableBackgroundBox Checkbox: {enable_background_box_cfg}")


    # Lấy chế độ nền từ config
            background_mode = config_source.get("sub_style_background_mode", "Đổ Bóng")

            # --- BẮT ĐẦU KHỐI LOGIC ĐÃ SỬA LỖI (V2 - HOÀN CHỈNH) ---
            
            # Thiết lập mặc định an toàn: Chỉ có chữ, không viền, không bóng, không box.
            piu_style.borderstyle = 1 
            piu_style.outline = 0.0
            piu_style.shadow = 0.0

            if background_mode == "Box Nền":
                logging.info("[HardsubStyleLogic] Áp dụng BOX NỀN (borderstyle=3).")
                piu_style.borderstyle = 3 # Bật chế độ box nền
                
                # Lấy các giá trị màu sắc và độ mờ cho box từ config
                bg_opacity_percent = config_source.get("sub_style_bg_box_actual_opacity_percent", 75)
                bg_color_str = config_source.get("sub_style_bg_color_rgb_str", "0,0,0")
                bg_rgb = parse_color_string_to_tuple(bg_color_str, (0,0,0))
                bg_alpha = int(round(255 * (100.0 - bg_opacity_percent) / 100.0))
                
                piu_style.backcolor = pysubs2.Color(r=bg_rgb[0], g=bg_rgb[1], b=bg_rgb[2], a=bg_alpha)
                # Đặt outline bằng 1 với màu trùng màu nền để có viền box sắc nét
                piu_style.outline = 1.0 
                piu_style.outlinecolor = piu_style.backcolor

            elif background_mode == "Đổ Bóng":
                logging.info("[HardsubStyleLogic] Áp dụng HIỆU ỨNG ĐỔ BÓNG (shadow=2.0).")
                piu_style.shadow = 2.0 # Đặt độ mờ của bóng
                
                # Lấy màu sắc và độ mờ của bóng từ config (dùng chung biến với box nền)
                shadow_opacity_percent = config_source.get("sub_style_bg_box_actual_opacity_percent", 75)
                shadow_color_str = config_source.get("sub_style_bg_color_rgb_str", "0,0,0")
                shadow_rgb = parse_color_string_to_tuple(shadow_color_str, (0,0,0))
                shadow_alpha = int(round(255 * (100.0 - shadow_opacity_percent) / 100.0))
                
                piu_style.backcolor = pysubs2.Color(r=shadow_rgb[0], g=shadow_rgb[1], b=shadow_rgb[2], a=shadow_alpha)
                
                # Nếu người dùng cũng bật viền chữ, thì áp dụng cả viền chữ
                if config_source.get("sub_style_outline_enabled", False):
                    logging.info("[HardsubStyleLogic]   -> Kèm cả VIỀN CHỮ.")
                    outline_size = config_source.get("sub_style_outline_size", 2.0)
                    outline_color_str = config_source.get("sub_style_outline_color_rgb_str", "0,0,0")
                    outline_rgb = parse_color_string_to_tuple(outline_color_str, (0,0,0))
                    outline_opacity = config_source.get("sub_style_outline_opacity_percent", 100)
                    outline_alpha = int(round(255 * (100.0 - outline_opacity) / 100.0))
                    
                    piu_style.outline = float(outline_size)
                    piu_style.outlinecolor = pysubs2.Color(r=outline_rgb[0], g=outline_rgb[1], b=outline_rgb[2], a=outline_alpha)

            elif background_mode == "Không Nền":
                # shadow đã được đặt về 0.0 ở phần mặc định.
                if config_source.get("sub_style_outline_enabled", False):
                    logging.info("[HardsubStyleLogic] Áp dụng VIỀN CHỮ (Không Nền).")
                    outline_size = config_source.get("sub_style_outline_size", 2.0)
                    outline_color_str = config_source.get("sub_style_outline_color_rgb_str", "0,0,0")
                    outline_rgb = parse_color_string_to_tuple(outline_color_str, (0,0,0))
                    outline_opacity = config_source.get("sub_style_outline_opacity_percent", 100)
                    outline_alpha = int(round(255 * (100.0 - outline_opacity) / 100.0))

                    piu_style.outline = float(outline_size)
                    piu_style.outlinecolor = pysubs2.Color(r=outline_rgb[0], g=outline_rgb[1], b=outline_rgb[2], a=outline_alpha)
                else:
                    logging.info("[HardsubStyleLogic] Chế độ Không Nền và không có viền.")

            # --- KẾT THÚC KHỐI LOGIC ĐÃ SỬA LỖI ---

            piu_style.alignment = 2
            piu_style.marginv = config_source.get("margin_v", 60)
            logging.info(f"[HardsubStyleDebug]   Alignment: {piu_style.alignment}, MarginV: {piu_style.marginv}")

            style_name_in_ass = "PiuCustomStyle"
            subs_srt.styles[style_name_in_ass] = piu_style
            for event in subs_srt:
                event.style = style_name_in_ass

            # Đặt PlayResX và PlayResY dựa trên kích thước video thực tế
            if not hasattr(subs_srt, 'info') or subs_srt.info is None: subs_srt.info = {}
            subs_srt.info["PlayResX"] = str(video_width_for_ass)
            subs_srt.info["PlayResY"] = str(video_height_for_ass)
            subs_srt.info["WrapStyle"] = "0" # Hoặc giá trị wrap style mong muốn
            logging.info(f"[HardsubASSInfo] Đã đặt PlayResX={subs_srt.info['PlayResX']}, PlayResY={subs_srt.info['PlayResY']}")

            temp_ass_filename = f"styled_subs_playres_{uuid.uuid4().hex[:8]}.ass"
            temp_ass_file_path = os.path.join(self.temp_folder, temp_ass_filename)
            subs_srt.save(temp_ass_file_path, encoding="utf-8", format_="ass")
            logging.info(f"Đã tạo file .ass (có PlayRes): {temp_ass_file_path}")

            try:
                with open(temp_ass_file_path, "r", encoding="utf-8") as f_ass_check:
                    ass_content_log = f_ass_check.read()
                logging.debug(f"[HardsubStyleDebug] Nội dung file ASS ({os.path.basename(temp_ass_file_path)}):\n{ass_content_log[:2000]}")
            except Exception as e_log_ass_content:
                logging.warning(f"[HardsubStyleDebug] Không thể đọc file ASS để log: {e_log_ass_content}")

            posix_path = Path(os.path.abspath(temp_ass_file_path)).as_posix()
            escaped_path = posix_path.replace('\\', '\\\\').replace("'", "\\'").replace(":", "\\:").replace(",", "\\,").replace("[", "\\[").replace("]", "\\]")
            filter_complex_str = f"[0:v]ass=filename='{escaped_path}'[video_out]"
            cmd_params = [
                "-y", 
                "-i", os.path.abspath(input_video), 
                "-filter_complex", filter_complex_str,
                "-map", "[video_out]", "-map", "0:a?", 
                "-c:v", "libx264",
                "-preset", config_source.get("ffmpeg_preset", "medium"),
                "-crf", str(config_source.get("ffmpeg_crf", 22)),
                # Thêm các cờ tương thích cho iPhone/mobile
                "-profile:v", "main",   # <-- THÊM DÒNG NÀY: Profile tương thích rộng
                "-level", "4.0",        # <-- THÊM DÒNG NÀY: Level cho FullHD, rất an toàn
                "-pix_fmt", "yuv420p",   # <-- THÊM DÒNG NÀY: Định dạng pixel bắt buộc cho nhiều thiết bị
                "-movflags", "+faststart", # <-- THÊM DÒNG NÀY: Tối ưu cho streaming
                "-c:a", "copy", 
                os.path.abspath(output_video)
            ]
            ffmpeg_run_command(
                cmd_params,
                "Hardsub",
                stop_event=self.stop_event,
                set_current_process=lambda p: setattr(self, 'current_process', p),
                clear_current_process=lambda: setattr(self, 'current_process', None),
            )
            logging.info(f"Hardsub hoàn tất cho: {os.path.basename(output_video)}")
        except Exception as e_burn:
            logging.error(f"Lỗi nghiêm trọng trong burn_sub_to_video: {e_burn}", exc_info=True)
            raise RuntimeError(f"Lỗi tạo hoặc burn file ASS/video: {e_burn}")
        finally:
            if temp_ass_file_path and os.path.exists(temp_ass_file_path):
                try:
                    os.remove(temp_ass_file_path) # Xóa file ASS tạm sau khi dùng
                    logging.info(f"Đã xóa file .ass tạm: {temp_ass_file_path}")
                except Exception as e_del:
                    logging.warning(f"Lỗi xóa file .ass tạm '{temp_ass_file_path}': {e_del}")                             


# Hàm logic: Gắn mềm (softsub) phụ đề vào container video bằng FFmpeg
    def merge_sub_as_soft_sub(self, video_path, sub_path, output_path, lang_code='und'):
        """ Gắn mềm (softsub) phụ đề vào container video bằng FFmpeg """
        logging.info(f"Bắt đầu Softsub: Video='{os.path.basename(video_path)}', Sub='{os.path.basename(sub_path)}'")
        sub_ext = os.path.splitext(sub_path)[1].lower()
        output_ext = os.path.splitext(output_path)[1].lower()

        # Xác định codec phụ đề dựa trên container output
        if output_ext == ".mkv":
            sub_codec = {".srt": "srt", ".ass": "ass", ".vtt": "webvtt"}.get(sub_ext)
            if not sub_codec: raise ValueError(f"Định dạng phụ đề '{sub_ext}' không hỗ trợ MKV Softsub.")
        elif output_ext == ".mp4":
            if sub_ext not in [".srt", ".vtt"]:
                 # Tự động chuyển sang MKV nếu định dạng không tương thích MP4 (như ASS)
                 output_path = os.path.splitext(output_path)[0] + ".mkv"
                 logging.warning(f"Đã chuyển output sang MKV để tương thích softsub '{sub_ext}': {os.path.basename(output_path)}")
                 sub_codec = {".srt": "srt", ".ass": "ass", ".vtt": "webvtt"}.get(sub_ext) # Kiểm tra lại codec cho MKV
            else: sub_codec = "mov_text" # Sử dụng mov_text cho SRT/VTT trong MP4
        else: raise ValueError(f"Container output '{output_ext}' không hỗ trợ Softsub.")
        if not sub_codec: raise ValueError(f"Không thể xác định codec phụ đề cho '{sub_ext}' trong '{output_ext}'.")


        cmd_params = [
            "-y", "-i", os.path.abspath(video_path), "-i", os.path.abspath(sub_path),
            "-map", "0:v", "-map", "0:a", "-map", "1:s", # Map các luồng
            "-c:v", "copy", "-c:a", "copy", "-c:s", sub_codec, # Sao chép video/audio, đặt codec sub
            "-metadata:s:s:0", f"language={lang_code}", # Đặt metadata ngôn ngữ cho luồng sub
            os.path.abspath(output_path).replace("\\", "/")
        ]
        ffmpeg_run_command(
            cmd_params,
            "Softsub",
            stop_event=self.stop_event,
            set_current_process=lambda p: setattr(self, 'current_process', p),
            clear_current_process=lambda: setattr(self, 'current_process', None),
        )                    


# Hàm xử lý ghép sub thủ công
    def _on_toggle_manual_merge_mode(self):
        is_manual_mode = self.manual_merge_mode_var.get()
        logging.info(f"Chế độ Ghép Sub Thủ Công được {'BẬT' if is_manual_mode else 'TẮT'}.")

        add_button_auto = getattr(self, 'add_button', None)
        add_button_manual = getattr(self, 'add_manual_task_button', None)
        queue_auto = getattr(self, 'queue_section', None)
        queue_manual = getattr(self, 'manual_queue_section', None)

        # LUÔN ẨN TẤT CẢ TRƯỚC
        if add_button_auto and add_button_auto.winfo_ismapped(): add_button_auto.pack_forget()
        if add_button_manual and add_button_manual.winfo_ismapped(): add_button_manual.pack_forget()
        if queue_auto and queue_auto.winfo_ismapped(): queue_auto.pack_forget()
        if queue_manual and queue_manual.winfo_ismapped(): queue_manual.pack_forget()

        # Xóa placeholder cũ trong cả hai hàng chờ (nếu có)
        if queue_auto:
            for widget in queue_auto.winfo_children(): widget.destroy()
        if queue_manual:
            for widget in queue_manual.winfo_children(): widget.destroy()

        # HIỂN THỊ LẠI CÁC THÀNH PHẦN ĐÚNG
        sub_and_dub_button = getattr(self, 'sub_and_dub_button', None)
        btn_row_frame = sub_and_dub_button.master if sub_and_dub_button else None
        
        if is_manual_mode:
            if add_button_manual and btn_row_frame:
                add_button_manual.pack(in_=btn_row_frame, side="left", expand=True, fill="x", padx=(2, 0))
            if queue_manual:
                right_panel_sub = getattr(self, 'right_panel_sub', None)
                sub_edit_frame = getattr(self, 'sub_edit_frame', None)
                if right_panel_sub and sub_edit_frame:
                    queue_manual.pack(in_=right_panel_sub, fill="x", padx=10, pady=(10, 5), before=sub_edit_frame)
                # KIỂM TRA VÀ HIỂN THỊ PLACEHOLDER THỦ CÔNG
                if not self.manual_sub_queue:
                    placeholder_text = (
                        "Hàng chờ trống.\n\n"
                        "Hướng dẫn:\n"
                        "1. Cung cấp Phụ đề (Nhập vào ô bên phải hoặc dùng 'Mở Sub...').\n"
                        "2. Chọn Media (Video/Ảnh) bằng nút 'Chọn Video/Ảnh Mới...'.\n"
                        "3. Nhấn '➕ Thêm vào Hàng chờ' để tạo một tác vụ."
                    )
                    ctk.CTkLabel(queue_manual, text=placeholder_text, text_color="gray", justify="left").pack(pady=20, padx=10)
        else: # Chế độ Tự động
            if add_button_auto and btn_row_frame:
                add_button_auto.pack(in_=btn_row_frame, side="left", expand=True, fill="x", padx=(2, 0))
            if queue_auto:
                right_panel_sub = getattr(self, 'right_panel_sub', None)
                sub_edit_frame = getattr(self, 'sub_edit_frame', None)
                if right_panel_sub and sub_edit_frame:
                    queue_auto.pack(in_=right_panel_sub, fill="x", padx=10, pady=(10, 5), before=sub_edit_frame)
                # KIỂM TRA VÀ HIỂN THỊ PLACEHOLDER TỰ ĐỘNG
                if not self.file_queue and not self.current_file:
                     ctk.CTkLabel(queue_auto, text="[Hàng chờ sub tự động trống]", font=("Segoe UI", 11), text_color="gray").pack(anchor="center", pady=20)

        self.master_app.save_current_config()
        self.master_app._set_subtitle_tab_ui_state(False)
        self.master_app._update_manual_mode_ui_elements()      


# Hàm hành động: Tải một file phụ đề đã có vào trình chỉnh sửa
    def load_old_sub_file(self):
        """ 
        Tải một file phụ đề.
        NẾU checkbox "Tự động định dạng" được bật, sẽ tái tạo timing với ngắt nghỉ động.
        NGƯỢC LẠI, sẽ hiển thị nội dung gốc của file.
        """
        if self.is_subbing and not self.is_actively_paused_for_edit: 
             messagebox.showwarning("Đang bận", "Vui lòng đợi xử lý phụ đề hiện tại hoàn tất.")
             return
        path = filedialog.askopenfilename(
             title="Chọn file Phụ đề để xem/chỉnh sửa",
             filetypes=[
                ("Tất cả file hỗ trợ", "*.srt *.vtt *.ass *.txt"),
                ("File phụ đề (Subrip)", "*.srt"),
                ("File văn bản (Text)", "*.txt"),
                ("File phụ đề (WebVTT)", "*.vtt"),
                ("File phụ đề (Advanced)", "*.ass"),
                ("Tất cả file", "*.*")
            ]
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8-sig") as f: 
                    content = f.read()

                self.last_loaded_script_path = path
                self.current_srt_path = path # Luôn cập nhật đường dẫn file đã mở
                self.allow_edit_sub = True   # Luôn cho phép sửa sau khi tải file

                # === BẮT ĐẦU LOGIC MỚI KIỂM TRA CHECKBOX ===
                if self.auto_format_plain_text_to_srt_var.get():
                    logging.info(f"Đang tự động định dạng và tái tạo timing cho file: {os.path.basename(path)}")
                    self.update_status(f"⏳ Đang định dạng lại timing cho {os.path.basename(path)}...")
                    
                    # 1. Trích xuất text thuần, bỏ qua timing cũ
                    plain_text = extract_dialogue_from_srt_string(content)
                    
                    # 2. Lấy cấu hình từ UI
                    split_cfg = {
                        "split_enabled": self.enable_split_var.get(),
                        "mode": self.split_mode_var.get(),
                        "max_chars": safe_int(self.max_chars_var.get(), 90),
                        "max_lines": safe_int(self.max_lines_var.get(), 1),
                        "DEFAULT_CPS_FOR_TIMING": safe_int(self.sub_cps_for_timing_var.get(), 17),
                        "PAUSE_BETWEEN_SEGMENTS_MS_FOR_TIMING": 1, # Sẽ bị logic ngắt nghỉ động ghi đè
                        "ABSOLUTE_MIN_DURATION_PER_CHUNK_MS": self.min_duration_per_segment_ms
                    }
                    
                    # 3. Tạo lại dữ liệu SRT với timing mới
                    retimed_data = self._parse_plain_text_to_srt_data(plain_text, True, split_cfg)
                    
                    if retimed_data:
                        final_content = format_srt_data_to_string(retimed_data)
                        self.current_srt_path = None # Reset vì nội dung đã khác file gốc
                        self.update_status("✅ Đã tái tạo timing thành công!")
                    else:
                        final_content = content # Fallback về nội dung gốc nếu lỗi
                        self.update_status("⚠️ Lỗi tái tạo timing, hiển thị file gốc.")
                    
                    self.show_sub_in_textbox(final_content)

                else: # Nếu checkbox không được tích, chỉ hiển thị nội dung gốc
                    logging.info(f"Hiển thị nội dung gốc của file: {os.path.basename(path)}")
                    self.show_sub_in_textbox(content) 
                # === KẾT THÚC LOGIC MỚI ===

                subtitle_textbox = getattr(self.subtitle_view_frame, 'subtitle_textbox', None) if hasattr(self, 'subtitle_view_frame') else None
                if subtitle_textbox and subtitle_textbox.winfo_exists():
                    subtitle_textbox.configure(state="normal")
                self.update_status(f"Đã mở file: {os.path.basename(path)}")

            except Exception as e:
                logging.error(f"Lỗi khi tải file phụ đề cũ '{path}': {e}", exc_info=True)
                messagebox.showerror("Lỗi Đọc", f"Không thể đọc file:\n{path}\n\nLỗi: {e}")
                self.current_srt_path = None
                self.last_loaded_script_path = None
                self.show_sub_in_textbox("")   


    # Hàm hành động: Lưu nội dung của ô textbox phụ đề
    def save_edited_sub(self):
        """ Lưu nội dung của ô textbox phụ đề """
        save_path = self.current_srt_path
        if not save_path: # Nếu chưa có file nào được tải/tạo, hỏi nơi lưu
            save_path = filedialog.asksaveasfilename(
                 title="Lưu File Phụ đề",
                 defaultextension=".srt",
                 filetypes=[("SubRip", ".srt"), ("WebVTT", ".vtt"), ("ASS", ".ass"), ("Văn bản", ".txt")],
                 initialdir=self.output_path_var.get() or os.getcwd()
            )
            if not save_path:
                logging.info("Người dùng đã hủy thao tác lưu.")
                return # Người dùng hủy
            self.current_srt_path = save_path
            # Cập nhật biến định dạng dựa trên đuôi file đã chọn (tùy chọn nhưng tốt)
            _, ext = os.path.splitext(save_path)
            new_fmt = ext.lstrip('.').lower()
            if new_fmt in ["srt", "vtt", "ass", "txt"]: self.format_var.set(new_fmt)
            else: # Mặc định về srt nếu đuôi file không xác định
                 self.format_var.set("srt")
                 self.current_srt_path = os.path.splitext(save_path)[0] + ".srt"

        try:
            # 1. Bật state='normal' để lấy nội dung
            subtitle_textbox = getattr(self.subtitle_view_frame, 'subtitle_textbox', None) if hasattr(self, 'subtitle_view_frame') else None
            if subtitle_textbox and subtitle_textbox.winfo_exists():
                subtitle_textbox.configure(state="normal")
                new_text = subtitle_textbox.get("0.0", "end-1c") # Lấy tất cả text trừ dòng mới cuối cùng
            else:
                logging.error("Textbox phụ đề không khả dụng để lấy nội dung.")
                messagebox.showerror("Lỗi UI", "Không thể truy cập ô nội dung phụ đề.")
                return

            # 2. Kiểm tra nội dung rỗng
            if not new_text.strip():
                 messagebox.showwarning("Nội dung rỗng", "Không có nội dung để lưu.")
                 # Nếu không có nội dung và không cho phép sửa, thì disable lại
                 if not self.allow_edit_sub and subtitle_textbox:
                      subtitle_textbox.configure(state="disabled")
                 return

            # 3. Lưu file
            with open(self.current_srt_path, "w", encoding="utf-8") as f: f.write(new_text)
            self.update_status(f"💾 Đã lưu: {os.path.basename(self.current_srt_path)}")
            logging.info(f"Lưu thành công: {self.current_srt_path}")

            # 4. Luôn tắt chế độ chỉnh sửa sau khi lưu thành công
            self.allow_edit_sub = False
            if subtitle_textbox and subtitle_textbox.winfo_exists():
                subtitle_textbox.configure(state="disabled")

            # Nếu nội dung đã lưu là rỗng (sau khi strip), hiển thị lại placeholder
            if not new_text.strip():
                self.show_sub_in_textbox("") # Gọi hàm đã sửa, nó sẽ tự chèn placeholder

        except Exception as e:
            logging.error(f"Lỗi khi lưu file phụ đề '{self.current_srt_path}': {e}", exc_info=True)
            messagebox.showerror("Lỗi Lưu File", f"Không thể lưu file:\n{self.current_srt_path}\n\nLỗi: {e}")
            # Cố gắng disable lại textbox nếu có lỗi xảy ra và không cho phép sửa
            try:
                subtitle_textbox = getattr(self.subtitle_view_frame, 'subtitle_textbox', None) if hasattr(self, 'subtitle_view_frame') else None
                if subtitle_textbox and subtitle_textbox.winfo_exists() and not self.allow_edit_sub:
                    subtitle_textbox.configure(state="disabled")
            except Exception: pass # Bỏ qua lỗi phụ                       


    # Hàm hành động: Cho phép chỉnh sửa ô textbox phụ đề
    def enable_sub_editing(self):
        """ Cho phép chỉnh sửa ô textbox phụ đề """
        self.allow_edit_sub = True
        subtitle_textbox = getattr(self.subtitle_view_frame, 'subtitle_textbox', None) if hasattr(self, 'subtitle_view_frame') else None
        if subtitle_textbox and subtitle_textbox.winfo_exists():
            subtitle_textbox.configure(state="normal")
            logging.info("Đã bật chế độ chỉnh sửa phụ đề.")     



# Đây là hàm sẽ chạy trong luồng để thực hiện việc ghép thủ công
    def _execute_manual_merge_threaded(self, task):
        """
        Hàm worker (chạy trong luồng): Thực thi một tác vụ ghép sub thủ công.
        Hàm này nhận vào một dictionary 'task' đã được chuẩn bị đầy đủ.
        """
        log_prefix = f"[{threading.current_thread().name}]"
        success = False
        merged_output_final_path = None
        error_message = None

        # Khai báo biến ở scope rộng hơn để khối except có thể truy cập
        merge_mode_for_log = "không xác định"
        
        try:
            video_path = task.get('media_data')
            srt_path = task.get('srt_path_for_ffmpeg')
            output_dir = task.get('final_output_dir')
            cfg_snapshot = task.get('cfg_snapshot', {})
            
            # Gán giá trị cho merge_mode_for_log để sử dụng trong cả try và except
            merge_mode_for_log = cfg_snapshot.get('merge_mode', 'không gộp')

            # Lấy "key định danh" đã được quyết định trước từ task object
            safe_output_base_name = task.get('identifier')
            
            # Thêm một fallback mạnh mẽ phòng trường hợp 'identifier' bị thiếu hoặc rỗng
            if not safe_output_base_name:
                logging.warning(f"{log_prefix} Task object thiếu 'identifier'. Fallback về tên media.")
                fallback_path = task.get('original_media_source_path') or task.get('media_data')
                base_name_fallback = os.path.splitext(os.path.basename(fallback_path))[0]
                safe_output_base_name = create_safe_filename(base_name_fallback, remove_accents=False)

            logging.info(f"{log_prefix} Sẽ sử dụng identifier đã được quyết định trước làm tên file: '{safe_output_base_name}'")
            
            temp_srt_to_delete = task.get('temp_srt_to_delete')

            if not all([video_path, srt_path, output_dir, merge_mode_for_log, safe_output_base_name]):
                raise ValueError("Worker nhận được thông tin tác vụ không đầy đủ.")

            if self.master_app.stop_event.is_set():
                raise InterruptedError("Ghép thủ công bị dừng trước khi bắt đầu FFmpeg.")

            def _update_status_thread_safe(msg):
                self.master_app.after(0, lambda m=msg: self.update_status(m))

            if merge_mode_for_log == "hard-sub":
                merged_output_final_path = os.path.join(output_dir, f"{safe_output_base_name}_hardsub_manual.mp4")
                _update_status_thread_safe(f"🔨 Đang hardsub (thủ công): {os.path.basename(video_path)}")
                self.burn_sub_to_video(video_path, srt_path, merged_output_final_path, cfg_snapshot)
            elif merge_mode_for_log == "soft-sub":
                merged_output_final_path = os.path.join(output_dir, f"{safe_output_base_name}_softsub_manual.mkv")
                _update_status_thread_safe(f"🔨 Đang softsub (thủ công): {os.path.basename(video_path)}")
                self.merge_sub_as_soft_sub(video_path, srt_path, merged_output_final_path)
            else:
                # Nếu không phải hard-sub hay soft-sub, coi như thành công và không làm gì
                success = True
                merged_output_final_path = video_path
                # return không cần thiết ở đây, để khối finally chạy

            if not success: # Chỉ kiểm tra nếu chưa được đặt là True
                if self.master_app.stop_event.is_set():
                    raise InterruptedError("Ghép thủ công bị dừng trong quá trình FFmpeg.")

                if merged_output_final_path and os.path.exists(merged_output_final_path) and os.path.getsize(merged_output_final_path) > 1000:
                    success = True
                    logging.info(f"{log_prefix} Ghép {merge_mode_for_log} thủ công thành công: {merged_output_final_path}")
                else:
                    error_message = f"FFmpeg không tạo được file output hoặc file output rỗng ({merge_mode_for_log})."
                    logging.error(f"{log_prefix} {error_message}")
                    success = False

        except InterruptedError as ie:
            success = False
            error_message = f"Quá trình ghép thủ công đã bị dừng bởi người dùng."
            logging.warning(f"{log_prefix} {error_message} ({ie})")
        except Exception as e:
            success = False
            # Sử dụng biến merge_mode_for_log đã được định nghĩa ở scope ngoài
            error_message = f"Lỗi trong quá trình ghép {merge_mode_for_log} thủ công: {e}"
            logging.error(f"{log_prefix} {error_message}", exc_info=True)

        finally:
            if temp_srt_to_delete and os.path.exists(temp_srt_to_delete):
                try:
                    os.remove(temp_srt_to_delete)
                    logging.info(f"{log_prefix} Đã xóa file sub tạm: {temp_srt_to_delete}")
                except Exception as e_del_temp:
                    logging.warning(f"{log_prefix} Lỗi xóa file sub tạm '{temp_srt_to_delete}': {e_del_temp}")

            self.master_app.after(0, self._handle_manual_task_completion, task.get('id'), success, merged_output_final_path, error_message)
    
    # ========================================================================
    # CONFIG SAVE FUNCTION
    # ========================================================================
    
    def save_config(self):
        """Lưu cấu hình Subtitle Tab vào master_app.cfg"""
        if not hasattr(self.master_app, 'cfg'):
            self.logger.error("master_app không có thuộc tính cfg")
            return
        
        # Lưu các cấu hình Subtitle Tab
        self.master_app.cfg["language"] = self.source_lang_var.get()
        self.master_app.cfg["merge_mode"] = self.merge_sub_var.get()
        self.master_app.cfg["bilingual"] = self.bilingual_var.get()
        self.master_app.cfg["target_lang"] = self.target_lang_var.get()
        self.master_app.cfg["split"] = self.enable_split_var.get()
        self.master_app.cfg["max_chars"] = int(self.max_chars_var.get())
        self.master_app.cfg["max_lines"] = int(self.max_lines_var.get())
        self.master_app.cfg["sub_cps_for_timing"] = int(self.sub_cps_for_timing_var.get())
        self.master_app.cfg["split_mode"] = self.split_mode_var.get()
        
        # Pacing
        self.master_app.cfg["sub_pacing_pause_medium_ms"] = int(self.sub_pacing_pause_medium_ms_var.get())
        self.master_app.cfg["sub_pacing_pause_period_ms"] = int(self.sub_pacing_pause_period_ms_var.get())
        self.master_app.cfg["sub_pacing_pause_question_ms"] = int(self.sub_pacing_pause_question_ms_var.get())
        self.master_app.cfg["sub_pacing_long_sentence_threshold"] = int(self.sub_pacing_long_sentence_threshold_var.get())
        self.master_app.cfg["sub_pacing_fast_cps_multiplier"] = float(self.sub_pacing_fast_cps_multiplier_var.get())
        
        # Style
        self.master_app.cfg["sub_style_font_name"] = self.sub_style_font_name_var.get()
        self.master_app.cfg["sub_style_font_size"] = self.sub_style_font_size_var.get()
        self.master_app.cfg["sub_style_font_bold"] = self.sub_style_font_bold_var.get()
        self.master_app.cfg["sub_style_text_color_rgb_str"] = self.sub_style_text_color_rgb_str_var.get()
        self.master_app.cfg["sub_style_text_opacity_percent"] = self.sub_style_text_opacity_percent_var.get()
        self.master_app.cfg["sub_style_background_mode"] = self.sub_style_background_mode_var.get()
        self.master_app.cfg["sub_style_bg_color_rgb_str"] = self.sub_style_bg_color_rgb_str_var.get()
        self.master_app.cfg["sub_style_bg_box_actual_opacity_percent"] = self.sub_style_bg_box_actual_opacity_percent_var.get()
        self.master_app.cfg["sub_style_outline_enabled"] = self.sub_style_outline_enabled_var.get()
        self.master_app.cfg["sub_style_outline_size"] = self.sub_style_outline_size_var.get()
        self.master_app.cfg["sub_style_outline_color_rgb_str"] = self.sub_style_outline_color_rgb_str_var.get()
        self.master_app.cfg["sub_style_outline_opacity_percent"] = self.sub_style_outline_opacity_percent_var.get()
        self.master_app.cfg["margin_v"] = self.sub_style_marginv_var.get()
        
        # FFmpeg
        self.master_app.cfg["ffmpeg_encoder"] = self.ffmpeg_encoder_var.get()
        self.master_app.cfg["ffmpeg_preset"] = self.ffmpeg_preset_var.get()
        self.master_app.cfg["ffmpeg_crf"] = int(self.ffmpeg_crf_var.get())
        
        # Block Merging
        self.master_app.cfg["enable_block_merging"] = self.enable_block_merging_var.get()
        self.master_app.cfg["merge_max_time_gap_ms"] = int(self.merge_max_time_gap_var.get())
        self.master_app.cfg["merge_curr_max_len"] = int(self.merge_curr_max_len_normal_var.get())
        
        # Pause for Edit
        self.master_app.cfg["pause_for_edit"] = self.pause_for_edit_var.get()
        
        # Manual Merge
        self.master_app.cfg["manual_merge_mode"] = self.manual_merge_mode_var.get()
        
        # Others
        self.master_app.cfg["auto_format_plain_text_to_srt"] = self.auto_format_plain_text_to_srt_var.get()
        self.master_app.cfg["auto_add_manual_sub_task"] = self.auto_add_manual_sub_task_var.get()
        self.master_app.cfg["save_in_media_folder"] = self.save_in_media_folder_var.get()
        self.master_app.cfg["optimize_whisper_tts_voice"] = self.optimize_whisper_tts_voice_var.get()
        
        # Output & Model
        self.master_app.cfg["output_path"] = self.output_path_var.get()
        self.master_app.cfg["model"] = self.model_var.get()
        self.master_app.cfg["format"] = self.format_var.get()
        
        self.logger.debug("[SubtitleTab.save_config] Đã lưu cấu hình Subtitle Tab vào master_app.cfg")                   