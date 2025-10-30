"""
Update service: fetch update info and compare versions.
"""

import logging
import requests
from packaging import version
from typing import Dict, Optional


def is_newer(remote_version: str, current_version: str) -> bool:
    try:
        return version.parse(remote_version) > version.parse(current_version)
    except Exception:
        return False


def result_payload(status: str, message: str = "", data: Dict = None) -> Dict:
    return {"status": status, "message": message, "data": data or {}}


def fetch_update_info(update_url: str, timeout_seconds: int = 15) -> Dict:
    """
    Fetch update JSON from endpoint.
    Expected JSON keys: version (str), changelog (str), download_url (str)
    Returns a dict with keys: status, data|error
    """
    try:
        resp = requests.get(update_url, timeout=timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        logging.info(f"[UpdateService] Fetched update info: {data}")
        latest_ver = (data.get("version") or "").strip()
        dl_url = data.get("download_url") or ""
        if not latest_ver or not dl_url:
            return {"status": "invalid", "error": "Missing version or download_url", "data": data}
        return {"status": "ok", "data": data}
    except requests.exceptions.RequestException as e:
        logging.error(f"[UpdateService] Network error: {e}")
        return {"status": "network_error", "error": str(e)}
    except ValueError as e:
        # JSON decode error bubbles as ValueError
        logging.error(f"[UpdateService] Invalid JSON: {e}")
        return {"status": "invalid_json", "error": str(e)}


