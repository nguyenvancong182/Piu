"""
ImagenSettingsWindow class for Piu application.
Manages Imagen image generation settings.
"""
import customtkinter as ctk
import logging
import os
import json
from tkinter import filedialog, messagebox
import threading
import time

from utils.helpers import get_default_downloads_folder, safe_int
from ui.widgets.menu_utils import textbox_right_click_menu

class ImagenSettingsWindow(ctk.CTkToplevel):
    """
    Lớp cửa sổ cài đặt và tạo ảnh bằng Google Imagen (Gemini AI).
    >>> PHIÊN BẢN HOÀN CHỈNH: Giao diện quản lý nhân vật động, thanh cuộn, và các nút chức năng cố định. <<<
    """

    IMAGEN_ART_STYLES = {
        "Mặc định (AI tự do)": "",
        "Hoạt Hình 3D (Pixar)": "3d animation, disney pixar style, rendered in maya, cute, vibrant, high detail",
        "Hoạt Hình 3D Cổ Trang (Trung Quốc)": "3D animation, ancient Chinese style, traditional hanfu clothing, intricate details, cinematic lighting, rendered in Unreal Engine 5",
        "Hoạt Hình 3D Tu Tiên": (
            "3D animation, Xianxia style, divine and ethereal atmosphere, characters in flowing immortal robes "
            "with glowing magical artifacts, spiritual energy effects, rendered in Unreal Engine 5, cinematic, high resolution"
        ),
        "Tu Tiên - Tiên Hiệp (Kỳ Ảo)": (
            "Xianxia style, ethereal fantasy concept art, divine aura, glowing spiritual energy (qi), "
            "characters in flowing immortal robes, intricate details, cinematic lighting, masterpiece, ultra detailed"
        ),
        "Anime/Manga (Hiện đại)": "anime style, key visual, beautiful detailed, by makoto shinkai, pixiv",
        "Ảo Diệu (Fantasy)": "fantasy concept art, magical, ethereal, glowing, detailed, intricate, by greg rutkowski",
        "Ảnh Chụp Siêu Thực": "photorealistic, photograph, highly detailed, sharp focus, 8k, professional photography",
        "Điện Ảnh (Cinematic)": "cinematic still, dramatic lighting, film grain, 35mm lens, shallow depth of field",
        "Tranh Sơn Dầu": "oil painting, masterpiece, impasto, visible brush strokes, textured canvas",
        "Tranh Màu Nước": "watercolor painting, delicate, soft colors, paper texture, vibrant",
        "Khoa Học Viễn Tưởng": "sci-fi concept art, futuristic, cyberpunk, neon lights, detailed environment",
        "Tối Giản (Minimalist)": "minimalist, clean background, simple, vector art, flat design",
        "Tranh Chì (Sketch)": "charcoal sketch, detailed pencil drawing, black and white, paper texture",

        "Minh Hoạ Sách Thiếu Nhi Châu Âu (Sơn Dầu TK19)": (
            "classic European children's book illustration, 19th-century Europe, "
            "oil painting on canvas, glazing, texture-rich painterly brushwork, "
            "muted earthy palette with warm ambers and cool twilight blues, "
            'cinematic composition, rule of thirds, '
            "volumetric lighting, soft bloom, subtle film grain, masterpiece, highly detailed"
        ),

        "Châu Âu TK19 (Sơn Dầu Cổ Điển)": (
            "19th-century Europe, academic realism oil painting, glazing, "
            "texture-rich painterly brushwork, muted earthy palette with warm ambers and cool twilight blues, "
            "cinematic composition, rule of thirds, volumetric lighting, soft bloom, subtle film grain, "
            "masterpiece, highly detailed"
        ),
        
        "Graphic-Novel Bán Hiện Thực (Dark Wuxia)": (
            "semi-realistic graphic novel illustration, bold ink outlines, high-contrast chiaroscuro, "
            "gritty textured shading, dramatic dusk backlight, orange embers and smoke, burning ancient city, "
            "wuxia/samurai robes, intense gaze, cinematic composition, atmospheric haze"
        ),
        # ==== ĐÔ THỊ ====
        "Đô Thị (Slice-of-life Anime)": (
            "anime key visual, modern city, cozy apartment, evening sunlight through window, street life, soft bokeh, "
            "clean lineart, vibrant yet natural palette, by makoto shinkai style"
        ),
        "Đô Thị Neo-noir (Điện Ảnh)": (
            "urban neo-noir, rain-soaked streets, reflective asphalt, moody cinematic lighting, 35mm film look, "
            "smoke and neon signage, high contrast, shallow depth of field"
        ),
        "Đô Thị Cyberpunk (Khoa Huyễn)": (
            "cyberpunk cityscape, dense holograms and neon, rainy night, crowded alley, techwear, "
            "futuristic signage, volumetric fog, high detail, wide-angle"
        ),

        # ==== LINH DỊ / KINH DỊ ====
        "Linh Dị (Kinh Dị Á Đông)": (
            "east asian horror, eerie atmosphere, dilapidated house, paper talismans, cold moonlight, "
            "subtle film grain, desaturated colors, slow-burn tension"
        ),
        "Linh Dị (Tranh Mực Đen)": (
            "ink wash horror illustration, bold brush strokes, rough paper texture, stark black-and-white, "
            "minimal color, unsettling composition"
        ),
        "Linh Dị (Ảnh Chụp Phim)": (
            "photorealistic horror still, handheld 35mm film aesthetic, soft flash, dust and scratches, "
            "natural grain, claustrophobic framing"
        ),

        # ==== HUYỀN HUYỄN / KỲ HUYỄN ====
        "Huyền Huyễn (High Fantasy Châu Âu)": (
            "high fantasy concept art, towering castles, ancient forests, spell effects, ornate armor, "
            "golden rim light, epic scale, ultra-detailed"
        ),
        "Kỳ Huyễn (Kiếm & Ma Pháp)": (
            "western fantasy illustration, swords and sorcery, dynamic action pose, painterly rendering, "
            "rich textures, dramatic clouds, rim lighting"
        ),

        # ==== VÕ HIỆP ====
        "Võ Hiệp (Thủy Mặc)": (
            "wuxia shan shui ink painting, sweeping mountains, flowing robes, dynamic brush strokes, "
            "mist and waterfalls, elegant minimal palette"
        ),
        "Võ Hiệp (Truyện Tranh Bán Hiện Thực)": (
            "semi-realistic wuxia comic style, bold ink outlines, dynamic motion lines, high-contrast lighting, "
            "dust and embers, cinematic framing"
        ),

        # ==== LỊCH SỬ ====
        "Lịch Sử (Sơn Dầu Cổ Trang Việt/Á)": (
            "historical oil painting, traditional attire, textured canvas, warm earthy palette, "
            "soft glazing, museum lighting, meticulous details"
        ),
        "Lịch Sử (Khắc Gỗ Cổ)": (
            "traditional woodblock print style, limited color palette, flat shading, decorative patterns, "
            "aged paper texture, historical layout"
        ),

        # ==== ĐỒNG NHÂN (FANFIC) ====
        "Đồng Nhân (Graphic Novel Trung Tính IP)": (
            "graphic novel panel, dynamic composition, neutral homage without direct IP, clean inks, halftone shading, "
            "bold captions, vibrant spot colors"
        ),
        "Đồng Nhân (Anime Parody Trung Tính IP)": (
            "anime parody style, generic hero silhouette, iconic-but-generic costume shapes, energetic pose, "
            "studio key art look, bright gradients, safe IP-neutral design"
        ),

        # ==== QUÂN SỰ ====
        "Quân Sự (Chiến Trường Hiện Đại)": (
            "modern military concept art, realistic gear, tactical lighting, dust and smoke, depth haze, "
            "cinematic desaturated palette, high detail"
        ),
        "Quân Sự (Bản Vẽ Kỹ Thuật)": (
            "technical blueprint style, orthographic views, labels and measurements, blueprint paper texture, "
            "fine linework, precise minimal palette"
        ),

        # ==== DU HÍ (Game/LitRPG) ====
        "Du Hí (UI HUD In-World)": (
            "litrpg scene with floating HUD, quest panels, damage numbers, stylized game interface elements, "
            "clean readability, soft bloom, adventure tone"
        ),
        "Du Hí (Isometric Map)": (
            "isometric game map illustration, modular tiles, icons and markers, clean vector edges, "
            "crisp readability, light ambient occlusion"
        ),

        # ==== CẠNH KỸ (Công Nghệ/Đối Kháng) ====
        "Cạnh Kỹ (Mecha/Đấu Trường)": (
            "mecha arena, dynamic motion, sparks and debris, industrial lighting, cinematic dust, "
            "hard-surface detail, wide-angle action"
        ),
        "Cạnh Kỹ (Tech Thriller Minimalist)": (
            "minimalist tech thriller poster, bold typography space, strong silhouette, high contrast, "
            "clean geometric shapes, subtle noise texture"
        ),

        # ==== KHOA HUYỄN (Sci-Fi/Science Fantasy) ====
        "Khoa Huyễn (Space Opera)": (
            "space opera matte painting, grand starships, nebula backdrops, lens flares, "
            "epic scale, volumetric light, ultra-detailed"
        ),
        "Khoa Huyễn (Biopunk)": (
            "biopunk lab aesthetic, organic tech, translucent materials, eerie fluorescence, "
            "sterile yet unsettling, high micro-detail"
        ),

        # ==== NGÔN TÌNH ====
        "Ngôn Tình (Lãng Mạn Hiện Đại)": (
            "romance illustration, soft pastel palette, golden hour backlight, gentle bloom, "
            "subtle film grain, intimate framing, warm atmosphere"
        ),
        "Ngôn Tình (Cổ Trang Dịu Dàng)": (
            "ancient romance painting, flowing hanfu, peach blossoms, soft silk textures, "
            "dreamy haze, delicate color grading, elegant composition"
        ),
    }

    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        
        self.enhance_with_gpt_var = ctk.BooleanVar(
            value=self.master_app.cfg.get("imagen_enhance_with_gpt", False)
        )
        self.enhance_with_gemini_var = ctk.BooleanVar(
            value=self.master_app.cfg.get("imagen_enhance_with_gemini", False)
        )        

        self.title("🖼 Tạo Ảnh bằng Google Imagen")
        self.geometry("650x712")
        
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()

        try:
            self.after(50, self._center_window)
        except Exception as e:
            logging.warning(f"Không thể căn giữa cửa sổ Imagen: {e}")

        # --- Khai báo các biến lưu trữ giá trị ---
        cfg = self.master_app.cfg
        self.style_var = ctk.StringVar(value=cfg.get("imagen_last_style", "Mặc định (AI tự do)"))
        self.prompt_var = ctk.StringVar(value=cfg.get("imagen_last_prompt", "Một chú chó con dễ thương đang ngồi trên bãi cỏ xanh mướt, phong cách ảnh chụp siêu thực."))
        self.negative_prompt_var = ctk.StringVar(value=cfg.get("imagen_last_negative_prompt", ""))
        self.num_images_var = ctk.StringVar(value=cfg.get("imagen_last_num_images", "1"))
        self.aspect_ratio_var = ctk.StringVar(value=cfg.get("imagen_last_aspect_ratio", "16:9"))
        self.auto_split_var = ctk.BooleanVar(value=cfg.get("imagen_auto_split_scenes", True)) # Mặc định là bật
        self.motion_effect_var = self.master_app.imagen_motion_effect_var
        self.motion_speed_var = self.master_app.imagen_motion_speed_var 

        self.ffmpeg_encoder_var = self.master_app.ffmpeg_encoder_var
        self.ffmpeg_preset_var = self.master_app.ffmpeg_preset_var
        self.ffmpeg_crf_var = self.master_app.ffmpeg_crf_var
        
        imagen_folder = cfg.get("imagen_last_output_folder")
        dalle_folder = cfg.get("dalle_output_folder_setting")
        main_output_folder = self.master_app.output_path_var.get()
        system_downloads_folder = get_default_downloads_folder()
        final_folder_to_load = imagen_folder or dalle_folder or main_output_folder or system_downloads_folder
        self.output_folder_var = ctk.StringVar(value=final_folder_to_load)

        self.use_character_sheet_var = ctk.BooleanVar(
            value=self.master_app.cfg.get("imagen_use_character_sheet", True) # Mặc định là bật
        )        
        self.character_slots = []

        # --- Tạo giao diện ---
        # Tách biệt phần cuộn và phần cố định
        # 1. Phần nội dung có thể cuộn
        self.main_scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll_frame.pack(expand=True, fill="both", padx=15, pady=(15, 5))
        self._create_widgets()
        self._load_initial_characters()

        # 2. Phần nút bấm cố định ở dưới cùng
        self.bottom_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_button_frame.pack(fill="x", padx=15, pady=(5, 15), side="bottom")
        self._create_bottom_buttons()

        self.protocol("WM_DELETE_WINDOW", self._on_close_window)

    def _center_window(self):
        try:
            self.master_app.update_idletasks()
            self.update_idletasks()
            x = self.master_app.winfo_x() + (self.master_app.winfo_width() // 2) - (self.winfo_width() // 2)
            y = self.master_app.winfo_y() + (self.master_app.winfo_height() // 2) - (self.winfo_height() // 2)
            self.geometry(f"+{x}+{y}")
        except Exception as e:
            logging.warning(f"Lỗi căn giữa cửa sổ Imagen (trong _center_window): {e}")

    def _create_widgets(self):
        """Tạo các widget con (phần có thể cuộn) cho cửa sổ."""
        # Parent của container này là main_scroll_frame
        content_container = ctk.CTkFrame(self.main_scroll_frame, fg_color="transparent")
        content_container.pack(expand=True, fill="x")

        prompt_header_frame = ctk.CTkFrame(content_container, fg_color="transparent")
        prompt_header_frame.pack(fill="x", pady=(0,5), padx=0)
        prompt_header_frame.grid_columnconfigure(1, weight=1) 

        ctk.CTkLabel(prompt_header_frame, text="Mô tả ảnh (Prompt):").grid(row=0, column=0, sticky="w")
        self.gemini_enhance_checkbox = ctk.CTkCheckBox(prompt_header_frame, text="Nâng cấp với Gemini", variable=self.enhance_with_gemini_var, command=self._on_gemini_enhance_toggled) 
        self.gemini_enhance_checkbox.grid(row=0, column=2, sticky="e", padx=5)
        self.gpt_enhance_checkbox = ctk.CTkCheckBox(prompt_header_frame, text="Nâng cấp với GPT", variable=self.enhance_with_gpt_var, command=self._on_gpt_enhance_toggled)
        self.gpt_enhance_checkbox.grid(row=0, column=3, sticky="e", padx=5)
        
        self.prompt_textbox = ctk.CTkTextbox(content_container, height=120, wrap="word", border_width=1)
        self.prompt_textbox.pack(fill="x", expand=True, pady=(0,10))
        self.prompt_textbox.insert("1.0", self.prompt_var.get())
        self.prompt_textbox.bind("<Button-3>", textbox_right_click_menu)

        ctk.CTkLabel(content_container, text="Prompt phủ định (Những thứ KHÔNG muốn xuất hiện):").pack(anchor="w", pady=(5,2))
        self.negative_prompt_textbox = ctk.CTkTextbox(content_container, height=60, wrap="word", border_width=1)
        self.negative_prompt_textbox.pack(fill="x", expand=True, pady=(0,10))
        self.negative_prompt_textbox.insert("1.0", self.negative_prompt_var.get())
        self.negative_prompt_textbox.bind("<Button-3>", textbox_right_click_menu)
        
        character_management_frame = ctk.CTkFrame(content_container) 
        character_management_frame.pack(fill="x", expand=True, pady=(5, 10)) 
          
        character_header_frame = ctk.CTkFrame(character_management_frame, fg_color="transparent") 
        character_header_frame.pack(fill="x", padx=10, pady=(5,5))
        # --- THÊM CHECKBOX VÀO ĐÂY ---
        self.use_char_sheet_checkbox = ctk.CTkCheckBox(
            character_header_frame,
            text="👤 Sử dụng Dàn diễn viên:",
            variable=self.use_character_sheet_var
        )
        self.use_char_sheet_checkbox.pack(side="left", anchor="w")
        # ---------------------------        
        ctk.CTkButton(character_header_frame, text="+ Thêm nhân vật", width=120, command=self._add_character_slot).pack(side="right") 
          
        self.characters_scrollable_frame = ctk.CTkScrollableFrame(character_management_frame, label_text="Danh sách nhân vật", height=65) 
        self.characters_scrollable_frame.pack(expand=True, fill="both", padx=5, pady=5)

        options_frame = ctk.CTkFrame(content_container)
        options_frame.pack(fill="x", pady=(5,10))
        options_frame.grid_columnconfigure(3, weight=1)
        
        options_frame.grid_columnconfigure(4, weight=1) # Sửa cột giãn ra là cột 4

        ctk.CTkLabel(options_frame, text="Số lượng ảnh (tối đa):").grid(row=0, column=0, padx=(10,5), pady=10)
        ctk.CTkEntry(options_frame, textvariable=self.num_images_var, width=60).grid(row=0, column=1, sticky="w", pady=10)
        
        # <<< THÊM CHECKBOX MỚI VÀO CỘT 2 >>>
        self.auto_split_checkbox = ctk.CTkCheckBox(options_frame, text="AI tự do chia cảnh", variable=self.auto_split_var)
        self.auto_split_checkbox.grid(row=0, column=2, padx=(10, 5), pady=10, sticky="w")

        # Hàng 1: Giới hạn thời lượng
        ctk.CTkLabel(options_frame, text="Thời lượng tối thiểu / ảnh:").grid(row=1, column=0, columnspan=2, padx=(10,5), pady=(5, 10), sticky="w")
        self.min_duration_menu = ctk.CTkOptionMenu(
            options_frame,
            variable=self.master_app.imagen_min_scene_duration_var,
            values=["Không giới hạn", "Ít nhất 15 giây", "Ít nhất 30 giây", "Ít nhất 1 phút", "Ít nhất 2 phút", "Ít nhất 3 phút"]
        )
        self.min_duration_menu.grid(row=1, column=2, columnspan=2, padx=5, pady=(5, 10), sticky="ew")
        
        ctk.CTkLabel(options_frame, text="Tỷ lệ Ảnh:").grid(row=0, column=3, padx=(20, 5), sticky="e", pady=10)
        self.aspect_ratio_menu = ctk.CTkOptionMenu(options_frame, variable=self.aspect_ratio_var, values=["16:9", "1:1", "9:16", "4:3", "3:4"])
        self.aspect_ratio_menu.grid(row=0, column=4, padx=5, pady=10, sticky="ew")

        # Hàng 2: Phong cách nghệ thuật
        ctk.CTkLabel(options_frame, text="Phong cách nghệ thuật:").grid(row=2, column=0, columnspan=2, padx=(10, 5), pady=(0, 10), sticky="w")
        self.style_menu = ctk.CTkOptionMenu(options_frame, variable=self.style_var, values=list(self.IMAGEN_ART_STYLES.keys()))
        self.style_menu.grid(row=2, column=2, columnspan=2, padx=5, pady=(0, 10), sticky="ew")

        # Hàng 3: Hiệu ứng chuyển động
        ctk.CTkLabel(options_frame, text="Hiệu ứng ảnh tĩnh:").grid(row=3, column=0, columnspan=2, padx=(10, 5), pady=(5, 10), sticky="w")
        self.motion_effect_menu = ctk.CTkOptionMenu(
            options_frame,
            variable=self.motion_effect_var,
            values=["Không có", "Ngẫu nhiên", "Phóng to chậm", "Thu nhỏ chậm", 
                    "Lia trái sang phải", "Lia phải sang trái", 
                    "Lia trên xuống dưới", "Lia dưới lên trên"] # <<< THÊM 2 HIỆU ỨNG MỚI
        )
        self.motion_effect_menu.grid(row=3, column=2, columnspan=2, padx=5, pady=(5, 10), sticky="ew")

        # Hàng 4: Tốc độ hiệu ứng
        ctk.CTkLabel(options_frame, text="Tốc độ hiệu ứng:").grid(row=4, column=0, columnspan=2, padx=(10, 5), pady=(5, 10), sticky="w")
        self.motion_speed_selector = ctk.CTkSegmentedButton(
            options_frame,
            variable=self.motion_speed_var,
            values=["Chậm", "Vừa", "Nhanh"]
        )
        self.motion_speed_selector.grid(row=4, column=2, columnspan=2, padx=5, pady=(5, 10), sticky="ew")

        # KHUNG CÀI ĐẶT FFmpeg NÂNG CAO
        ffmpeg_settings_frame = ctk.CTkFrame(content_container)
        ffmpeg_settings_frame.pack(fill="x", pady=(10, 5))
        ffmpeg_settings_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ffmpeg_settings_frame, text="⚙️ Cài đặt FFmpeg Nâng cao (Slideshow):", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=3, padx=10, pady=(5,0), sticky="w")

        # Hàng 1: Encoder (với logic tự động kiểm tra GPU)
        ctk.CTkLabel(ffmpeg_settings_frame, text="Encoder:").grid(row=1, column=0, padx=(10,5), pady=5, sticky="e")

        # Kiểm tra trạng thái CUDA đã được lưu ở app chính
        if self.master_app.cuda_status == 'AVAILABLE':
            logging.info("[ImagenSettings] Phát hiện GPU NVIDIA. Hiển thị tùy chọn Encoder GPU.")
            # Nếu có GPU, hiển thị menu với cả 2 lựa chọn và cho phép chọn
            encoder_menu = ctk.CTkOptionMenu(
                ffmpeg_settings_frame, 
                variable=self.ffmpeg_encoder_var, 
                values=["libx264 (CPU, Mặc định)", "h264_nvenc (NVIDIA GPU)"]
            )
            encoder_menu.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        else:
            logging.warning(f"[ImagenSettings] Không phát hiện GPU NVIDIA (Status: {self.master_app.cuda_status}). Vô hiệu hóa tùy chọn Encoder GPU.")
            # Nếu không có GPU, chỉ hiển thị lựa chọn CPU và vô hiệu hóa menu
            encoder_menu = ctk.CTkOptionMenu(
                ffmpeg_settings_frame, 
                variable=self.ffmpeg_encoder_var, 
                values=["libx264 (CPU, Mặc định)"], # Chỉ có 1 lựa chọn
                state="disabled" # Vô hiệu hóa menu
            )
            encoder_menu.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

            # Tự động đặt lại lựa chọn về CPU để đảm bảo an toàn
            self.ffmpeg_encoder_var.set("libx264 (CPU, Mặc định)")

        # Hàng 2: Preset và CRF
        ctk.CTkLabel(ffmpeg_settings_frame, text="Preset (Tốc độ):").grid(row=2, column=0, padx=(10,5), pady=5, sticky="e")
        ctk.CTkOptionMenu(ffmpeg_settings_frame, variable=self.ffmpeg_preset_var, values=["veryslow", "slower", "slow", "medium", "fast", "faster", "veryfast", "superfast", "ultrafast"]).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(ffmpeg_settings_frame, text="CRF (Chất lượng):").grid(row=2, column=2, padx=(10,5), pady=5, sticky="e")
        ctk.CTkEntry(ffmpeg_settings_frame, textvariable=self.ffmpeg_crf_var, width=60).grid(row=2, column=3, padx=5, pady=5, sticky="w")

        folder_frame = ctk.CTkFrame(content_container)
        folder_frame.pack(fill="x", pady=(5,10))
        folder_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(folder_frame, text="Lưu tại:").grid(row=0, column=0, padx=(10,5), pady=10)
        ctk.CTkLabel(folder_frame, textvariable=self.output_folder_var, wraplength=350, text_color="gray").grid(row=0, column=1, sticky="ew", padx=5, pady=10)
        ctk.CTkButton(folder_frame, text="Chọn...", width=80, command=self._select_output_folder).grid(row=0, column=2, padx=10, pady=10)

    # Tạo các nút cố định ở dưới cùng
    def _create_bottom_buttons(self):
        """Tạo các nút hành động chính, cố định ở dưới cùng của cửa sổ."""
        inner_button_frame = ctk.CTkFrame(self.bottom_button_frame, fg_color="transparent")
        inner_button_frame.pack(side="right")
        
        ctk.CTkButton(inner_button_frame, text="Hủy", width=100, command=self._on_close_window).pack(side="right", padx=(10,0))
        ctk.CTkButton(inner_button_frame, text="🖼 Tạo Ảnh", width=130, fg_color="#1f6aa5", command=self._initiate_imagen_generation).pack(side="right", padx=5)
        
        redraw_state = "normal" if self.master_app.last_imagen_parameters_used else "disabled"
        self.redraw_button = ctk.CTkButton(inner_button_frame, text="🔄 Vẽ lại", width=100, command=self._initiate_redraw, state=redraw_state)
        self.redraw_button.pack(side="right", padx=(0, 5))

    def _add_character_slot(self, alias="", desc=""):
        slot_frame = ctk.CTkFrame(self.characters_scrollable_frame, fg_color=("gray90", "gray20"))
        slot_frame.pack(fill="x", pady=2, padx=2)
        slot_frame.grid_columnconfigure(3, weight=1)

        alias_var = ctk.StringVar(value=alias)
        desc_var = ctk.StringVar(value=desc)

        ctk.CTkLabel(slot_frame, text="Bí danh:").grid(row=0, column=0, padx=(5,2), pady=5)
        alias_entry = ctk.CTkEntry(slot_frame, textvariable=alias_var, width=120)
        alias_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(slot_frame, text="Mô tả:").grid(row=0, column=2, padx=(10,2), pady=5)
        desc_entry = ctk.CTkEntry(slot_frame, textvariable=desc_var)
        desc_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        delete_button = ctk.CTkButton(
            slot_frame, text="✕", width=28, height=28,
            fg_color="transparent", hover_color="#555555", text_color=("gray10", "gray80"),
            command=lambda sf=slot_frame: self._remove_character_slot(sf)
        )
        delete_button.grid(row=0, column=4, padx=5, pady=5)

        slot_data = { "frame": slot_frame, "alias_var": alias_var, "desc_var": desc_var }
        self.character_slots.append(slot_data)

    def _remove_character_slot(self, slot_frame_to_remove):
        slot_to_delete = next((slot for slot in self.character_slots if slot["frame"] == slot_frame_to_remove), None)
        if slot_to_delete: self.character_slots.remove(slot_to_delete)
        slot_frame_to_remove.destroy()

    def _load_initial_characters(self):
        saved_sheet_text = self.master_app.cfg.get("imagen_last_character_sheet", "")
        if not saved_sheet_text.strip():
            self._add_character_slot("Piu", "Chú chó nhỏ, lông vàng, cổ đeo vòng dây màu đỏ, bốn chân có đốm trắng ở bàn chân")
            return
        lines = saved_sheet_text.split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                alias = parts[0].strip()
                desc = parts[1].strip()
                if alias and desc:
                    self._add_character_slot(alias, desc)
        if not self.character_slots:
            self._add_character_slot()

    def _get_character_sheet_text(self):
        sheet_lines = []
        for slot in self.character_slots:
            alias = slot["alias_var"].get().strip()
            desc = slot["desc_var"].get().strip()
            if alias and desc:
                sheet_lines.append(f"{alias}: {desc}")
        return "\n".join(sheet_lines)

    def _on_gpt_enhance_toggled(self):
        if self.enhance_with_gpt_var.get():
            self.enhance_with_gemini_var.set(False)

    def _on_gemini_enhance_toggled(self):
        if self.enhance_with_gemini_var.get():
            self.enhance_with_gpt_var.set(False)

    def _initiate_redraw(self):
        last_params = self.master_app.last_imagen_parameters_used
        if last_params:
            logging.info(f"Yêu cầu Vẽ lại với params đã lưu: {last_params}")
            self.prompt_var.set(last_params.get("prompt", ""))
            self.negative_prompt_var.set(last_params.get("negative_prompt", ""))
            self.num_images_var.set(str(last_params.get("number_of_images", 1)))
            self.aspect_ratio_var.set(last_params.get("aspect_ratio", "16:9"))
            self.output_folder_var.set(last_params.get("output_folder", ""))
            self.style_var.set(last_params.get("style_name", "Mặc định (AI tự do)"))
            self.enhance_with_gpt_var.set(last_params.get("enhance_gpt", False))
            self.enhance_with_gemini_var.set(last_params.get("enhance_gemini", False))

            self.prompt_textbox.delete("1.0", "end"); self.prompt_textbox.insert("1.0", self.prompt_var.get())
            self.negative_prompt_textbox.delete("1.0", "end"); self.negative_prompt_textbox.insert("1.0", self.negative_prompt_var.get())

            for slot in self.character_slots:
                slot['frame'].destroy()
            self.character_slots.clear()
            saved_sheet_text = last_params.get("character_sheet", "")
            if saved_sheet_text.strip():
                lines = saved_sheet_text.split('\n')
                for line in lines:
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                            self._add_character_slot(parts[0].strip(), parts[1].strip())
            if not self.character_slots:
                self._add_character_slot()
            
            self._initiate_imagen_generation(is_redraw=True)
        else:
            messagebox.showinfo("Thông báo", "Chưa có thông tin để 'Vẽ lại'.\nVui lòng tạo ảnh ít nhất một lần.", parent=self)

    def _select_output_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_folder_var.get(), parent=self)
        if folder: self.output_folder_var.set(folder)

    def _initiate_imagen_generation(self, is_redraw=False):
        user_prompt = self.prompt_textbox.get("1.0", "end-1c").strip()
        negative_prompt = self.negative_prompt_textbox.get("1.0", "end-1c").strip()
        num_images_str = self.num_images_var.get()
        output_folder = self.output_folder_var.get()
        aspect_ratio = self.aspect_ratio_var.get()

        if not user_prompt: messagebox.showwarning("Thiếu Prompt", "Vui lòng nhập mô tả ảnh.", parent=self); return
        try:
            num_images = int(num_images_str)
            if not 1 <= num_images <= 16: messagebox.showwarning("Số lượng không hợp lệ", "Số lượng ảnh cho mỗi lần tạo phải từ 1 đến 16.", parent=self); return
        except (ValueError, TypeError): messagebox.showwarning("Số lượng không hợp lệ", "Số lượng ảnh phải là một số nguyên.", parent=self); return
        if not output_folder or not os.path.isdir(output_folder): messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn một thư mục hợp lệ để lưu ảnh.", parent=self); return
        if not aspect_ratio: messagebox.showwarning("Thiếu tỷ lệ", "Vui lòng chọn tỷ lệ khung hình.", parent=self); return

        selected_style_name = self.style_var.get()
        style_prompt_fragment = self.IMAGEN_ART_STYLES.get(selected_style_name, "")
        character_sheet_text = self._get_character_sheet_text()
        final_prompt_for_ai = f"{user_prompt}, {style_prompt_fragment}" if user_prompt and style_prompt_fragment else user_prompt
        
        self.master_app.last_imagen_parameters_used = {
            "prompt": user_prompt, "negative_prompt": negative_prompt, "number_of_images": num_images, 
            "output_folder": output_folder, "aspect_ratio": aspect_ratio, "style_name": selected_style_name,
            "enhance_gpt": self.enhance_with_gpt_var.get(), "enhance_gemini": self.enhance_with_gemini_var.get(),
            "character_sheet": character_sheet_text
        }
        
        use_gpt = self.enhance_with_gpt_var.get()
        use_gemini = self.enhance_with_gemini_var.get()
        
        if use_gpt or use_gemini:
            engine = "gpt" if use_gpt else "gemini"
            self.master_app.is_gpt_processing_script = True 
            self.master_app.update_status(f"✨ Đang dùng {engine.upper()} để nâng cấp prompt...")
        else:
            self.master_app.is_imagen_processing = True
            self.master_app.update_status(f"🖼 Imagen: Chuẩn bị tạo {num_images} ảnh...")

        self.master_app.start_time = time.time()
        self.master_app.update_time_realtime()
        self._on_close_window() 

        if use_gpt or use_gemini:
            engine = "gpt" if use_gpt else "gemini"
            self.master_app._initiate_prompt_enhancement(
                short_prompt=user_prompt, engine=engine, selected_style_name=selected_style_name,
                character_sheet_text=character_sheet_text, negative_prompt=negative_prompt,
                number_of_images=num_images, output_folder=output_folder, aspect_ratio=aspect_ratio
            )
        else:
            thread = threading.Thread(
                target=self.master_app._execute_imagen_generation_thread, 
                args=(final_prompt_for_ai, negative_prompt, num_images, output_folder, aspect_ratio),
                daemon=True, name="ImagenGenerationThread"
            )
            thread.start()

    def _on_close_window(self):
        self._save_imagen_settings_to_config()
        self.destroy()

    def _save_imagen_settings_to_config(self):
        if not hasattr(self.master_app, 'cfg'): return
        try:
            self.master_app.cfg["imagen_last_prompt"] = self.prompt_textbox.get("1.0", "end-1c").strip()
            self.master_app.cfg["imagen_last_negative_prompt"] = self.negative_prompt_textbox.get("1.0", "end-1c").strip()
            self.master_app.cfg["imagen_last_num_images"] = self.num_images_var.get()
            self.master_app.cfg["imagen_last_aspect_ratio"] = self.aspect_ratio_var.get()
            self.master_app.cfg["imagen_last_style"] = self.style_var.get()
            self.master_app.cfg["imagen_last_character_sheet"] = self._get_character_sheet_text()
            self.master_app.cfg["imagen_auto_split_scenes"] = self.auto_split_var.get()      
            self.master_app.cfg["imagen_min_scene_duration"] = self.master_app.imagen_min_scene_duration_var.get()
            output_folder = self.output_folder_var.get()
            if output_folder and os.path.isdir(output_folder):
                self.master_app.cfg["imagen_last_output_folder"] = output_folder
            self.master_app.cfg["imagen_enhance_with_gpt"] = self.enhance_with_gpt_var.get()
            self.master_app.cfg["imagen_enhance_with_gemini"] = self.enhance_with_gemini_var.get()
            self.master_app.cfg["imagen_use_character_sheet"] = self.use_character_sheet_var.get()
            self.master_app.cfg["imagen_motion_effect"] = self.motion_effect_var.get()
            self.master_app.cfg["imagen_motion_speed"] = self.motion_speed_var.get()

            # LƯU CẤU HÌNH FFmpeg
            # Lấy giá trị encoder chính từ chuỗi, ví dụ "h264_nvenc" từ "h264_nvenc (NVIDIA GPU)"
            encoder_full_string = self.ffmpeg_encoder_var.get()
            encoder_value_to_save = encoder_full_string.split(" ")[0]
            self.master_app.cfg["ffmpeg_encoder"] = encoder_value_to_save

            self.master_app.cfg["ffmpeg_preset"] = self.ffmpeg_preset_var.get()
            self.master_app.cfg["ffmpeg_crf"] = safe_int(self.ffmpeg_crf_var.get(), 23) # Dùng safe_int để đảm bảo là số

            self.master_app.save_current_config()
            logging.info("[ImagenSettings] Đã lưu các cài đặt cuối cùng của Imagen vào config.")
        except Exception as e:
            logging.error(f"[ImagenSettings] Lỗi khi lưu cài đặt Imagen: {e}", exc_info=True)

