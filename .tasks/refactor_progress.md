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
1) Tách logic License/Activation và Update Check
   - `services/licensing_service.py`: gọi `APPS_SCRIPT_URL`, timeout/retry, parse kết quả, lỗi thân thiện
   - `services/update_service.py`: kiểm tra phiên bản, lấy changelog, so sánh version
   - `Piu.py` chỉ gọi service, nhận kết quả hiển thị UI

2) Gom System utils rải rác về `utils/system_utils.py`
   - Single-instance/mutex, cleanup tiến trình con, phát hiện/resolve đường dẫn `yt-dlp`, kiểm tra GPU/CUDA

3) Tách Image generation/download
   - `services/image_service.py`: gọi DALL·E/Imagen, tải ảnh (`requests.get`), validate MIME/size
   - Trả về đường dẫn file/bytes cho UI

4) Model/Whisper management (nếu còn lẫn trong UI)
   - `services/model_service.py`: load/unload, chọn device, đo VRAM, cache model

5) UI-facade qua `application/app.py`
   - UI tabs không import service trực tiếp; gọi qua `app.services.*` để giảm coupling

6) Kiểm thử hồi quy nhanh theo kịch bản
   - Hardsub/Softsub, yt-dlp download (có/không cookies), kích hoạt/dùng thử, kiểm tra cập nhật thủ công/tự động

## Kế hoạch test nhanh sau mỗi bước
- Syntax check (đã làm)
- Chạy tính năng liên quan (manual smoke):
  - Hardsub/Softsub với file nhỏ mẫu
  - Download 1 video/1 audio bằng yt-dlp (có/không cookies)
- Kiểm tra log file `Piu_app.log` có ghi đúng và không nhân đôi handler

## Ghi chú
- Giữ nguyên `ctk.*Var` trong `application/app_state.py`; chỉ dùng dataclass cho item hàng đợi nếu cần.
- Không thay đổi UI layout/behavior; chỉ refactor tách lớp.
