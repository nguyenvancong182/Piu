"""
AIEditorTab class for Piu application.
AI-powered script editing tab
Extracted from Piu.py
"""

import customtkinter as ctk
import logging
import os
import json
import time
from tkinter import filedialog, messagebox

from utils.helpers import get_default_downloads_folder
from ui.widgets.menu_utils import textbox_right_click_menu

# Import HAS_OPENAI from Piu.py
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class AIEditorTab(ctk.CTkFrame):
    # --- Các hằng số và danh sách model của riêng Tab này ---
    AVAILABLE_GPT_MODELS_FOR_SCRIPT_EDITING = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"]
    AVAILABLE_GEMINI_MODELS_FOR_SCRIPT_EDITING = [
        "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
        "gemini-2.0-flash", 
        "gemini-2.0-flash-lite", "gemini-1.5-pro-latest", "gemini-1.5-flash-latest"
    ]

    # HẰNG SỐ PROMPT
    DEFAULT_AI_EDITOR_PROMPT = """Bạn là một API xử lý văn bản chuyên nghiệp. Nhiệm vụ của bạn là nhận văn bản gốc và CHỈ trả về kết quả đã biên tập theo đúng 3 phần được yêu cầu dưới đây, tuân thủ nghiêm ngặt quy trình và các quy tắc.

**YÊU CẦU TUYỆT ĐỐI:**
- KHÔNG được phép thêm bất kỳ lời chào, câu dẫn, giải thích, hay tóm tắt nào.
- KHÔNG được phép sử dụng bất kỳ định dạng markdown nào (như `**`, `*`, `#`, `_`).
- KHÔNG được phép thêm số chú thích (như `[1]`, `[2]`).
- KHÔNG được phép lặp lại các nhãn như "Tiêu đề chương:", "Nội dung biên tập:" bên trong phần nội dung trả về.
- KHÔNG được phép trả về các chuỗi placeholder như "[Nội dung tiêu đề ở đây]".

## ĐỊNH DẠNG ĐẦU RA BẮT BUỘC (Sử dụng dấu phân cách):

<<<TITLE>>>
[Chỉ chứa nội dung tiêu đề chương đã tạo, trên một dòng duy nhất]
<<<CONTENT>>>
[Chỉ chứa toàn bộ nội dung chương đã được biên tập, bắt đầu từ dòng tiếp theo]
<<<NOTES>>>
[Chỉ chứa các ghi chú ngắn gọn về lỗi đã sửa, bắt đầu từ dòng tiếp theo]

---

## QUY TRÌNH BIÊN TẬP

### BƯỚC 1: XÁC ĐỊNH NGÔN NGỮ VÀ DỊCH THUẬT (NẾU CẦN)
- Nếu văn bản gốc **không phải tiếng Việt**: Dịch một cách tự nhiên sang tiếng Việt, giữ nguyên tên riêng gốc (ví dụ: John, London, v.v.). Trong bước dịch thuật này, **Quy tắc số 3 (Giữ nguyên nguyên tác)** tạm thời **KHÔNG** áp dụng để đảm bảo bản dịch tự nhiên.
- Nếu văn bản gốc **đã là tiếng Việt**: Bỏ qua bước này và chuyển thẳng đến BƯỚC 2.

### BƯỚC 2: BIÊN TẬP KỸ THUẬT (ÁP DỤNG CHO VĂN BẢN TIẾNG VIỆT SAU BƯỚC 1)
**(CHỈ DẪN QUAN TRỌNG)** SAU KHI BƯỚC 1 HOÀN TẤT, bạn phải coi bản dịch tiếng Việt là **BẢN GỐC CUỐI CÙNG**. TUYỆT ĐỐI không được so sánh lại với ngôn ngữ gốc hoặc thay đổi từ ngữ trong bản dịch để "sát nghĩa hơn". Mọi quy tắc biên tập bên dưới chỉ áp dụng cho bản dịch này.

---

## QUY TẮC CHO BƯỚC 2: BIÊN TẬP KỸ THUẬT

1.  **Soát lỗi:** Sửa tất cả lỗi chính tả, ngữ pháp, lỗi đánh máy. Loại bỏ các ký tự rác từ quá trình sao chép như số thứ tự chương ở đầu văn bản, tên website, hoặc các ký hiệu không thuộc hệ thống dấu câu chuẩn của tiếng Việt.

2.  **Chuyển đổi ký tự:** Chuyển đổi các ký tự đặc biệt (ví dụ: `g·iết`, `v.v...`) thành từ ngữ thông thường (`giết`, `vân vân`).

3.  **GIỮ NGUYÊN NGUYÊN TÁC (QUAN TRỌNG NHẤT):** Đây là quy tắc ưu tiên hàng đầu của bạn.
    * **TUYỆT ĐỐI KHÔNG** thay đổi từ ngữ gốc bằng các từ đồng nghĩa, dù bạn cho rằng nó hay hơn. Ví dụ: **KHÔNG** đổi "ngẩn ra" thành "sững người".
    * **TUYỆT ĐỐI KHÔNG** thay đổi cấu trúc câu gốc hoặc "làm mềm" câu chữ.
    * **TUYỆT ĐỐI KHÔNG** thay đổi hoặc kiểm duyệt các từ ngữ "nhạy cảm" hoặc "thô tục" để giữ nguyên ý đồ của tác giả.
    * Nhiệm vụ của bạn là một người **sửa lỗi kỹ thuật**, không phải là một biên tập viên văn học.

4.  **Chuẩn hóa dấu câu cho Giọng đọc (TTS):** Chỉ sửa các lỗi dấu câu rõ ràng (ví dụ: thiếu dấu chấm cuối câu, thừa dấu cách trước dấu phẩy). **TUYỆT ĐỐI KHÔNG** thêm dấu phẩy vào giữa câu nếu câu gốc không có, nhằm bảo toàn nhịp điệu và văn phong của tác giả.

5.  **PHIÊN ÂM VÀ THAY THẾ TÙY CHỈNH (Quy trình thông minh):** Thực hiện theo đúng thứ tự ưu tiên sau:
    * **A. Áp dụng Bảng chú giải (Ưu tiên cao nhất và linh hoạt):** Dựa vào `BẢNG CHÚ GIẢI TÙY CHỌN`, bạn phải thực hiện thao tác tìm và thay thế. Với mỗi dòng "khóa: giá trị", hãy tìm **tất cả các lần xuất hiện** của 'khóa' trong văn bản và thay thế nó bằng 'giá trị'. Quy tắc này áp dụng ngay cả khi 'khóa' là một phần của một cụm từ lớn hơn. Ví dụ: nếu có `phù thủy: Yêu bà bà`, thì cụm từ "lão phù thủy" phải được đổi thành "lão Yêu bà bà".
    * **B. Tự động học:** Tiếp theo, quét toàn bộ văn bản. Nếu tìm thấy mẫu "Tên Đầy Đủ (TĐR)", ví dụ "Hồn Thiên Đế (HTĐ)", hãy tự động ghi nhớ và áp dụng phiên âm này cho tất cả các từ "HTĐ" trong văn bản (nếu "HTĐ" chưa được định nghĩa trong Bảng chú giải).
    * **C. Phiên âm tên nước ngoài:** Với các từ IN HOA còn lại, nếu xác định là tên riêng nước ngoài, hãy phiên âm. Ví dụ: "COPERNICUS" -> "Cô-péc-ni-cút".
    * **D. Giữ nguyên:** Với các từ viết thường (Robert Langdon), từ viết tắt thông dụng (VIP, USA) hoặc các từ IN HOA không xác định được sau khi đã thực hiện các bước trên, hãy **GIỮ NGUYÊN**.

6.  **PHIÊN ÂM SỐ LA MÃ:** Chuyển đổi tất cả các số La Mã (ví dụ: I, II, V, X, IV, Chương XX) thành dạng chữ viết tiếng Việt tương ứng (ví dụ: một, hai, năm, mười, bốn, Chương hai mươi).

7.  **Định dạng Ghi chú:** Liệt kê các thay đổi đã thực hiện bằng gạch đầu dòng (`-`).

8.  **Đề xuất chú giải cho lần sau (QUAN TRỌNG):** Trong phần "Ghi chú ngắn gọn lỗi đã sửa", sau khi đã liệt kê các lỗi, hãy thêm một dòng phân cách (`---`) và một tiêu đề "**Đề xuất chú giải:**". Dưới tiêu đề này, liệt kê tất cả các từ IN HOA mà bạn đã phải giữ nguyên ở bước 5D. Điều này giúp người dùng biết cần bổ sung từ nào vào Bảng chú giải.
    * **Ví dụ định dạng Ghi chú:**
      - Sửa lỗi chính tả: 'hte' -> 'thế'
      - Phiên âm: 'COPERNICUS' -> 'Cô-péc-ni-cút'
      - ---
      - **Đề xuất chú giải:** QPP, TTV

---

## BẢNG CHÚ GIẢI TÙY CHỌN (DO NGƯỜI DÙNG CUNG CẤP)
QPP: Quách Piu Piu
"""

    # Prompt EN + delimiters cho TTS
    DEFAULT_AI_EDITOR_PROMPT_EN_TTS_V2 = """
You are a professional text-processing API. Your task is to take a source text and ONLY return the edited result in exactly the 3 sections below, using the EXACT delimiters provided. Do NOT output any other text.

ABSOLUTE REQUIREMENTS:
- DO NOT add any greetings, lead-ins, explanations, or summaries.
- DO NOT use any markdown formatting (such as **, *, #, _).
- DO NOT add footnote numbers (such as [1], [2]).
- DO NOT wrap any section content in quotation marks.
- DO NOT echo section labels (e.g., “Edited Content:”) inside the content itself.
# <<< THAY ĐỔI 1: Thêm quy tắc cấm trả về placeholder >>>
- DO NOT return placeholders like "[Chapter title only, on the next line]". You MUST generate the actual title.
- OUTPUT MUST USE THE DELIMITERS BELOW, EXACTLY ON THEIR OWN LINES.

MANDATORY OUTPUT SECTIONS (DELIMITERS):
# <<< THAY ĐỔI 2: Thay đổi ví dụ định dạng để trông giống một lời bình luận hơn, tránh AI sao chép >>>
<<<TITLE>>>
(The generated title goes here on one line)
<<<CONTENT>>>
(The full edited content starts here)
<<<NOTES>>>
(The editing notes start here)

---

EDITING WORKFLOW

STEP 1: LANGUAGE CHECK, TRANSLATION & NAME ROMANIZATION (IF NEEDED)
- If the source text is NOT in English:
  • Translate it naturally into English without paraphrasing beyond what is necessary for natural English.
  • Romanize/anglicize ALL proper names and titles into English-friendly forms for TTS, with this priority:
    (A) If the user Glossary provides a mapping, use it.
    (B) If a widely accepted English form exists, use that (e.g., Copernicus, Beijing, Park Ji-sung).
    (C) Otherwise, use standard romanization for the language, simplified for English TTS (no tone marks/diacritics):
        - Vietnamese: strip diacritics; keep spacing/capitalization. Examples: “Hàn Lập” → “Han Lap”; “Quách Piu Piu” → “Quach Piu Piu”.
        - Chinese: Hanyu Pinyin (no tone marks); space multi-syllable names. “张三丰” → “Zhang Sanfeng”.
        - Japanese: Hepburn; omit macrons. “Tōkyō” → “Tokyo”.
        - Korean: Revised Romanization. “박지성” → “Park Ji-sung”.
        - Cyrillic/Arabic/others: use common English exonyms if any; otherwise a simple, diacritic-free romanization approximating English phonetics.
  • Keep romanization consistent across the chapter.
- If the source text IS already in English:
  • Do NOT re-translate. Proceed to STEP 2.
  • If non-Latin or diacritic-heavy proper names appear, romanize them now per above.

IMPORTANT: After STEP 1, treat the English text (with romanized names) as the FINAL SOURCE. DO NOT compare back to the original or revise wording for “closer meaning.” All rules below apply only to this English version.

---

STEP 2: TECHNICAL EDITING (ENGLISH, TTS-AWARE)

1) Proofreading:
   - Fix spelling, grammar, and typos.
   - Remove copy-paste artifacts (chapter numbers at the top, site watermarks, non-standard symbols outside standard English punctuation).

2) Character & Symbol Normalization:
   - Normalize broken/odd tokens to plain words (e.g., “k·ill” → “kill”; “etc...” → “etc.”).
   - Normalize quotes to straight ASCII for TTS: “ ” → " ; ‘ ’ → ' .
   - Normalize ellipses consistently to either “…” (U+2026) or “...”.
   - Prefer an em dash with spaces for natural TTS pauses: " — ".

3) PRESERVE ORIGINAL WORDING (HIGHEST PRIORITY):
   - DO NOT replace original wording with synonyms.
   - DO NOT change sentence structure or “smooth” the prose.
   - DO NOT censor “sensitive” or “vulgar” words.
   - EXCEPTION: Proper-name romanization from STEP 1 is allowed for TTS; otherwise, no paraphrasing.

4) Punctuation Normalization for TTS:
   - Fix only clear punctuation errors (missing final periods, stray spaces before commas, duplicated punctuation).
   - DO NOT add commas mid-sentence if the original did not have them.
   - Numbers and units:
     • Spell out one through nine in narration when appropriate; keep numerals for 10+ and for measurements/dates.
     • Keep standard unit abbreviations (cm, km, kg) and times (AM/PM).

5) TRANSLITERATION & CUSTOM REPLACEMENTS (Smart Procedure):
   (A) Apply the OPTIONAL USER-PROVIDED GLOSSARY (highest priority). Replace ALL occurrences of each key with its value, even inside longer phrases.
   (B) Auto-Learn Abbreviations: If a pattern “Full Name (ABBR)” appears (e.g., “Heavenly Soul Emperor (HSE)”), expand ABBR consistently thereafter (unless defined in the Glossary).
   (C) Remaining ALL-CAPS tokens:
       • If proper names, convert to standard English forms (Title Case) per STEP 1 or common usage: “COPERNICUS” → “Copernicus”.
       • If no accepted form is clear, keep Title Case and list under Glossary Suggestions.
   (D) Keep As-Is: lowercase proper names (e.g., Robert Langdon) and common abbreviations (VIP, USA).

6) ROMAN NUMERALS (Refined rule):
   - For chapter titles and title-like headers (output under <<<TITLE>>>; “Chapter XX”, “Act IV”, “Part III”), convert to ARABIC numerals:
       • “Chapter XX” → “Chapter 20”; “Act IV” → “Act 4”; “Part III” → “Part 3”.
   - For in-narrative text (dialogue and prose), convert to written-out English words:
       • “He won in Round V.” → “He won in Round five.”; “the king Louis XIV” → “the king Louis fourteen”.
   - If ambiguous (e.g., product names like “iPhone X”), DO NOT convert; add to Glossary Suggestions.

7) Notes Formatting (for <<<NOTES>>>):
   - Use bullet lines starting with “- ”.
   - After bullets, output exactly one line with three hyphens: ---
   - On the next line, output “Glossary Suggestions: ” followed by comma-separated tokens (if none, output “Glossary Suggestions: (none)”).

EXAMPLE NOTES:
- Spelling fix: “hte” → “the”
- Romanization: “Hàn Lập” → “Han Lap”
- Roman numerals: “Chapter XX” → “Chapter 20”; “Round V” → “Round five”
---
Glossary Suggestions: QPP, TTV, iPhone X

---

OPTIONAL USER-PROVIDED GLOSSARY
QPP: Quach Piu Piu
"""

#----------------------

    def __init__(self, master, master_app):
        super().__init__(master)
        self.master_app = master_app
        logging.info("Khởi tạo Tab AI Biên Tập (Module Độc Lập v3.0 - 3 Textbox)...")

        self.is_running = False
        self.queue = []
        self.current_file = None

        # Tải lại engine và prompt đã lưu từ lần trước
        self.current_engine = self.master_app.cfg.get("last_used_ai_engine_aie", "💎 Gemini")        
        # Xác định key config dựa trên engine đã lưu
        prompt_config_key = f"last_used_{'gemini' if 'Gemini' in self.current_engine else 'gpt'}_prompt_ai_batch_editor"        
        # Tải prompt đã lưu vào biến self.current_prompt

        self.current_prompt = self.master_app.cfg.get(prompt_config_key, "")
        self.start_time = None
        self._last_status_text = ""
        self.batch_counter = 0
        
        default_output_folder = self.master_app.cfg.get("ai_editor_output_folder", get_default_downloads_folder())
        self.output_folder_var = ctk.StringVar(value=default_output_folder)
        self.rename_var = ctk.BooleanVar(value=self.master_app.cfg.get("ai_editor_rename_enabled", False))
        self.rename_base_name_var = ctk.StringVar(value=self.master_app.cfg.get("ai_editor_rename_base_name", ""))

        # <<< THÊM 2 BIẾN MỚI NÀY VÀO ĐÂY >>>
        self.enable_production_chain_var = ctk.BooleanVar(value=self.master_app.cfg.get("ai_editor_enable_chain", False))
        self.production_chain_output_path_var = ctk.StringVar(value=self.master_app.cfg.get("ai_editor_chain_output_path", ""))
        # <<< KẾT THÚC THÊM MỚI >>>        
        
        self.auto_naming_var = ctk.BooleanVar(value=self.master_app.cfg.get("ai_editor_auto_naming_enabled", True))
        self.series_name_var = ctk.StringVar(value=self.master_app.cfg.get("ai_editor_series_name", "Đấu Phá Thương Khung"))
        self.start_chapter_var = ctk.StringVar(value=self.master_app.cfg.get("ai_editor_start_chapter", "1"))

        # Bật/tắt chế độ EN TTS
        self.en_tts_mode_var = ctk.BooleanVar(value=self.master_app.cfg.get("ai_editor_en_tts_mode", False))
        
        self.current_engine = self.master_app.cfg.get("last_used_ai_engine_aie", "💎 Gemini")
        self.gpt_model_var = ctk.StringVar(value=self.master_app.cfg.get("gpt_model_for_aie", self.AVAILABLE_GPT_MODELS_FOR_SCRIPT_EDITING[0]))
        self.gemini_model_var = ctk.StringVar(value=self.master_app.cfg.get("gemini_model_for_aie", self.AVAILABLE_GEMINI_MODELS_FOR_SCRIPT_EDITING[0]))

        # Biến tự động dán
        self.auto_add_on_paste_var = ctk.BooleanVar(value=self.master_app.cfg.get("ai_editor_auto_add_on_paste", True))
        # Biến đếm ký tự
        self.content_label_var = ctk.StringVar(value="📖 Nội dung Kịch bản (Dán vào đây):")

        # <<< THAY ĐỔI 1: Thêm các hằng số cho ô tiêu đề >>>
        self.MANUAL_TITLE_PLACEHOLDER = "Nhập tiêu đề thủ công (tùy chọn)..."
        # Lấy màu chữ mặc định từ theme để đảm bảo tương thích Sáng/Tối
        self.ACTIVE_TITLE_COLOR = ctk.ThemeManager.theme["CTkLabel"]["text_color"] 
        self.PLACEHOLDER_COLOR = "gray"
        # <<< KẾT THÚC THAY ĐỔI 1 >>>
                
        self._create_widgets()

    # ----------------------------------------------------
    # KHỐI CÁC HÀM GIAO DIỆN (UI)
    # ----------------------------------------------------

    def _create_widgets(self):
        """Tạo toàn bộ giao diện cho tab AI Biên Tập (PHIÊN BẢN 2.4 - Thêm checkbox Tự động thêm)."""
        panel_bg_color = ("gray92", "gray14")
        card_bg_color = ("gray86", "gray17")
        textbox_bg_color = ("#F9F9FA", "#212121")

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1, uniform="panelgroup") # Cột 0 cho panel trái (tỷ lệ 1)
        main_frame.grid_columnconfigure(1, weight=2, uniform="panelgroup") # Cột 1 cho panel phải (tỷ lệ 2)
        main_frame.grid_rowconfigure(0, weight=1)

        # --- Panel Trái (Không thay đổi) ---
        left_panel_container = ctk.CTkFrame(main_frame, fg_color=panel_bg_color, corner_radius=12)
        left_panel_container.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        left_panel_container.pack_propagate(False)
        left_scrollable_content = ctk.CTkScrollableFrame(left_panel_container, fg_color="transparent")
        left_scrollable_content.pack(expand=True, fill="both", padx=5, pady=5)
        action_buttons_frame = ctk.CTkFrame(left_scrollable_content, fg_color="transparent")
        action_buttons_frame.pack(pady=10, padx=5, fill="x")
        action_buttons_frame.grid_columnconfigure((0, 1), weight=1)
        self.add_files_button = ctk.CTkButton(action_buttons_frame, text="➕ Thêm Files Kịch bản...", height=35, font=("Segoe UI", 13, "bold"), command=self._add_files_to_queue)
        self.add_files_button.grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="ew")
        self.start_button = ctk.CTkButton(action_buttons_frame, text="🚀 Bắt đầu Biên tập Hàng loạt", height=45, font=("Segoe UI", 15, "bold"), command=self._start_batch_editing_aie)
        self.start_button.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")
        self.stop_button = ctk.CTkButton(action_buttons_frame, text="🛑 Dừng", height=35, font=("Segoe UI", 13, "bold"), fg_color=("#D32F2F", "#C62828"), command=self._stop_batch_editing_aie, state=ctk.DISABLED)
        self.stop_button.grid(row=2, column=0, padx=(0, 2), pady=(5, 0), sticky="ew")
        self.open_output_folder_button = ctk.CTkButton(action_buttons_frame, text="📂 Mở Thư Mục Lưu", height=35, font=("Segoe UI", 13, "bold"), command=self._open_output_folder)
        self.open_output_folder_button.grid(row=2, column=1, padx=(2, 0), pady=(5, 0), sticky="ew")

        # ====== THAM SỐ KHOẢNG CÁCH CHUNG ======
        CARD_PADX = 5          # lề ngoài hai bên của card
        CARD_PADY = 12         # khoảng cách dọc giữa các card
        INNER_PADX = 10        # lề trái/phải bên trong card
        INNER_PADY = 10        # lề trên/dưới bên trong card
        CONTROL_GAP_Y = 10     # khoảng cách dọc giữa các control trong cùng card

        # ───────────────── Card 1: Tùy chỉnh Prompt AI ─────────────────
        edit_prompt_frame = ctk.CTkFrame(left_scrollable_content, fg_color=card_bg_color, corner_radius=8)
        edit_prompt_frame.pack(fill="x", padx=CARD_PADX, pady=(10, 5))  # card đầu tiên giữ nguyên 10 ở trên cho "êm"
        self.edit_prompt_button = ctk.CTkButton(
            edit_prompt_frame,
            text="⚙️ Tùy chỉnh Prompt AI...",
            height=38,
            font=("Segoe UI", 13, "bold"),
            command=self._open_ai_popup_aie,
            fg_color="#00838F",
            hover_color="#006064"
        )
        self.edit_prompt_button.pack(fill="x", expand=True, padx=INNER_PADX, pady=INNER_PADY)

        # ───────────────── Card 2: Biên tập tiếng Anh (TTS) ─────────────────
        en_tts_frame = ctk.CTkFrame(left_scrollable_content, fg_color=card_bg_color, corner_radius=8)
        en_tts_frame.pack(fill="x", padx=CARD_PADX, pady=(CARD_PADY, 5))

        self.chk_en_tts = ctk.CTkCheckBox(
            en_tts_frame,
            text="🗣 Biên tập tiếng Anh (TTS)",
            variable=self.en_tts_mode_var,
            font=("Segoe UI", 12, "bold")
        )
        self.chk_en_tts.pack(anchor="w", padx=INNER_PADX, pady=(INNER_PADY, INNER_PADY))

        # ───────────────── Card 3: Chuỗi Sản xuất AI ─────────────────
        chain_frame = ctk.CTkFrame(left_scrollable_content, fg_color=card_bg_color, corner_radius=8)
        chain_frame.pack(fill="x", padx=CARD_PADX, pady=(CARD_PADY, 5))

        self.chain_enabled_checkbox = ctk.CTkCheckBox(
            chain_frame,
            text="🚀 Kích hoạt Chuỗi Sản xuất AI (sau khi biên tập)",
            variable=self.enable_production_chain_var,
            font=("Segoe UI", 12, "bold"),
            command=self._toggle_production_chain_widgets
        )
        self.chain_enabled_checkbox.pack(anchor="w", padx=INNER_PADX, pady=(INNER_PADY, CONTROL_GAP_Y))

        # Khối chọn đường dẫn (hiện/ẩn sau)
        self.chain_path_frame = ctk.CTkFrame(chain_frame, fg_color="transparent")
        self.chain_path_frame.pack(fill="x", padx=INNER_PADX, pady=(0, INNER_PADY))  # pack để canh lề đều; có thể pack_forget() ở toggle
        self.chain_path_frame.grid_columnconfigure(1, weight=1)  # Cho label đường dẫn giãn ra

        ctk.CTkLabel(
            self.chain_path_frame,
            text="Thư mục kịch bản đã sửa cho chuỗi AI:",
            font=("Segoe UI", 11)
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=(5, 4))

        self.chain_path_label = ctk.CTkLabel(
            self.chain_path_frame,
            textvariable=self.production_chain_output_path_var,
            anchor="w",
            wraplength=200,
            text_color="gray"
        )
        self.chain_path_label.grid(row=1, column=0, columnspan=2, padx=10, pady=(2, 2), sticky="ew")

        ctk.CTkButton(
            self.chain_path_frame,
            text="Chọn...",
            width=80,
            command=self._select_chain_output_folder
        ).grid(row=1, column=2, padx=(0, 5), pady=(2, 2), sticky="e")

        # ───────────────── Card 4: Thư mục lưu ─────────────────
        out_frame = ctk.CTkFrame(left_scrollable_content, fg_color=card_bg_color, corner_radius=8)
        out_frame.pack(fill="x", padx=CARD_PADX, pady=(CARD_PADY, 5))

        out_frame_inner = ctk.CTkFrame(out_frame, fg_color="transparent")
        out_frame_inner.pack(fill="x", padx=INNER_PADX, pady=(INNER_PADY, INNER_PADY))
        out_frame_inner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(out_frame_inner, text="📁 Thư mục lưu:", font=("Poppins", 13)).grid(
            row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 0)
        )
        ctk.CTkButton(
            out_frame_inner, text="Chọn...", width=80, command=self._select_output_folder
        ).grid(row=0, column=2, sticky="e")

        self.output_display_label = ctk.CTkLabel(
            out_frame_inner,
            textvariable=self.output_folder_var,
            anchor="w",
            font=("Segoe UI", 10),
            text_color=("gray30", "gray70")
        )
        self.output_display_label.grid(row=0, column=1, padx=10, sticky="ew")
        self.output_folder_var.trace_add(
            "write",
            lambda *a: self.output_display_label.configure(text=self.output_folder_var.get() or "Chưa chọn")
        )

        # ───────────────── Card 5: Đặt tên file ─────────────────
        rename_frame = ctk.CTkFrame(left_scrollable_content, fg_color=card_bg_color, corner_radius=8)
        rename_frame.pack(fill="x", padx=CARD_PADX, pady=(CARD_PADY, 10))
        rename_frame.grid_columnconfigure((0, 1), weight=1)

        self.rename_checkbox = ctk.CTkCheckBox(
            rename_frame,
            text="Đặt lại tên file",
            variable=self.rename_var,
            command=self._toggle_rename_entry,
            checkbox_width=18,
            checkbox_height=18,
            font=("Segoe UI", 12)
        )
        self.rename_checkbox.grid(row=0, column=0, padx=INNER_PADX, pady=(INNER_PADY, CONTROL_GAP_Y), sticky="w")

        self.auto_naming_var = ctk.BooleanVar(value=self.master_app.cfg.get("ai_editor_auto_naming_enabled", True))
        self.auto_naming_checkbox = ctk.CTkCheckBox(
            rename_frame,
            text="Tự động đặt tên chương",
            variable=self.auto_naming_var,
            command=self._toggle_naming_options,
            checkbox_width=18,
            checkbox_height=18,
            font=("Segoe UI", 12)
        )
        self.auto_naming_checkbox.grid(row=0, column=1, padx=INNER_PADX, pady=(INNER_PADY, CONTROL_GAP_Y), sticky="w")

        self.rename_entry_frame = ctk.CTkFrame(rename_frame, fg_color="transparent")
        self.rename_entry_frame.grid(row=1, column=0, columnspan=2, padx=0, pady=(0, INNER_PADY), sticky="ew")

        ctk.CTkLabel(self.rename_entry_frame, text="Tên chung:", anchor="w").pack(side="left", padx=(INNER_PADX, 6))
        self.rename_entry = ctk.CTkEntry(self.rename_entry_frame, textvariable=self.rename_base_name_var)
        self.rename_entry.pack(side="left", fill="x", expand=True, padx=(0, INNER_PADX))
        self.rename_entry.bind("<KeyRelease>", lambda event: self._update_queue_display())
        self.rename_entry.bind("<Button-3>", textbox_right_click_menu)

        # --- Panel Phải (Đã Cập Nhật) ---
        right_panel = ctk.CTkFrame(main_frame, fg_color=panel_bg_color, corner_radius=12)
        right_panel.grid(row=0, column=1, pady=0, sticky="nsew")
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)
        self.queue_frame = ctk.CTkScrollableFrame(right_panel, label_text="📋 Hàng chờ Biên tập", label_font=("Poppins", 14, "bold"), height=100)
        self.queue_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.textbox_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self.textbox_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.textbox_frame.grid_columnconfigure(0, weight=1)
        self.textbox_frame.grid_rowconfigure(2, weight=1)
        self.naming_options_frame = ctk.CTkFrame(self.textbox_frame, fg_color=card_bg_color)
        self.naming_options_frame.grid(row=0, column=0, sticky="ew", pady=(2, 2))
        self.naming_options_frame.grid_columnconfigure(4, weight=1)
        ctk.CTkLabel(self.naming_options_frame, text="Chương...").grid(row=0, column=0, padx=(10, 5), pady=5, sticky="e")
        self.start_chapter_var = ctk.StringVar(value=self.master_app.cfg.get("ai_editor_start_chapter", "1"))
        start_chapter_entry = ctk.CTkEntry(self.naming_options_frame, textvariable=self.start_chapter_var, width=150)
        start_chapter_entry.grid(row=0, column=1, pady=5, sticky="w")
        start_chapter_entry.bind("<Button-3>", textbox_right_click_menu)
        down_button = ctk.CTkButton(self.naming_options_frame, text="−", width=28, height=28, font=("Segoe UI", 16, "bold"), command=self._decrement_chapter)
        down_button.grid(row=0, column=2, padx=(5, 2), pady=5)
        up_button = ctk.CTkButton(self.naming_options_frame, text="+", width=28, height=28, font=("Segoe UI", 16, "bold"), command=self._increment_chapter)
        up_button.grid(row=0, column=3, padx=(2, 3), pady=5)
        self.title_textbox = ctk.CTkTextbox(self.naming_options_frame, height=30, wrap="word", border_width=1, fg_color=textbox_bg_color)
        self.title_textbox.grid(row=0, column=4, padx=(5,10), pady=5, sticky="ew")
        self.title_textbox.configure(state="normal", font=("Segoe UI", 12, "italic"))
        self.title_textbox.bind("<Button-3>", textbox_right_click_menu)
        self.title_textbox.bind("<FocusIn>", self._on_title_focus_in)
        self.title_textbox.bind("<FocusOut>", self._on_title_focus_out)
        
        content_header_frame = ctk.CTkFrame(self.textbox_frame, fg_color="transparent")
        content_header_frame.grid(row=1, column=0, sticky="ew", pady=(5,2))
        content_header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(content_header_frame, textvariable=self.content_label_var, font=("Poppins", 13, "bold")).grid(row=0, column=0, sticky="w")
        add_to_queue_button = ctk.CTkButton(content_header_frame, text="➕ Thêm vào hàng chờ", command=self._add_current_content_to_queue, width=160)
        add_to_queue_button.grid(row=0, column=1, sticky="e")
        self.content_textbox = ctk.CTkTextbox(self.textbox_frame, wrap="word", border_width=1, fg_color=textbox_bg_color)
        self.content_textbox.grid(row=2, column=0, sticky="nsew", pady=(0, 2))
        self.content_textbox.bind("<<Paste>>", self._handle_paste_and_add_to_queue)
        self.content_textbox.bind("<Button-3>", textbox_right_click_menu)
        self.content_textbox.bind("<KeyRelease>", self._update_character_count)
        
        # --- KHUNG MỚI CHO TIÊU ĐỀ GHI CHÚ VÀ CHECKBOX ---
        notes_header_frame = ctk.CTkFrame(self.textbox_frame, fg_color="transparent")
        notes_header_frame.grid(row=3, column=0, sticky="ew", pady=(2,2))
        notes_header_frame.grid_columnconfigure(0, weight=1) # Giúp label giãn ra

        ctk.CTkLabel(notes_header_frame, text="🔧 Ghi chú lỗi đã sửa (AI tự điền):", font=("Poppins", 13, "bold")).grid(row=0, column=0, sticky="w")

        # Checkbox mới nằm ở đây
        self.auto_add_checkbox = ctk.CTkCheckBox(
            notes_header_frame,
            text="Thêm hàng chờ tự động",
            variable=self.auto_add_on_paste_var,
            checkbox_width=20, checkbox_height=20,
            font=("Segoe UI", 12)
        )
        self.auto_add_checkbox.grid(row=0, column=1, sticky="e", padx=(10,0))
        # --- KẾT THÚC KHUNG MỚI ---

        self.notes_textbox = ctk.CTkTextbox(self.textbox_frame, height=70, wrap="word", border_width=1, fg_color=textbox_bg_color)
        self.notes_textbox.grid(row=4, column=0, sticky="ew")
        self.notes_textbox.configure(state="disabled")
        
        self.status_label_aie = ctk.CTkLabel(main_frame, text="✅ AI Biên Tập: Sẵn sàng biên tập Kịch Bản.", font=("Segoe UI", 12), anchor='w')
        self.status_label_aie.grid(row=1, column=0, columnspan=2, padx=10, pady=(5,0), sticky="ew")

        self._toggle_rename_entry()
        self._update_queue_display()
        self._toggle_naming_options()
        self._update_character_count()
        self._toggle_production_chain_widgets()

    # Xóa placeholder khi người dùng click vào ô tiêu đề."""
    def _on_title_focus_in(self, event=None):
        """
        (ĐÃ SỬA LỖI)
        Xóa placeholder/tiêu đề tạm và đổi màu chữ thành 'active' khi người dùng click vào.
        Logic này bây giờ sẽ dựa vào MÀU SẮC để xác định nội dung có phải là 'inactive' hay không.
        """
        try:
            # Lấy màu chữ hiệu dụng hiện tại (tương thích Sáng/Tối)
            current_effective_color = self.title_textbox._apply_appearance_mode(self.title_textbox.cget("text_color"))
            
            # Lấy màu chữ placeholder hiệu dụng
            placeholder_effective_color = self.title_textbox._apply_appearance_mode(self.PLACEHOLDER_COLOR)

            # Nếu màu hiện tại là màu placeholder -> đây là nội dung "inactive"
            if current_effective_color == placeholder_effective_color:
                # Xóa nội dung (dù đó là placeholder hay tiêu đề cũ)
                self.title_textbox.delete("1.0", "end")
                # Đặt lại màu chữ về màu "active" mặc định
                self.title_textbox.configure(text_color=self.ACTIVE_TITLE_COLOR)
        except Exception as e:
            logging.error(f"Lỗi trong _on_title_focus_in: {e}")

    # Hiện lại placeholder và đổi màu chữ thành 'inactive' nếu ô trống
    def _on_title_focus_out(self, event=None):
        """Hiện lại placeholder và đổi màu chữ thành 'inactive' nếu ô trống."""
        current_text = self.title_textbox.get("1.0", "end-1c").strip()
        
        if not current_text:
            # Đổi màu chữ sang màu xám (màu mờ)
            self.title_textbox.configure(text_color=self.PLACEHOLDER_COLOR)
            self.title_textbox.insert("1.0", self.MANUAL_TITLE_PLACEHOLDER)    

    # Cập nhật hiển thị hàng chờ, có tooltip cho cả mục đang xử lý và đang chờ.
    def _update_queue_display(self):
        """
        (PHIÊN BẢN 5.1 - THÊM TOOLTIP HOÀN CHỈNH)
        Cập nhật hiển thị hàng chờ, có tooltip cho cả mục đang xử lý và đang chờ.
        """
        for widget in self.queue_frame.winfo_children(): widget.destroy()
        
        current_task_display = self.current_file
        queue_to_display = list(self.queue)

        if not queue_to_display and not current_task_display:
            ctk.CTkLabel(self.queue_frame, text="[Hàng chờ AI biên tập trống]", font=("Segoe UI", 11), text_color="gray").pack(pady=20)
            return

        # --- Hiển thị task đang xử lý (ĐÃ THÊM TOOLTIP) ---
        if self.is_running and current_task_display:
            frame = ctk.CTkFrame(self.queue_frame, fg_color="#9932CC")
            frame.pack(fill="x", pady=(2, 5), padx=2)
            
            # <<<--- BẮT ĐẦU THAY ĐỔI 1 --->>>
            display_name = current_task_display['display_name']
            full_filepath = current_task_display['filepath']
            
            shortened_display_name = display_name if len(display_name) < 50 else display_name[:47] + "..."
            label_text = f"▶️ ĐANG XỬ LÝ:\n    {shortened_display_name}"
            
            processing_label = ctk.CTkLabel(frame, text=label_text, font=("Poppins", 11, "bold"), justify="left", anchor='w', text_color="white")
            processing_label.pack(side="left", padx=5, pady=3, fill="x", expand=True)

            Tooltip(processing_label, text=full_filepath) # Gắn tooltip với đường dẫn đầy đủ
            # <<<--- KẾT THÚC THAY ĐỔI 1 --->>>

        # --- Hiển thị các task trong hàng chờ (ĐÃ THÊM TOOLTIP) ---
        for i, task in enumerate(queue_to_display):
            item_frame = ctk.CTkFrame(self.queue_frame, fg_color="transparent")
            item_frame.pack(fill="x", padx=2, pady=(1,2))
            
            # <<<--- BẮT ĐẦU THAY ĐỔI 2 --->>>
            display_name = task['display_name']
            full_path = task['filepath'] # Lấy đường dẫn đầy đủ cho tooltip
            
            rename_info = task['rename_info']
            if rename_info['use_rename'] and rename_info['base_name'].strip():
                base_name = rename_info['base_name'].strip()
                original_extension = os.path.splitext(task['filepath'])[1]
                display_name = f"{base_name}_{i+1:03d}{original_extension} (Xem trước)"

            # Rút gọn tên hiển thị trên label
            shortened_display_name = display_name if len(display_name) < 45 else display_name[:42] + "..."

            # Gán label cho biến và thêm tooltip
            item_label = ctk.CTkLabel(item_frame, text=f"{i+1}. {shortened_display_name}", anchor="w", font=("Segoe UI", 11))
            item_label.pack(side="left", padx=(5, 0), expand=True, fill="x")
            Tooltip(item_label, text=full_path) # Gắn tooltip
            # <<<--- KẾT THÚC THAY ĐỔI 2 --->>>
            
            # Các nút điều khiển không thay đổi
            del_button = ctk.CTkButton(item_frame, text="✕", width=26, height=26, font=("Segoe UI", 12, "bold"), command=lambda idx=i: self._remove_from_queue(idx), fg_color="#E74C3C", hover_color="#C0392B")
            del_button.pack(side="right", padx=(3, 5))
            down_button = ctk.CTkButton(item_frame, text="↓", width=26, height=26, font=("Segoe UI", 14, "bold"), state="disabled" if i == len(queue_to_display) - 1 else "normal", command=lambda idx=i: self._move_item_in_queue(idx, "down"))
            down_button.pack(side="right", padx=(3, 0))
            up_button = ctk.CTkButton(item_frame, text="↑", width=26, height=26, font=("Segoe UI", 14, "bold"), state="disabled" if i == 0 else "normal", command=lambda idx=i: self._move_item_in_queue(idx, "up"))
            up_button.pack(side="right", padx=(0, 0))


    # Đếm số ký tự trong ô nội dung và cập nhật nhãn
    def _update_character_count(self, event=None):
        """Đếm số ký tự trong ô nội dung và cập nhật nhãn."""
        text_content = self.content_textbox.get("1.0", "end-1c")
        char_count = len(text_content)
        # Dùng f-string với định dạng {:,} để thêm dấu phẩy hàng nghìn
        self.content_label_var.set(f"📖 Nội dung Kịch bản (Dán vào đây) - [{char_count:,} ký tự]")


    def _toggle_rename_entry(self):
        """
        (ĐÃ SỬA LỖI)
        Hiện/ẩn ô nhập "Tên chung" bằng cách sử dụng grid() và grid_remove()
        để tương thích với layout của frame cha.
        """
        if self.rename_var.get():
            # Dùng .grid() để đặt ô nhập vào hàng thứ 2 (row=1),
            # kéo dài 2 cột (columnspan=2) để nằm ngay dưới 2 checkbox.
            self.rename_entry_frame.grid(row=1, column=0, columnspan=2, padx=0, pady=(0,10), sticky="ew")
            self.rename_entry.configure(state="normal")
        else:
            # Dùng .grid_remove() để ẩn đi mà vẫn giữ lại cấu hình grid.
            self.rename_entry_frame.grid_remove()
            self.rename_entry.configure(state="disabled")
        
        # Cập nhật hiển thị hàng chờ vẫn cần thiết
        self._update_queue_display()


    # Bật/tắt các ô nhập liệu cho việc đặt tên tự động
    def _toggle_naming_options(self):
        """Bật/tắt các ô nhập liệu cho việc đặt tên tự động."""
        state = "normal" if self.auto_naming_var.get() else "disabled"
        # Chỉ có một ô nhập liệu cần bật/tắt
        for widget in self.naming_options_frame.winfo_children():
            if isinstance(widget, ctk.CTkEntry):
                widget.configure(state=state)

# === CÁC HÀM MỚI CHO NÚT TĂNG/GIẢM SỐ CHƯƠNG ===
    def _increment_chapter(self):
        """
        (Nâng cấp) Tăng số cuối cùng tìm thấy trong chuỗi lên 1.
        Ví dụ: "Tập 1" -> "Tập 2".
        """
        current_val = self.start_chapter_var.get()
        # Tìm tất cả các chuỗi số trong giá trị hiện tại
        matches = list(re.finditer(r'\d+', current_val))

        # Nếu tìm thấy ít nhất một số
        if matches:
            # Lấy số cuối cùng tìm được
            last_match = matches[-1]
            num = int(last_match.group(0))
            start, end = last_match.span()

            # Tăng số đó lên 1
            new_num = num + 1

            # Tạo lại chuỗi mới bằng cách thay thế số cũ bằng số mới
            new_val = current_val[:start] + str(new_num) + current_val[end:]
            self.start_chapter_var.set(new_val)

    def _decrement_chapter(self):
        """
        (Nâng cấp) Giảm số cuối cùng tìm thấy trong chuỗi xuống 1.
        Ví dụ: "Tập 10" -> "Tập 9".
        """
        current_val = self.start_chapter_var.get()
        matches = list(re.finditer(r'\d+', current_val))

        if matches:
            last_match = matches[-1]
            num = int(last_match.group(0))
            start, end = last_match.span()

            # Chỉ giảm nếu số lớn hơn 1 để tránh số âm hoặc 0
            if num > 1:
                new_num = num - 1
                new_val = current_val[:start] + str(new_num) + current_val[end:]
                self.start_chapter_var.set(new_val)


    # Sửa lại hàm này trong lớp AIEditorTab
    def _handle_paste_and_add_to_queue(self, event=None):
        """
        (Nâng cấp) Xử lý sự kiện dán. Nếu checkbox được chọn, tự động thêm vào hàng chờ.
        """
        try:
            pasted_content = self.clipboard_get()
            if not pasted_content.strip():
                return "break"

            # Xóa các ô trước khi dán
            self._clear_textbox_content()
            self.content_textbox.insert("1.0", pasted_content)
            self._update_character_count()
            
            # KIỂM TRA CHECKBOX Ở ĐÂY
            if self.auto_add_on_paste_var.get():
                # Nếu được tick, gọi hàm thêm vào hàng chờ ngay lập tức
                # Dùng `after` để đảm bảo nội dung được dán xong xuôi trước khi xử lý
                self.after(50, self._add_current_content_to_queue)
            else:
                # Nếu không, chỉ cập nhật trạng thái như cũ
                self._update_status_aie("Đã dán nội dung. Nhấn 'Thêm vào hàng chờ' để xác nhận.")
            
            return "break"
        except Exception as e:
            logging.error(f"Lỗi khi xử lý sự kiện dán: {e}")
            messagebox.showerror("Lỗi Dán", f"Không thể xử lý nội dung từ clipboard.\nLỗi: {e}", parent=self)
            return "break"


    # Lấy nội dung từ textbox, tạo task object với thông tin đặt tên
    def _add_current_content_to_queue(self):
        """(ĐÃ NÂNG CẤP v4.4) Lấy tiêu đề thủ công DỰA TRÊN MÀU SẮC CHỮ."""

        # Logic kiểm tra và xóa tiêu đề "tạm" từ lô trước
        try:
            current_color = self.title_textbox._apply_appearance_mode(self.title_textbox.cget("text_color"))
            placeholder_color = self.title_textbox._apply_appearance_mode(self.PLACEHOLDER_COLOR)

            # Nếu màu chữ của ô tiêu đề là màu xám mờ (màu của placeholder)
            if current_color == placeholder_color:
                logging.info("Phát hiện tiêu đề 'inactive' từ lô trước. Tự động xóa trước khi thêm tác vụ mới.")
                # <<< THAY ĐỔI Ở ĐÂY: Gọi hàm helper mới chỉ reset ô tiêu đề >>>
                self._reset_title_textbox_to_placeholder()
        except Exception as e:
            logging.warning(f"Lỗi khi kiểm tra và xóa tiêu đề tạm: {e}")
        
        content_to_add = self.content_textbox.get("1.0", "end-1c").strip()
        if not content_to_add:
            messagebox.showwarning("Nội dung trống", "Không có nội dung kịch bản để thêm vào hàng chờ.", parent=self)
            return

        try:
            chapter_input = self.start_chapter_var.get().strip()

            # <<< THAY ĐỔI 2 (ĐÃ SỬA LỖI): LẤY TIÊU ĐỀ DỰA TRÊN NỘI DUNG, KHÔNG DÙNG MÀU SẮC >>>
            manual_title_from_ui = "" # Mặc định là không có tiêu đề thủ công

            # Lấy nội dung hiện tại của ô tiêu đề
            raw_title = self.title_textbox.get("1.0", "end-1c").strip()

            # Chỉ coi là tiêu đề thủ công nếu nó có nội dung VÀ không phải là placeholder
            if raw_title and raw_title != self.MANUAL_TITLE_PLACEHOLDER:
                manual_title_from_ui = raw_title
                logging.info(f"Phát hiện tiêu đề thủ công hợp lệ: '{manual_title_from_ui}'")
            else:
                logging.info("Không có tiêu đề thủ công hợp lệ, sẽ để AI tự tạo.")
            # <<< KẾT THÚC THAY ĐỔI 2 >>>

            temp_base_name = manual_title_from_ui or content_to_add[:30]
            safe_name = create_safe_filename(temp_base_name)
            temp_filename = f"pasted_{safe_name}_{int(time.time())}.txt"
            temp_filepath = os.path.join(self.master_app.temp_folder, temp_filename)

            with open(temp_filepath, "w", encoding="utf-8") as f: f.write(content_to_add)

            naming_params = {
                'use_auto_naming': self.auto_naming_var.get(),
                'series_name': self.rename_base_name_var.get(),
                'chapter_num': chapter_input 
            }
            
            display_name = f"Chương '{chapter_input}' (Dán từ Textbox)" if chapter_input else "Kịch bản (Dán từ Textbox)"

            task = {
                'filepath': temp_filepath, 'is_temp': True, 'display_name': display_name,
                'naming_params': naming_params,
                'rename_info': {'use_rename': self.rename_var.get(), 'base_name': self.rename_base_name_var.get()},
                'manual_title': manual_title_from_ui
            }

            self.queue.append(task)
            self._update_queue_display()
            self._update_status_aie(f"Đã thêm '{task['display_name']}' vào hàng chờ.")
            
            self._clear_textbox_content(clear_chapter_field=False, clear_title_field=True)

        except Exception as e:
            logging.error(f"Lỗi khi thêm từ textbox vào hàng chờ: {e}", exc_info=True)
            messagebox.showerror("Lỗi", f"Không thể thêm kịch bản vào hàng chờ.\nLỗi: {e}", parent=self)


    def _open_output_folder(self):
        folder = self.output_folder_var.get()
        if folder and os.path.isdir(folder):
            # SỬA LỖI Ở ĐÂY: Gọi trực tiếp hàm toàn cục, không cần self.master_app
            open_file_with_default_app(folder) 
        else:
            messagebox.showwarning("Lỗi Đường dẫn", "Vui lòng chọn một thư mục hợp lệ.", parent=self)


    # Xóa và reset ô tiêu đề về trạng thái placeholder mặc định
    def _reset_title_textbox_to_placeholder(self):
        """(AI Editor) Xóa và reset ô tiêu đề về trạng thái placeholder mặc định."""
        if not (hasattr(self, 'title_textbox') and self.title_textbox.winfo_exists()):
            return
        try:
            self.title_textbox.configure(state="normal")
            self.title_textbox.delete("1.0", "end")
            # Gọi hàm focus_out để nó tự điền placeholder và đổi màu xám
            self._on_title_focus_out()
        except Exception as e:
            logging.error(f"Lỗi khi reset ô tiêu đề: {e}")

    # Bên trong lớp AIEditorTab
    def _clear_textbox_content(self, clear_chapter_field=False, clear_title_field=False):
        if self.is_running:
            return

        # Luôn bật state để có thể chỉnh sửa
        self.title_textbox.configure(state="normal")
        self.content_textbox.configure(state="normal")
        self.notes_textbox.configure(state="normal")

        # Xóa các ô theo yêu cầu
        if clear_chapter_field:
            self.start_chapter_var.set("")
            
        if clear_title_field:
            # <<< THAY ĐỔI Ở ĐÂY: Gọi hàm helper mới >>>
            self._reset_title_textbox_to_placeholder()

        self.content_textbox.delete("1.0", "end")
        self.notes_textbox.delete("1.0", "end")

    # Mở dialog, tạo task object cho mỗi file và thêm vào hàng chờ.
    def _add_files_to_queue(self):
        """(ĐÃ NÂNG CẤP v3) Thêm file với logic nhận diện số chương thông minh."""
        if self.is_running:
            return

        paths = filedialog.askopenfilenames(
            title="Chọn các file Kịch bản (.txt, .srt)",
            filetypes=[("File Kịch bản", "*.txt *.srt"), ("All files", "*.*")],
            parent=self
        )
        if not paths:
            return

        added_count = 0
        # Biến này sẽ theo dõi số chương tuần tự cho các file không có số
        last_sequential_chapter = self.queue[-1]['naming_params']['chapter_num'] if self.queue else 0

        for i, path in enumerate(paths):
            if os.path.exists(path) and not any(task['filepath'] == path for task in self.queue):
                current_chapter_num = None

                # --- LOGIC THÔNG MINH BẮT ĐẦU TỪ ĐÂY ---
                # 1. Ưu tiên tìm số trong tên file
                match = re.search(r'(\d+)', os.path.basename(path))
                if match:
                    try:
                        current_chapter_num = int(match.group(1))
                    except (ValueError, IndexError):
                        pass # Bỏ qua nếu không chuyển thành số được

                # 2. Nếu không có số trong tên file, dùng logic tuần tự
                if current_chapter_num is None:
                    # Nếu hàng chờ rỗng, bắt đầu từ số trong UI
                    if not self.queue and i == 0:
                         try:
                             # Lấy số từ UI cho file đầu tiên
                             last_sequential_chapter = int(self.start_chapter_var.get())
                         except ValueError:
                             last_sequential_chapter = 1 # Fallback
                    else:
                        # Nếu không phải file đầu, cộng 1 từ số tuần tự cuối cùng
                        last_sequential_chapter += 1
                    current_chapter_num = last_sequential_chapter
                # --- KẾT THÚC LOGIC THÔNG MINH ---

                naming_params = {
                    'use_auto_naming': self.auto_naming_var.get(),
                    'series_name': self.rename_base_name_var.get(),
                    'chapter_num': current_chapter_num
                }

                task = {
                    'filepath': path,
                    'is_temp': False,
                    'display_name': os.path.basename(path),
                    'naming_params': naming_params,
                    'rename_info': {
                        'use_rename': self.rename_var.get(),
                        'base_name': self.rename_base_name_var.get()
                    },
                    'manual_title': "" # <<<--- THÊM DÒNG NÀY: Báo hiệu không có tiêu đề thủ công
                }
                self.queue.append(task)
                # Cập nhật lại số tuần tự nếu file vừa thêm có số lớn hơn
                if current_chapter_num > last_sequential_chapter:
                    last_sequential_chapter = current_chapter_num
                added_count += 1
        
        if added_count > 0:
            self._update_queue_display()
            self._update_status_aie(f"Đã thêm {added_count} file vào hàng chờ biên tập.")

    def _remove_from_queue(self, idx):
        """(AI Editor) Xóa một file khỏi hàng chờ."""
        if self.is_running: return
        if 0 <= idx < len(self.queue):
            self.queue.pop(idx)
            self._update_queue_display()

    def _move_item_in_queue(self, idx, direction):
        """(AI Editor) Di chuyển một file trong hàng chờ."""
        if self.is_running: return
        new_idx = idx - 1 if direction == "up" else idx + 1
        if 0 <= new_idx < len(self.queue):
            self.queue[idx], self.queue[new_idx] = self.queue[new_idx], self.queue[idx]
            self._update_queue_display()

    def _select_output_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_folder_var.get(), parent=self)
        if folder: self.output_folder_var.set(folder)

    def _set_ui_state(self, is_running):
        self.is_running = is_running
        state = ctk.DISABLED if is_running else ctk.NORMAL
        self.start_button.configure(state=state)
        self.add_files_button.configure(state=state)
        self.rename_checkbox.configure(state=state)
        self.rename_entry.configure(state=state if self.rename_var.get() else ctk.DISABLED)
        for row_frame in self.queue_frame.winfo_children():
            for control_widget in row_frame.winfo_children():
                if isinstance(control_widget, ctk.CTkFrame):
                    for button in control_widget.winfo_children():
                        if isinstance(button, ctk.CTkButton):
                            button.configure(state=state)
        self.stop_button.configure(state=ctk.NORMAL if is_running else ctk.DISABLED)

    # ----------------------------------------------------
    # KHỐI LOGIC POPUP CỦA RIÊNG AI EDITOR TAB (ĐÃ NÂNG CẤP)
    # ----------------------------------------------------
    
    def _open_ai_popup_aie(self):
        """(AI Editor) Hiển thị cửa sổ popup AI nâng cao của riêng tab này."""

        can_use_gpt = HAS_OPENAI and self.master_app.openai_key_var.get()
        can_use_gemini = self.master_app.gemini_key_var.get()

        if not can_use_gpt and not can_use_gemini:
            messagebox.showerror("Thiếu API Key", "Vui lòng cấu hình OpenAI hoặc Gemini API Key.", parent=self)
            return

        popup = ctk.CTkToplevel(self)
        popup.title("✨ AI Xử Lý Kịch Bản (Biên tập Hàng loạt)")
        
        # --- BẮT ĐẦU KHỐI MÃ CĂN GIỮA ĐÚNG ---
        popup_width = 620
        popup_height = 480
        
        popup.geometry(f"{popup_width}x{popup_height}")
        popup.resizable(False, False)
        popup.transient(self.master_app) # Gắn popup vào cửa sổ chính
        popup.attributes("-topmost", True)
        popup.grab_set()

        def _center_popup_final():
            try:
                self.master_app.update_idletasks()
                master_x = self.master_app.winfo_x()
                master_y = self.master_app.winfo_y()
                master_w = self.master_app.winfo_width()
                master_h = self.master_app.winfo_height()
                center_x = master_x + (master_w // 2) - (popup_width // 2)
                center_y = master_y + (master_h // 2) - (popup_height // 2)
                popup.geometry(f"{popup_width}x{popup_height}+{int(center_x)}+{int(center_y)}")
            except Exception as e:
                logging.warning(f"Không thể căn giữa cửa sổ popup AI Editor: {e}")

        self.after(50, _center_popup_final)
        # --- KẾT THÚC KHỐI MÃ CĂN GIỮA ĐÚNG ---

        # --- Phần còn lại của hàm tạo widget (giữ nguyên không đổi) ---
        popup_main_frame = ctk.CTkFrame(popup, fg_color="transparent")
        popup_main_frame.pack(expand=True, fill="both", padx=15, pady=15)
        popup_main_frame.grid_columnconfigure(0, weight=1)
        popup_main_frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(popup_main_frame, text="Chọn Engine AI:", font=("Poppins", 13, "bold")).grid(row=0, column=0, padx=5, pady=(0, 5), sticky="w")
        
        available_engines = []
        if can_use_gpt: available_engines.append("🤖 GPT")
        if can_use_gemini: available_engines.append("💎 Gemini")
        
        popup.ai_engine_selection_var = ctk.StringVar(value=self.current_engine)

        engine_options_container = ctk.CTkFrame(popup_main_frame, fg_color="transparent")
        engine_options_container.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        engine_options_container.grid_columnconfigure(0, weight=1)

        gpt_options_frame = ctk.CTkFrame(engine_options_container, fg_color="transparent")
        gpt_model_row = ctk.CTkFrame(gpt_options_frame, fg_color="transparent")
        gpt_model_row.pack(fill="x", expand=True)
        gpt_model_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(gpt_model_row, text="Model GPT:", font=("Poppins", 13)).grid(row=0, column=0, padx=(0,5), pady=5, sticky="w")
        gpt_model_menu = ctk.CTkOptionMenu(gpt_model_row, variable=self.gpt_model_var, values=self.AVAILABLE_GPT_MODELS_FOR_SCRIPT_EDITING)
        gpt_model_menu.grid(row=0, column=1, padx=(0,5), pady=5, sticky="ew")        

        gemini_options_frame = ctk.CTkFrame(engine_options_container, fg_color="transparent")
        gemini_model_row = ctk.CTkFrame(gemini_options_frame, fg_color="transparent")
        gemini_model_row.pack(fill="x", expand=True)
        gemini_model_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(gemini_model_row, text="Model Gemini:", font=("Poppins", 13)).grid(row=0, column=0, padx=(0,5), pady=5, sticky="w")
        gemini_model_menu = ctk.CTkOptionMenu(gemini_model_row, variable=self.gemini_model_var, values=self.AVAILABLE_GEMINI_MODELS_FOR_SCRIPT_EDITING)
        gemini_model_menu.grid(row=0, column=1, padx=(0,5), pady=5, sticky="ew")

        prompt_label = ctk.CTkLabel(popup_main_frame, text="Nhập yêu cầu chung cho tất cả các file trong hàng chờ:", font=("Poppins", 13, "normal"), wraplength=580)
        prompt_label.grid(row=3, column=0, sticky="w", pady=(10, 2))
        prompt_textbox_popup_local = ctk.CTkTextbox(popup_main_frame, font=("Segoe UI", 13), wrap="word", height=200)
        prompt_textbox_popup_local.grid(row=4, column=0, sticky="nsew", pady=(0, 15))
        prompt_textbox_popup_local.focus()
        prompt_textbox_popup_local.bind("<Button-3>", textbox_right_click_menu)

        action_buttons_row_frame = ctk.CTkFrame(popup_main_frame, fg_color="transparent")
        action_buttons_row_frame.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        action_buttons_row_frame.grid_columnconfigure(0, weight=1)
        
        def _update_popup_for_engine(selected_engine_str):
            is_gpt = "GPT" in selected_engine_str
            gpt_options_frame.pack_forget()
            gemini_options_frame.pack_forget()
            if is_gpt:
                gpt_options_frame.pack(fill="x", expand=True)
                config_key = "last_used_gpt_prompt_ai_batch_editor"
            else:
                gemini_options_frame.pack(fill="x", expand=True)
                config_key = "last_used_gemini_prompt_ai_batch_editor"
            
            saved_prompt = self.master_app.cfg.get(config_key, self.DEFAULT_AI_EDITOR_PROMPT)
            prompt_textbox_popup_local.delete("1.0", "end")
            prompt_textbox_popup_local.insert("1.0", saved_prompt)
        
        ai_engine_selector = ctk.CTkSegmentedButton(
            popup_main_frame, variable=popup.ai_engine_selection_var, values=available_engines,
            command=_update_popup_for_engine, height=32, font=("Segoe UI", 13, "bold")
        )
        ai_engine_selector.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        def _save_settings_and_close():
            selected_engine = popup.ai_engine_selection_var.get()
            prompt_text = prompt_textbox_popup_local.get("1.0", "end-1c").strip()

            # Chấp nhận rỗng cho cả 2 chế độ (EN TTS / VN)
            # - EN TTS: dùng prompt EN mặc định
            # - VN (không tick): dùng prompt VN mặc định
            self.current_engine = selected_engine
            self.current_prompt = prompt_text  # có thể là ""

            if "GPT" in selected_engine:
                self.master_app.cfg["gpt_model_for_aie"] = self.gpt_model_var.get()
            else:
                self.master_app.cfg["gemini_model_for_aie"] = self.gemini_model_var.get()

            self.master_app.cfg["last_used_ai_engine_aie"] = selected_engine
            config_key = f"last_used_{'gemini' if 'Gemini' in selected_engine else 'gpt'}_prompt_ai_batch_editor"
            self.master_app.cfg[config_key] = prompt_text  # có thể là ""
            self.save_config()  # Gọi save_config() của tab thay vì master_app

            popup.destroy()
        
        cancel_btn_popup_local = ctk.CTkButton(action_buttons_row_frame, text="Hủy", width=100, command=popup.destroy)
        cancel_btn_popup_local.pack(side="right", padx=(10,0))
        # Sửa lại nút "Bắt đầu" thành "Lưu & Đóng"
        process_btn_popup_local = ctk.CTkButton(action_buttons_row_frame, text="Lưu Prompt & Đóng", command=_save_settings_and_close, fg_color="#1f6aa5")
        process_btn_popup_local.pack(side="right")
        
        popup.protocol("WM_DELETE_WINDOW", popup.destroy)
        _update_popup_for_engine(popup.ai_engine_selection_var.get())

    # --- HÀM LOGIC XỬ LÝ ---
    def _start_batch_editing_aie(self):
        """(AI Editor) Bắt đầu quy trình xử lý hàng loạt của riêng tab này."""

        # --- Kiểm tra Chuỗi Sản xuất (nếu bật) ---
        if self.enable_production_chain_var.get():
            chain_output_folder = self.production_chain_output_path_var.get()
            if not chain_output_folder or not os.path.isdir(chain_output_folder):
                messagebox.showerror(
                    "Thiếu Thư mục cho Chuỗi Sản xuất",
                    "Bạn đã kích hoạt Chuỗi Sản xuất AI, nhưng chưa chọn một thư mục hợp lệ để lưu kịch bản đã biên tập.\n\n"
                    "Vui lòng chọn thư mục và thử lại.",
                    parent=self
                )
                return

        # --- KHÔNG CHẶN PROMPT TRỐNG: dùng prompt mặc định theo chế độ ---
        if not (self.current_prompt or "").strip():
            if self.en_tts_mode_var.get():
                logging.info("[AIEditorTab] Prompt trống → EN TTS bật: dùng prompt EN mặc định.")
            else:
                logging.info("[AIEditorTab] Prompt trống → VN mode: dùng prompt VN mặc định.")

        # --- Kiểm tra hàng chờ ---
        if not self.queue:
            messagebox.showinfo("Hàng chờ trống", "Vui lòng thêm ít nhất một file kịch bản vào hàng chờ.", parent=self)
            return

        # --- Cờ tắt máy sau khi xong (theo app chính) ---
        if self.master_app.download_shutdown_var.get():
            self.master_app.shutdown_requested_by_task = True
            logging.info("[AIEditorTab] 'Hẹn giờ tắt máy' đang BẬT. Đã ghi nhận yêu cầu.")
        else:
            self.master_app.shutdown_requested_by_task = False
            logging.info("[AIEditorTab] 'Hẹn giờ tắt máy' đang TẮT.")

        # --- Lưu cài đặt trước khi chạy ---
        self.save_config()  # Gọi save_config() của tab

        # --- Khởi tạo lô ---
        self.batch_results = []
        logging.info(f"--- Bắt đầu Lô Biên tập AI (Tab Độc Lập) với {len(self.queue)} file ---")
        logging.info(
            f"    Engine: {self.current_engine}, Model: "
            f"{self.gpt_model_var.get() if 'GPT' in self.current_engine else self.gemini_model_var.get()}"
        )

        self.master_app.stop_event.clear()
        self.batch_counter = 0
        self._set_ui_state(is_running=True)
        self.start_time = time.time()
        self._update_time_realtime_aie()

        # --- Bắt đầu xử lý ---
        self._process_next_task_aie()

    def _stop_batch_editing_aie(self):
        logging.info("[AIEditorTab] Người dùng yêu cầu dừng quá trình biên tập hàng loạt.")
        self.master_app.stop_event.set()
        self._update_status_aie("🛑 Đang yêu cầu dừng, vui lòng chờ file hiện tại hoàn tất...")
        self.stop_button.configure(state=ctk.DISABLED) # Vô hiệu hóa nút dừng để tránh nhấn nhiều lần        

    def _process_next_task_aie(self):
        if self.master_app.stop_event.is_set():
            self._on_batch_finished_aie(stopped=True)
            return
        if not self.queue:
            self._on_batch_finished_aie(stopped=False)
            return
        
        # self.current_file giờ là một task object
        self.current_file = self.queue.pop(0) 
        self._update_queue_display()
        
        # Lấy đường dẫn file từ object
        current_filepath = self.current_file['filepath'] 
        
        self._update_status_aie(f"Biên tập: {os.path.basename(current_filepath)}...")
        try:
            with open(current_filepath, "r", encoding="utf-8-sig") as f:
                content = f.read()
            self._clear_textbox_content()
            self.content_textbox.insert("1.0", content)

            self._update_character_count()

            base_filename = os.path.splitext(os.path.basename(current_filepath))[0]
            if "GPT" in self.current_engine:
                self._trigger_gpt_aie(input_script=content, user_prompt=self.current_prompt, base_filename=base_filename)
            else:
                self._trigger_gemini_aie(input_script=content, user_prompt=self.current_prompt, base_filename=base_filename)
        except Exception as e:
            logging.error(f"Lỗi khi đọc file '{current_filepath}': {e}")
            messagebox.showerror("Lỗi Đọc File", f"Lỗi đọc file: {os.path.basename(current_filepath)}\n\nLỗi: {e}\n\nBỏ qua file này.", parent=self)
            self.after(50, self._process_next_task_aie)


#-------------------------

# Thu thập kết quả từ lô biên tập và xuất ra file master_metadata.json.
    def _export_batch_metadata_aie(self, batch_results, output_folder):
        """
        (ĐÃ NÂNG CẤP v4) Thu thập kết quả, lấy dữ liệu mẫu, và xuất ra file
        metadata. Sẽ đọc và hợp nhất nếu file đã tồn tại.
        """
        log_prefix = "[ExportAIMetadata_v4_Merge]"
        logging.info(f"{log_prefix} Bắt đầu xuất metadata (với logic hợp nhất).")

        if not batch_results:
            logging.warning(f"{log_prefix} Không có kết quả nào để xuất.")
            return None

        # Lấy dữ liệu mẫu từ metadata chính (logic này giữ nguyên)
        template_description, template_tags, template_thumbnail, template_playlist = "", "", "", ""
        try:
            master_cache = self.master_app.master_metadata_cache
            if master_cache and isinstance(master_cache, dict):
                first_key = next(iter(master_cache))
                template_data = master_cache[first_key]
                template_description = template_data.get("description", "")
                template_tags = template_data.get("tags", "")
                template_thumbnail = template_data.get("thumbnail", "")
                template_playlist = template_data.get("playlist", "")
                logging.info(f"{log_prefix} Đã lấy thành công dữ liệu mẫu từ key '{first_key}'.")
            else:
                logging.info(f"{log_prefix} Không tìm thấy dữ liệu mẫu trong cache.")
        except Exception as e_template:
            logging.warning(f"{log_prefix} Lỗi khi lấy dữ liệu mẫu: {e_template}.")

        # master_data chứa dữ liệu của lô hiện tại
        master_data = {}
        for content_path, title_path in batch_results:
            identifier = os.path.splitext(os.path.basename(content_path))[0]
            with open(title_path, 'r', encoding='utf-8-sig') as f_title:
                title = f_title.read().strip()
            
            master_data[identifier] = {
                "title": title, "description": template_description, "tags": template_tags,
                "thumbnail": template_thumbnail, "playlist": template_playlist
            }
        
        if not master_data:
            logging.warning(f"{log_prefix} Không có dữ liệu hợp lệ để tạo file metadata.")
            return None

        # Tạo tên file metadata động (logic này giữ nguyên)
        series_name = self.rename_base_name_var.get().strip()
        metadata_filename = f"{create_safe_filename(series_name, remove_accents=False)}_metadata.json" if series_name else "master_metadata.json"
        metadata_file_path = os.path.join(output_folder, metadata_filename)

        # <<< BƯỚC 2: KIỂM TRA, ĐỌC VÀ HỢP NHẤT DỮ LIỆU (LOGIC MỚI) >>>
        final_data_to_save = {}
        if os.path.exists(metadata_file_path):
            logging.info(f"{log_prefix} File metadata '{metadata_filename}' đã tồn tại. Đang đọc để hợp nhất.")
            try:
                with open(metadata_file_path, 'r', encoding='utf-8-sig') as f_existing:
                    existing_data = json.load(f_existing)
                    if not isinstance(existing_data, dict):
                        raise json.JSONDecodeError("File không chứa dữ liệu dictionary.", "", 0)
                    
                    # Hợp nhất dữ liệu mới vào dữ liệu cũ
                    existing_data.update(master_data)
                    final_data_to_save = existing_data
                    logging.info(f"{log_prefix} Hợp nhất thành công. Tổng số mục: {len(final_data_to_save)}")

            except json.JSONDecodeError as e:
                logging.error(f"{log_prefix} File metadata hiện tại bị lỗi: {e}. Hỏi người dùng để ghi đè.")
                overwrite = messagebox.askyesno(
                    "Lỗi File Metadata",
                    f"File metadata '{metadata_filename}' hiện tại có vẻ bị lỗi và không thể đọc.\n\n"
                    "Bạn có muốn ghi đè file này với dữ liệu của các file vừa biên tập không?\n\n"
                    "(Nếu chọn 'Không', file metadata sẽ không được lưu.)",
                    icon='warning',
                    parent=self
                )
                if overwrite:
                    final_data_to_save = master_data
                else:
                    logging.info(f"{log_prefix} Người dùng đã chọn không ghi đè file bị lỗi. Hủy lưu.")
                    return None
        else:
            # Nếu file chưa tồn tại, chỉ cần dùng dữ liệu mới
            final_data_to_save = master_data
        # <<< KẾT THÚC BƯỚC 2 >>>
            
        try:
            # <<< BƯỚC 3: LƯU FILE ĐÃ ĐƯỢC HỢP NHẤT >>>
            with open(metadata_file_path, 'w', encoding='utf-8') as f_json:
                json.dump(final_data_to_save, f_json, ensure_ascii=False, indent=2)
            
            logging.info(f"{log_prefix} Đã lưu thành công metadata vào: {metadata_file_path}")
            return metadata_file_path
            # <<< KẾT THÚC BƯỚC 3 >>>

        except Exception as e:
            logging.error(f"{log_prefix} Lỗi không mong muốn khi xuất metadata: {e}", exc_info=True)
            return None
    

# Xử lý sau khi lô biên tập xong và chuyển giao cho chuỗi AI chính nếu cần.
    def _on_batch_finished_aie(self, stopped=False):
        """(ĐÃ SỬA LỖI UI, XUẤT METADATA, CẬP NHẬT POPUP VÀ SỬA LỖI TẮT MÁY)"""
        logging.info(f"[AIEditorTab] Kết thúc lô biên tập. Bị dừng: {stopped}")
        self.current_file = None
        self.start_time = None
        
        is_handoff = False
        if not stopped and self.enable_production_chain_var.get():
            is_handoff = True
            logging.info("[AIEditorTab] Biên tập xong, chuỗi sản xuất được kích hoạt. Bắt đầu chuyển giao...")
            self._update_status_aie("✅ Biên tập xong! Bắt đầu chuỗi AI sản xuất...")
            results_to_pass = list(self.batch_results)
            self.master_app.after(500, self.master_app._handle_chain_handoff_from_editor, results_to_pass)

        # Dọn dẹp UI sẽ luôn được chạy
        self.master_app.is_ai_batch_processing = False
        self._set_ui_state(is_running=False)
        self._update_queue_display()
        
        if not is_handoff:
            self.master_app._check_completion_and_shutdown()

            if stopped:
                self._update_status_aie("🛑 Quá trình biên tập đã dừng.")
            else:
                self._update_status_aie("✅ Hoàn tất lô biên tập kịch bản!")
                self.after(4000, lambda: self._update_status_aie("✅ AI Biên Tập: Sẵn sàng biên tập Kịch Bản."))                
                
                if self.batch_results:
                    logging.info("[AIEditorTab] Lô biên tập hoàn thành (không chuyển giao). Bắt đầu xuất file metadata.")
                    
                    saved_metadata_path = self._export_batch_metadata_aie(
                        self.batch_results, 
                        self.output_folder_var.get()
                    )
                    
                    # <<< THAY ĐỔI 1: HIỂN THỊ TIÊU ĐỀ CUỐI CÙNG VỚI MÀU MỜ >>>
                    # Lấy tiêu đề của file cuối cùng trong lô vừa xử lý
                    last_title_path = self.batch_results[-1][1] if self.batch_results else None
                    if last_title_path and os.path.exists(last_title_path):
                        with open(last_title_path, "r", encoding="utf-8-sig") as f:
                            last_title_content = f.read().strip()
                        
                        # Hiển thị tiêu đề đó nhưng đặt màu thành màu placeholder
                        self.title_textbox.configure(state="normal")
                        self.title_textbox.delete("1.0", "end")
                        self.title_textbox.insert("1.0", last_title_content)
                        self.title_textbox.configure(text_color=self.PLACEHOLDER_COLOR)
                        logging.info(f"Đã hiển thị tiêu đề cuối cùng '{last_title_content}' với màu inactive.")
                    else:
                        # Nếu không lấy được tiêu đề cuối, reset về placeholder mặc định
                        self._clear_textbox_content(clear_chapter_field=False, clear_title_field=True)
                    # <<< KẾT THÚC THAY ĐỔI 1 >>>
                    
                    if saved_metadata_path:
                        metadata_filename = os.path.basename(saved_metadata_path)
                        popup_message = (
                            "Đã xử lý xong tất cả các file trong hàng chờ.\n\n"
                            f"Đã tự động lưu file metadata '{metadata_filename}' vào thư mục output:\n\n"
                            f"{self.output_folder_var.get()}"
                        )
                        messagebox.showinfo("Hoàn thành & Xuất Metadata", popup_message, parent=self)
                    else:
                         messagebox.showwarning(
                            "Lỗi Xuất Metadata",
                            "Quá trình biên tập đã hoàn thành, nhưng đã xảy ra lỗi khi lưu file metadata. Vui lòng kiểm tra log.",
                            parent=self
                        )

    def save_config(self):
        """Lưu cấu hình AI Editor vào master_app.cfg"""
        if not hasattr(self.master_app, 'cfg'):
            logging.error("master_app không có thuộc tính cfg")
            return
        
        # Lưu các cấu hình AI Editor
        self.master_app.cfg["ai_editor_output_folder"] = self.output_folder_var.get()
        self.master_app.cfg["ai_editor_rename_enabled"] = self.rename_var.get()
        self.master_app.cfg["ai_editor_rename_base_name"] = self.rename_base_name_var.get()
        self.master_app.cfg["ai_editor_auto_naming_enabled"] = self.auto_naming_var.get()
        self.master_app.cfg["ai_editor_series_name"] = self.series_name_var.get()
        self.master_app.cfg["ai_editor_start_chapter"] = self.start_chapter_var.get()
        self.master_app.cfg["ai_editor_enable_chain"] = self.enable_production_chain_var.get()
        self.master_app.cfg["ai_editor_chain_output_path"] = self.production_chain_output_path_var.get()
        self.master_app.cfg["ai_editor_en_tts_mode"] = self.en_tts_mode_var.get()
        self.master_app.cfg["ai_editor_auto_add_on_paste"] = self.auto_add_on_paste_var.get()
        self.master_app.cfg["last_used_ai_engine_aie"] = self.current_engine
        self.master_app.cfg["gpt_model_for_aie"] = self.gpt_model_var.get()
        self.master_app.cfg["gemini_model_for_aie"] = self.gemini_model_var.get()
        
        # Lưu prompt (có thể là prompt VN hoặc EN tùy theo engine đã chọn)
        if hasattr(self, 'current_engine') and hasattr(self, 'current_prompt'):
            config_key = f"last_used_{'gemini' if 'Gemini' in self.current_engine else 'gpt'}_prompt_ai_batch_editor"
            if self.current_prompt:
                self.master_app.cfg[config_key] = self.current_prompt
        
        logging.debug("[AIEditorTab.save_config] Đã lưu cấu hình AI Editor vào master_app.cfg")
            

    def _update_status_aie(self, text):
        """(ĐÃ NÂNG CẤP) Cập nhật trạng thái cho tab AI Biên Tập, tự động thêm icon."""
        if not hasattr(self, 'status_label_aie') or not self.status_label_aie or not self.status_label_aie.winfo_exists():
            return

        # --- KHỐI LOGIC THÊM ICON TỰ ĐỘNG ---
        # Kiểm tra xem text đã có icon chưa để tránh thêm nhiều lần
        has_icon = any(text.startswith(icon) for icon in ["✅", "ℹ️", "✍️", "🛑", "🚀", "❌", "⚠️"])
        
        icon_text = text
        if not has_icon:
            text_lower = text.lower()
            if "thêm" in text_lower or "hoàn tất" in text_lower:
                icon_text = f"✅ {text}"
            elif "dán" in text_lower:
                icon_text = f"ℹ️ {text}"
            elif "biên tập:" in text_lower:
                icon_text = f"✍️ {text}"
            elif "dừng" in text_lower:
                icon_text = f"🛑 {text}"
            elif "bắt đầu chuỗi" in text_lower:
                icon_text = f"🚀 {text}"
            # Bạn có thể thêm các trường hợp khác ở đây, ví dụ cho lỗi
            elif "lỗi" in text_lower:
                icon_text = f"❌ {text}"

        final_text_to_display = icon_text
        if self.is_running and self.start_time:
            elapsed = time.time() - self.start_time
            t_str = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"
            base_text = icon_text if icon_text else self._last_status_text
            self._last_status_text = base_text
            final_text_to_display = f"{base_text} | ⏱ {t_str}"
            
        self.status_label_aie.configure(text=final_text_to_display)

    def _update_time_realtime_aie(self):
        if self.is_running and self.start_time:
            self._update_status_aie(self._last_status_text)
            self.after(1000, self._update_time_realtime_aie)

    def _trigger_gemini_aie(self, input_script, user_prompt, base_filename):
        selected_model = self.gemini_model_var.get()
        thread = threading.Thread(
            target=self._execute_gemini_thread_aie,
            args=(input_script, user_prompt, selected_model, base_filename),
            daemon=True, name=f"AIEditor_GeminiThread"
        )
        thread.start()


# Thực thi gọi Gemini API Biên Tập
    def _execute_gemini_thread_aie(self, script_content, user_instruction, selected_model, base_filename):
        """(NÂNG CẤP) Thực thi gọi Gemini API với cơ chế thử lại cho các lỗi mạng/server."""
        log_prefix = f"[ExecuteGemini_AIE_v2_Retry]"
        processed_script = None
        error_message = None
        
        max_retries = 2 # Thử lại tối đa 2 lần (tổng cộng 3 lần gọi)
        retry_delay_seconds = 15 # Chờ 15 giây trước khi thử lại lần đầu

        with keep_awake(f"AI Editor (Gemini) processing: {base_filename}"):        

            for attempt in range(max_retries + 1):
                try:
                    if self.master_app.stop_event.is_set():
                        raise InterruptedError("Dừng bởi người dùng.")

                    import google.generativeai as genai
                    from google.api_core import exceptions as google_api_exceptions
                    from google.genai.types import HarmCategory, HarmBlockThreshold

                    genai.configure(api_key=self.master_app.gemini_key_var.get())
                    model = genai.GenerativeModel(selected_model)

                    extra = (self.current_prompt or "").strip()
                    script = str(script_content)

                    if self.en_tts_mode_var.get():
                        # ===== EN TTS: dùng prompt EN mặc định + optional extra =====
                        base_prompt = AIEditorTab.DEFAULT_AI_EDITOR_PROMPT_EN_TTS_V2
                        if extra:
                            final_prompt = extra + "\n\n" + base_prompt + "\n" + script
                        else:
                            final_prompt = base_prompt + "\n" + script
                    else:
                        # ===== VN mode: dùng prompt VN mặc định + optional extra =====
                        base_prompt = AIEditorTab.DEFAULT_AI_EDITOR_PROMPT
                        if extra:
                            final_prompt = extra + "\n\n" + base_prompt + "\n" + script
                        else:
                            final_prompt = base_prompt + "\n" + script

                    logging.info(f"{log_prefix} (Thử lần {attempt + 1}/{max_retries + 1}) Đang gửi yêu cầu đến Gemini...")

                    # <<< BẮT ĐẦU THAY ĐỔI: THÊM CÀI ĐẶT AN TOÀN VÀ TIMEOUT >>>
                    safety_settings = {
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    }

                    response = model.generate_content(
                        final_prompt,
                        safety_settings=safety_settings,
                        request_options={"timeout": 300} # 300 giây = 5 phút
                    )
                    # <<< KẾT THÚC THAY ĐỔI >>>
                    
                    if not response.candidates:
                        block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Không rõ"
                        raise RuntimeError(f"Yêu cầu bị chặn bởi bộ lọc an toàn của Gemini (Lý do: {block_reason}).")

                    processed_script = response.text
                    self.master_app._track_api_call(service_name="gemini_calls", units=1)
                    error_message = None # Reset lỗi nếu thành công
                    break # Thoát khỏi vòng lặp retry nếu thành công

                except (google_api_exceptions.ResourceExhausted, google_api_exceptions.ServiceUnavailable,
                        google_api_exceptions.DeadlineExceeded, google_api_exceptions.InternalServerError) as e_retryable:
                    logging.warning(f"{log_prefix} (Thử lần {attempt + 1}) Gặp lỗi có thể thử lại ({type(e_retryable).__name__}). Chờ {retry_delay_seconds}s...")
                    error_message = f"Lỗi tạm thời từ Google API: {type(e_retryable).__name__}."
                    if attempt < max_retries:
                        time.sleep(retry_delay_seconds)
                        retry_delay_seconds *= 2 # Tăng thời gian chờ cho lần sau
                        continue
                    else:
                        logging.error(f"{log_prefix} Vẫn gặp lỗi sau {max_retries + 1} lần thử. Bỏ qua.")
                        break

                except Exception as e:
                    error_message = f"Lỗi không thể thử lại khi gọi API Gemini: {e}"
                    logging.error(f"{log_prefix} {error_message}", exc_info=False)
                    break
            
            self.master_app.after(0, self._handle_ai_result_aie, processed_script, error_message, base_filename)


    def _trigger_gpt_aie(self, input_script, user_prompt, base_filename):
        selected_model = self.gpt_model_var.get()
        thread = threading.Thread(
            target=self._execute_gpt_thread_aie,
            args=(input_script, user_prompt, selected_model, base_filename),
            daemon=True, name=f"AIEditor_GPTThread"
        )
        thread.start()


    def _execute_gpt_thread_aie(self, script_content, user_instruction, selected_model, base_filename):
        """(NÂNG CẤP) Thực thi gọi GPT API với cơ chế thử lại và xử lý lỗi chi tiết."""
        log_prefix = f"[ExecuteGPT_AIE_v2_Retry]"
        processed_script = None
        error_message = None
        
        max_retries = 2
        retry_delay_seconds = 15

        with keep_awake(f"AI Editor (GPT) processing: {base_filename}"):        
            for attempt in range(max_retries + 1):
                try:
                    if self.master_app.stop_event.is_set():
                        raise InterruptedError("Dừng bởi người dùng.")

                    # IMPORT CÁC LỚP LỖI CỤ THỂ 
                    from openai import OpenAI, RateLimitError, AuthenticationError, APIConnectionError, APIStatusError, APITimeoutError

                    client = OpenAI(api_key=self.master_app.openai_key_var.get(), timeout=300.0) # Tăng timeout lên 5 phút

                    extra = (self.current_prompt or "").strip()
                    script = str(script_content)

                    if self.en_tts_mode_var.get():
                        # ===== EN TTS: dùng prompt EN mặc định + optional extra =====
                        base_prompt = AIEditorTab.DEFAULT_AI_EDITOR_PROMPT_EN_TTS_V2
                        if extra:
                            final_prompt = extra + "\n\n" + base_prompt + "\n" + script
                        else:
                            final_prompt = base_prompt + "\n" + script
                    else:
                        # ===== VN mode: dùng prompt VN mặc định + optional extra =====
                        base_prompt = AIEditorTab.DEFAULT_AI_EDITOR_PROMPT
                        if extra:
                            final_prompt = extra + "\n\n" + base_prompt + "\n" + script
                        else:
                            final_prompt = base_prompt + "\n" + script
                    
                    logging.info(f"{log_prefix} (Thử lần {attempt + 1}/{max_retries + 1}) Đang gửi yêu cầu đến GPT...")
                    response = client.chat.completions.create(
                        model=selected_model,
                        messages=[{"role": "user", "content": final_prompt}],
                        temperature=0.5
                    )
                    processed_script = response.choices[0].message.content.strip()
                    self.master_app._track_api_call(service_name="openai_calls", units=1)
                    error_message = None # Reset lỗi nếu thành công
                    break # Thoát vòng lặp

                except (RateLimitError, APIConnectionError, APITimeoutError) as e_retryable:
                    logging.warning(f"{log_prefix} (Thử lần {attempt + 1}) Gặp lỗi có thể thử lại ({type(e_retryable).__name__}). Chờ {retry_delay_seconds}s...")
                    error_message = f"Lỗi tạm thời từ OpenAI API: {type(e_retryable).__name__}."
                    if attempt < max_retries:
                        time.sleep(retry_delay_seconds)
                        retry_delay_seconds *= 2
                        continue
                    else:
                        logging.error(f"{log_prefix} Vẫn gặp lỗi sau {max_retries + 1} lần thử. Bỏ qua.")
                        break
                
                except APIStatusError as e_status:
                    logging.warning(f"{log_prefix} (Thử lần {attempt + 1}) Gặp lỗi API Status ({e_status.status_code}).")
                    error_message = f"Lỗi API Status từ OpenAI: {e_status.message}"
                    # Chỉ thử lại với các lỗi server (5xx)
                    if e_status.status_code >= 500 and attempt < max_retries:
                        time.sleep(retry_delay_seconds)
                        retry_delay_seconds *= 2
                        continue
                    else: # Lỗi client (4xx) hoặc hết số lần thử
                        logging.error(f"{log_prefix} Lỗi không thể thử lại hoặc đã hết lần thử. Lỗi: {e_status.message}")
                        break

                except Exception as e:
                    error_message = f"Lỗi không thể thử lại khi gọi API GPT: {e}"
                    logging.error(f"{log_prefix} {error_message}", exc_info=False)
                    break
            
            self.master_app.after(0, self._handle_ai_result_aie, processed_script, error_message, base_filename)


    # Xử lý kết quả từ AI, xóa và cập nhật UI một cách tường minh để tránh cộng dồn
    def _handle_ai_result_aie(self, processed_script, error_message, base_filename):
        """
        (PHIÊN BẢN HOÀN CHỈNH)
        Xử lý kết quả AI, ưu tiên tiêu đề thủ công đã lưu trong tác vụ,
        hiển thị popup lỗi không chặn và luôn tiếp tục xử lý file tiếp theo.
        """
        log_prefix = f"[HandleAIResult_AIE_v6_FinalManualTitle]"
        
        # --- BƯỚC 1: XỬ LÝ LỖI ---
        if error_message or not processed_script:
            error_to_show = error_message or "AI không trả về kết quả."
            current_filepath = self.current_file['filepath'] if self.current_file else "Không rõ"
            logging.error(f"{log_prefix} Lỗi xử lý file '{current_filepath}': {error_to_show}")
            
            batch_error_msg = (
                f"Lỗi khi xử lý file '{os.path.basename(current_filepath)}':\n\n"
                f"{error_to_show}\n\n"
                "Ứng dụng sẽ tự động bỏ qua file này và tiếp tục với các file còn lại."
            )
            
            self.master_app._show_non_blocking_error_popup("Lỗi Biên tập AI (Hàng loạt)", batch_error_msg)
            self.after(100, self._process_next_task_aie)
            return

        # --- BƯỚC 2: XỬ LÝ KHI THÀNH CÔNG ---
        parsed_parts = self.master_app._parse_ai_response(processed_script)

        # <<<--- LOGIC ƯU TIÊN TIÊU ĐỀ THỦ CÔNG --->>>
        # 1. Lấy tiêu đề thủ công đã được lưu trong task object
        manual_title_from_task = self.current_file.get('manual_title', '').strip()
        
        # 2. Quyết định tiêu đề cuối cùng
        if manual_title_from_task:
            # Nếu có, ưu tiên tiêu đề thủ công
            final_title_to_use = manual_title_from_task
            parsed_parts["title"] = final_title_to_use
            logging.info(f"{log_prefix} Ưu tiên sử dụng tiêu đề thủ công từ hàng chờ: '{final_title_to_use}'")
        else:
            # Nếu không, dùng tiêu đề của AI
            final_title_to_use = parsed_parts["title"]
            logging.info(f"{log_prefix} Sử dụng tiêu đề do AI tạo: '{final_title_to_use}'")
        # <<<--- KẾT THÚC LOGIC ƯU TIÊN --->>>

        # Bật và điền nội dung vào các ô textbox
        self.title_textbox.configure(state="normal")
        self.content_textbox.configure(state="normal")
        self.notes_textbox.configure(state="normal")
        
        self.title_textbox.delete("1.0", "end"); self.title_textbox.insert("1.0", final_title_to_use)
        self.content_textbox.delete("1.0", "end"); self.content_textbox.insert("1.0", parsed_parts["content"])
        self.notes_textbox.delete("1.0", "end"); self.notes_textbox.insert("1.0", parsed_parts["notes"])

        # --- Các bước lưu file và xử lý tiếp theo ---
        self.batch_counter += 1
        self.current_file['naming_params']['ai_title'] = parsed_parts.get("title", "")
        
        saved_content_path, saved_title_path = self._save_ai_results_aie(
            task=self.current_file,
            parsed_data=parsed_parts,
            base_filename=base_filename,
            output_folder=self.output_folder_var.get()
        )
        
        if saved_content_path and saved_title_path:
            self.batch_results.append((saved_content_path, saved_title_path))
        
        # Lên lịch xử lý file tiếp theo
        self.after(50, self._process_next_task_aie)
    

    # Lọc và làm sạch nội dung văn bản để an toàn cho việc đọc TTS
    def _sanitize_tts_content(self, text_content):
        """
        (v3) Lọc và làm sạch nội dung, nhưng giữ lại các dấu xuống dòng đơn và đôi
        để giọng đọc TTS có thể ngắt nghỉ tự nhiên.
        """
        if not text_content:
            return ""

        # 1. Loại bỏ các ký tự Markdown phổ biến (không đổi)
        cleaned_text = re.sub(r'[\[\]\*_#{}<>]+', '', text_content)

        # 2. Loại bỏ các dấu gạch chéo ngược và xuôi (không đổi)
        cleaned_text = re.sub(r'[\\/]+', ' ', cleaned_text)

        # 3. Thay thế nhiều dấu cách hoặc tab bằng một dấu cách duy nhất.
        #    Lưu ý: Bước này không ảnh hưởng đến dấu xuống dòng.
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)

        # 4. Thay thế ba hoặc nhiều dấu xuống dòng liên tiếp bằng hai dấu xuống dòng.
        #    Việc này giữ lại các đoạn văn mà không tạo ra khoảng trống quá lớn.
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

        # 5. Xóa các khoảng trắng hoặc xuống dòng ở đầu và cuối chuỗi.
        cleaned_text = cleaned_text.strip()

        return cleaned_text


    # Lưu 3 phần dữ liệu, áp dụng logic đặt tên tự động nếu được bật.
    def _save_ai_results_aie(self, task, parsed_data, base_filename, output_folder):
        """
        (PHIÊN BẢN 14.3 - Giữ prefix với manual title, KHÔNG dính 'pasted_*', khử 'x2 Chương')
        Logic:
          - Nếu auto naming: '<Series> - <Chương N> | <Manual/AI title (đã khử tiền tố)>'
            * Nếu AI/manual title trống hoặc là 'tên rác' → chỉ dùng '<Series> - <Chương N>'
          - Nếu không auto naming: dùng Manual nếu có, ngược lại dùng AI title; cuối cùng mới fallback.
          - Content filename base:
              * Auto naming: '<Series> - <Chương N>'
              * Không auto naming: '<final_title_to_save>'
          - Thêm hậu tố _<9 ký tự từ tiêu đề thủ công> vào các file .txt
        """
        log_prefix = "[SaveAIResults_AIE_v14.3_CombinedNaming]"
        try:
            # --- 1) Input ---
            rename_info = task.get('rename_info', {}) or {}
            naming_params = task.get('naming_params', {}) or {}
            manual_title_from_task = (task.get('manual_title', '') or '').strip()

            # KHÔNG fallback về base_filename ở đây: để trống nếu parser không có title
            ai_title_raw = (parsed_data.get("title", "") or "").strip()

            # --- 2) Hậu tố từ tiêu đề thủ công ---
            title_suffix = ""
            if manual_title_from_task:
                safe_title_part = create_safe_filename(manual_title_from_task, remove_accents=False)
                title_suffix = f"_{safe_title_part[:9]}"
                logging.info(f"{log_prefix} Hậu tố từ tiêu đề thủ công: '{title_suffix}'")

            # --- 3) Cờ rename/auto naming ---
            use_rename = bool(rename_info.get('use_rename', False))
            use_auto_naming = bool(naming_params.get('use_auto_naming', False))

            # --- 4) Tạo prefix '<Series> - <Chương N>' ---
            series_name = (rename_info.get('base_name', "") or "").strip()
            chapter_info = str(naming_params.get('chapter_num', '') or '').strip()
            display_chapter_part = f"Chương {chapter_info}" if chapter_info and chapter_info.isnumeric() else (chapter_info or "")
            prefix_parts = [p for p in [series_name, display_chapter_part] if p]
            file_prefix = " - ".join(prefix_parts)  # có thể rỗng

            # --- 5) Khử tiền tố trong Manual & AI title để tránh x2 ---
            manual_title_core = strip_series_chapter_prefix(manual_title_from_task, series_name) if manual_title_from_task else ""
            ai_title_core = strip_series_chapter_prefix(ai_title_raw, series_name)

            # Loại các "tên rác" thường gặp (pasted_, copy_, untitled, new document...)
            if ai_title_core and re.match(r'(?i)^(pasted_|copy_|untitled|new[_\s-]*document)\b', ai_title_core):
                ai_title_core = ""

            # --- 6) Quyết định final_title_to_save (tiêu đề trong file title.txt) ---
            if use_rename and use_auto_naming and file_prefix:
                # GIỮ PREFIX kể cả khi có manual title
                if manual_title_core:
                    final_title_to_save = f"{file_prefix} | {manual_title_core}"
                else:
                    final_title_to_save = f"{file_prefix} | {ai_title_core}" if ai_title_core else file_prefix
            else:
                # Không auto naming → ưu tiên manual, sau đó AI title
                final_title_to_save = manual_title_from_task or ai_title_raw or ""

            # --- 7) Fallback cứng để không rỗng ---
            if not final_title_to_save.strip():
                if file_prefix:
                    final_title_to_save = file_prefix
                elif series_name:
                    final_title_to_save = series_name
                elif base_filename:
                    final_title_to_save = base_filename
                else:
                    final_title_to_save = "Chưa có tiêu đề"

            # --- 8) Xác định content_filename_base ---
            if use_rename and use_auto_naming and file_prefix:
                # Content file đặt theo '<Series> - <Chương N>'
                content_filename_base = create_safe_filename(file_prefix, remove_accents=False)
            else:
                content_filename_base = create_safe_filename(final_title_to_save, remove_accents=False, max_length=80)

            # --- 9) Tên thư mục hiển thị ---
            final_folder_name = create_safe_filename(final_title_to_save, remove_accents=False, max_length=80)

            # --- 10) Tên file (ghép hậu tố nếu có) ---
            content_filename = f"{content_filename_base}{title_suffix}.txt"
            title_filename   = f"title_{content_filename_base}{title_suffix}.txt"
            notes_filename   = f"notes_{content_filename_base}{title_suffix}.txt"

            # --- 11) Tạo thư mục & đường dẫn ---
            unique_result_folder = os.path.join(output_folder, final_folder_name)
            os.makedirs(unique_result_folder, exist_ok=True)

            path_title   = os.path.join(unique_result_folder, title_filename)
            path_content = os.path.join(unique_result_folder, content_filename)
            path_notes   = os.path.join(unique_result_folder, notes_filename)

            # --- 12) Ghi file ---
            with open(path_title, "w", encoding="utf-8-sig") as f:
                f.write(final_title_to_save)

            original_content = parsed_data.get("content", "") or ""
            sanitized_content = self._sanitize_tts_content(original_content)
            with open(path_content, "w", encoding="utf-8-sig") as f:
                f.write(sanitized_content)

            with open(path_notes, "w", encoding="utf-8-sig") as f:
                f.write((parsed_data.get("notes", "") or ""))

            logging.info(
                f"{log_prefix} Lưu OK. Folder: '{final_folder_name}', "
                f"content: '{content_filename}', title: '{title_filename}', notes: '{notes_filename}'"
            )

            # --- 13) Copy sang chuỗi sản xuất (nếu bật) ---
            if self.enable_production_chain_var.get():
                chain_output_folder = self.production_chain_output_path_var.get()
                if chain_output_folder and os.path.isdir(chain_output_folder):
                    try:
                        dest_content_path = os.path.join(chain_output_folder, os.path.basename(path_content))
                        shutil.copy2(path_content, dest_content_path)
                        logging.info(f"{log_prefix} Đã copy CHỈ content → '{chain_output_folder}'")
                    except Exception as e_copy:
                        logging.error(f"{log_prefix} Lỗi copy content → chuỗi sản xuất: {e_copy}", exc_info=True)
                else:
                    logging.warning(f"{log_prefix} Chuỗi sản xuất bật nhưng output '{chain_output_folder}' không hợp lệ → bỏ qua.")

            return path_content, path_title

        except Exception as e:
            logging.error(f"{log_prefix} Lỗi khi lưu file kết quả: {e}", exc_info=True)
            return None, None


# 3 Hàm cho qui trình từ động hàng loạt 
    def _toggle_production_chain_widgets(self):
        """Hiện hoặc ẩn các widget chọn đường dẫn cho chuỗi sản xuất."""
        is_enabled = self.enable_production_chain_var.get()
        if is_enabled:
            # Hiện frame chứa các widget chọn đường dẫn
            if not self.chain_path_frame.winfo_ismapped():
                self.chain_path_frame.pack(fill="x", padx=5, pady=(0, 10), after=self.chain_enabled_checkbox)
                # Cập nhật hiển thị label lần đầu
                self._update_chain_path_label()
        else:
            # Ẩn frame đi
            if self.chain_path_frame.winfo_ismapped():
                self.chain_path_frame.pack_forget()

    def _select_chain_output_folder(self):
        """Mở dialog để chọn thư mục output cho chuỗi sản xuất."""
        initial_dir = self.production_chain_output_path_var.get() or self.output_folder_var.get() or get_default_downloads_folder()
        folder = filedialog.askdirectory(
            title="Chọn Thư mục LƯU Kịch bản đã sửa (cho Chuỗi AI)",
            initialdir=initial_dir,
            parent=self
        )
        if folder:
            self.production_chain_output_path_var.set(folder)
            self._update_chain_path_label()

    def _update_chain_path_label(self):
        """Cập nhật label hiển thị đường dẫn thư mục chuỗi sản xuất."""
        path = self.production_chain_output_path_var.get()
        if path and os.path.isdir(path):
            self.chain_path_label.configure(text=path, text_color="gray")
        elif path:
            self.chain_path_label.configure(text=f"Lỗi: '{path}' không hợp lệ!", text_color="red")
        else:
            self.chain_path_label.configure(text="(Chưa chọn)", text_color="gray")


