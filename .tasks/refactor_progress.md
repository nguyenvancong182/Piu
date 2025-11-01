# Refactor Progress - Piu

**Cập nhật lần cuối:** 2025-11-01  
**Focus:** Refactor 5 Tab Phases

---

## 📊 Tổng quan

### Kế hoạch hiện tại: Refactor 5 Tab Phases
Mục tiêu: Di chuyển logic của từng Tab từ `Piu.py` sang các Tab class riêng biệt.

### Tiến độ
- ✅ **Phase 1: Download Tab** - HOÀN THÀNH 100% (2025-10-31)
- ✅ **Phase 2: Subtitle Tab** - HOÀN THÀNH 100% (2025-11-01)
- ⏳ **Phase 3: Dubbing Tab** - Chưa bắt đầu (Trung bình - ưu tiên sau)
- ✅ **Phase 4: YouTube Upload & AI Editor Tabs** - HOÀN THÀNH 100% (2025-01-31)
- ⏳ **Phase 5: Dọn dẹp Piu.py** - 40% (đã xóa hàm Google Sheet cũ, đã sửa save_config)

**Tiến độ tổng thể:** 3/5 phases = 60%

### 💡 Đề xuất thứ tự thực hiện (Đã điều chỉnh)
**Lý do:** Phase 4 dễ hơn và nhanh hơn (2-3h/tab), giúp tăng momentum trước khi làm Phase 2/3 phức tạp.
1. ✅ **Phase 1** (Hoàn thành)
2. 🎯 **Phase 4** (Đề xuất làm tiếp theo - Dễ, nhanh, ít rủi ro)
3. **Phase 2** (Sau Phase 4 - Phức tạp nhất, cần tập trung)
4. **Phase 3** (Sau Phase 2 - Trung bình)
5. **Phase 5** (Cuối cùng - Dọn dẹp)

---

## 🎉 PHASE 1: REFACTOR DOWNLOAD TAB - HOÀN THÀNH ✅

**Ngày hoàn thành:** 2025-10-31

### ✅ Đã hoàn thành
- ✅ **Di chuyển tất cả biến download** từ `Piu.py` → `DownloadTab` (15+ biến)
- ✅ **Di chuyển tất cả hàm download** từ `Piu.py` → `DownloadTab` (12+ hàm, ~2,400 dòng)
- ✅ **Sửa tất cả tham chiếu** trong `DownloadTab` (`self.master_app.xxx`)
- ✅ **Sửa UI commands** để gọi hàm trong `DownloadTab`
- ✅ **Tạo `save_config()`** trong `DownloadTab` để lưu cấu hình
- ✅ **Sửa hàm liên-tab** (`start_download_and_sub`) để tham chiếu đúng
- ✅ **Xóa code cũ** trong `Piu.py` (~317 dòng hàm Google Sheet)
- ✅ **Tạo wrapper functions** trong `Piu.py` để backward compatibility

### 📊 Kết quả
- **Piu.py:** 29,416 dòng → 28,691 dòng (giảm ~725 dòng)
- **download_tab.py:** ~855 dòng → 2,395 dòng (tăng ~1,540 dòng)
- **Net effect:** Logic được tổ chức tốt hơn, dễ maintain hơn
- ✅ **Download hoạt động bình thường** (đã test)

### 📋 Chi tiết
Xem file chi tiết: [refactor_download_tab_summary.md](./refactor_download_tab_summary.md)

---

## 🎉 PHASE 2: REFACTOR SUBTITLE TAB - HOÀN THÀNH ✅

**Ngày hoàn thành:** 2025-11-01  
**Status:** ✅ Hoàn thành 100% + Test thành công

### ✅ Đã hoàn thành

#### Bước 2.1: Di chuyển BIẾN (State) ✅
- ✅ **Di chuyển 60+ biến state** từ `Piu.py` → `SubtitleTab`:
  - Model & Queue: `whisper_model`, `file_queue`, `current_file`, `is_subbing`, `is_gpt_processing_script`, `is_gemini_processing`
  - Language & Options: `source_lang_var`, `merge_sub_var`, `bilingual_var`, `target_lang_var`, `enable_split_var`, `max_chars_var`, `max_lines_var`
  - Pacing (Advanced): `sub_pacing_pause_medium_ms_var`, `sub_pacing_pause_period_ms_var`, `sub_pacing_pause_question_ms_var`, `sub_pacing_long_sentence_threshold_var`, `sub_pacing_fast_cps_multiplier_var`
  - Style: `sub_style_font_name_var`, `sub_style_font_size_var`, `sub_style_font_bold_var`, `sub_style_text_color_rgb_str_var`, `sub_style_text_opacity_percent_var`, `sub_style_background_mode_var`, `sub_style_bg_color_rgb_str_var`, `sub_style_bg_box_actual_opacity_percent_var`, `sub_style_outline_enabled_var`, `sub_style_outline_size_var`, `sub_style_outline_color_rgb_str_var`, `sub_style_outline_opacity_percent_var`, `sub_style_marginv_var`
  - FFmpeg: `ffmpeg_encoder_var`, `ffmpeg_preset_var`, `ffmpeg_crf_var`
  - Block Merging: `enable_block_merging_var`, `merge_max_time_gap_var`, `merge_curr_max_len_normal_var`
  - Pause for Edit: `pause_for_edit_var`
  - Manual Merge: `manual_merge_mode_var`
  - Others: `auto_format_plain_text_to_srt_var`, `auto_add_manual_sub_task_var`, `save_in_media_folder_var`, `optimize_whisper_tts_voice_var`
  - Output & Model: `output_path_var`, `model_var`, `format_var`
  - GPT/Gemini Undo & Rewrite: `gemini_undo_buffer`, `last_gemini_parameters_used`, `gpt_undo_buffer`, `last_gpt_parameters_used`
  - Chain Processing: `files_for_chained_dubbing`
- ✅ **Sửa tất cả `self.cfg.get()` → `self.master_app.cfg.get()`**

#### Bước 2.2-2.6: Di chuyển HÀM (Logic) ✅
- ✅ **Phase 2.2: Di chuyển 7 hàm Whisper** (~291 dòng):
  - `run_whisper_engine()`, `_on_toggle_optimize_whisper_tts_voice()`, `_determine_target_device()`, `load_whisper_model_if_needed()`, `_load_whisper_model_thread()`, `_update_loaded_model()`, `_reset_model_loading_ui()`
- ✅ **Phase 2.3-2.6: Di chuyển 24 hàm logic** (~1,880 dòng):
  - **GPT/Gemini (14 hàm):** `_trigger_gemini_script_processing_with_chain()`, `_execute_gemini_script_editing_thread_for_chain()`, `_handle_gemini_script_editing_result_for_chain()`, `_execute_gemini_scene_division_thread()`, `_handle_gemini_scene_division_result()`, `_trigger_gemini_script_processing()`, `_execute_gemini_script_editing_thread()`, `_handle_gemini_script_editing_result()`, `_trigger_gpt_script_processing_from_popup()`, `_execute_gpt_script_editing_thread()`, `_execute_gpt_scene_division_thread()`, `_execute_gpt_single_summary_prompt_thread()`, `_handle_gpt_scene_division_result()`, `_handle_gpt_script_editing_result()`
  - **Translation (3 hàm):** `translate_subtitle_file()`, `translate_google_cloud()`, `translate_openai()`
  - **Merge/Burn (2 hàm):** `burn_sub_to_video()`, `merge_sub_as_soft_sub()`
  - **Edit & Manual Merge (5 hàm):** `_on_toggle_manual_merge_mode()`, `load_old_sub_file()`, `save_edited_sub()`, `enable_sub_editing()`, `_execute_manual_merge_threaded()`

#### Bước 2.7: Sửa lỗi Tham chiếu ✅
- ✅ **Thêm imports:** `re`, `json`, `uuid`, `datetime`, `sys`, `subprocess`, `Path`, `pysubs2`, helper functions
- ✅ **Sửa tham chiếu state:** `self.ai_service` → `self.master_app.ai_service`, `self.stop_event` → `self.master_app.stop_event`, `self._track_api_call` → `self.master_app._track_api_call`, `self.after` → `self.master_app.after`
- ✅ **Sửa tham chiếu UI:** `self.start_time`, `self.cfg`, `self.gemini_key_var`, `self.openai_key_var` → `self.master_app.xxx`
- ✅ **0 linter errors**

#### Bước 2.8: Di chuyển Logic Lưu Config ✅
- ✅ **Tạo `save_config()`** trong `SubtitleTab` (lưu 39 cấu hình)
- ✅ **Cập nhật `Piu.save_current_config()`** để gọi `self.subtitle_view_frame.save_config()`

### 📊 Kết quả
- **subtitle_tab.py:** 798 dòng → 3,391 dòng (tăng ~2,593 dòng)
- **Piu.py:** Giảm ~2,234 dòng logic Subtitle
- **0 linter errors** sau khi hoàn tất
- ✅ **App chạy thành công, không có lỗi**
- ✅ **Tất cả logic Subtitle đã được tổ chức tốt hơn**

### 📋 Chi tiết
- **Tổng số hàm di chuyển:** 31 hàm (7 Whisper + 24 GPT/Gemini/Translation/Merge/Edit)
- **Tổng số biến di chuyển:** 60+ biến state
- **Phương pháp:** Manual copy + auto fix references (theo yêu cầu người dùng)
- **Alias tương thích:** Tạo alias cho `manual_merge_mode_var`, `pause_for_edit_var`, `continue_merge_event`, `manual_sub_queue` để backward compatibility

---

## 🎯 PHASE 3: REFACTOR DUBBING TAB

**Status:** ⏳ Chưa bắt đầu  
**Thời gian ước tính:** 3-4 giờ  
**Rủi ro:** Thấp - logic tương đối độc lập

### Mục tiêu
Di chuyển toàn bộ logic Dubbing từ `Piu.py` sang `DubbingTab` (ui/tabs/dubbing_tab.py).

### Các bước (tương tự Phase 1 & 2)

#### Bước 3.1: Di chuyển BIẾN (State)
- Tất cả các biến `dub_xxx_var`
- Các biến trạng thái: `dub_is_processing`, `dub_thread`, `dub_queue`, ...

#### Bước 3.2: Di chuyển HÀM (Logic)
- `dub_load_video()`, `dub_load_script()`, `dub_start_batch_processing()`
- `_dub_process_next_item_in_queue()`, `dub_ffmpeg_...`
- `dub_on_tts_engine_selected()`, `dub_on_background_audio_option_changed()`, ...

#### Bước 3.3: Sửa lỗi Tham chiếu
#### Bước 3.4: Sửa lỗi Kết nối UI
#### Bước 3.5: Di chuyển Logic Lưu Config

---

## 🎉 PHASE 4: REFACTOR YOUTUBE UPLOAD & AI EDITOR TABS - HOÀN THÀNH ✅

**Ngày hoàn thành:** 2025-01-31  
**Status:** ✅ Hoàn thành 100%

### ✅ Đã hoàn thành

#### YouTube Upload Tab:
- ✅ **Di chuyển tất cả biến YouTube** từ `Piu.py` → `YouTubeUploadTab` (15+ biến)
- ✅ **Di chuyển tất cả hàm YouTube** từ `Piu.py` → `YouTubeUploadTab` (17+ hàm):
  - `_select_youtube_video_file()`
  - `_start_youtube_batch_upload()`
  - `_stop_youtube_upload()`
  - `_process_next_youtube_task()`
  - `_handle_youtube_upload_completion()`
  - `_on_youtube_batch_finished()`
  - `_select_youtube_thumbnail()`
  - `_add_youtube_task_to_queue()`
  - `_update_youtube_ui_state()`
  - `update_youtube_queue_display()`
  - `_remove_youtube_task_from_queue()`
  - `_autofill_youtube_fields()`
  - `_on_metadata_checkbox_toggled()`
  - `_on_upload_method_changed()`
  - `_browse_chrome_portable_path()`
  - `_browse_chromedriver_path()`
  - `_get_youtube_description()`
  - `_perform_youtube_upload_thread()` (thread upload API)
  - `_upload_video_via_browser_thread()` (thread upload browser)
- ✅ **Sửa tất cả tham chiếu** trong `YouTubeUploadTab`
- ✅ **Sửa UI commands** để gọi hàm trong `YouTubeUploadTab`
- ✅ **Tạo `save_config()`** trong `YouTubeUploadTab` (lưu 16 cấu hình)
- ✅ **Tạo wrapper functions** trong `Piu.py` để backward compatibility
- ✅ **Xóa duplicate code** - Đã xóa 2 hàm thread upload duplicate khỏi `Piu.py` (~170 dòng)

#### AI Editor Tab:
- ✅ **Kiểm tra và hoàn thiện** - Tab này đã được refactor nhiều trước đó
- ✅ **Tạo `save_config()`** trong `AIEditorTab` (lưu 13+ cấu hình)
- ✅ **Sửa các chỗ gọi trực tiếp** `self.master_app.save_current_config()` → `self.save_config()`
- ✅ **Xóa duplicate code save config** trong `Piu.py` (dòng 16077-16086)
- ✅ **Sửa UI state management** - Đã sửa gọi `_set_ai_edit_tab_ui_state()` → `ai_editor_view_frame._set_ui_state(False)`

### 📊 Kết quả
- **youtube_upload_tab.py:** Từ ~500 dòng → ~2,522 dòng (tăng ~2,000 dòng logic)
- **ai_editor_tab.py:** Đã có sẵn, chỉ thêm `save_config()` method
- **Piu.py:** Đã tạo wrapper functions cho các hàm đã di chuyển, đã xóa duplicate code
- ✅ **YouTube Upload và AI Editor hoạt động bình thường**

### 📋 Chi tiết
- Tất cả logic YouTube Upload đã được di chuyển sang `YouTubeUploadTab`
- AI Editor Tab đã hoàn thiện 100% với `save_config()` method và không còn duplicate code
- `save_current_config()` trong `Piu.py` đã được cập nhật để gọi `save_config()` từ cả hai tab
- Đã xóa duplicate code save config và sửa UI state management cho AI Editor Tab

---

## 🎯 PHASE 5: DỌN DẸP PIU.PY CUỐI CÙNG

**Status:** 🔄 30% hoàn thành  
**Thời gian ước tính:** 1-2 giờ

### Đã hoàn thành
- ✅ Xóa các hàm Google Sheet cũ (~317 dòng)
- ✅ Tạo wrapper functions cho backward compatibility

### Cần làm
- ⏳ Xóa các biến đã di chuyển khỏi `__init__`
- ⏳ Tối ưu `save_current_config()` để chỉ gọi các tab
- ⏳ Xóa wrapper functions nếu không còn cần thiết (sau khi tất cả tabs đã refactor)

### Mục tiêu
- Chỉ giữ lại các biến chung: `self.cfg`, `self.stop_event`, `self.dub_stop_event`
- Chỉ giữ lại các Services: `self.ai_service`, `self.model_service`, `self.image_service`, ...
- `save_current_config()` sẽ chỉ gọi:
  ```python
  if hasattr(self, 'download_view_frame'):
      self.download_view_frame.save_config()
  if hasattr(self, 'subtitle_view_frame'):
      self.subtitle_view_frame.save_config()
  if hasattr(self, 'dubbing_view_frame'):
      self.dubbing_view_frame.save_config()
  # ... các tab khác
  ```

---

## 📊 Thống kê

### File sizes hiện tại
- **Piu.py:** ~27,019 dòng (giảm từ ~31,000 = -12.8%)
- **download_tab.py:** 2,395 dòng
- **youtube_upload_tab.py:** 2,522 dòng
- **ai_editor_tab.py:** ~1,445 dòng
- **subtitle_tab.py:** ~? dòng (chưa refactor)
- **dubbing_tab.py:** ~? dòng (chưa refactor)

### Mục tiêu sau khi hoàn thành tất cả phases
- **Piu.py:** < 25,000 dòng (giảm thêm ~3,500 dòng)
- Logic được tổ chức tốt hơn trong các Tab classes

---

## 📝 Ghi chú

### Nguyên tắc refactor
1. **Không thay đổi UI behavior:** Chỉ tách logic, không sửa UI
2. **Giữ backward compatibility:** Tạo wrapper functions nếu cần
3. **Gradual migration:** Tách từng phase, test từng phase
4. **Error handling:** Giữ nguyên error handling patterns
5. **Logging:** Đảm bảo logging vẫn hoạt động đúng

### Pattern đã áp dụng (Phase 1)
- **Wrapper pattern:** Giữ các hàm trong Piu.py gọi đến Tab để backward compatibility
- **save_config() pattern:** Mỗi Tab có `save_config()` riêng, được gọi từ `Piu.save_current_config()`
- **Helper functions:** Tạo helper để truy cập global variables từ master_app

---

## ✅ Checklist Phase 2 (Subtitle Tab)

### Bước 2.1: Di chuyển BIẾN
- [ ] Tìm tất cả biến subtitle trong `Piu.py.__init__`
- [ ] Di chuyển sang `SubtitleTab.__init__`
- [ ] Sửa `self.cfg.get` → `self.master_app.cfg.get`

### Bước 2.2: Di chuyển HÀM
- [ ] Di chuyển các hàm Whisper
- [ ] Di chuyển các hàm GPT/Gemini
- [ ] Di chuyển các hàm Dịch
- [ ] Di chuyển các hàm Merge/Burn
- [ ] Di chuyển các hàm Edit
- [ ] Di chuyển các hàm Manual merge

### Bước 2.3: Sửa lỗi Tham chiếu
- [ ] Sửa tất cả `self.master_app.xxx` → `self.xxx` trong SubtitleTab
- [ ] Giữ nguyên tham chiếu chéo cần thiết

### Bước 2.4: Sửa lỗi Kết nối UI
- [ ] Sửa tất cả `command=` trong SubtitleTab

### Bước 2.5: Di chuyển Logic Lưu Config
- [ ] Tạo `save_config()` trong SubtitleTab
- [ ] Cập nhật `Piu.save_current_config()`

### Test
- [ ] Syntax check
- [ ] Test Subtitle hoạt động
- [ ] Test GPT/Gemini editing hoạt động
- [ ] Test Translation hoạt động
- [ ] Test Merge/Burn hoạt động

---

**Sẵn sàng cho Phase 2!** 🚀
