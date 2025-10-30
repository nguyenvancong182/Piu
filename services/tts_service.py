"""
TTS Service for voice discovery and caching.

Phase 1 goals:
- Provide a simple, dependency-light API to fetch Google Cloud TTS voices
- Support cache file usage with freshness TTL to avoid frequent API calls

Notes:
- This service does NOT perform synthesis; only discovers voices and maps
  voice_id -> display_name, with grouping left to caller if desired.
"""

from __future__ import annotations

import os
import json
import time
import logging
from typing import Dict, Optional, Tuple

try:
    # Lazy import; we only need google packages when a valid key is provided
    from google.cloud import texttospeech as gtts  # type: ignore
    HAS_GOOGLE = True
except Exception:
    HAS_GOOGLE = False


DEFAULT_CACHE_FILENAME = "google_tts_voices_cache.json"
DEFAULT_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


class TTSService:
    """Service to fetch and cache TTS voices."""

    def __init__(
        self,
        cache_dir: str = ".",
        cache_filename: str = DEFAULT_CACHE_FILENAME,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        self.logger = logging.getLogger("PiuApp")
        self.cache_dir = cache_dir
        self.cache_filename = cache_filename
        self.cache_ttl_seconds = cache_ttl_seconds

    # ---------------------- Cache Helpers ----------------------
    def _get_cache_path(self) -> str:
        return os.path.join(self.cache_dir, self.cache_filename)

    def _is_cache_fresh(self, path: str) -> bool:
        try:
            if not os.path.exists(path):
                return False
            mtime = os.path.getmtime(path)
            return (time.time() - mtime) < self.cache_ttl_seconds
        except Exception:
            return False

    def _read_cache(self) -> Optional[Dict[str, str]]:
        path = self._get_cache_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            return None
        return None

    def _write_cache(self, voices: Dict[str, str]) -> None:
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            path = self._get_cache_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(voices, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"[TTSService] Failed to write cache: {e}")

    # ---------------------- Public API ----------------------
    def get_google_voices(
        self,
        key_json_path: Optional[str],
        prefer_cache: bool = True,
    ) -> Tuple[Dict[str, str], str]:
        """
        Return mapping: voice_id -> display_name.

        Args:
            key_json_path: Path to Google service account JSON.
            prefer_cache: If True and cache is fresh, use it.

        Returns:
            (voices_map, source):
              voices_map: {voice_id: display_name}
              source: "cache" | "api" | "empty" | "error"
        """
        cache_path = self._get_cache_path()

        # Use cache if allowed and fresh
        if prefer_cache and self._is_cache_fresh(cache_path):
            cached = self._read_cache()
            if cached:
                return cached, "cache"

        # Fallback to API if possible
        if not key_json_path or not os.path.exists(key_json_path):
            self.logger.warning("[TTSService] Missing Google key JSON; cannot fetch voices from API.")
            cached = self._read_cache()
            if cached:
                return cached, "cache"
            return {}, "empty"

        if not HAS_GOOGLE:
            self.logger.warning("[TTSService] google-cloud-texttospeech not available.")
            cached = self._read_cache()
            if cached:
                return cached, "cache"
            return {}, "error"

        try:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_json_path
            client = gtts.TextToSpeechClient()
            response = client.list_voices()

            voices: Dict[str, str] = {}
            for v in response.voices:
                # voice_id example: "vi-VN-Wavenet-A"
                # Build a readable display name from language + name + gender
                lang = v.language_codes[0] if v.language_codes else ""
                name = getattr(v, "name", "") or ""
                gender = getattr(v, "ssml_gender", 0)  # enum int
                gender_str = {1: "MALE", 2: "FEMALE", 3: "NEUTRAL"}.get(int(gender), "")
                display = f"{lang} - {name}{(' - ' + gender_str) if gender_str else ''}"
                voice_id = f"{lang}-{name}" if name and lang else name or lang
                if voice_id:
                    voices[voice_id] = display

            if voices:
                self._write_cache(voices)
                return voices, "api"

            cached = self._read_cache()
            if cached:
                return cached, "cache"
            return {}, "empty"
        except Exception as e:
            self.logger.error(f"[TTSService] Error fetching Google voices: {e}", exc_info=True)
            cached = self._read_cache()
            if cached:
                return cached, "cache"
            return {}, "error"


