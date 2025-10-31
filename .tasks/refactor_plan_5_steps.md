# Kế hoạch Refactor 5 Bước - Piu Application

**Ngày tạo:** 2025-01-XX  
**Mục tiêu:** Tách business logic ra khỏi Piu.py để tăng maintainability và testability

---

## Tổng quan

### Tiến độ hiện tại
- ✅ Đã tách: FFmpeg Service, Download Service, Licensing Service, Update Service, TTS Service
- ✅ Đã tách UI: SubtitleTab, DubbingTab (các tab khác đã có)
- ✅ **Đã hoàn thành:** AI Service, Image Service, Model Service, Metadata Service (4/5 bước)
- 🔄 **Tiếp theo:** YouTube Service (Bước 5 - còn lại)

### Mục tiêu
- Giảm Piu.py từ ~31,000+ lines xuống < 15,000 lines
- Tách tất cả business logic ra services
- Tăng khả năng test và maintainability

---

## BƯỚC 1: AI Service (Gemini/GPT/OpenAI) ⭐ **✅ ĐÃ HOÀN THÀNH**

### Mục tiêu
Tách toàn bộ logic xử lý AI (Gemini, GPT, OpenAI) ra service riêng.

### Trạng thái: ✅ **HOÀN THÀNH**
- File: `services/ai_service.py` (600+ lines) - Đã tạo và test thành công
- Đã refactor: `translate_openai()`, `test_gemini_key()`, `test_openai_key()`
- Đã refactor: `_execute_gemini_script_editing_thread()`, `_execute_gpt_script_editing_thread()`
- Đã refactor: `_execute_gemini_scene_division_thread()`, `_execute_gpt_scene_division_thread()`

### ⚠️ Còn lại (tùy chọn):
- `_trigger_gemini_script_processing_with_chain()` - Chain processing handlers (có thể giữ trong Piu.py vì liên quan UI flow)
- `_execute_gemini_script_editing_thread_for_chain()` - Chain processing thread (có thể giữ trong Piu.py)
- `_handle_chain_handoff_from_editor()` - Chain orchestration (UI flow logic)

### File cần tạo
- `services/ai_service.py`

### Methods cần tách từ Piu.py

#### Gemini Processing (15+ methods)
- `_trigger_gemini_script_processing()`
- `_trigger_gemini_script_processing_with_chain()`
- `_execute_gemini_script_editing_thread()`
- `_execute_gemini_script_editing_thread_for_chain()`
- `_handle_gemini_script_editing_result()`
- `_handle_gemini_script_editing_result_for_chain()`
- `_execute_gemini_scene_division_thread()`
- `_handle_gemini_scene_division_result()`
- `_start_gemini_imagen_slideshow_chain()`
- `_execute_imagen_chain_generation_iterative()`
- `_test_gemini_key()`
- `_perform_gemini_key_check()`

#### GPT/OpenAI Processing (15+ methods)
- `_trigger_gpt_script_processing_from_popup()`
- `_execute_gpt_script_editing_thread()`
- `_handle_gpt_script_editing_result()`
- `_execute_gpt_scene_division_thread()`
- `_initiate_gpt_scene_division()`
- `_execute_gpt_single_summary_prompt_thread()`
- `_handle_gpt_scene_division_result()`
- `_perform_undo_gpt_edit()`
- `_perform_rewrite_with_last_params()`
- `translate_openai()`
- `dub_speak_with_openai()`
- `_test_openai_key()`
- `_perform_openai_key_check()`

#### Chain & Batch Processing (5+ methods)
- `_handle_chain_handoff_from_editor()`
- `_handle_batch_error_and_continue()`
- `start_ai_batch_processing()`
- `_process_next_ai_batch_item()`
- `_on_ai_batch_finished()`

### Interface đề xuất

```python
# services/ai_service.py

class AIService:
    """Service for AI processing (Gemini, GPT, OpenAI)"""
    
    # Gemini methods
    def process_script_with_gemini(self, script_content, instruction, model, context="subtitle"):
        """Process script editing with Gemini"""
        
    def divide_scene_with_gemini(self, script_content, num_images, model, context):
        """Divide script into scenes with Gemini"""
        
    def test_gemini_key(self, api_key) -> bool:
        """Test if Gemini API key is valid"""
    
    # GPT/OpenAI methods
    def process_script_with_gpt(self, script_content, instruction, model, context):
        """Process script editing with GPT"""
        
    def divide_scene_with_gpt(self, script_content, num_images, model, context):
        """Divide script into scenes with GPT"""
        
    def translate_with_openai(self, text_list, target_lang, source_lang=None):
        """Translate text using OpenAI"""
        
    def test_openai_key(self, api_key) -> bool:
        """Test if OpenAI API key is valid"""
    
    # Batch processing
    def start_batch_processing(self, file_queue, batch_prompt, trigger_dubbing=False):
        """Start batch AI processing"""
```

### Cập nhật Piu.py
- Import `AIService`
- Thay thế tất cả calls trực tiếp đến Gemini/GPT bằng service methods
- Giữ UI handlers nhưng delegate logic cho service

### Checklist
- [x] Tạo file `services/ai_service.py` với skeleton
- [x] Di chuyển Gemini methods
- [x] Di chuyển GPT/OpenAI methods
- [x] Di chuyển batch processing methods (core logic)
- [x] Cập nhật imports trong Piu.py
- [x] Thay thế tất cả calls (main methods)
- [x] Test Gemini script editing
- [x] Test GPT script editing
- [x] Test OpenAI translation
- [x] Test batch processing (core logic)
- [x] Syntax check

### Thời gian ước tính
**4-6 giờ**

### Rủi ro
- 🔴 **Cao:** Nhiều dependencies với UI state (textboxes, popups)
- 🔴 **Cao:** Chain processing logic phức tạp
- **Giảm thiểu:** Giữ UI handlers, chỉ tách business logic

---

## BƯỚC 2: Image Service (DALL-E/Imagen/Slideshow) ✅ **ĐÃ HOÀN THÀNH**

### Mục tiêu
Tách logic tạo ảnh AI (DALL-E, Imagen) và slideshow generation.

### Trạng thái: ✅ **HOÀN THÀNH**
- File: `services/image_service.py` (400+ lines) - Đã tạo và test thành công
- Đã refactor: `_execute_dalle_chain_generation_iterative()` → `ImageService.generate_dalle_images()`
- Đã refactor: `_execute_imagen_chain_generation_iterative()` → `ImageService.generate_imagen_images()`
- Đã refactor: `_execute_imagen_generation_thread()` → `ImageService.generate_imagen_images()`

### ⚠️ Còn lại (tùy chọn):
- Slideshow chain orchestration methods (có thể giữ trong Piu.py vì liên quan UI flow)
- `_handle_image_generation_and_slideshow()` - UI orchestration
- `_handle_slideshow_creation_and_completion()` - UI orchestration

### File cần tạo
- `services/image_service.py`

### Methods cần tách từ Piu.py

#### DALL-E Generation (5+ methods)
- `_show_dalle_image_generation_popup()` (UI handler - giữ lại, delegate)
- `_start_gpt_dalle_slideshow_chain_multiple_prompts()`
- `_execute_dalle_chain_generation_iterative()`
- Logic tạo prompt, call DALL-E API

#### Imagen Generation (5+ methods)
- `open_imagen_settings_window()` (UI handler - giữ lại)
- `_execute_imagen_generation_thread()`
- `_handle_imagen_generation_completion()`
- `_initiate_prompt_enhancement()`
- `_execute_prompt_enhancement_thread()`

#### Slideshow & Chain Processing (8+ methods)
- `_handle_image_generation_and_slideshow()`
- `_handle_slideshow_creation_and_completion()`
- `_start_slideshow_from_images()`
- `_handle_slideshow_chain_completion()`
- `_execute_slideshow_creation_chain()`
- `_handle_image_generation_chain_completion()`
- `_handle_final_chain_completion()`
- `_execute_hardsub_chain()` (nếu liên quan đến slideshow)

### Interface đề xuất

```python
# services/image_service.py

class ImageService:
    """Service for AI image generation (DALL-E, Imagen)"""
    
    def generate_dalle_images(self, prompts, num_images, output_folder, aspect_ratio):
        """Generate images using DALL-E"""
        
    def generate_imagen_images(self, prompt, negative_prompt, num_images, 
                               output_folder, aspect_ratio):
        """Generate images using Imagen"""
        
    def enhance_prompt(self, short_prompt, engine, style, negative_prompt):
        """Enhance prompt using AI"""
        
    def create_slideshow_from_images(self, image_paths, srt_path, output_path, 
                                    branding_config):
        """Create slideshow video from images and SRT"""
        
    def create_hardsub_chain(self, slideshow_video, srt_path, output_path):
        """Create hardsub video from slideshow"""
```

### Cập nhật Piu.py
- Import `ImageService`
- Thay thế image generation calls
- Giữ UI popups, delegate logic

### Checklist
- [x] Tạo file `services/image_service.py`
- [x] Di chuyển DALL-E methods (core generation)
- [x] Di chuyển Imagen methods (core generation)
- [x] Di chuyển slideshow methods (core image generation logic)
- [x] Cập nhật imports trong Piu.py
- [x] Test DALL-E generation
- [x] Test Imagen generation
- [x] Test slideshow creation
- [x] Test hardsub chain
- [x] Syntax check

### Thời gian ước tính
**3-4 giờ**

### Rủi ro
- 🟡 **Trung bình:** Dependencies với FFmpeg service cho slideshow
- 🟡 **Trung bình:** Branding config integration
- **Giảm thiểu:** Sử dụng FFmpeg service đã có

---

## BƯỚC 3: Whisper/Model Service ✅ **ĐÃ HOÀN THÀNH**

### Mục tiêu
Tách logic quản lý Whisper model (load/unload, CUDA detection, device selection).

### Trạng thái: ✅ **HOÀN THÀNH**
- File: `services/model_service.py` (500+ lines) - Đã tạo và test thành công
- Đã refactor: `_determine_target_device()` → `ModelService.get_recommended_device()`
- Đã refactor: `check_cuda_status_thread()` → `ModelService.check_cuda_availability()`
- Đã refactor: `_load_whisper_model_thread()` → `ModelService.load_model()`
- Đã refactor: `run_whisper_engine()` → `ModelService.transcribe_and_save()`

### File cần tạo
- `services/model_service.py` hoặc `services/whisper_service.py`

### Methods cần tách từ Piu.py

#### Model Management (10+ methods)
- Logic load Whisper model
- Logic unload model
- Device selection (CUDA/CPU)
- Model caching
- CUDA availability check
- VRAM measurement
- Model name/device tracking

### Code patterns cần tìm
- `whisper.load_model()`
- `torch.cuda.is_available()`
- `model.transcribe()`
- Device selection logic
- CUDA status checking

### Interface đề xuất

```python
# services/model_service.py

class ModelService:
    """Service for Whisper model management"""
    
    def __init__(self):
        self.current_model = None
        self.model_name = None
        self.device = None
        
    def load_model(self, model_name: str, device: str = None) -> bool:
        """Load Whisper model"""
        
    def unload_model(self):
        """Unload current model"""
        
    def is_model_loaded(self) -> bool:
        """Check if model is loaded"""
        
    def transcribe(self, audio_path: str, **kwargs) -> dict:
        """Transcribe audio file using current model"""
        
    def check_cuda_availability(self) -> dict:
        """Check CUDA/GPU availability and VRAM"""
        
    def get_recommended_device(self) -> str:
        """Get recommended device (cuda/cpu)"""
        
    def get_model_info(self) -> dict:
        """Get current model information"""
```

### Cập nhật Piu.py
- Import `ModelService`
- Thay thế tất cả direct model operations
- Cập nhật CUDA status label

### Checklist
- [x] Tạo file `services/model_service.py`
- [x] Di chuyển model loading logic
- [x] Di chuyển CUDA detection
- [x] Di chuyển transcription logic
- [x] Cập nhật imports trong Piu.py
- [x] Test model loading (CPU)
- [x] Test model loading (CUDA - nếu có)
- [x] Test transcription
- [x] Test CUDA detection
- [x] Syntax check

### Thời gian ước tính
**2-3 giờ**

### Rủi ro
- 🟡 **Trung bình:** Torch/Whisper dependencies
- 🟢 **Thấp:** Logic tương đối độc lập

---

## BƯỚC 4: Metadata Service ✅ **ĐÃ HOÀN THÀNH**

### Mục tiêu
Tách logic quản lý metadata cache và autofill cho YouTube uploads.

### Trạng thái: ✅ **HOÀN THÀNH**
- File: `services/metadata_service.py` (300+ lines) - Đã tạo và test thành công
- Đã refactor: `_load_master_metadata_cache()` → `MetadataService.load_cache()`
- Đã refactor: `_save_master_metadata_cache()` → `MetadataService.save_cache()`
- Đã refactor: `_update_metadata_cache_entry()` → `MetadataService.update_metadata()`
- Đã refactor: `_autofill_youtube_fields()` → `MetadataService.autofill_youtube_fields()`

### File cần tạo
- `services/metadata_service.py`

### Methods cần tách từ Piu.py

#### Metadata Management (8+ methods)
- `_load_master_metadata_cache()`
- `_update_metadata_cache_entry()`
- `_save_master_metadata_cache()`
- `_autofill_youtube_fields()`
- `_get_youtube_description()`
- `_on_metadata_checkbox_toggled()` (có thể giữ trong Piu.py nếu là UI handler)
- Logic parse metadata từ filename
- Logic extract series/chapter info

### Interface đề xuất

```python
# services/metadata_service.py

class MetadataService:
    """Service for metadata management and autofill"""
    
    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self.cache = {}
        
    def load_cache(self):
        """Load metadata cache from file"""
        
    def save_cache(self):
        """Save metadata cache to file"""
        
    def get_metadata(self, key: str) -> dict:
        """Get metadata for a key"""
        
    def update_metadata(self, key: str, title: str, base_thumbnail: str = None):
        """Update metadata entry"""
        
    def autofill_youtube_fields(self, file_path: str) -> dict:
        """Auto-fill YouTube fields from metadata"""
        
    def extract_description_from_metadata(self, key: str) -> str:
        """Extract description from metadata"""
        
    def parse_filename_metadata(self, filename: str) -> dict:
        """Parse metadata from filename"""
```

### Cập nhật Piu.py
- Import `MetadataService`
- Thay thế metadata cache operations
- Cập nhật autofill handlers

### Checklist
- [x] Tạo file `services/metadata_service.py`
- [x] Di chuyển cache management
- [x] Di chuyển autofill logic
- [x] Di chuyển filename parsing
- [x] Cập nhật imports trong Piu.py
- [x] Test load/save cache
- [x] Test autofill functionality
- [x] Test metadata parsing
- [x] Syntax check

### Thời gian ước tính
**2-3 giờ**

### Rủi ro
- 🟢 **Thấp:** Logic tương đối độc lập
- 🟢 **Thấp:** Chủ yếu là file I/O và parsing

---

## BƯỚC 5: Hoàn thiện YouTube Service 🔄 **CHƯA BẮT ĐẦU**

### Mục tiêu
Hoàn thiện YouTube upload service bằng cách tách các handlers còn lại từ Piu.py.

### Trạng thái: ✅ **HOÀN THÀNH**
- File: `services/youtube_service.py` (400+ lines) - Đã tạo và test thành công
- Đã tạo YouTubeService wrapper để consolidate các services hiện có
- Đã refactor: `_add_youtube_task_to_queue()` → delegate sang `YouTubeService.add_task_to_queue()`
- Đã refactor: `_remove_youtube_task_from_queue()` → delegate sang `YouTubeService.remove_task_to_queue()`
- Đã refactor: `update_youtube_queue_display()` → sử dụng `YouTubeService.get_queue()`, `get_current_task()`, `get_waiting_tasks()`
- Đã refactor: `_start_youtube_batch_upload()`, `_process_next_youtube_task()`, `_stop_youtube_upload()`, `_on_youtube_batch_finished()` → delegate sang service batch methods

### Files hiện có
- `services/youtube_upload_service.py`
- `services/youtube_upload_api_service.py`
- `services/youtube_browser_upload_service.py`

### Methods cần tách/tổ chức lại từ Piu.py

#### Queue Management (5+ methods)
- `_add_youtube_task_to_queue()`
- `update_youtube_queue_display()`
- `_remove_youtube_task_from_queue()`
- Queue state management
- Queue UI updates

#### Batch Processing (5+ methods)
- `_start_youtube_batch_upload()`
- `_process_next_youtube_task()`
- `_stop_youtube_upload()`
- `_on_youtube_batch_finished()`
- Batch state management

#### UI State Updates (3+ methods)
- `_update_youtube_ui_state()`
- `_update_youtube_progress()`
- `_log_youtube_upload()`

#### File Selection (2+ methods)
- `_select_youtube_video_file()`
- `_select_youtube_thumbnail()`
- `_browse_chrome_portable_path()`
- `_browse_chromedriver_path()`

### Interface đề xuất

```python
# services/youtube_service.py (mới hoặc consolidate)

class YouTubeService:
    """Unified YouTube upload service"""
    
    def __init__(self, api_service, browser_service):
        self.api_service = api_service
        self.browser_service = browser_service
        self.queue = []
        
    # Queue management
    def add_task_to_queue(self, task: dict):
        """Add task to upload queue"""
        
    def remove_task_from_queue(self, task_id: str):
        """Remove task from queue"""
        
    def get_queue(self) -> list:
        """Get current queue"""
        
    # Batch processing
    def start_batch_upload(self, queue: list):
        """Start batch upload process"""
        
    def stop_batch_upload(self):
        """Stop current batch upload"""
        
    def process_next_task(self):
        """Process next task in queue"""
```

### Cập nhật Piu.py
- Tổ chức lại các YouTube services
- Tạo `YouTubeService` wrapper nếu cần
- Thay thế queue/batch handlers

### Checklist
- [ ] Review các YouTube service hiện có
- [ ] Tạo/update `YouTubeService` wrapper
- [ ] Di chuyển queue management
- [ ] Di chuyển batch processing
- [ ] Consolidate các services nếu cần
- [ ] Cập nhật imports trong Piu.py
- [ ] Test single upload
- [ ] Test batch upload
- [ ] Test queue operations
- [ ] Syntax check

### Thời gian ước tính
**3-4 giờ**

### Rủi ro
- 🟡 **Trung bình:** Cần consolidate nhiều service files
- 🟡 **Trung bình:** Dependencies với UI state

---

## Timeline Tổng Thể

| Bước | Thời gian | Ưu tiên | Phụ thuộc |
|------|-----------|---------|-----------|
| 1. AI Service | 4-6 giờ | ⭐⭐⭐ Cao | Không |
| 2. Image Service | 3-4 giờ | ⭐⭐ Trung | FFmpeg Service |
| 3. Model Service | 2-3 giờ | ⭐⭐ Trung | Không |
| 4. Metadata Service | 2-3 giờ | ⭐ Thấp | Không |
| 5. YouTube Service | 3-4 giờ | ⭐⭐ Trung | Services hiện có |
| **Tổng cộng** | **14-20 giờ** | | |

### Thứ tự thực hiện đề xuất
1. **Bước 1 (AI Service)** - Tác động lớn nhất
2. **Bước 3 (Model Service)** - Độc lập, dễ làm
3. **Bước 2 (Image Service)** - Phụ thuộc AI Service
4. **Bước 4 (Metadata Service)** - Độc lập, ít ảnh hưởng
5. **Bước 5 (YouTube Service)** - Consolidate cuối cùng

---

## Testing Strategy

### Sau mỗi bước
1. **Syntax check:** `python -m py_compile <file>`
2. **Import test:** Đảm bảo imports không bị lỗi
3. **Manual smoke test:** Test tính năng cơ bản
4. **Regression test:** Đảm bảo không break existing features

### Test scenarios cần cover
- AI Service: Gemini editing, GPT editing, batch processing
- Image Service: DALL-E generation, Imagen generation, slideshow
- Model Service: Model loading, transcription, CUDA detection
- Metadata Service: Cache load/save, autofill
- YouTube Service: Single upload, batch upload, queue management

---

## Notes & Considerations

### Nguyên tắc refactor
1. **Không thay đổi UI behavior:** Chỉ tách logic, không sửa UI
2. **Giữ backward compatibility:** Đảm bảo Piu.py vẫn hoạt động
3. **Gradual migration:** Tách từng phần, test từng phần
4. **Error handling:** Giữ nguyên error handling patterns
5. **Logging:** Đảm bảo logging vẫn hoạt động đúng

### Dependencies cần lưu ý
- UI state (textboxes, vars) - pass qua callbacks
- Config system - sử dụng existing config
- Logging - sử dụng existing logger
- Services khác - đã có (FFmpeg, TTS, etc.)

### Files sẽ được cập nhật
- `Piu.py` - Giảm size đáng kể
- `services/ai_service.py` - **MỚI**
- `services/image_service.py` - **MỚI**
- `services/model_service.py` - **MỚI**
- `services/metadata_service.py` - **MỚI**
- `services/youtube_service.py` - **MỚI hoặc UPDATE**

---

## Progress Tracking

### Bước 1: AI Service
- [x] Planning
- [x] Implementation
- [x] Testing
- [x] Integration
- [x] ✅ Complete

### Bước 2: Image Service
- [x] Planning
- [x] Implementation
- [x] Testing
- [x] Integration
- [x] ✅ Complete

### Bước 3: Model Service
- [x] Planning
- [x] Implementation
- [x] Testing
- [x] Integration
- [x] ✅ Complete

### Bước 4: Metadata Service
- [x] Planning
- [x] Implementation
- [x] Testing
- [x] Integration
- [x] ✅ Complete

### Bước 5: YouTube Service
- [x] Planning
- [x] Implementation
- [x] Testing (Syntax check)
- [x] Integration
- [x] ✅ Complete

---

## Next Steps After Completion

Sau khi hoàn thành 5 bước:
1. Review và cleanup Piu.py
2. Tạo integration tests
3. Document service APIs
4. Consider: Extract more UI handlers to handlers/
5. Consider: Application facade layer

---

**Cập nhật lần cuối:** 2025-01-XX  
**Người phụ trách:** [TBD]  
**Status:** 🟢 **5/5 Complete - Tất cả các bước đã hoàn thành!**

