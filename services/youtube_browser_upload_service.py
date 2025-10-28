"""
YouTube Browser Upload Service for Piu Application

This service handles YouTube video uploads via browser automation using Selenium.
"""

import os
import time
import logging
import shutil
from typing import Tuple, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException,
    NoSuchWindowException
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config.settings import get_config_path


# YouTube Locators (moved from Piu.py to here for reusability)
YOUTUBE_LOCATORS = {
    # --- Các locators không đổi ---
    "title": (By.XPATH, "//div[@aria-label='Thêm tiêu đề để mô tả video của bạn (nhập ký tự @ để đề cập tên một kênh)' or @aria-label='Add a title that describes your video (type @ to mention a channel)']"),
    "description": (By.XPATH, "//div[@aria-label='Giới thiệu về video của bạn cho người xem (nhập ký tự @ để đề cập tên một kênh)' or @aria-label='Tell viewers about your video (type @ to mention a channel)']"),
    "not_for_kids": (By.NAME, "VIDEO_MADE_FOR_KIDS_NOT_MFK"),
    "next_button": (By.ID, "next-button"),
    "done_button": (By.ID, "done-button"),
    "video_url_link": (By.XPATH, "//a[contains(@href, 'youtu.be/') or contains(@href, '/shorts/')]"),
    "privacy_private_radio": (By.CSS_SELECTOR, "tp-yt-paper-radio-button[name='PRIVATE']"),
    "privacy_unlisted_radio": (By.CSS_SELECTOR, "tp-yt-paper-radio-button[name='UNLISTED']"),
    "privacy_public_radio": (By.CSS_SELECTOR, "tp-yt-paper-radio-button[name='PUBLIC']"),
    "thumbnail_file_input": (By.XPATH, "//input[@id='file-loader']"),
    "tags_container": (By.ID, "tags-container"),
    "tags_input": (By.ID, "text-input"),
    "uploading_popup": (By.XPATH, "//ytcp-dialog[.//h1[contains(text(), 'Tải video lên') or contains(text(), 'Uploading video')]]"),
    "alternative_upload_popup": (By.CSS_SELECTOR, "ytcp-multi-progress-monitor"),
    "add_cards_button": (By.ID, "cards-button"),
    "cards_editor_dialog": (By.ID, "dialog"),
    "ALL_PLAYLISTS_IN_LIST": (By.XPATH, "//ytcp-entity-card"),
    "cards_editor_save_button": (By.ID, "save-button"),
    "cards_editor_save_button_ENABLED": (By.CSS_SELECTOR, "ytcp-button#save-button:not([disabled])"),
    "ENDSCREEN_VIDEO_TIMELINE_TRACK": (By.ID, "VIDEO_THUMBNAILS"),
    "RETRY_BUTTON_IN_EDITOR": (By.ID, "error-retry-button"),
    
    # --- CÁC LOCATORS ĐÃ ĐƯỢC CẬP NHẬT ĐA NGÔN NGỮ ---
    "show_more_button": (By.XPATH, "//ytcp-button[.//div[contains(text(),'Hiện thêm') or contains(text(), 'Show more')]]"),
    "CARD_TYPE_PLAYLIST": (By.XPATH, "//div[contains(@class, 'info-card-type-option-container') and .//span[contains(text(), 'Danh sách phát') or contains(text(), 'Playlist')]]"),
    "SELECTED_PLAYLIST_NAME_IN_CARD_EDITOR": (By.XPATH, "//div[@id='label-container']//div[contains(@class, 'entityName') and (contains(., 'Danh sách phát:') or contains(., 'Playlist:'))]"),
    "add_end_screen_button": (By.XPATH, "//ytcp-button[@id='endscreens-button']"),
    "endscreen_template_1vid_1sub": (By.XPATH, "//div[@aria-label='1 video, 1 đăng ký' or @aria-label='1 video, 1 subscribe']"),
    "save_button_on_main_page_ENABLED": (By.XPATH, "//ytcp-button[@id='save-button' and not(@disabled)]"),
    "DISCARD_CHANGES_BUTTON": (By.XPATH, "//ytcp-button-shape[.//div[contains(text(), 'Hủy thay đổi') or contains(text(), 'Discard changes')]]//button"),
    
    # Dialog editor End screen (đa ngôn ngữ, CHỈ khi đang mở)
    "ENDSCREEN_EDITOR_DIALOG": (By.XPATH, "//ytcp-dialog[@opened and .//h1[contains(., 'Màn hình kết thúc') or contains(., 'End screen')]]"),
    
    # Dialog editor Cards (đa ngôn ngữ, CHỈ khi đang mở)
    "CARDS_EDITOR_DIALOG": (By.XPATH, "//ytcp-dialog[@opened and .//h1[contains(., 'Thẻ') or contains(., 'Cards')]]"),
    
    # Bất kỳ dialog editor chung (fallback, CHỈ khi đang mở)
    "EDITOR_DIALOG_ANY": (By.CSS_SELECTOR, "ytcp-dialog[opened], tp-yt-paper-dialog[opened]"),
}


def click_with_fallback(driver, locator, timeout=10, human_delay_s=0.5):
    """
    Phương thức click "tối thượng" v9.8:
    1. Thay đổi: Chờ "presence" (hiện diện) thay vì "clickable" (có thể click)
       để cho phép các lớp fallback (JS) hoạt động ngay cả khi element bị che.
    2. Cuộn đến element trước khi click.
    3. Có cơ chế thử lại nhiều lớp (Click thường -> ActionChains -> JavaScript).
    4. Chống lỗi StaleElementReferenceException bằng cách thử lại.
    5. (MỚI) Trả về element sau khi click thành công.
    """
    for i in range(2):  # Thử lại tối đa 2 lần nếu gặp StaleElementReferenceException
        try:
            # === THAY ĐỔI CHÍNH: Chờ HIỆN DIỆN thay vì CÓ THỂ CLICK ===
            element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))
            # === KẾT THÚC THAY ĐỔI ===
            
            # 1. Cuộn đến element và chờ một chút
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
                time.sleep(0.3)  # Chờ một chút để giao diện ổn định sau khi cuộn
            except Exception as e_scroll:
                logging.warning(f"  -> ⚠️ Không thể cuộn đến {locator}: {e_scroll}")

            # 2. Thử các phương pháp click
            try:
                # Lớp 1: Click thường (Thử nhanh 1s, nếu bị chặn thì bỏ qua ngay)
                clickable_element = WebDriverWait(driver, 1).until(EC.element_to_be_clickable(locator))
                clickable_element.click()
                logging.info(f"  -> ✅ Lớp 1 (Click thường) thành công vào locator: {locator}")
                time.sleep(human_delay_s)
                return clickable_element  # <--- TRẢ VỀ ELEMENT
            except (ElementClickInterceptedException, TimeoutException, StaleElementReferenceException):
                logging.warning(f"  -> ⚠️ Lớp 1 (Click thường) vào {locator} bị chặn/timeout. Chuyển sang Lớp 2...")
            
            try:
                # Lớp 2: ActionChains (Dùng 'element' đã tìm thấy bằng 'presence')
                ActionChains(driver).move_to_element(element).click().perform()
                logging.info(f"  -> ✅ Lớp 2 (ActionChains) thành công vào locator: {locator}")
                time.sleep(human_delay_s)
                return element  # <--- TRẢ VỀ ELEMENT
            except Exception as e_ac:
                logging.warning(f"  -> ⚠️ Lớp 2 (ActionChains) vào {locator} thất bại ({e_ac}). Chuyển sang Lớp 3...")

            try:
                # Lớp 3: JavaScript (Dùng 'element' đã tìm thấy bằng 'presence')
                driver.execute_script("arguments[0].click();", element)
                logging.info(f"  -> ✅ Lớp 3 (JavaScript) thành công vào locator: {locator}")
                time.sleep(human_delay_s)
                return element  # <--- TRẢ VỀ ELEMENT
            except Exception as e_js:
                logging.error(f"  -> ❌ Lớp 3 (JavaScript) vào {locator} cũng thất bại! Không còn phương án nào khác.")
                raise e_js

        except StaleElementReferenceException:
            logging.warning(f"  -> Gặp StaleElementReferenceException với {locator}. Đang thử lại lần {i+1}/2...")
            if i == 1:
                logging.error(f"  -> Thử lại lần 2 vẫn gặp StaleElementReferenceException. Bỏ cuộc.")
                raise
            time.sleep(0.5)

        except Exception as e_other:
            # Đây là nơi nó bị fail (TimeoutException khi chờ 'presence' sau 10s)
            logging.error(f"  -> Lỗi không mong muốn với locator {locator}: {type(e_other).__name__} - {e_other}")
            raise e_other


def create_chrome_options(chrome_portable_exe_path: str, headless: bool, user_data_dir: str) -> Options:
    """
    Create and configure Chrome options for browser automation.
    
    Args:
        chrome_portable_exe_path: Path to Chrome portable executable
        headless: Whether to run in headless mode
        user_data_dir: Path to user data directory
        
    Returns:
        Configured ChromeOptions object
    """
    chrome_options = Options()
    chrome_options.binary_location = chrome_portable_exe_path
    
    # 1. Giả mạo User-Agent của một trình duyệt Chrome thật trên Windows
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    chrome_options.add_argument(f'user-agent={user_agent}')
    
    # 2. Các cờ để vô hiệu hóa tính năng tự động hóa mà trang web có thể phát hiện
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # Headless mode configuration
    if headless:
        logging.info("Chạy ở chế độ không đầu (headless) với kích thước cửa sổ 1920x1080.")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")  # Rất quan trọng!
    else:
        logging.info("Chạy ở chế độ có giao diện.")
    
    # Standard Chrome options
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--disable-features=RendererCodeIntegrity")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--log-level=3")
    
    prefs = {"profile.default_content_setting_values.notifications": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    os.makedirs(user_data_dir, exist_ok=True)
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    logging.info(f"Sử dụng User Data Directory: {user_data_dir}")
    
    return chrome_options


def init_chrome_driver(
    chrome_portable_exe_path: str,
    chromedriver_exe_path: str,
    headless: bool,
    max_retries: int = 3,
    retry_delay: int = 5
) -> Tuple[Optional[webdriver.Chrome], Optional[Service], str]:
    """
    Initialize Chrome WebDriver with retry logic.
    
    Args:
        chrome_portable_exe_path: Path to Chrome portable executable
        chromedriver_exe_path: Path to chromedriver executable
        headless: Whether to run in headless mode
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Tuple of (driver, service, user_data_dir) or (None, None, user_data_dir) on failure
    """
    worker_log_prefix = "[BrowserUploadWorker]"
    
    config_directory = os.path.dirname(get_config_path())
    user_data_dir_for_chrome = os.path.join(config_directory, "ChromeProfile")
    
    driver = None
    service = None
    
    for attempt in range(max_retries):
        try:
            logging.info(f"{worker_log_prefix} Đang khởi tạo WebDriver (thử lần {attempt + 1}/{max_retries})...")
            
            chrome_options = create_chrome_options(chrome_portable_exe_path, headless, user_data_dir_for_chrome)
            service = Service(chromedriver_exe_path, log_path=os.path.join(config_directory, "chromedriver.log"))
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            logging.info(f"{worker_log_prefix} WebDriver đã khởi động thành công.")
            return driver, service, user_data_dir_for_chrome
            
        except Exception as e_driver_init:
            logging.error(f"{worker_log_prefix} Lỗi khi khởi tạo WebDriver (thử lần {attempt + 1}): {e_driver_init}", exc_info=False)
            
            if os.path.exists(user_data_dir_for_chrome):
                try:
                    shutil.rmtree(user_data_dir_for_chrome)
                    logging.warning(f"{worker_log_prefix} Đã xóa thư mục User Data Directory.")
                except Exception as e_rm:
                    logging.error(f"{worker_log_prefix} Lỗi khi xóa thư mục profile: {e_rm}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    return None, None, user_data_dir_for_chrome

