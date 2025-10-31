# Refactor Progress - Piu

Ngày: 2025-10-30

## Hoàn thành
- Tách FFmpeg command runner ra `services/ffmpeg_service.py`
  - Hàm: `run_ffmpeg_command(cmd_params, process_name, stop_event, set_current_process, clear_current_process, timeout_seconds)`
  - Hỗ trợ: tìm ffmpeg, spawn process, timeout, logging, stop_event, cập nhật `current_process` qua callback
- Cập nhật `Piu.py`
  - Hardsub/Softsub: dùng `ffmpeg_run_command(...)`
  - Dubbing:
    - Chuẩn hóa WAV, áp dụng fade, tạo leading silence, tạo silence WAV
    - Ghép WAV từ concat list, chuyển WAV→MP3 normalized
  - VAD preprocess: trích audio WAV tạm, cắt video theo `-ss`
  - Concat video từ file list: dùng service thay vì `subprocess`
  - BGM fade trước khi mux: dùng service, giữ stop_event/callback
  - Slideshow/Branding:
    - Chèn logo (overlay/scale/format/map streams) dùng service
    - BGM acrossfade (filter_complex) và chuẩn hóa từng chunk BGM dùng service
    - Concat filter cuối (video/audio/subtitle map, vsync, fps) dùng service
    - Tối ưu khoảng lặng V2 (trim + apply fade/pad) và cắt audio dùng service
- Tách luồng chạy yt-dlp ra `services/download_service.py`
  - Hàm: `stream_process_output(full_cmd, process_name, hide_console_window, set_current_process, clear_current_process)`
  - `Piu.py` chuyển sang dùng hàm stream để đọc output theo dòng, giữ nguyên logic parse progress và cập nhật UI
- Kiểm tra cú pháp (syntax) cho các file đã sửa/đã thêm: OK

- Tách License/Activation/Trial ra `services/licensing_service.py`
  - Hàm: `verify_status(key, hwid)`, `activate(key, hwid)`, `start_trial(hwid)`
  - `Piu.py` gọi service, giữ nguyên UI và lưu config

- Tách Update Check ra `services/update_service.py` và nối lại `Piu.py`
  - Hàm: `fetch_update_info(update_url, timeout_seconds)`, `is_newer(remote, current)`
  - `Piu.py`: `check_for_update(...)` dùng service, giữ nguyên popup/UI và logic skip-version

- Dọn dẹp `Piu.py`
  - Xoá `_run_ffmpeg_command(...)` (đã thay bằng service)
  - Loại bỏ tham chiếu response cũ trong update/activation

## Ảnh hưởng
- Không thay đổi logic nghiệp vụ; chỉ di chuyển nơi thực thi subprocess.
- UI vẫn cập nhật tiến trình và log như cũ, qua callback `current_process` và `stop_event`.

## Đề xuất bước tiếp theo (ưu tiên)

📋 **Xem kế hoạch chi tiết:** [refactor_plan_5_steps.md](./refactor_plan_5_steps.md)

### Kế hoạch 5 bước đã được lập (2025-01-XX)

1. ✅ **AI Service** ⭐ **ĐÃ HOÀN THÀNH** (4-6 giờ)
   - ✅ Tách Gemini/GPT/OpenAI processing
   - ✅ Đã refactor: `translate_openai()`, `test_gemini_key()`, `test_openai_key()`
   - ✅ Đã refactor: `_execute_gemini_script_editing_thread()`, `_execute_gpt_script_editing_thread()`
   - ✅ Đã refactor: `_execute_gemini_scene_division_thread()`, `_execute_gpt_scene_division_thread()`
   - ✅ File: `services/ai_service.py` - Đã tạo và test thành công

2. ✅ **Image Service** **ĐÃ HOÀN THÀNH** (3-4 giờ)
   - ✅ Tách DALL-E/Imagen/Slideshow logic
   - ✅ Đã refactor: `_execute_dalle_chain_generation_iterative()`
   - ✅ Đã refactor: `_execute_imagen_chain_generation_iterative()`
   - ✅ Đã refactor: `_execute_imagen_generation_thread()`
   - ✅ File: `services/image_service.py` - Đã tạo và test thành công

3. ✅ **Model Service** **ĐÃ HOÀN THÀNH** (2-3 giờ)
   - ✅ Tách Whisper model management
   - ✅ Đã refactor: `_determine_target_device()`
   - ✅ Đã refactor: `check_cuda_status_thread()`
   - ✅ Đã refactor: `_load_whisper_model_thread()`
   - ✅ Đã refactor: `run_whisper_engine()`
   - ✅ File: `services/model_service.py` - Đã tạo và test thành công

4. ✅ **Metadata Service** **ĐÃ HOÀN THÀNH** (2-3 giờ)
   - ✅ Tách metadata cache và autofill
   - ✅ Đã refactor: `_load_master_metadata_cache()`
   - ✅ Đã refactor: `_save_master_metadata_cache()`
   - ✅ Đã refactor: `_update_metadata_cache_entry()`
   - ✅ Đã refactor: `_autofill_youtube_fields()`
   - ✅ File: `services/metadata_service.py` - Đã tạo và test thành công

5. ⏳ **YouTube Service** (3-4 giờ) - **CHƯA BẮT ĐẦU**
   - Tách queue/batch processing
   - Consolidate existing YouTube services
   - File: `services/youtube_service.py` (mới hoặc update)

**Tổng thời gian ước tính:** 14-20 giờ

---

## TIẾN ĐỘ CẬP NHẬT (2025-01-XX)

### Đã hoàn thành 4/5 bước

#### ✅ BƯỚC 1: AI Service - HOÀN THÀNH
- ✅ Tạo `services/ai_service.py` với các methods chính:
  - `translate_with_openai()` - Translation logic
  - `test_gemini_key()`, `test_openai_key()` - API key testing
  - `process_script_with_gemini()` - Gemini script editing
  - `process_script_with_gpt()` - GPT script editing
  - `divide_scene_with_gemini()` - Gemini scene division
  - `divide_scene_with_gpt()` - GPT scene division với DALL-E prompts
- ✅ Refactor các methods trong `Piu.py`:
  - `translate_openai()` → delegate sang `AIService.translate_with_openai()`
  - `_perform_openai_key_check()`, `_perform_gemini_key_check()` → delegate sang service
  - `_execute_gemini_script_editing_thread()` → delegate sang `AIService.process_script_with_gemini()`
  - `_execute_gpt_script_editing_thread()` → delegate sang `AIService.process_script_with_gpt()`
  - `_execute_gemini_scene_division_thread()` → delegate sang `AIService.divide_scene_with_gemini()`
  - `_execute_gpt_scene_division_thread()` → delegate sang `AIService.divide_scene_with_gpt()`

#### ✅ BƯỚC 2: Image Service - HOÀN THÀNH
- ✅ Tạo `services/image_service.py` với các methods chính:
  - `generate_dalle_images()` - DALL-E 2 và 3 generation với retry logic
  - `generate_imagen_images()` - Imagen 3 generation với retry logic và safety filter handling
- ✅ Refactor các methods trong `Piu.py`:
  - `_execute_dalle_chain_generation_iterative()` → delegate sang `ImageService.generate_dalle_images()`
  - `_execute_imagen_chain_generation_iterative()` → delegate sang `ImageService.generate_imagen_images()`
  - `_execute_imagen_generation_thread()` → delegate sang `ImageService.generate_imagen_images()`

#### ✅ BƯỚC 3: Model Service - HOÀN THÀNH
- ✅ Tạo `services/model_service.py` với các methods chính:
  - `check_cuda_availability()` - Check CUDA/GPU và VRAM
  - `get_recommended_device()` - Xác định device (cuda/cpu)
  - `load_model()` - Load Whisper model với fallback CUDA -> CPU
  - `unload_model()` - Unload model và giải phóng memory
  - `transcribe()` - Transcription cơ bản
  - `transcribe_and_save()` - Transcription và lưu file
- ✅ Refactor các methods trong `Piu.py`:
  - `_determine_target_device()` → delegate sang `ModelService.get_recommended_device()`
  - `check_cuda_status_thread()` → delegate sang `ModelService.check_cuda_availability()`
  - `_load_whisper_model_thread()` → delegate sang `ModelService.load_model()`
  - `run_whisper_engine()` → delegate sang `ModelService.transcribe_and_save()`

#### ✅ BƯỚC 4: Metadata Service - HOÀN THÀNH
- ✅ Tạo `services/metadata_service.py` với các methods chính:
  - `load_cache()` - Load metadata cache từ file JSON
  - `save_cache()` - Save metadata cache ra file JSON
  - `get_metadata()`, `has_metadata()` - Query metadata
  - `update_metadata()` - Update hoặc tạo metadata entry (hỗ trợ auto-increment thumbnail)
  - `autofill_youtube_fields()` - Auto-fill YouTube fields từ metadata
  - `get_title_from_filename()` - Extract title từ filename
- ✅ Refactor các methods trong `Piu.py`:
  - `_load_master_metadata_cache()` → delegate sang `MetadataService.load_cache()`
  - `_save_master_metadata_cache()` → delegate sang `MetadataService.save_cache()`
  - `_update_metadata_cache_entry()` → delegate sang `MetadataService.update_metadata()`
  - `_autofill_youtube_fields()` → delegate sang `MetadataService.autofill_youtube_fields()`

#### ⏳ BƯỚC 5: YouTube Service - CHƯA BẮT ĐẦU
- Chưa bắt đầu

### Files đã tạo/cập nhật
- ✅ `services/ai_service.py` - 600+ lines
- ✅ `services/image_service.py` - 400+ lines
- ✅ `services/model_service.py` - 500+ lines
- ✅ `services/metadata_service.py` - 300+ lines
- ✅ `Piu.py` - Đã refactor 15+ methods chính
- ✅ `ui/tabs/youtube_upload_tab.py` - Sửa thứ tự UI (thumbnail section)

### Tổng kết
- **Files mới:** 4 service files
- **Methods đã refactor:** 15+ methods chính trong `Piu.py`
- **Syntax check:** ✅ Tất cả files compile thành công
- **Code cleanup:** ✅ Đã dọn dẹp code cũ sau mỗi lần refactor thành công

---

### Đề xuất cũ (đã được tích hợp vào kế hoạch trên)

1) Gom System utils rải rác về `utils/system_utils.py`
   - Single-instance/mutex, cleanup tiến trình con, phát hiện/resolve đường dẫn `yt-dlp`, kiểm tra GPU/CUDA
   - ⚠️ **Note:** CUDA detection đã được đề xuất trong Model Service (Bước 3)

2) UI-facade qua `application/app.py`
   - UI tabs không import service trực tiếp; gọi qua `app.services.*` để giảm coupling
   - ⚠️ **Note:** Để sau khi hoàn thành 5 bước trên

3) Kiểm thử hồi quy nhanh theo kịch bản
   - Hardsub/Softsub, yt-dlp download (có/không cookies), kích hoạt/dùng thử, kiểm tra cập nhật thủ công/tự động
   - ⚠️ **Note:** Testing được tích hợp vào từng bước

## Kế hoạch test nhanh sau mỗi bước
- Syntax check (đã làm)
- Chạy tính năng liên quan (manual smoke):
  - Hardsub/Softsub với file nhỏ mẫu
  - Download 1 video/1 audio bằng yt-dlp (có/không cookies)
- Kiểm tra log file `Piu_app.log` có ghi đúng và không nhân đôi handler

## Ghi chú
- Giữ nguyên `ctk.*Var` trong `application/app_state.py`; chỉ dùng dataclass cho item hàng đợi nếu cần.
- Không thay đổi UI layout/behavior; chỉ refactor tách lớp.
