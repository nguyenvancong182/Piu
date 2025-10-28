"""
Splash screen widget for Piu application.
"""

import time
import logging
import customtkinter as ctk
from PIL import Image

# Import resource_path from utils
import os
try:
    from utils.helpers import resource_path
except ImportError:
    # Fallback if not available
    def resource_path(relative_path):
        # Get the project root directory (parent of ui/widgets/)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(project_root, relative_path)


class SplashScreen(ctk.CTkToplevel):
    """
    Lớp cửa sổ màn hình chờ, hiển thị trong khi ứng dụng chính đang tải.
    ĐÃ CẬP NHẬT: Thêm nút X để đóng và bỏ qua.
    """
    def __init__(self, master):
        super().__init__(master)
        
        # LƯU THỜI GIAN BẮT ĐẦU >>>
        self.start_time = time.time()

        # --- Cấu hình cửa sổ ---
        self.lift()
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        
        splash_width = 450
        splash_height = 310
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_pos = (screen_width / 2) - (splash_width / 2)
        y_pos = (screen_height / 2) - (splash_height / 2)
        
        self.geometry(f"{splash_width}x{splash_height}+{int(x_pos)}+{int(y_pos)}")

        # --- Tạo giao diện cho màn hình chờ ---
        self.main_frame = ctk.CTkFrame(self, fg_color="#1c1c1c", corner_radius=10, border_width=1, border_color="#00FFC8") # Thêm viền để nổi bật
        self.main_frame.pack(expand=True, fill="both")

        # <<< ĐỒNG HỒ  >>>
        #self.stopwatch_label = ctk.CTkLabel(self.main_frame, text="00:00.00", font=("Consolas", 12, "bold"), text_color="gray")
        # Dùng .place() để đặt nó chính xác ở góc trên bên trái
        #self.stopwatch_label.place(x=12, y=10)
        
        # <<<--- NÚT X ĐÓNG CỬA SỔ ---<<<
        close_button = ctk.CTkButton(
            self.main_frame,
            text="✕",  # Dùng ký tự X
            width=28,
            height=28,
            font=("Segoe UI", 16),
            fg_color="transparent", # Nền trong suốt
            hover_color="#555555",
            text_color="gray",
            command=self._force_close_and_show_main_app # Gọi hàm xử lý
        )
        # Dùng .place() để đặt nút ở góc trên bên phải
        close_button.place(relx=1.0, rely=0.0, anchor='ne', x=-5, y=5)
        # >>>--- KẾT THÚC THÊM NÚT X ---<<<

        # Logo
        try:
            logo_path = resource_path("logo_Piu_resized.png")
            logo_img = ctk.CTkImage(Image.open(logo_path), size=(80, 80))
            logo_label = ctk.CTkLabel(self.main_frame, image=logo_img, text="")
            logo_label.pack(pady=(30, 10))
        except Exception as e:
            logging.error(f"Lỗi tải logo cho màn hình chờ: {e}")
            ctk.CTkLabel(self.main_frame, text="").pack(pady=(30, 10))

        # Tiêu đề "Piu"
        title_label = ctk.CTkLabel(self.main_frame, text="Piu", font=("Consolas", 60, "bold"), text_color="#EEEEEE")
        title_label.pack(pady=(0, 20))
        
        # Nhãn trạng thái
        self.status_label = ctk.CTkLabel(self.main_frame, text="Khởi động ứng dụng...", font=("Poppins", 12), text_color="gray")
        self.status_label.pack(pady=(10, 5))
        
        # Thanh tiến trình
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, mode='indeterminate', height=5)
        self.progress_bar.pack(fill="x", padx=40, pady=(0, 20))
        self.progress_bar.start()

        # Dòng bản quyền
        self.copyright_label = ctk.CTkLabel(
            self.main_frame,
            text="© 2025 Công Bạc & Piu – All rights reserved. (Stable 1.1)",
            font=("Segoe UI", 9, "italic"),
            text_color="#68e0cf"
        )
        self.copyright_label.pack(side="bottom", pady=(0, 10)) # Tăng pady dưới một chút

        #self._update_stopwatch() # Bắt đầu vòng lặp cập nhật đồng hồ

    # <<< 4 HÀM CHO CHUỖI KHỞI ĐỘNG SplashScreen ---<<<
    def _fade_transition(self, widget, start_color, end_color, steps=15, delay=20, callback=None):
        """Hàm nội bộ để tạo hiệu ứng mờ dần bằng cách thay đổi màu sắc."""
        try:
            # Chuyển đổi màu từ mã hex (nếu có) sang tuple RGB
            start_rgb = self.winfo_rgb(start_color)
            end_rgb = self.winfo_rgb(end_color)

            # Lấy giá trị R, G, B (giá trị trả về nằm trong khoảng 0-65535, cần chia cho 256)
            sr, sg, sb = start_rgb[0] // 256, start_rgb[1] // 256, start_rgb[2] // 256
            er, eg, eb = end_rgb[0] // 256, end_rgb[1] // 256, end_rgb[2] // 256
        except Exception:
            # Fallback nếu màu không hợp lệ
            sr, sg, sb = (200, 200, 200)
            er, eg, eb = (40, 40, 40)

        def update_step(step):
            if step > steps:
                if callback:
                    callback()
                return

            # Nội suy tuyến tính để tìm màu trung gian
            r = sr + (er - sr) * step / steps
            g = sg + (eg - sg) * step / steps
            b = sb + (eb - sb) * step / steps
            
            new_color = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
            
            if widget.winfo_exists():
                widget.configure(text_color=new_color)
                self.after(delay, update_step, step + 1)

        update_step(1)

    def update_status_with_fade(self, new_text):
        """Cập nhật trạng thái với hiệu ứng fade-out và fade-in."""
        if not self.status_label or not self.status_label.winfo_exists():
            return
        
        # Màu của bạn có thể khác, đây là các giá trị ước tính
        current_text_color = "#999999" # Màu "gray"
        background_color = "#1c1c1c"   # Màu nền

        def after_fade_out():
            if self.status_label.winfo_exists():
                self.status_label.configure(text=new_text)
                self._fade_transition(self.status_label, background_color, current_text_color)

        self._fade_transition(self.status_label, current_text_color, background_color, callback=after_fade_out)

    # <<<--- HÀM MỚI CHO NÚT X ---<<<
    def _force_close_and_show_main_app(self):
        """Hàm này được gọi khi nút X trên splash screen được nhấn."""
        logging.warning("Người dùng nhấn nút X trên Splash Screen để bỏ qua chờ khởi động.")
        # Gọi một hàm đặc biệt trên cửa sổ chính để xử lý
        if hasattr(self.master, '_force_show_from_splash_close'):
            self.master._force_show_from_splash_close()
        else:
            # Fallback nếu hàm trên chưa có, chỉ đóng splash screen
            logging.error("Lỗi: Không tìm thấy hàm _force_show_from_splash_close trên cửa sổ chính.")
            self.close()

    # def _update_stopwatch(self):
    #     """Cập nhật đồng hồ bấm giờ liên tục để tạo cảm giác "nhanh"."""
    #     if not (self and self.winfo_exists()):
    #         return
    #
    #     # Tính thời gian đã trôi qua
    #     elapsed_seconds = time.time() - self.start_time
    #    
    #     # <<< LOGIC ĐỊNH DẠNG THỜI GIAN >>>
    #     # Chuyển thành phút, giây, và phần trăm giây
    #     minutes = int(elapsed_seconds // 60)
    #     seconds = int(elapsed_seconds % 60)
    #     # Lấy 2 chữ số của phần thập phân (ví dụ: 1.23s -> 23)
    #     centiseconds = int((elapsed_seconds * 100) % 100) 
    #    
    #     time_string = f"{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
    #
    #     # Cập nhật label đồng hồ
    #     if hasattr(self, 'stopwatch_label') and self.stopwatch_label.winfo_exists():
    #         self.stopwatch_label.configure(text=time_string)
    #
    #     # <<< CẬP NHẬT NHANH HƠN >>>
    #     # Hẹn giờ để gọi lại chính nó sau 80ms (khoảng 12 lần/giây)
    #     self.after(80, self._update_stopwatch)

    def update_status(self, message):
        """Phương thức để cập nhật dòng trạng thái từ bên ngoài."""
        # Bây giờ nó sẽ gọi hàm fade mới của chúng ta!
        self.update_status_with_fade(message)

    def close(self):
        """Đóng và hủy màn hình chờ."""
        if self and self.winfo_exists():
            self.progress_bar.stop()
            self.destroy()

