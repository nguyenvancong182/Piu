"""
API Settings Window for Piu Application.

A popup window for managing API keys (OpenAI, Google Cloud, Gemini).
"""

import os
import json
import logging
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ui.widgets.menu_utils import textbox_right_click_menu


# Import optional libraries
try:
    from openai import OpenAI, RateLimitError, AuthenticationError, APIConnectionError, APIStatusError, APITimeoutError
    HAS_OPENAI_LIBS = True
except ImportError:
    HAS_OPENAI_LIBS = False

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_api_exceptions
    HAS_GEMINI_LIBS = True
except ImportError:
    HAS_GEMINI_LIBS = False

try:
    from google.cloud import translate_v2 as google_translate
    from google.oauth2 import service_account
    HAS_GOOGLE_CLOUD_TRANSLATE = True
except ImportError:
    HAS_GOOGLE_CLOUD_TRANSLATE = False
    service_account = None
    google_translate = None


class APISettingsWindow(ctk.CTkToplevel):

# Hàm khởi tạo cửa sổ cài đặt API Keys
    def __init__(self, master, openai_var, google_var, gemini_var): # Sửa lại dòng này
        super().__init__(master)
        self.master_app = master 
        self.openai_key_var = openai_var
        self.google_key_path_var = google_var
        self.gemini_key_var = gemini_var 
        self.dub_batch_had_api_key_errors = False # Cờ theo dõi lỗi API key

        self.title("🔑 Cài đặt API Keys")
        self.geometry("550x450") 
        self.resizable(False, False)
        self.attributes("-topmost", True) 
        self.grab_set() 

        try: # Căn giữa cửa sổ
            master.update_idletasks()
            self.update_idletasks()
            x = master.winfo_x() + (master.winfo_width() // 2) - (550 // 2)
            y = master.winfo_y() + (master.winfo_height() // 2) - (380 // 2) 
            self.geometry(f"+{x}+{y}")
        except Exception as e:
            logging.warning(f"Không thể căn giữa cửa sổ cài đặt API: {e}")

        # --- Frame chính --- (Giữ nguyên)
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=15, pady=15)

        # === KHỐI CODE MỚI CHO OPENAI VÀ GOOGLE KEY - LAYOUT MỚI ===

        # --- Phần Google Cloud Key File ---
        google_frame = ctk.CTkFrame(main_frame) 
        google_frame.pack(fill="x", pady=(0, 10))

        # Cấu hình cột tương tự OpenAI
        google_frame.grid_columnconfigure(0, weight=0, minsize=120) 
        google_frame.grid_columnconfigure(1, weight=1)             
        google_frame.grid_columnconfigure(2, weight=0, minsize=130)

        # --- Hàng 0: Chỉ có Label chính ---
        ctk.CTkLabel(google_frame, text="Google Cloud Key File:", anchor="w").grid(row=0, column=0, padx=(10, 5), pady=(5,0), sticky="w")

        # --- Hàng 1: Label đường dẫn và Nút Chọn File ---
        self.google_path_label = ctk.CTkLabel(google_frame, textvariable=self.google_key_path_var, anchor="w", 
                                              text_color="gray", wraplength=350, 
                                              justify=ctk.LEFT, font=("Segoe UI", 10)) 
        # Đặt path label vào cột 0 và 1
        self.google_path_label.grid(row=1, column=0, columnspan=2, padx=(10, 5), pady=(2, 5), sticky="ew") 

        google_select_button = ctk.CTkButton(google_frame, text="Chọn File JSON...", width=120, command=self._select_google_key_file)
        # Đặt nút chọn file vào cột 2, hàng 1
        google_select_button.grid(row=1, column=2, padx=(0, 10), pady=(2, 5), sticky="e") 

        # --- Hàng 2: Nhãn trạng thái và Nút Kiểm tra ---
        self.google_status_label = ctk.CTkLabel(google_frame, text="", font=("Segoe UI", 10), text_color="gray", justify=ctk.LEFT) 
        # Đặt status vào cột 0, hàng 2, căn trái
        self.google_status_label.grid(row=2, column=0, columnspan=2, padx=(10, 5), pady=(0, 10), sticky="w")

        self.google_test_button = ctk.CTkButton(google_frame, text="Kiểm tra File Key", width=120, command=self._test_google_key) 
        # Đặt nút kiểm tra vào cột 2, hàng 2
        self.google_test_button.grid(row=2, column=2, padx=(0, 10), pady=(0, 10), sticky="e") 

        # Cập nhật text ban đầu cho label đường dẫn Google
        initial_google_path = self.google_key_path_var.get()
        self.google_path_label.configure(text=initial_google_path if initial_google_path else "(Chưa chọn file)")
        if hasattr(self.google_key_path_var, 'trace_add'): 
             self.google_key_path_var.trace_add("write", self._update_google_label)

        # --- Phần Gemini API Key --- (Thêm khối code này vào)
        gemini_frame = ctk.CTkFrame(main_frame)
        gemini_frame.pack(fill="x", pady=(10, 5)) # Thêm pady trên để có khoảng cách

        gemini_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(gemini_frame, text="Gemini API Key:", anchor="w").grid(row=0, column=0, padx=(10, 5), pady=(5,0), sticky="w")

        self.gemini_entry = ctk.CTkEntry(gemini_frame, textvariable=self.gemini_key_var, show="*")
        self.gemini_entry.grid(row=1, column=0, columnspan=2, padx=(10, 5), pady=(2,5), sticky="ew")
        self.gemini_entry.bind("<Button-3>", textbox_right_click_menu)

        # Nút kiểm tra sẽ được thêm logic sau
        self.gemini_test_button = ctk.CTkButton(gemini_frame, text="Kiểm tra", width=120, command=self._test_gemini_key) 
        self.gemini_test_button.grid(row=1, column=2, padx=(0, 10), pady=(2,5), sticky="e")

        self.gemini_status_label = ctk.CTkLabel(gemini_frame, text="", font=("Segoe UI", 10), text_color="gray")
        self.gemini_status_label.grid(row=2, column=0, columnspan=3, padx=(10, 5), pady=(0, 10), sticky="w")

        # --- Phần OpenAI API Key ---
        openai_frame = ctk.CTkFrame(main_frame) 
        openai_frame.pack(fill="x", pady=(0, 15)) 

        # Cấu hình cột: Cột 0 (Label chính/Status), Cột 1 (Entry - giãn), Cột 2 (Nút Test)
        openai_frame.grid_columnconfigure(0, weight=0, minsize=120) 
        openai_frame.grid_columnconfigure(1, weight=1)             
        openai_frame.grid_columnconfigure(2, weight=0, minsize=130) 

        # --- Hàng 0: Chỉ có Label chính ---
        ctk.CTkLabel(openai_frame, text="OpenAI API Key:", anchor="w").grid(row=0, column=0, padx=(10, 5), pady=(5,0), sticky="w")

        # --- Hàng 1: Ô nhập Key và Nút Kiểm tra ---
        self.openai_entry = ctk.CTkEntry(openai_frame, textvariable=self.openai_key_var, show="*") 
        self.openai_entry.grid(row=1, column=0, columnspan=2, padx=(10, 5), pady=(2,5), sticky="ew") # Chiếm cột 0 và 1
        self.openai_entry.bind("<Button-3>", textbox_right_click_menu)
        
        self.openai_test_button = ctk.CTkButton(openai_frame, text="Kiểm tra", width=120, command=self._test_openai_key) 
        self.openai_test_button.grid(row=1, column=2, padx=(0, 10), pady=(2,5), sticky="e") # Ở cột 2 cùng hàng

        # --- Hàng 2: Chỉ có Nhãn trạng thái ---
        self.openai_status_label = ctk.CTkLabel(openai_frame, text="", font=("Segoe UI", 10), text_color="gray", justify=ctk.LEFT)
        # Đặt status vào cột 0, hàng 2, căn trái
        self.openai_status_label.grid(row=2, column=0, columnspan=3, padx=(10, 5), pady=(0, 10), sticky="w") 

 
        # --- Khung Nút Lưu / Hủy --- 
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(side="bottom", fill="x", pady=(15, 0)) 

        cancel_button = ctk.CTkButton(button_frame, text="Hủy", width=100, command=self.destroy)
        cancel_button.pack(side="right", padx=(10, 0))

        save_button = ctk.CTkButton(button_frame, text="Lưu Cài Đặt", width=120, command=self._save_settings, fg_color="#1f6aa5")
        save_button.pack(side="right")


# Xử lý sự kiện nhấn nút "Kiểm tra" cho OpenAI API Key.
    def _test_openai_key(self):
        """ Bắt đầu kiểm tra OpenAI API Key trong một luồng riêng. """
        current_key = self.openai_key_var.get().strip()
        if not current_key:
            self.openai_status_label.configure(text="Vui lòng nhập API Key.", text_color="orange")
            return

        # Vô hiệu hóa nút kiểm tra và hiển thị trạng thái "Đang kiểm tra..."
        self.openai_test_button.configure(state=ctk.DISABLED, text="...")
        self.openai_status_label.configure(text="Đang kiểm tra OpenAI Key...", text_color="gray")
        self.update_idletasks() # Cập nhật giao diện ngay

        # Chạy kiểm tra trong thread
        thread = threading.Thread(target=self._perform_openai_key_check, args=(current_key,), daemon=True, name="OpenAIKeyCheckThread")
        thread.start()


# Thực hiện kiểm tra tính hợp lệ của OpenAI API Key (chạy trong luồng).
    def _perform_openai_key_check(self, api_key_to_test):
        """ 
        Thực hiện kiểm tra OpenAI API Key (chạy trong thread) - BẢN NÂNG CẤP
        Bằng cách thử một yêu cầu chat completion nhỏ.
        """
        logging.info(f"[API Check] Bắt đầu kiểm tra OpenAI Key (bản nâng cấp): ...{api_key_to_test[-4:]}")
        status_message = "Lỗi không xác định."
        status_color = "red"
        
        try:
            from openai import OpenAI, RateLimitError, AuthenticationError, APIConnectionError, APIStatusError, APITimeoutError
            HAS_OPENAI_LIBS_FOR_CHECK = True
        except ImportError:
            logging.error("[API Check] Thiếu thư viện OpenAI để kiểm tra key.")
            status_message = "Lỗi: Thiếu thư viện OpenAI."
            status_color = "red"
            HAS_OPENAI_LIBS_FOR_CHECK = False

        if HAS_OPENAI_LIBS_FOR_CHECK:
            try:
                test_client = OpenAI(api_key=api_key_to_test, timeout=15.0) 
                
                # --- THAY ĐỔI CHÍNH NẰM Ở ĐÂY ---
                # Thay vì gọi client.models.list(), ta thử một yêu cầu chat nhỏ
                # để đảm bảo key không chỉ hợp lệ mà còn có quyền sử dụng model.
                logging.debug("[API Check] Đang gọi client.chat.completions.create() để kiểm tra...")
                test_client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Dùng model rẻ và nhanh để test
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,          # Giới hạn output tối đa để tiết kiệm
                    temperature=0          # Không cần sáng tạo
                )
                # --- KẾT THÚC THAY ĐỔI ---

                logging.info(f"[API Check] Kiểm tra OpenAI Key thành công (đã thử Chat Completion).")
                status_message = "Key hợp lệ! (Kết nối thành công)"
                status_color = ("#0B8457", "lightgreen") # Xanh đậm cho nền sáng, xanh tươi cho nền tối

            except AuthenticationError as e:
                logging.warning(f"[API Check] Lỗi xác thực OpenAI: {e}")
                status_message = "Lỗi: Key không đúng hoặc hết hạn."
                status_color = "orange"
            except RateLimitError as e:
                logging.warning(f"[API Check] Lỗi giới hạn yêu cầu OpenAI: {e}")
                status_message = "Lỗi: Vượt quá giới hạn request."
                status_color = "orange"
            except (APIConnectionError, APITimeoutError) as e:
                logging.error(f"[API Check] Lỗi kết nối/timeout OpenAI: {e}")
                status_message = "Lỗi: Không kết nối được OpenAI."
                status_color = "red"
            except APIStatusError as e: 
                logging.error(f"[API Check] Lỗi trạng thái API OpenAI: {e.status_code} - {e.response}")
                # Kiểm tra lỗi cụ thể do không có quyền truy cập model
                if "does not exist or you do not have access to it" in str(e).lower():
                    status_message = f"Lỗi: Key đúng, nhưng không có quyền truy cập model."
                    status_color = "orange"
                else:
                    status_message = f"Lỗi API OpenAI: {e.status_code}"
                    status_color = "red"
            except Exception as e: 
                logging.error(f"[API Check] Lỗi không xác định khi kiểm tra OpenAI Key: {e}", exc_info=True)
                status_message = "Lỗi không xác định."
                status_color = "red"

        def _update_ui():
            try:
                if self and self.winfo_exists(): 
                    self.openai_status_label.configure(text=status_message, text_color=status_color)
                    self.openai_test_button.configure(state=ctk.NORMAL, text="Kiểm tra") 
            except Exception as e_ui:
                logging.error(f"Lỗi cập nhật UI sau khi kiểm tra OpenAI Key: {e_ui}")

        if hasattr(self, 'master_app') and self.master_app and hasattr(self.master_app, 'after'):
             self.master_app.after(0, _update_ui)
        elif hasattr(self, 'after'):
             self.after(0, _update_ui)


# HÀM MỚI: Bắt đầu kiểm tra Gemini Key trong luồng nền
    def _test_gemini_key(self):
        """ Bắt đầu kiểm tra Gemini API Key trong một luồng riêng. """
        current_key = self.gemini_key_var.get().strip()
        if not current_key:
            self.gemini_status_label.configure(text="Vui lòng nhập API Key.", text_color="orange")
            return

        self.gemini_test_button.configure(state=ctk.DISABLED, text="...")
        self.gemini_status_label.configure(text="Đang kiểm tra Gemini Key...", text_color="gray")
        self.update_idletasks()

        thread = threading.Thread(target=self._perform_gemini_key_check, args=(current_key,), daemon=True, name="GeminiKeyCheckThread")
        thread.start()

# HÀM MỚI: Thực hiện kiểm tra tính hợp lệ của Gemini API Key (chạy trong luồng)
    def _perform_gemini_key_check(self, api_key_to_test):
        """ 
        Thực hiện kiểm tra Gemini API Key (chạy trong thread).
        PHIÊN BẢN NÂNG CẤP: Thử một lệnh generate_content nhỏ để kiểm tra sâu hơn.
        """
        logging.info(f"[API Check] Bắt đầu kiểm tra Gemini Key (bản nâng cấp): ...{api_key_to_test[-4:]}")
        status_message = "Lỗi không xác định."
        status_color = "red"

        try:
            import google.generativeai as genai
            from google.api_core import exceptions as google_api_exceptions

            genai.configure(api_key=api_key_to_test)

            logging.debug("[API Check] Đang thử tạo model và generate_content('test')...")
            
            # Khởi tạo model
            model = genai.GenerativeModel('gemini-1.5-pro-latest')
            
            # Thử gửi một yêu cầu generate_content cực nhỏ và vô hại.
            # Đây là bài kiểm tra thực tế hơn nhiều so với list_models().
            model.generate_content(
                "test", 
                generation_config=genai.types.GenerationConfig(max_output_tokens=1, temperature=0.0)
            )

            # Nếu dòng trên không gây lỗi, key và môi trường đều ổn.
            status_message = "Key hợp lệ! (Kết nối thành công)"
            status_color = ("#0B8457", "lightgreen") # Xanh đậm cho nền sáng, xanh tươi cho nền tối
            logging.info(f"[API Check] Kiểm tra Gemini Key thành công (bản nâng cấp).")

        except google_api_exceptions.PermissionDenied as e:
            logging.warning(f"[API Check] Lỗi xác thực Gemini: {e}")
            status_message = "Lỗi: Key không đúng hoặc không có quyền."
            status_color = "orange"
        except google_api_exceptions.GoogleAPICallError as e:
            # Lỗi này có thể do mạng hoặc các vấn đề kết nối khác
            logging.error(f"[API Check] Lỗi gọi API Google (có thể do mạng): {e}")
            status_message = "Lỗi: Không kết nối được tới Google."
            status_color = "red"
        except Exception as e:
            # Bắt tất cả các lỗi khác, bao gồm cả "Illegal header value" nếu nó xảy ra ở đây
            logging.error(f"[API Check] Lỗi không xác định khi kiểm tra Gemini Key: {e}", exc_info=True)
            # Kiểm tra xem có phải lỗi header không để đưa ra thông báo cụ thể
            if "illegal header value" in str(e).lower():
                status_message = "Lỗi: Key có vẻ đúng nhưng môi trường không hợp lệ (lỗi header)."
            else:
                status_message = f"Lỗi không xác định: {type(e).__name__}"
            status_color = "red"

        def _update_ui():
            if self and self.winfo_exists():
                self.gemini_status_label.configure(text=status_message, text_color=status_color)
                self.gemini_test_button.configure(state=ctk.NORMAL, text="Kiểm tra")

        if hasattr(self.master_app, 'after'):
             self.master_app.after(0, _update_ui)



# Xử lý sự kiện nhấn nút "Kiểm tra File Key" cho Google Cloud.
    def _test_google_key(self):
        """ Bắt đầu kiểm tra file Google Cloud Key trong một luồng riêng. """
        current_path = self.google_key_path_var.get().strip()
        if not current_path:
            self.google_status_label.configure(text="Vui lòng chọn file key JSON.", text_color="orange")
            return
        if not os.path.exists(current_path):
            self.google_status_label.configure(text="Lỗi: File key không tồn tại.", text_color="red")
            return
        if not current_path.lower().endswith(".json"):
             self.google_status_label.configure(text="Lỗi: File phải là định dạng .json.", text_color="red")
             return

        # Vô hiệu hóa nút kiểm tra và hiển thị trạng thái "Đang kiểm tra..."
        self.google_test_button.configure(state=ctk.DISABLED, text="...")
        self.google_status_label.configure(text="Đang kiểm tra Google Key File...", text_color="gray")
        self.update_idletasks() # Cập nhật giao diện ngay

        # Chạy kiểm tra trong thread
        thread = threading.Thread(target=self._perform_google_key_check, args=(current_path,), daemon=True, name="GoogleKeyCheckThread")
        thread.start()


# Thực hiện kiểm tra tính hợp lệ của file JSON Key Google Cloud (chạy trong luồng).
    def _perform_google_key_check(self, key_file_path):
        """ Thực hiện kiểm tra file Google Cloud Key (chạy trong thread). """
        logging.info(f"[API Check] Bắt đầu kiểm tra Google Key File: {key_file_path}")
        status_message = "Lỗi không xác định."
        status_color = "red"
        
        if not HAS_GOOGLE_CLOUD_TRANSLATE or service_account is None or google_translate is None:
            logging.error("[API Check] Thiếu thư viện Google Cloud hoặc Translate để kiểm tra key.")
            status_message = "Lỗi: Thiếu thư viện Google Cloud."
            status_color = "red"
        else:
            try:
                logging.debug(f"[API Check] Đang tải credentials từ: {key_file_path}")
                credentials = service_account.Credentials.from_service_account_file(key_file_path)
                logging.debug(f"[API Check] Tải credentials thành công. Project ID: {credentials.project_id}")

                logging.debug(f"[API Check] Đang khởi tạo Google Translate Client...")
                test_client = google_translate.Client(credentials=credentials)
                
                try:
                    logging.debug(f"[API Check] Đang thử dịch 'test' sang 'en'...")
                    test_client.translate("test", target_language="en") 
                    logging.info(f"[API Check] Kiểm tra Google Key File thành công (đã thử dịch).")
                    status_message = "File key hợp lệ! (Đã thử dịch)"
                    # SỬA Ở ĐÂY: Dùng cặp màu thay vì "lightgreen"
                    status_color = ("#0B8457", "lightgreen") # Xanh đậm cho nền sáng, xanh tươi cho nền tối
                except HttpError as http_err: 
                     error_content = getattr(http_err, 'content', b'').decode('utf-8', 'replace')
                     logging.warning(f"[API Check] Lỗi HttpError khi thử dịch: {http_err.resp.status} - {error_content}")
                     status_message = f"Lỗi API Google ({http_err.resp.status}). Có thể API chưa bật?"
                     status_color = "orange"
                     try:
                         error_json = json.loads(error_content)
                         error_detail = error_json.get('error', {}).get('message', '')
                         if error_detail: status_message += f"\nChi tiết: {error_detail[:100]}..."
                     except: pass
                except Exception as trans_err:
                    logging.warning(f"[API Check] Lỗi khi thử dịch với Google Key: {trans_err}", exc_info=True)
                    status_message = "File key đúng, nhưng lỗi khi thử dịch."
                    status_color = "orange"

            except FileNotFoundError:
                logging.error(f"[API Check] Lỗi không tìm thấy file key: {key_file_path}")
                status_message = "Lỗi: File key không tồn tại."
                status_color = "red"
            except ValueError as ve: 
                logging.error(f"[API Check] Lỗi định dạng file Google Key JSON: {ve}")
                status_message = "Lỗi: Định dạng file key không hợp lệ."
                status_color = "red"
            except Exception as e:
                logging.error(f"[API Check] Lỗi không xác định khi kiểm tra Google Key: {e}", exc_info=True)
                status_message = "Lỗi không xác định khi kiểm tra."
                status_color = "red"

        def _update_ui_google():
            try:
                if self and self.winfo_exists(): 
                    self.google_status_label.configure(text=status_message, text_color=status_color)
                    self.google_test_button.configure(state=ctk.NORMAL, text="Kiểm tra File Key") 
            except Exception as e_ui:
                logging.error(f"Lỗi cập nhật UI sau khi kiểm tra Google Key: {e_ui}")

        if hasattr(self, 'master_app') and self.master_app and hasattr(self.master_app, 'after'):
             self.master_app.after(0, _update_ui_google)
        elif hasattr(self, 'after'): 
             self.after(0, _update_ui_google)


# Hàm hành động (API Settings): Chọn file JSON key của Google Cloud
    def _select_google_key_file(self):
        """ Mở dialog chọn file JSON key của Google """
        initial_dir = os.path.dirname(self.google_key_path_var.get()) if self.google_key_path_var.get() else "/"
        filepath = filedialog.askopenfilename(
            title="Chọn file JSON Key của Google Service Account",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self # Đảm bảo dialog mở trên cửa sổ này
        )
        if filepath and os.path.exists(filepath) and filepath.lower().endswith(".json"):
            self.google_key_path_var.set(filepath)
            logging.info(f"Đã chọn file Google Key: {filepath}")
        elif filepath:
            messagebox.showerror("File không hợp lệ", "Vui lòng chọn một file .json hợp lệ.", parent=self)


     # Callback cập nhật label hiển thị đường dẫn file Google Key khi biến thay đổi.
    def _update_google_label(self, *args):
        """ Cập nhật label hiển thị đường dẫn file Google Key """
        path = self.google_key_path_var.get()
        if self.google_path_label and self.google_path_label.winfo_exists():
             self.google_path_label.configure(text=path if path else "(Chưa chọn file)")


# Lưu các cài đặt API (bằng cách gọi hàm lưu của app chính) và đóng cửa sổ.
    def _save_settings(self):
        """Lưu cấu hình API + làm tươi UI ngay, KHÔNG ghi đè giá trị người dùng vừa nhập."""
        logging.info("Lưu cài đặt API Keys...")
        try:
            if not (self.master_app and callable(getattr(self.master_app, 'save_current_config', None))):
                logging.error("Không thể gọi save_current_config từ cửa sổ cài đặt.")
                return

            # 1) ĐẨY GIÁ TRỊ TỪ POPUP -> MAIN APP (nếu popup giữ StringVar riêng)
            try:
                if hasattr(self, 'openai_key_var') and hasattr(self.master_app, 'openai_key_var'):
                    self.master_app.openai_key_var.set(self.openai_key_var.get().strip())
                if hasattr(self, 'gemini_key_var') and hasattr(self.master_app, 'gemini_key_var'):
                    self.master_app.gemini_key_var.set(self.gemini_key_var.get().strip())
                if hasattr(self, 'google_key_path_var') and hasattr(self.master_app, 'google_key_path_var'):
                    self.master_app.google_key_path_var.set(self.google_key_path_var.get().strip())
            except Exception as e_sync:
                logging.debug(f"Sync popup->main StringVar lỗi (bỏ qua): {e_sync}")

            # 2) LƯU CONFIG
            self.master_app.save_current_config()
            logging.info("Đã gọi save_current_config từ cửa sổ chính.")

            # 3) THÔNG BÁO + (tuỳ chọn) re-check license
            if hasattr(self.master_app, 'update_status'):
                self.master_app.after(10, lambda: self.master_app.update_status("✅ Các cài đặt API đã được lưu."))
            if hasattr(self.master_app, 'check_activation_status'):
                logging.info("APISettings: Yêu cầu kiểm tra lại bản quyền sau khi lưu API keys.")
                self.master_app.after(3000, self.master_app.check_activation_status)

            # 4) REFRESH UI CÁC TAB NGAY (khỏi cần đổi tab)
            for fn_name in ("_set_dubbing_tab_ui_state",
                            "_update_dub_script_controls_state",
                            "_set_subtitle_tab_ui_state"):   # 👈 thêm dòng này cho tab Sub
                try:
                    fn = getattr(self.master_app, fn_name, None)
                    if callable(fn):
                        self.master_app.after(0, fn)
                except Exception as e_ref:
                    logging.debug(f"Refresh '{fn_name}' after save failed: {e_ref}")

        except Exception as e:
            logging.error(f"Lỗi khi gọi save_current_config: {e}")
            return
        finally:
            # 5) Đóng popup
            try:
                self.destroy()
            except Exception:
                pass

