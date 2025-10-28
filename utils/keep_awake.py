"""
Keep-Awake Manager for Piu application.

Prevents system from sleeping during long-running tasks.
Works across Windows, macOS, and Linux.
"""

import os
import sys
import ctypes
import subprocess
import threading
import time
import uuid
import logging


class KeepAwakeManager:
    """
    Prevent system sleep during long-running tasks.
    - Windows: SetThreadExecutionState (renew every 30s)
    - macOS: run `caffeinate -di` in background
    - Linux: use `systemd-inhibit` if available
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._tokens = set()
        self._hb_thread = None
        self._hb_stop = threading.Event()
        self._platform = sys.platform
        self._p_inhibit = None  # Popen process for macOS/Linux

    # ===== Windows =====
    def _win_poke(self):
        """Renew Windows keep-awake state"""
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
        except Exception as e:
            logging.warning(f"[KeepAwake] WinAPI poke failed: {e}")

    def _win_clear(self):
        """Clear Windows keep-awake state"""
        try:
            ES_CONTINUOUS = 0x80000000
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception as e:
            logging.warning(f"[KeepAwake] WinAPI clear failed: {e}")

    # ===== macOS / Linux =====
    def _spawn_inhibitor_proc(self, reason: str, app_name: str = "Piu"):
        """Start system inhibitor process for macOS/Linux"""
        try:
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                # Hide window if accidentally called on Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW

            if self._platform == "darwin":
                # -d: prevent display sleep, -i: prevent idle sleep
                cmd = ["caffeinate", "-di"]
                self._p_inhibit = subprocess.Popen(cmd, startupinfo=startupinfo, creationflags=creationflags)
                logging.info("[KeepAwake] macOS caffeinate started.")
            elif self._platform.startswith("linux"):
                # Block sleep while process is alive
                cmd = ["systemd-inhibit",
                       f"--who={app_name}",
                       f"--why={reason}",
                       "--what=sleep:idle",
                       "--mode=block",
                       "bash", "-c", "while true; do sleep 3600; done"]
                self._p_inhibit = subprocess.Popen(cmd, startupinfo=startupinfo, creationflags=creationflags)
                logging.info("[KeepAwake] Linux systemd-inhibit started.")
            else:
                logging.warning("[KeepAwake] Platform not supported. Using heartbeat only.")
                self._p_inhibit = None
        except FileNotFoundError:
            logging.warning("[KeepAwake] caffeinate/systemd-inhibit not found. Please disable sleep manually.")
            self._p_inhibit = None
        except Exception as e:
            logging.warning(f"[KeepAwake] Spawn inhibitor failed: {e}")
            self._p_inhibit = None

    def _terminate_inhibitor_proc(self):
        """Stop the inhibitor process"""
        try:
            if self._p_inhibit and self._p_inhibit.poll() is None:
                self._p_inhibit.terminate()
                try:
                    self._p_inhibit.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._p_inhibit.kill()
            self._p_inhibit = None
        except Exception as e:
            logging.warning(f"[KeepAwake] Terminate inhibitor failed: {e}")
        finally:
            logging.info("[KeepAwake] Inhibitor process stopped.")

    # ===== Heartbeat thread (Windows needs periodic renewal) =====
    def _hb_loop(self):
        """Heartbeat loop for Windows"""
        logging.info("[KeepAwake] Heartbeat started.")
        while not self._hb_stop.wait(30):
            if self._platform == "win32":
                self._win_poke()
        logging.info("[KeepAwake] Heartbeat stopped.")

    def _start_heartbeat(self, reason: str, app_name: str = "Piu"):
        """Start keep-awake mechanism"""
        if self._platform == "win32":
            self._win_poke()
            self._hb_stop.clear()
            self._hb_thread = threading.Thread(target=self._hb_loop, name="KeepAwakeHeartbeat", daemon=True)
            self._hb_thread.start()
        else:
            self._spawn_inhibitor_proc(reason, app_name)

    def _stop_heartbeat(self):
        """Stop keep-awake mechanism"""
        if self._platform == "win32":
            self._hb_stop.set()
            t = self._hb_thread
            self._hb_thread = None
            if t and t.is_alive():
                t.join(timeout=1.0)
            self._win_clear()
        else:
            self._terminate_inhibitor_proc()

    # ===== Public API =====
    def acquire(self, reason: str = "Processing", app_name: str = "Piu"):
        """
        Acquire keep-awake token.
        
        Args:
            reason: Reason for keeping awake
            app_name: Application name for inhibitor
            
        Returns:
            Token string to use for release
        """
        token = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
        with self._lock:
            prev = len(self._tokens)
            self._tokens.add(token)
            if prev == 0:
                logging.info(f"[KeepAwake] ON ({reason})")
                self._start_heartbeat(reason, app_name)
        return token

    def release(self, token):
        """
        Release keep-awake token.
        
        Args:
            token: Token returned from acquire()
        """
        if not token:
            return
        with self._lock:
            self._tokens.discard(token)
            if not self._tokens:
                logging.info("[KeepAwake] OFF")
                self._stop_heartbeat()

    def force_off(self):
        """Force turn off keep-awake"""
        with self._lock:
            self._tokens.clear()
            self._stop_heartbeat()


# Context manager function will be imported from Piu.py globally
# Global instance is created in Piu.py

