"""
Piu - Main entry point

File dự kiến sẽ thay thế dần Piu.py. Tạm thời chỉ chuẩn hóa logging.
"""

from utils.logging_utils import setup_logging


def bootstrap_logging_once() -> None:
    """Khởi tạo logging tập trung (idempotent)."""
    setup_logging()


# Khởi tạo logging ngay khi import main (an toàn vì idempotent)
bootstrap_logging_once()
