"""
Licensing service: verify status, activate license, and start trial via Apps Script backend.
"""

import logging
import requests
from typing import Any, Dict, Tuple

from config.constants import APPS_SCRIPT_URL


def _call_apps_script(action: str, params: Dict[str, Any], timeout: int = 25) -> Tuple[Dict[str, Any], str]:
    """
    Low-level GET call to Apps Script endpoint with unified error handling.

    Returns (result_json, raw_text). Raises requests.exceptions.RequestException on network errors.
    """
    all_params = {"action": action, **params}
    logging.debug(f"[LicensingService] GET {APPS_SCRIPT_URL} params={all_params}")
    resp = requests.get(APPS_SCRIPT_URL, params=all_params, timeout=timeout)
    raw = resp.text
    resp.raise_for_status()
    try:
        return resp.json(), raw
    except Exception:
        # Fallback attempt if server returns non-strict JSON
        import json as _json
        return _json.loads(raw), raw


def verify_status(key: str, hwid: str) -> Dict[str, Any]:
    """
    Verify license status.
    Returns dict with: status, activation_status, message, data.
    """
    try:
        result, raw = _call_apps_script("verify_status", {"key": key or "", "hwid": hwid}, timeout=25)
        status = result.get("status", "error")
        if status == "success":
            return {
                "status": "success",
                "activation_status": result.get("activation_status", "INACTIVE"),
                "message": result.get("message", ""),
                "data": result,
                "raw": raw,
            }
        return {
            "status": "error",
            "activation_status": result.get("activation_status", "INACTIVE"),
            "message": result.get("message", "Server reported error."),
            "data": result,
            "raw": raw,
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"[LicensingService] Network error in verify_status: {e}")
        return {
            "status": "network_error",
            "activation_status": "UNKNOWN_ERROR_CLIENT",
            "message": str(e),
            "data": {},
            "raw": "",
        }


def activate(key: str, hwid: str) -> Dict[str, Any]:
    """
    Activate license key for given HWID.
    Returns dict with: status, type, activation_status, expiry_date, message, data.
    """
    try:
        result, raw = _call_apps_script("activate", {"key": key, "hwid": hwid}, timeout=30)
        status = result.get("status", "error")
        payload = {
            "status": status,
            "type": result.get("type", "ACTIVE"),
            "activation_status": result.get("activation_status", result.get("type", "ACTIVE")),
            "expiry_date": result.get("expiry_date"),
            "message": result.get("message", ""),
            "data": result,
            "raw": raw,
        }
        return payload
    except requests.exceptions.RequestException as e:
        logging.error(f"[LicensingService] Network error in activate: {e}")
        return {
            "status": "network_error",
            "type": "INACTIVE",
            "activation_status": "INACTIVE",
            "expiry_date": None,
            "message": str(e),
            "data": {},
            "raw": "",
        }


def start_trial(hwid: str) -> Dict[str, Any]:
    """
    Start a trial for this HWID.
    Returns dict with: status, message, data.
    """
    try:
        result, raw = _call_apps_script("start_trial", {"hwid": hwid}, timeout=20)
        return {
            "status": result.get("status", "error"),
            "message": result.get("message", ""),
            "data": result,
            "raw": raw,
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"[LicensingService] Network error in start_trial: {e}")
        return {
            "status": "network_error",
            "message": str(e),
            "data": {},
            "raw": "",
        }


