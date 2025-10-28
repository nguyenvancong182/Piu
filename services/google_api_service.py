import os
import os.path
import logging
import sys
from tkinter import messagebox

try:
    import appdirs
    APPDIRS_AVAILABLE = True
except ImportError:
    APPDIRS_AVAILABLE = False
    logging.warning("Thư viện 'appdirs' không khả dụng. Token sẽ được lưu trong thư mục làm việc hiện tại.")

# Import từ Google Libraries
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import từ dự án Piu
from config.constants import (
    APP_NAME, APP_AUTHOR, TOKEN_FILENAME,
    CREDENTIALS_FILENAME, SCOPES
)
from utils.helpers import resource_path

# ============================================================
# HÀM LẤY GOOGLE API SERVICE
# (Đã di chuyển từ Piu.py)
# ============================================================
def get_google_api_service(api_name, api_version):
    """
    Xác thực với Google và xây dựng một đối tượng service cho API được yêu cầu.
    Xử lý việc tải, làm mới, và tạo token.
    """
    creds = None
    token_path = None

    if APPDIRS_AVAILABLE:
        try:
            user_data_dir_for_token = appdirs.user_data_dir(appname=APP_NAME, appauthor=APP_AUTHOR)
            os.makedirs(user_data_dir_for_token, exist_ok=True)
            token_path = os.path.join(user_data_dir_for_token, TOKEN_FILENAME)
            logging.info(f"[Auth] Sẽ sử dụng đường dẫn token (appdirs): {token_path}")
        except Exception as e_appdirs:
            logging.error(f"[Auth] Lỗi khi lấy user_data_dir từ appdirs: {e_appdirs}. Fallback về thư mục hiện tại cho token.")
            base_dir_fallback = os.getcwd()
            token_path = os.path.join(base_dir_fallback, TOKEN_FILENAME)
    else:
        logging.warning("[Auth] Thư viện 'appdirs' không khả dụng. Token sẽ được lưu trong thư mục làm việc hiện tại.")
        base_dir_fallback = os.path.dirname(os.path.abspath(__file__)) if hasattr(sys, 'frozen') and sys.frozen and hasattr(sys, '_MEIPASS') else \
                           os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
        token_path = os.path.join(base_dir_fallback, TOKEN_FILENAME)
        logging.info(f"[Auth] Sẽ sử dụng đường dẫn token (fallback): {token_path}")

    credentials_path = resource_path(CREDENTIALS_FILENAME)
    logging.info(f"[Auth] Sẽ sử dụng đường dẫn credentials: {credentials_path}")

    # 1. Tải credentials từ file token.json nếu tồn tại
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            logging.info(f"[Auth] Đã tải credentials từ: {token_path}")
        except Exception as e:
            logging.error(f"[Auth] Lỗi khi tải file token '{token_path}': {e}. Đang thử xác thực lại.")
            try:
                os.remove(token_path)
                logging.info(f"[Auth] Đã xóa file token có thể bị lỗi: {token_path}")
            except OSError as del_err: logging.error(f"[Auth] Không thể xóa file token bị lỗi '{token_path}': {del_err}")
            creds = None

    # 2. Nếu không có credentials hợp lệ
    if not creds or not creds.valid:
        # 2a. Thử làm mới token
        if creds and creds.expired and creds.refresh_token:
            try:
                logging.info("[Auth] Đang làm mới token truy cập...")
                creds.refresh(Request())
                logging.info("[Auth] Token truy cập đã được làm mới thành công.")
                try: # Lưu lại token đã làm mới
                    with open(token_path, 'w') as token_file:
                        token_file.write(creds.to_json())
                    logging.info(f"[Auth] Đã lưu token được làm mới vào: {token_path}")
                except Exception as e: logging.error(f"[Auth] Lỗi khi lưu file token được làm mới '{token_path}': {e}")
            except Exception as e:
                logging.error(f"[Auth] Lỗi khi làm mới token: {e}. Cần xác thực lại.")
                if os.path.exists(token_path):
                    try: os.remove(token_path); logging.info(f"[Auth] Đã xóa file token do lỗi làm mới: {token_path}")
                    except OSError as del_err: logging.error(f"[Auth] Không thể xóa file token sau lỗi làm mới '{token_path}': {del_err}")
                creds = None

        # 2b. Chạy luồng xác thực mới
        if not creds:
            logging.info("[Auth] Không tìm thấy credentials hợp lệ, đang khởi tạo luồng OAuth...")
            if not os.path.exists(credentials_path):
                logging.error(f"[Auth] QUAN TRỌNG: Không tìm thấy file credentials tại đường dẫn dự kiến: {credentials_path}")
                messagebox.showerror("Lỗi Credentials", f"Không tìm thấy file credentials:\n{credentials_path}\n\nVui lòng đặt file '{CREDENTIALS_FILENAME}' đúng vị trí.")
                return None

            try:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0,
                                               authorization_prompt_message="Please grant access to Google API for Piu (Sheets & YouTube):",
                                               success_message="Authentication successful! You can close this browser tab now.")
                logging.info("[Auth] Luồng OAuth hoàn tất thành công.")
                if creds:
                    try: # Lưu credentials mới
                        with open(token_path, 'w') as token_file:
                            token_file.write(creds.to_json())
                        logging.info(f"[Auth] Đã lưu token truy cập mới vào: {token_path}")
                    except Exception as e:
                        logging.error(f"[Auth] Lỗi khi lưu file token mới '{token_path}': {e}")
                        messagebox.showwarning("Lỗi Lưu Token", f"Đã xác thực thành công nhưng không thể lưu token:\n{e}\n\nBạn có thể cần cấp quyền lại lần sau.")
            except FileNotFoundError:
                logging.error(f"[Auth] Không tìm thấy file credentials '{credentials_path}' trong quá trình OAuth.")
                messagebox.showerror("Lỗi Credentials", f"Không tìm thấy file '{CREDENTIALS_FILENAME}' khi đang xác thực.")
                return None
            except Exception as e:
                logging.error(f"[Auth] Lỗi trong quá trình OAuth: {e}", exc_info=True)
                messagebox.showerror("Lỗi Xác Thực", f"Đã xảy ra lỗi trong quá trình yêu cầu quyền:\n{e}\n\nVui lòng thử lại.")
                return None

    # 3. Xây dựng và trả về service
    if creds and creds.valid:
        try:
            service = build(api_name, api_version, credentials=creds)
            logging.info(f"[Auth] Đối tượng service '{api_name} v{api_version}' đã được tạo thành công.")
            return service
        except HttpError as err:
            logging.error(f"[Auth] Đã xảy ra lỗi khi xây dựng service '{api_name}': {err}")
            messagebox.showerror("Lỗi Service API", f"Không thể khởi tạo kết nối đến Google API ({api_name}):\n{err}")
            return None
        except Exception as e:
            logging.error(f"[Auth] Lỗi không mong muốn khi xây dựng service '{api_name}': {e}", exc_info=True)
            messagebox.showerror("Lỗi Không Xác Định", f"Lỗi không mong muốn khi khởi tạo API ({api_name}):\n{e}")
            return None
    else:
        logging.error("[Auth] Không thể lấy được credentials hợp lệ sau tất cả các bước.")
        messagebox.showerror("Lỗi Xác Thực Cuối Cùng", "Không thể lấy được thông tin xác thực hợp lệ. Vui lòng kiểm tra file credentials.json và thử lại.")
        return None

