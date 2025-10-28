"""
Logging utilities for Piu application.

This module handles logging configuration and setup.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from config.constants import LOG_FILENAME


def setup_logging():
    """Configure logging for Piu application."""
    fmt = "%(asctime)s - %(levelname)s - [%(threadName)s:%(funcName)s] - %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    log_formatter = logging.Formatter(fmt, datefmt=datefmt)

    root_logger = logging.getLogger()

    # Nếu đã init trước đó thì bỏ qua (tránh add handler 2 lần)
    if getattr(root_logger, "_piu_logging_initialized", False):
        return

    # Xoá sạch handler cũ để khỏi in đôi
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass

    root_logger.setLevel(logging.INFO)  # đổi DEBUG khi cần

    # Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(log_formatter)
    root_logger.addHandler(ch)

    # File (xoay vòng)
    try:
        base_path_for_log = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
                            else os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(base_path_for_log, LOG_FILENAME)
        fh = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=2, encoding="utf-8")
        fh.setFormatter(log_formatter)
        root_logger.addHandler(fh)
        logging.info(f"--- GHI LOG VÀO FILE '{log_file_path}' ĐÃ KÍCH HOẠT ---")
    except Exception as e:
        logging.warning(f"Không thể tạo file log: {e}")

    # Giảm ồn third-party
    logging.getLogger("gtts").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Đánh dấu đã init
    root_logger._piu_logging_initialized = True


def log_failed_task(failed_item_identifier):
    """
    Log a failed task to a dedicated log file (Piu_failed_tasks.log).
    
    Args:
        failed_item_identifier: Identifier of the failed task
    """
    log_prefix = "[FailedTaskLogger]"
    try:
        # Determine log file path (same directory as Piu_app.log)
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        failed_log_path = os.path.join(base_path, "Piu_failed_tasks.log")

        # Write to log file
        with open(failed_log_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {failed_item_identifier}\n")
        
        logging.info(f"{log_prefix} Đã ghi lại tác vụ lỗi '{failed_item_identifier}' vào file: {failed_log_path}")

    except Exception as e:
        logging.error(f"{log_prefix} Lỗi nghiêm trọng khi ghi log cho tác vụ lỗi: {e}", exc_info=True)

