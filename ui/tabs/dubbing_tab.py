# -*- coding: utf-8 -*-
# File: ui/tabs/dubbing_tab.py

import customtkinter as ctk
import os
import logging
from tkinter import filedialog, messagebox

# Import các thành phần UI chung
from config.ui_constants import get_theme_colors
from ui.widgets.tooltip import Tooltip
from ui.widgets.menu_utils import textbox_right_click_menu
from ui.widgets.custom_voice_dropdown import CustomVoiceDropdown
from services.tts_service import TTSService

# Import các hàm tiện ích
from utils.helpers import open_file_with_default_app, get_default_downloads_folder
from config.constants import APP_NAME

# Import optional libraries
try:
    from underthesea import sent_tokenize
    HAS_UNDERTHESEA = True
except ImportError:
    HAS_UNDERTHESEA = False
    sent_tokenize = None


class DubbingTab(ctk.CTkFrame):
    """
    Lớp quản lý toàn bộ giao diện và logic cho Tab Thuyết Minh (Dubbing).
    """

    def __init__(self, master, master_app):
        """
        Khởi tạo frame cho Tab Thuyết Minh.

        Args:
            master (ctk.CTkFrame): Frame cha (main_content_frame từ SubtitleApp).
            master_app (SubtitleApp): Instance của ứng dụng chính (PiuApp).
        """
        super().__init__(master, fg_color="transparent")
        self.master_app = master_app
        self.logger = logging.getLogger(APP_NAME)

        # Khai báo các widget con của tab này (sẽ được gán trong _build_ui)
        # Action buttons
        self.dub_load_audio_button = None
        self.dub_load_script_button = None
        self.dub_start_batch_button = None
        self.dub_stop_button = None
        self.dub_load_video_button = None
        
        # Output config
        self.dub_lbl_output_dir_display_left = None
        self.dub_select_output_dir_button = None
        self.dub_btn_open_output_folder_left = None
        
        # Slideshow
        self.dub_slideshow_folder_frame = None
        self.dub_chk_use_image_folder = None
        self.dub_btn_browse_image_folder = None
        self.dub_lbl_image_folder_path = None
        
        # TTS controls
        self.dub_tts_controls_frame = None
        self.dub_tts_engine_menu = None
        self.voice_row_frame_ref = None
        self.dub_voice_option_menu = None
        self.ssml_row_frame = None
        self.dub_chk_use_google_ssml = None
        self.api_settings_button_dub_tab = None
        self.branding_settings_button_dub_tab = None
        
        # Audio output
        self.dub_audio_output_options_frame = None
        self.dub_background_audio_menu = None
        self.dub_mix_level_controls_frame = None
        self.dub_lbl_mix_level = None
        self.dub_slider_mix_level = None
        self.dub_lbl_mix_level_display = None
        self.dub_custom_bg_music_frame = None
        self.checkbox_and_volume_grid_frame = None
        self.dub_chk_use_custom_bg_music = None
        self.dub_lbl_custom_bg_music_volume_title_inline = None
        self.custom_bg_vol_entry_frame = None
        self.dub_entry_custom_bg_music_volume = None
        self.percent_label_for_custom_vol = None
        self.dub_music_selection_controls_frame = None
        self.dub_btn_browse_bg_folder = None
        self.dub_btn_browse_bg_music = None
        self.dub_chk_randomize_music = None
        self.dub_lbl_bg_music_path = None
        
        # Flow optimization
        self.dub_flow_optimization_frame = None
        self.chk_optimize_dub_flow = None
        self.dub_flow_details_frame = None
        self.dub_max_chars_entry_flow = None
        self.dub_max_lines_entry_flow = None
        self.dub_split_mode_menu_flow = None
        self.chk_force_recalculate_timing = None
        self.chk_dub_auto_optimize_on_paste = None
        
        # Advanced audio
        self.dub_advanced_audio_main_frame = None
        self.dub_chk_show_advanced_audio_settings = None
        self.dub_advanced_audio_processing_frame = None
        
        # Right panel
        self.dub_queue_display_frame = None
        self.placeholder_dub_queue = None
        self.dub_script_textbox = None
        self.ai_edit_dub_script_button = None
        self.dalle_button_dub_tab = None
        self.imagen_button_dub_tab = None
        self.dub_btn_edit_script = None
        self.dub_btn_save_script = None
        self.dub_preview_button = None
        self.dub_btn_save_audio_from_text = None

        # Gọi hàm xây dựng UI
        self._build_ui()

        self.logger.info("DubbingTab đã được khởi tạo.")

    def _build_ui(self):
        """
        Tạo các thành phần UI cho tab Thuyết Minh.
        (Đây là hàm _create_dubbing_tab cũ, đã được di chuyển sang đây)
        """
        self.logger.debug("[DubbingUI] Đang tạo UI cho tab Thuyết Minh (Theme-Aware)...")

        # --- Định nghĩa các màu sắc thích ứng theme ---
        colors = get_theme_colors()
        panel_bg_color = colors["panel_bg"]
        card_bg_color = colors["card_bg"]
        textbox_bg_color = colors["textbox_bg"]
        danger_button_color = colors["danger_button"]
        danger_button_hover_color = colors["danger_button_hover"]
        special_action_button_color = colors["special_action_button"]
        special_action_hover_color = colors["special_action_hover"]

        main_frame_dub = ctk.CTkFrame(self, fg_color="transparent")
        main_frame_dub.pack(fill="both", expand=True)

        main_frame_dub.grid_columnconfigure(0, weight=1, uniform="panelgroup")
        main_frame_dub.grid_columnconfigure(1, weight=2, uniform="panelgroup")
        main_frame_dub.grid_rowconfigure(0, weight=1)

        # --- KHUNG BÊN TRÁI - CONTAINER CỐ ĐỊNH CHIỀU RỘNG (Panel Điều khiển) ---
        dub_left_panel_container = ctk.CTkFrame(main_frame_dub, fg_color=panel_bg_color, corner_radius=12)
        dub_left_panel_container.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew") 
        dub_left_panel_container.pack_propagate(False) 

        dub_left_scrollable_content = ctk.CTkScrollableFrame(dub_left_panel_container, fg_color="transparent") 
        dub_left_scrollable_content.pack(expand=True, fill="both", padx=0, pady=0) 

        # === CỤM NÚT HÀNH ĐỘNG CHÍNH (DUBBING) ===
        self._create_dubbing_action_buttons_section(
            dub_left_scrollable_content,
            special_action_button_color,
            special_action_hover_color,
            danger_button_color,
            danger_button_hover_color
        )

        # === KHUNG CÀI ĐẶT OUTPUT ===
        self._create_dubbing_output_config_section(dub_left_scrollable_content, card_bg_color)

        # === KHUNG TÙY CHỌN SLIDESHOW ===
        self._create_dubbing_slideshow_section(dub_left_scrollable_content, card_bg_color)

        # === KHUNG ĐIỀU KHIỂN TTS ===
        self._create_dubbing_tts_controls_section(
            dub_left_scrollable_content,
            card_bg_color,
            special_action_button_color,
            special_action_hover_color
        )

        # === KHUNG TÙY CHỌN ÂM THANH NỀN ===
        self._create_dubbing_audio_output_section(dub_left_scrollable_content, card_bg_color)

        # === KHUNG TÙY CHỈNH TỐI ƯU LUỒNG ĐỌC ===
        self._create_dubbing_flow_optimization_section(dub_left_scrollable_content, card_bg_color)

        # === KHUNG TÙY CHỈNH AUDIO NÂNG CAO ===
        self._create_dubbing_advanced_audio_section(dub_left_scrollable_content, card_bg_color)

        # TTS Voice Dropdown - created separately because it requires self
        self.dub_voice_option_menu = CustomVoiceDropdown(
            master=self.voice_row_frame_ref, 
            master_app=self.master_app,
            variable=self.master_app.dub_selected_voice_display_name_var,
            values_dict=self.master_app.dub_current_engine_voice_display_to_id_map
        )
        self.dub_voice_option_menu.grid(row=0, column=1, sticky="ew")

        # Expose widgets/frames to master_app so existing handlers (in main app) can access them
        # This keeps backward compatibility with logic that references these attributes on the app instance
        self.master_app.dub_voice_option_menu = self.dub_voice_option_menu
        self.master_app.voice_row_frame_ref = self.voice_row_frame_ref
        self.master_app.ssml_row_frame = self.ssml_row_frame
        self.master_app.dub_tts_controls_frame = self.dub_tts_controls_frame

        # Optional: warm up Google TTS voices cache in background (non-blocking)
        def _warm_google_cache():
            try:
                key_path = getattr(self.master_app, 'google_key_path_var', None)
                key_path_val = key_path.get() if key_path else None
                if key_path_val and os.path.exists(key_path_val):
                    tts = TTSService(cache_dir=os.getcwd())
                    tts.get_google_voices(key_json_path=key_path_val, prefer_cache=True)
            except Exception:
                pass
        self.after(200, _warm_google_cache)

        # --- KHUNG BÊN PHẢI ---
        self._create_dubbing_right_panel(
            main_frame_dub, panel_bg_color, card_bg_color, textbox_bg_color,
            special_action_button_color, special_action_hover_color
        )

        self.master_app.after(50, lambda: self.master_app.dub_on_tts_engine_selected(self.master_app.dub_selected_tts_engine_var.get()))
        self.master_app.after(100, lambda: self.master_app.dub_on_background_audio_option_changed(self.master_app.dub_background_audio_option_var.get()))
        self.master_app.after(150, self.master_app.update_dub_queue_display)
        self.master_app.after(200, self.master_app._update_dub_script_controls_state)
        self.master_app.after(250, self.master_app._update_dub_start_batch_button_state)
        self.master_app.after(300, self.master_app._toggle_dub_flow_options_visibility)
        
        self.logger.debug("[DubbingUI] Tạo xong UI cho tab Thuyết Minh với layout đã cập nhật theme-aware (đầy đủ).")

    # ========================================================================
    # UI CREATION METHODS - Di chuyển từ Piu.py
    # ========================================================================

    def _create_dubbing_action_buttons_section(self, parent_frame, special_action_button_color, special_action_hover_color, danger_button_color, danger_button_hover_color):
        """Create action buttons section for Dubbing tab"""
        action_buttons_main_frame_dubbing = ctk.CTkFrame(parent_frame, fg_color="transparent")
        action_buttons_main_frame_dubbing.pack(pady=10, padx=10, fill="x")
        
        # Row 1: Load Audio and Script buttons
        btn_row_1_dubbing = ctk.CTkFrame(action_buttons_main_frame_dubbing, fg_color="transparent")
        btn_row_1_dubbing.pack(fill="x", pady=(0, 5))
        btn_row_1_dubbing.grid_columnconfigure(0, weight=1, uniform="equal")
        btn_row_1_dubbing.grid_columnconfigure(1, weight=1, uniform="equal")
        
        # --- KIỂM TRA BẢN QUYỀN (chuẩn hoá) ---
        try:
            is_app_active_on_create = self.master_app._is_app_fully_activated()
        except Exception:
            is_app_active_on_create = False

        unactivated_text_short_on_create = "🔒 Kích hoạt"

        initial_audio_button_text = "🎵 Chọn Audio..."
        initial_script_button_text = "📜 Chọn Script..."
        initial_button_state = ctk.NORMAL if is_app_active_on_create else ctk.DISABLED
        if not is_app_active_on_create:
            initial_audio_button_text = unactivated_text_short_on_create
            initial_script_button_text = unactivated_text_short_on_create
        
        self.dub_load_audio_button = ctk.CTkButton(
            btn_row_1_dubbing, text=initial_audio_button_text, 
            state=initial_button_state, height=35, font=("Segoe UI", 13, "bold"),
            command=self.master_app.dub_load_audio_file,
        )
        self.dub_load_audio_button.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        
        self.dub_load_script_button = ctk.CTkButton(
            btn_row_1_dubbing, text=initial_script_button_text, 
            state=initial_button_state, height=35, font=("Segoe UI", 13, "bold"),
            command=self.master_app.dub_load_script,
        )
        self.dub_load_script_button.grid(row=0, column=1, sticky="ew", padx=(3, 0))
        
        # Row 2: Start Dubbing button - spans full width
        self.dub_start_batch_button = ctk.CTkButton(
            action_buttons_main_frame_dubbing, text="🚀 Bắt đầu Dubbing Hàng loạt",
            height=45, font=("Segoe UI", 15, "bold"),
            command=self.master_app.dub_start_batch_processing, state="disabled",
            fg_color=special_action_button_color, hover_color=special_action_hover_color
        )
        self.dub_start_batch_button.pack(pady=5, fill="x")
        
        # Row 3: Stop button and Load Video button
        btn_row_3_dubbing_controls = ctk.CTkFrame(action_buttons_main_frame_dubbing, fg_color="transparent")
        btn_row_3_dubbing_controls.pack(fill="x", pady=(5, 0))
        btn_row_3_dubbing_controls.grid_columnconfigure(0, weight=1)
        btn_row_3_dubbing_controls.grid_columnconfigure(1, weight=1)
        
        self.dub_stop_button = ctk.CTkButton(
            btn_row_3_dubbing_controls, text="🛑 Dừng TM", 
            height=35, font=("Segoe UI", 13, "bold"),
            command=self.master_app.dub_stop_processing, state="disabled",
            fg_color=danger_button_color, hover_color=danger_button_hover_color, border_width=0
        )
        self.dub_stop_button.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        
        self.dub_load_video_button = ctk.CTkButton(
            btn_row_3_dubbing_controls, text="🎬 Video/Ảnh...",
            height=35, font=("Segoe UI", 13, "bold"),
            command=self.master_app.dub_load_video, border_width=0
        )
        self.dub_load_video_button.grid(row=0, column=1, sticky="ew", padx=(3, 0))
        
        return action_buttons_main_frame_dubbing

    def _create_dubbing_output_config_section(self, parent_frame, card_bg_color):
        """Create output configuration section for Dubbing tab"""
        dub_output_config_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        dub_output_config_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(
            dub_output_config_frame, 
            text="📁 Thư mục lưu Video (Hàng loạt):", 
            font=("Poppins", 13, "bold")
        ).pack(anchor="w", padx=10, pady=(5,2))
        
        self.dub_lbl_output_dir_display_left = ctk.CTkLabel(
            dub_output_config_frame, 
            textvariable=self.master_app.dub_output_path_var, 
            wraplength=300, 
            font=("Segoe UI", 10), 
            text_color=("gray30", "gray70"), 
            anchor="w", 
            justify="left"
        )
        self.dub_lbl_output_dir_display_left.pack(fill="x", padx=10, pady=(2,5))
        
        dub_output_buttons_container = ctk.CTkFrame(dub_output_config_frame, fg_color="transparent")
        dub_output_buttons_container.pack(fill="x", padx=10, pady=(0, 5))
        # Use grid so the two buttons expand evenly across available width
        dub_output_buttons_container.grid_columnconfigure(0, weight=1)
        dub_output_buttons_container.grid_columnconfigure(1, weight=1)
        
        self.dub_select_output_dir_button = ctk.CTkButton(
            dub_output_buttons_container, 
            text="Chọn thư mục lưu...", 
            height=30, 
            font=("Poppins", 12), 
            command=self.master_app.dub_select_output_dir
        )
        self.dub_select_output_dir_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.dub_btn_open_output_folder_left = ctk.CTkButton(
            dub_output_buttons_container, 
            text="📂 Mở Output", 
            height=30, 
            font=("Poppins", 12), 
            command=self.master_app.dub_open_output_folder
        )
        self.dub_btn_open_output_folder_left.grid(row=0, column=1, sticky="ew")
        
        ctk.CTkLabel(
            dub_output_config_frame, 
            text="ⓘ Lưu ý: Các cài đặt từ panel trái (giọng đọc, âm thanh nền,...)\nsẽ được áp dụng cho tác vụ tiếp theo được thêm vào hàng chờ.",
            font=("Segoe UI", 10), 
            text_color=("gray40", "gray60"), 
            justify="left"
        ).pack(fill="x", padx=10, pady=(0, 8))
        
        return dub_output_config_frame

    def _create_dubbing_slideshow_section(self, parent_frame, card_bg_color):
        """Create slideshow image folder section for Dubbing tab"""
        self.dub_slideshow_folder_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        self.dub_slideshow_folder_frame.pack(pady=(0, 5), padx=10, fill="x")
        
        self.dub_chk_use_image_folder = ctk.CTkCheckBox(
            self.dub_slideshow_folder_frame, 
            text="🖼 Tạo Slideshow từ Thư mục Ảnh", 
            variable=self.master_app.dub_use_image_folder_var, 
            command=self.master_app.dub_update_image_folder_controls_visibility, 
            font=("Segoe UI", 12), 
            checkbox_width=18, 
            checkbox_height=18
        )
        self.dub_chk_use_image_folder.pack(anchor="w", padx=10, pady=(8, 5))
        
        self.dub_btn_browse_image_folder = ctk.CTkButton(
            self.dub_slideshow_folder_frame, 
            text="Chọn thư mục ảnh...", 
            height=30, 
            font=("Segoe UI", 11), 
            command=self.master_app.dub_browse_image_folder_for_slideshow
        )
        self.dub_btn_browse_image_folder.pack(anchor="w", padx=10, pady=(0, 5))
        
        self.dub_lbl_image_folder_path = ctk.CTkLabel(
            self.dub_slideshow_folder_frame, 
            textvariable=self.master_app.dub_selected_image_folder_path_var, 
            wraplength=300, 
            anchor="w", 
            font=("Segoe UI", 10), 
            text_color=("gray30", "gray70"), 
            justify=ctk.LEFT
        )
        self.dub_lbl_image_folder_path.pack(fill="x", padx=10, pady=(0, 8))
        
        return self.dub_slideshow_folder_frame

    def _create_dubbing_tts_controls_section(self, parent_frame, card_bg_color, special_action_button_color, special_action_hover_color):
        """Create TTS engine and voice controls section for Dubbing tab"""
        self.dub_tts_controls_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        self.dub_tts_controls_frame.pack(pady=(0,5), padx=10, fill="x")
        
        # TTS Engine selection
        tts_engine_row_frame = ctk.CTkFrame(self.dub_tts_controls_frame, fg_color="transparent")
        tts_engine_row_frame.pack(fill="x", padx=10, pady=(8,5))
        
        ctk.CTkLabel(
            tts_engine_row_frame, 
            text="🔊 Engine TTS:", 
            font=("Poppins", 12, "bold")
        ).grid(row=0, column=0, sticky="w", padx=(0,5))
        
        self.dub_tts_engine_menu = ctk.CTkOptionMenu(
            tts_engine_row_frame, 
            variable=self.master_app.dub_selected_tts_engine_var, 
            values=list(self.master_app.dub_tts_voice_options.keys()), 
            command=self.master_app.dub_on_tts_engine_selected
        )
        self.dub_tts_engine_menu.grid(row=0, column=1, sticky="ew", padx=(5,0))
        tts_engine_row_frame.grid_columnconfigure(1, weight=1)
        
        # Voice selection
        self.voice_row_frame_ref = ctk.CTkFrame(self.dub_tts_controls_frame, fg_color="transparent")
        self.voice_row_frame_ref.pack(fill="x", padx=10, pady=(5,5))
        
        ctk.CTkLabel(
            self.voice_row_frame_ref, 
            text="🎙 Giọng đọc:", 
            font=("Poppins", 12, "bold")
        ).grid(row=0, column=0, sticky="w", padx=(0,5))
        
        # Voice dropdown will be created here
        self.voice_row_frame_ref.grid_columnconfigure(1, weight=1)
        
        # SSML option
        self.ssml_row_frame = ctk.CTkFrame(self.dub_tts_controls_frame, fg_color="transparent")
        self.ssml_row_frame.pack(fill="x", padx=10, pady=(5,5))
        
        self.dub_chk_use_google_ssml = ctk.CTkCheckBox(
            self.ssml_row_frame, 
            text="Tạo SSML cơ bản (Google TTS)", 
            variable=self.master_app.dub_use_google_ssml_var, 
            font=("Segoe UI", 11), 
            checkbox_width=18, 
            checkbox_height=18
        )
        self.dub_chk_use_google_ssml.pack(anchor="w")
        # Expose checkbox to master_app so app-level logic can update its state/text
        self.master_app.dub_chk_use_google_ssml = self.dub_chk_use_google_ssml
        
        # API and Branding buttons
        api_button_row_frame = ctk.CTkFrame(self.dub_tts_controls_frame, fg_color="transparent")
        api_button_row_frame.pack(fill="x", padx=10, pady=(5,8))
        # Use grid so both buttons expand evenly
        api_button_row_frame.grid_columnconfigure(0, weight=1)
        api_button_row_frame.grid_columnconfigure(1, weight=1)
        
        self.api_settings_button_dub_tab = ctk.CTkButton(
            api_button_row_frame, 
            text="🔑 API Keys...", 
            font=("Poppins", 13), 
            height=30, 
            command=self.master_app.open_api_settings_window, 
            fg_color=special_action_button_color, 
            hover_color=special_action_hover_color
        )
        self.api_settings_button_dub_tab.grid(row=0, column=0, padx=(0,5), sticky="ew")
        
        self.branding_settings_button_dub_tab = ctk.CTkButton(
            api_button_row_frame, 
            text="🎨 Logo/Intro", 
            height=30, 
            font=("Poppins", 13), 
            command=self.master_app.open_branding_settings_window
        )
        self.branding_settings_button_dub_tab.grid(row=0, column=1, sticky="ew")
        
        return self.dub_tts_controls_frame

    def _create_dubbing_audio_output_section(self, parent_frame, card_bg_color):
        """Create audio output and background music section for Dubbing tab"""
        self.dub_audio_output_options_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        self.dub_audio_output_options_frame.pack(pady=(0,5), padx=10, fill="x")
        
        ctk.CTkLabel(
            self.dub_audio_output_options_frame, 
            text="🎧 Âm thanh nền Video:", 
            font=("Poppins", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(5,2))
        
        self.dub_background_audio_menu = ctk.CTkOptionMenu(
            self.dub_audio_output_options_frame,
            variable=self.master_app.dub_background_audio_option_var,
            values=self.master_app.dub_background_audio_options,
            command=self.master_app.dub_on_background_audio_option_changed
        )
        self.dub_background_audio_menu.pack(fill="x", padx=10, pady=(2,5))
        
        # Mix level controls
        self.dub_mix_level_controls_frame = ctk.CTkFrame(self.dub_audio_output_options_frame, fg_color="transparent")
        
        self.dub_lbl_mix_level = ctk.CTkLabel(
            self.dub_mix_level_controls_frame, 
            text="Âm lượng nền (gốc):", 
            font=("Segoe UI", 11)
        )
        self.dub_lbl_mix_level.pack(side="left", padx=(0,5), pady=5)
        
        self.dub_slider_mix_level = ctk.CTkSlider(
            self.dub_mix_level_controls_frame,
            from_=0.0, to=0.7, number_of_steps=70,
            variable=self.master_app.dub_background_mix_level_var,
            command=self.master_app.dub_update_mix_level_label_display
        )
        self.dub_slider_mix_level.pack(side="left", padx=0, pady=5, fill="x", expand=True)
        
        self.dub_lbl_mix_level_display = ctk.CTkLabel(
            self.dub_mix_level_controls_frame, 
            text=f"{self.master_app.dub_background_mix_level_var.get()*100:.0f}%", 
            font=("Segoe UI", 10), 
            width=35
        )
        self.dub_lbl_mix_level_display.pack(side="left", padx=(5,0), pady=5)
        
        # Pack the frame
        self.dub_mix_level_controls_frame.pack(fill="x", padx=10, pady=(5,5))
        
        # Custom background music section
        self.dub_custom_bg_music_frame = ctk.CTkFrame(self.dub_audio_output_options_frame, fg_color="transparent")
        
        # Frame con 1 (chứa checkbox và volume)
        self.checkbox_and_volume_grid_frame = ctk.CTkFrame(self.dub_custom_bg_music_frame, fg_color="transparent")
        self.checkbox_and_volume_grid_frame.grid_columnconfigure(0, weight=0)
        self.checkbox_and_volume_grid_frame.grid_columnconfigure(1, weight=0, pad=5)
        self.checkbox_and_volume_grid_frame.grid_columnconfigure(2, weight=0)
        
        self.dub_chk_use_custom_bg_music = ctk.CTkCheckBox(
            self.checkbox_and_volume_grid_frame, 
            text="Nhạc nền tùy chỉnh", 
            variable=self.master_app.dub_use_custom_bg_music_var, 
            command=lambda: self.master_app.dub_on_background_audio_option_changed("Thay thế âm thanh gốc"), 
            font=("Segoe UI", 11), 
            checkbox_width=18, 
            checkbox_height=18
        )
        self.dub_chk_use_custom_bg_music.grid(row=0, column=0, sticky="w", pady=2, padx=(0, 0))
        
        self.dub_lbl_custom_bg_music_volume_title_inline = ctk.CTkLabel(
            self.checkbox_and_volume_grid_frame, 
            text="Âm lượng:", 
            font=("Segoe UI", 11)
        )
        self.custom_bg_vol_entry_frame = ctk.CTkFrame(self.checkbox_and_volume_grid_frame, fg_color="transparent")
        self.dub_entry_custom_bg_music_volume = ctk.CTkEntry(
            self.custom_bg_vol_entry_frame, 
            textvariable=self.master_app.dub_custom_bg_music_volume_percent_str_var, 
            width=45, 
            font=("Segoe UI", 11), 
            justify="right", 
            validate="key", 
            validatecommand=self.master_app.volume_vcmd
        )
        self.dub_entry_custom_bg_music_volume.pack(side="left", padx=(0, 2))
        self.percent_label_for_custom_vol = ctk.CTkLabel(
            self.custom_bg_vol_entry_frame, 
            text="%", 
            font=("Segoe UI", 11)
        )
        self.percent_label_for_custom_vol.pack(side="left")
        
        # Frame con 2 (chứa các nút chọn nhạc)
        self.dub_music_selection_controls_frame = ctk.CTkFrame(self.dub_custom_bg_music_frame, fg_color="transparent")
        self.dub_music_selection_controls_frame.grid_columnconfigure((0, 1), weight=1)
        self.dub_music_selection_controls_frame.grid_columnconfigure(2, weight=0)
        
        self.dub_btn_browse_bg_folder = ctk.CTkButton(
            self.dub_music_selection_controls_frame, 
            text="📁Thư mục...", 
            height=28, 
            font=("Segoe UI", 11), 
            command=self.master_app._dub_browse_custom_bg_folder
        )
        self.dub_btn_browse_bg_folder.grid(row=0, column=0, padx=(0, 2), sticky="ew")
        
        self.dub_btn_browse_bg_music = ctk.CTkButton(
            self.dub_music_selection_controls_frame, 
            text="🎵File Nhạc...", 
            height=28, 
            font=("Segoe UI", 11), 
            command=self.master_app.dub_browse_custom_bg_music
        )
        self.dub_btn_browse_bg_music.grid(row=0, column=1, padx=(3, 10), sticky="ew")
        
        self.dub_chk_randomize_music = ctk.CTkCheckBox(
            self.dub_music_selection_controls_frame, 
            text="Ngẫu nhiên", 
            variable=self.master_app.dub_randomize_bg_music_var, 
            font=("Segoe UI", 11), 
            checkbox_width=18, 
            checkbox_height=18
        )
        self.dub_chk_randomize_music.grid(row=0, column=2, padx=(0, 0), sticky="w")
        
        # Label đường dẫn
        self.dub_lbl_bg_music_path = ctk.CTkLabel(
            self.dub_custom_bg_music_frame, 
            text="Nhạc nền: Chưa chọn", 
            wraplength=280, 
            anchor="w", 
            font=("Segoe UI", 10), 
            text_color=("gray30", "gray70"), 
            justify="left"
        )
        
        # This frame will be shown/hidden based on audio type selection
        
        return self.dub_audio_output_options_frame

    def _create_dubbing_flow_optimization_section(self, parent_frame, card_bg_color):
        """Create flow optimization section for Dubbing tab"""
        self.dub_flow_optimization_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        self.dub_flow_optimization_frame.pack(pady=(5, 5), padx=10, fill="x")
        
        self.chk_optimize_dub_flow = ctk.CTkCheckBox(
            self.dub_flow_optimization_frame, 
            text="🌊 Tối ưu luồng đọc cho Thuyết Minh", 
            variable=self.master_app.optimize_dub_flow_var, 
            command=self.master_app._toggle_dub_flow_options_visibility, 
            font=("Segoe UI", 14, "bold"), 
            checkbox_width=20, 
            checkbox_height=20
        )
        self.chk_optimize_dub_flow.pack(anchor="w", padx=10, pady=(8,5))
        
        # Flow optimization details (will be shown/hidden by toggle)
        self.dub_flow_details_frame = ctk.CTkFrame(self.dub_flow_optimization_frame, fg_color="transparent")
        
        # Configure grid layout for details frame
        self.dub_flow_details_frame.grid_columnconfigure(1, weight=1)
        
        # Row 0: Split checkbox
        chk_dub_split_for_flow = ctk.CTkCheckBox(
            self.dub_flow_details_frame, 
            text="Chia lại văn bản đã gộp:", 
            variable=self.master_app.dub_split_enabled_for_flow_var, 
            font=("Poppins", 13), 
            checkbox_height=20, 
            checkbox_width=20, 
            command=self.master_app._toggle_dub_flow_split_details_visibility
        )
        chk_dub_split_for_flow.grid(row=0, column=0, columnspan=2, sticky="w", padx=0, pady=(5,5))
        
        # Row 1: Character and Line count (on same row)
        char_line_frame = ctk.CTkFrame(self.dub_flow_details_frame, fg_color="transparent")
        char_line_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,5))
        char_line_frame.grid_columnconfigure(1, weight=1)
        char_line_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(char_line_frame, text="Ký tự (tối đa):", font=("Poppins", 12)).grid(row=0, column=0, padx=(0,5))
        self.dub_max_chars_entry_flow = ctk.CTkEntry(char_line_frame, textvariable=self.master_app.dub_max_chars_for_flow_var)
        self.dub_max_chars_entry_flow.grid(row=0, column=1, sticky="ew")
        
        ctk.CTkLabel(char_line_frame, text="Số dòng:", font=("Poppins", 12)).grid(row=0, column=2, padx=(10, 5))
        self.dub_max_lines_entry_flow = ctk.CTkEntry(char_line_frame, textvariable=self.master_app.dub_max_lines_for_flow_var)
        self.dub_max_lines_entry_flow.grid(row=0, column=3, sticky="ew")
        
        # Row 2: Split mode
        ctk.CTkLabel(self.dub_flow_details_frame, text="Cách chia:", font=("Poppins", 13)).grid(row=2, column=0, sticky="w", padx=(0,10))
        _dub_split_mode_options_ui = ["underthesea (Tiếng Việt)"]
        if not HAS_UNDERTHESEA: 
            _dub_split_mode_options_ui.extend(["sentence", "char"])
        else:
            if "sentence" not in _dub_split_mode_options_ui: 
                _dub_split_mode_options_ui.append("sentence")
            if "char" not in _dub_split_mode_options_ui: 
                _dub_split_mode_options_ui.append("char")
        self.dub_split_mode_menu_flow = ctk.CTkOptionMenu(
            self.dub_flow_details_frame, 
            variable=self.master_app.dub_split_mode_for_flow_var, 
            values=_dub_split_mode_options_ui
        )
        self.dub_split_mode_menu_flow.grid(row=2, column=1, sticky="ew")
        
        # Row 3: CPS timing
        ctk.CTkLabel(
            self.dub_flow_details_frame, 
            text="Ký tự/giây (timing):", 
            anchor="w", 
            font=("Poppins", 12)
        ).grid(row=3, column=0, padx=(0,5), pady=5, sticky="w")
        cps_timing_entry_dub_flow = ctk.CTkEntry(
            self.dub_flow_details_frame, 
            textvariable=self.master_app.dub_cps_for_timing_var
        )
        cps_timing_entry_dub_flow.grid(row=3, column=1, pady=5, sticky="ew")
        
        # Row 4 & 5: Other checkboxes
        self.chk_force_recalculate_timing = ctk.CTkCheckBox(
            self.dub_flow_details_frame, 
            text="Tính lại timing từ CPS (Bỏ qua timing gốc)", 
            variable=self.master_app.dub_force_recalculate_timing_var, 
            font=("Segoe UI", 12), 
            checkbox_width=18, 
            checkbox_height=18
        )
        self.chk_force_recalculate_timing.grid(row=4, column=0, columnspan=2, padx=0, pady=5, sticky="w")
        
        self.chk_dub_auto_optimize_on_paste = ctk.CTkCheckBox(
            self.dub_flow_details_frame, 
            text="🔄 Tự động tối ưu & hiện timing khi dán text", 
            variable=self.master_app.dub_auto_optimize_on_paste_var, 
            font=("Segoe UI", 12), 
            checkbox_width=18, 
            checkbox_height=18
        )
        self.chk_dub_auto_optimize_on_paste.grid(row=5, column=0, columnspan=2, padx=0, pady=5, sticky="w")
        
        return self.dub_flow_optimization_frame

    def _create_dubbing_advanced_audio_section(self, parent_frame, card_bg_color):
        """Create advanced audio processing section for Dubbing tab"""
        self.dub_advanced_audio_main_frame = ctk.CTkFrame(parent_frame, fg_color=card_bg_color, corner_radius=8)
        self.dub_advanced_audio_main_frame.pack(pady=(5, 5), padx=10, fill="x")
        
        self.dub_chk_show_advanced_audio_settings = ctk.CTkCheckBox(
            self.dub_advanced_audio_main_frame,
            text="⚙ Hiện tùy chỉnh xử lý Audio nâng cao",
            variable=self.master_app.dub_show_advanced_audio_settings_var,
            checkbox_width=20,
            checkbox_height=20,
            font=("Segoe UI", 13, "bold"),
            command=self.master_app._toggle_advanced_dub_audio_settings_visibility
        )
        self.dub_chk_show_advanced_audio_settings.pack(side="top", anchor="w", padx=10, pady=10)
        
        self.dub_advanced_audio_processing_frame = ctk.CTkFrame(
            self.dub_advanced_audio_main_frame,
            fg_color="transparent"
        )
        
        adv_options_grid = ctk.CTkFrame(self.dub_advanced_audio_processing_frame, fg_color="transparent")
        adv_options_grid.pack(fill="x", padx=10, pady=(0, 10))
        adv_options_grid.grid_columnconfigure(0, weight=3)
        adv_options_grid.grid_columnconfigure(1, weight=1, minsize=70)
        
        current_row_adv = 0
        label_font_size = ("Segoe UI", 11)
        
        chk_force_cut = ctk.CTkCheckBox(
            adv_options_grid, 
            text="Luôn cắt TTS nếu vẫn dài hơn SRT", 
            variable=self.master_app.dub_sync_force_cut_if_over_srt_duration_var, 
            font=label_font_size, 
            checkbox_width=20, 
            checkbox_height=20
        )
        chk_force_cut.grid(row=current_row_adv, column=0, columnspan=2, padx=0, pady=2, sticky="w")
        current_row_adv += 1
        
        chk_pad_short_tts = ctk.CTkCheckBox(
            adv_options_grid, 
            text="Thêm khoảng lặng nếu TTS ngắn hơn SRT", 
            variable=self.master_app.dub_sync_pad_short_tts_var, 
            font=label_font_size, 
            checkbox_width=20, 
            checkbox_height=20
        )
        chk_pad_short_tts.grid(row=current_row_adv, column=0, columnspan=2, padx=0, pady=2, sticky="w")
        current_row_adv += 1
        
        ctk.CTkLabel(
            adv_options_grid, 
            text="Dung sai đồng bộ TTS/SRT (ms):", 
            anchor="w", 
            font=label_font_size
        ).grid(row=current_row_adv, column=0, padx=(0,5), pady=2, sticky="w")
        ctk.CTkEntry(
            adv_options_grid, 
            textvariable=self.master_app.dub_sync_tolerance_ms_var, 
            width=70
        ).grid(row=current_row_adv, column=1, pady=2, sticky="e")
        current_row_adv += 1
        
        ctk.CTkLabel(
            adv_options_grid, 
            text="Tốc độ TTS tối đa (vd: 1.5, max 3.0):", 
            anchor="w", 
            font=label_font_size
        ).grid(row=current_row_adv, column=0, padx=(0,5), pady=2, sticky="w")
        ctk.CTkEntry(
            adv_options_grid, 
            textvariable=self.master_app.dub_sync_max_speed_up_var, 
            width=70
        ).grid(row=current_row_adv, column=1, pady=2, sticky="e")
        current_row_adv += 1
        
        ctk.CTkLabel(
            adv_options_grid, 
            text="Tốc độ TTS tối thiểu (vd: 0.9):", 
            anchor="w", 
            font=label_font_size
        ).grid(row=current_row_adv, column=0, padx=(0,5), pady=2, sticky="w")
        ctk.CTkEntry(
            adv_options_grid, 
            textvariable=self.master_app.dub_sync_min_speed_down_var, 
            width=70
        ).grid(row=current_row_adv, column=1, pady=2, sticky="e")
        current_row_adv += 1
        
        ctk.CTkLabel(
            adv_options_grid, 
            text="Ngưỡng SRT chỉnh tốc độ (ms):", 
            anchor="w", 
            font=label_font_size
        ).grid(row=current_row_adv, column=0, padx=(0,5), pady=2, sticky="w")
        ctk.CTkEntry(
            adv_options_grid, 
            textvariable=self.master_app.dub_sync_min_srt_duration_for_adjust_ms_var, 
            width=70
        ).grid(row=current_row_adv, column=1, pady=2, sticky="e")
        current_row_adv += 1
        
        ctk.CTkLabel(
            adv_options_grid, 
            text="Pause giữa các đoạn (ms):", 
            anchor="w", 
            font=label_font_size
        ).grid(row=current_row_adv, column=0, padx=(0,5), pady=2, sticky="w")
        ctk.CTkEntry(
            adv_options_grid, 
            textvariable=self.master_app.dub_min_gap_between_segments_ms_var, 
            width=70
        ).grid(row=current_row_adv, column=1, pady=2, sticky="e")
        current_row_adv += 1
        
        ctk.CTkLabel(
            adv_options_grid, 
            text="Thời lượng Fade-in (s):", 
            anchor="w", 
            font=label_font_size
        ).grid(row=current_row_adv, column=0, padx=(0,5), pady=2, sticky="w")
        ctk.CTkEntry(
            adv_options_grid, 
            textvariable=self.master_app.dub_audio_fade_in_duration_s_var, 
            width=70
        ).grid(row=current_row_adv, column=1, pady=2, sticky="e")
        current_row_adv += 1
        
        ctk.CTkLabel(
            adv_options_grid, 
            text="Thời lượng Fade-out (s):", 
            anchor="w", 
            font=label_font_size
        ).grid(row=current_row_adv, column=0, padx=(0,5), pady=2, sticky="w")
        ctk.CTkEntry(
            adv_options_grid, 
            textvariable=self.master_app.dub_audio_fade_out_duration_s_var, 
            width=70
        ).grid(row=current_row_adv, column=1, pady=2, sticky="e")
        
        self.master_app.after(10, self.master_app._toggle_advanced_dub_audio_settings_visibility)
        
        return self.dub_advanced_audio_main_frame

    def _create_dubbing_right_panel(self, main_frame, panel_bg_color, card_bg_color, textbox_bg_color, special_action_button_color, special_action_hover_color):
        """Create right panel for Dubbing tab (queue and script editor)"""
        dub_right_panel = ctk.CTkFrame(main_frame, fg_color=panel_bg_color, corner_radius=12)
        dub_right_panel.grid(row=0, column=1, pady=0, sticky="nsew")
        dub_right_panel.grid_rowconfigure(1, weight=1)
        dub_right_panel.grid_columnconfigure(0, weight=1)

        self.dub_queue_display_frame = ctk.CTkScrollableFrame(dub_right_panel, label_text="📋 Hàng chờ Thuyết minh", label_font=("Poppins", 14, "bold"), height=180)
        self.dub_queue_display_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.placeholder_dub_queue = ctk.CTkLabel(self.dub_queue_display_frame, text="[Hàng chờ thuyết minh sẽ hiển thị ở đây]", text_color=("gray30", "gray70"))
        self.placeholder_dub_queue.pack(pady=20)

        dub_script_preview_frame = ctk.CTkFrame(dub_right_panel, fg_color="transparent")
        dub_script_preview_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        dub_script_preview_frame.grid_rowconfigure(1, weight=1)
        dub_script_preview_frame.grid_columnconfigure(0, weight=1)

        dub_script_header = ctk.CTkFrame(dub_script_preview_frame, fg_color="transparent")
        dub_script_header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(dub_script_header, text="📝 Nd Kịch bản:", font=("Poppins", 15, "bold")).pack(side="left", padx=(0,10))

        buttons_container_for_grid_dub = ctk.CTkFrame(dub_script_header, fg_color=card_bg_color, corner_radius=6) 
        buttons_container_for_grid_dub.pack(side="right", fill="x", expand=True, padx=(5,0))
        
        num_header_buttons_dub = 7
        for i in range(num_header_buttons_dub): buttons_container_for_grid_dub.grid_columnconfigure(i, weight=1)
        button_height = 28
        button_font_style = ("Poppins", 11)
        self.ai_edit_dub_script_button = ctk.CTkButton(buttons_container_for_grid_dub, text="✨ Biên tập (AI)", height=button_height, font=button_font_style, command=lambda: self.master_app._show_ai_script_editing_popup(self.dub_script_textbox, "dubbing"), fg_color=special_action_button_color, hover_color=special_action_hover_color)
        self.ai_edit_dub_script_button.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        self.dalle_button_dub_tab = ctk.CTkButton(buttons_container_for_grid_dub, text="🎨 Tạo Ảnh AI", height=button_height, font=button_font_style, command=self.master_app._show_dalle_image_generation_popup, fg_color=special_action_button_color, hover_color=special_action_hover_color)
        self.dalle_button_dub_tab.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        self.imagen_button_dub_tab = ctk.CTkButton(buttons_container_for_grid_dub, text="🖼 Ảnh(Imagen)", height=button_height, font=button_font_style, command=self.master_app.open_imagen_settings_window, fg_color=special_action_button_color, hover_color=special_action_hover_color)
        self.imagen_button_dub_tab.grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        self.dub_btn_edit_script = ctk.CTkButton(buttons_container_for_grid_dub, text="✍ Sửa Script", height=button_height, font=button_font_style, command=self.master_app.dub_enable_script_editing)
        self.dub_btn_edit_script.grid(row=0, column=3, padx=2, pady=2, sticky="ew")
        self.dub_btn_save_script = ctk.CTkButton(buttons_container_for_grid_dub, text="💾 Lưu Script", height=button_height, font=button_font_style, command=self.master_app.dub_save_script_from_textbox)
        self.dub_btn_save_script.grid(row=0, column=4, padx=2, pady=2, sticky="ew")
        self.dub_preview_button = ctk.CTkButton(buttons_container_for_grid_dub, text="🔊 Nghe thử Script", height=button_height, font=button_font_style, command=self.master_app.dub_preview_current_line, state="disabled")
        self.dub_preview_button.grid(row=0, column=5, padx=2, pady=2, sticky="ew")
        self.dub_btn_save_audio_from_text = ctk.CTkButton(buttons_container_for_grid_dub, text="💾 Lưu Audio", height=button_height, font=button_font_style, command=self.master_app.dub_trigger_generate_and_save_audio, state="disabled")
        self.dub_btn_save_audio_from_text.grid(row=0, column=6, padx=2, pady=2, sticky="ew")
        
        self.dub_script_textbox = ctk.CTkTextbox(dub_script_preview_frame, font=("Segoe UI", 13),
                                                 wrap="word", state="normal", 
                                                 fg_color=textbox_bg_color, border_width=1
                                                 )
        self.dub_script_textbox.grid(row=1, column=0, sticky="nsew", padx=0, pady=(2,0))
        self.dub_script_textbox.insert("1.0", self.master_app.dub_script_textbox_placeholder)
        self.dub_script_textbox.bind("<Button-3>", textbox_right_click_menu)
        if hasattr(self.dub_script_textbox, 'bind'):
            self.dub_script_textbox.bind("<KeyRelease>", lambda event: self.master_app._update_dub_script_controls_state())
            self.dub_script_textbox.bind("<<Paste>>", self.master_app._dub_handle_paste_and_optimize_text)

