"""
FFmpeg service: running ffmpeg commands with logging, timeouts, and integration hooks.

This service centralizes execution of FFmpeg commands so core/UI code doesn't manage
subprocess details directly.
"""

import logging
import subprocess
import sys
from typing import Callable, Optional, Sequence, Tuple

from utils.ffmpeg_utils import find_ffmpeg


def run_ffmpeg_command(
    cmd_params: Sequence[str],
    process_name: str = "FFmpeg",
    stop_event: Optional[object] = None,
    set_current_process: Optional[Callable[[subprocess.Popen], None]] = None,
    clear_current_process: Optional[Callable[[], None]] = None,
    timeout_seconds: int = 1800,
) -> Tuple[int, str, str]:
    """
    Execute FFmpeg with provided parameters.

    Args:
        cmd_params: FFmpeg arguments (excluding executable)
        process_name: Label for logging
        stop_event: Optional threading.Event-like object with is_set()
        set_current_process: Optional callback to expose the spawned Popen
        clear_current_process: Optional callback to clear current process reference
        timeout_seconds: Max time to wait for ffmpeg to complete

    Returns:
        (return_code, stdout, stderr)

    Raises:
        RuntimeError on missing ffmpeg or non-zero return codes/timeouts
    """
    ffmpeg_executable = find_ffmpeg()
    if not ffmpeg_executable:
        error_msg = (
            "Không tìm thấy file thực thi FFmpeg. Vui lòng cài đặt hoặc đảm bảo nó có trong PATH / đi kèm."
        )
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    full_cmd = [ffmpeg_executable] + list(cmd_params)
    log_cmd = subprocess.list2cmdline(full_cmd)
    logging.info(f"Đang chạy {process_name}: {log_cmd}")

    proc_local_ref = None
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        proc_local_ref = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=creationflags,
        )
        if set_current_process:
            try:
                set_current_process(proc_local_ref)
            except Exception:
                # Non-fatal; continue
                logging.debug("set_current_process callback raised, continuing.")

        logging.info(f"[{process_name}] Tiến trình FFmpeg (PID: {proc_local_ref.pid}) đã bắt đầu.")

        try:
            stdout_data, stderr_data = proc_local_ref.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            logging.error(f"[{process_name}] FFmpeg (PID: {proc_local_ref.pid}) bị timeout. Đang thử kill...")
            proc_local_ref.kill()
            stdout_data, stderr_data = proc_local_ref.communicate()
            raise RuntimeError(f"{process_name} bị timeout.")

        return_code = proc_local_ref.returncode

        if stop_event is not None and getattr(stop_event, "is_set", None):
            try:
                if stop_event.is_set():
                    logging.warning(
                        f"[{process_name}] Phát hiện stop_event SAU KHI FFmpeg (PID: {proc_local_ref.pid}) chạy xong. Coi như bị dừng."
                    )
                    raise InterruptedError(
                        f"{process_name} bị dừng bởi người dùng (phát hiện sau khi FFmpeg kết thúc)."
                    )
            except Exception:
                # If stop_event is not a proper Event, ignore
                pass

        if return_code != 0:
            logging.error(f"[{process_name}] FFmpeg (PID: {proc_local_ref.pid}) thất bại với mã {return_code}:")
            logging.error(f"  Lệnh: {log_cmd}")
            logging.error(f"  Stderr: {stderr_data[-1500:]}")
            raise RuntimeError(
                f"{process_name} thất bại. Kiểm tra log để biết chi tiết. Đoạn Stderr: {stderr_data[-200:]}"
            )

        logging.info(f"[{process_name}] FFmpeg (PID: {proc_local_ref.pid}) hoàn thành thành công (mã {return_code}).")
        return return_code, stdout_data or "", stderr_data or ""

    except FileNotFoundError:
        logging.error(f"Không tìm thấy file thực thi FFmpeg trong lệnh: {full_cmd[0]}")
        raise RuntimeError(f"Không thể thực thi FFmpeg tại '{full_cmd[0]}'.")
    finally:
        if clear_current_process:
            try:
                clear_current_process()
            except Exception:
                logging.debug("clear_current_process callback raised, continuing.")

