# Refactoring Plan: Piu Project Structure

## Cấu trúc đề xuất (Updated)

```
piu/
├── main.py                 # Entry point - khởi chạy app
│
├── config/
│   ├── __init__.py
│   ├── settings.py         # load_config(), save_config()
│   └── constants.py        # APP_NAME, CATEGORIES, etc.
│
├── application/
│   ├── __init__.py
│   ├── app.py             # SubtitleApp - main orchestrator
│   └── app_state.py       # StateManager - TOÀN BỘ state variables
│
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── ai_service.py
│   ├── tts_service.py
│   ├── image_service.py
│   ├── download_service.py
│   ├── ffmpeg_service.py
│   └── youtube_service.py
│
├── ui/
│   ├── __init__.py
│   ├── tabs/
│   │   ├── ai_editor_tab.py
│   │   ├── download_tab.py
│   │   ├── subtitle_tab.py
│   │   ├── dubbing_tab.py
│   │   └── upload_tab.py
│   │
│   ├── popups/
│   │   ├── api_settings.py
│   │   ├── branding.py
│   │   ├── style_settings.py
│   │   ├── image_gen.py
│   │   └── metadata.py
│   │
│   └── widgets/
│       ├── splash_screen.py
│       ├── tooltip.py
│       ├── custom_dropdown.py
│       └── custom_font_dropdown.py
│
├── utils/
│   ├── __init__.py
│   ├── keep_awake.py
│   ├── helpers.py          # resource_path, etc.
│   └── logger.py           # Logging configuration
│
├── models/                 # NEW: Data models
│   ├── __init__.py
│   ├── subtitle_model.py   # Subtitle data structure
│   └── config_model.py     # Configuration schema
│
├── exceptions/             # NEW: Custom exceptions
│   ├── __init__.py
│   └── app_exceptions.py   # SingleInstanceException, etc.
│
├── assets/
│   ├── logo_Piu.ico
│   └── logo_Piu_resized.png
│
└── tests/                  # NEW: Testing structure
    ├── __init__.py
    ├── test_services/
    ├── test_utils/
    └── test_ui/
```

## Điểm cải thiện so với cấu trúc gốc:

### 1. **Thêm `/models`** (Quan trọng!)
- Quản lý data structures (subtitle, config schema)
- Type hints rõ ràng hơn
- Dễ validate data

### 2. **Thêm `/exceptions`** (Quan trọng!)
- Tách riêng SingleInstanceException và custom exceptions khác
- Dễ handle errors

### 3. **Thêm `/tests`**
- Cấu trúc sẵn cho testing
- Phân chia theo module

### 4. **Thêm `/utils/logger.py`**
- Centralize logging configuration
- Dễ quản lý log levels

## Chi tiết từng module:

### `config/settings.py`
```python
class SettingsManager:
    def load_config()
    def save_config()
    def get_config_path()
```

### `application/app_state.py`
```python
class StateManager:
    # Tất cả StringVar, IntVar, BooleanVar
    self.cfg
    self.is_subbing
    self.queue = []
    # State management methods
```

### `application/app.py`
```python
class SubtitleApp(ctk.CTk):
    def __init__(self):
        self.state = StateManager()
        self.services = self._init_services()
        self.ui = self._init_ui()
    
    def _init_services()
    def _init_ui()
```

## Lộ trình implementation:

### Phase 1: Setup cấu trúc (30 phút)
1. Tạo cấu trúc thư mục
2. Tạo __init__.py files
3. Di chuyển assets

### Phase 2: Tách Config & Constants (1-2 giờ)
1. Extract constants.py
2. Extract settings.py
3. Test imports

### Phase 3: Tách State Management (2-3 giờ)
1. Tạo app_state.py
2. Migrate state variables
3. Update references

### Phase 4: Tách Services (4-6 giờ)
1. Extract từng service một
2. Test từng service
3. Update app.py references

### Phase 5: Tách UI (3-4 giờ)
1. Extract tabs
2. Extract popups
3. Extract widgets

### Phase 6: Testing & Cleanup (2-3 giờ)
1. Test toàn bộ app
2. Fix bugs
3. Documentation

## Tổng thời gian ước tính: 12-18 giờ

