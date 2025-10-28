"""
Test script to verify the new project structure
This will test imports and basic functionality
"""

import sys
import os

print("=" * 50)
print("Testing Piu Project Structure")
print("=" * 50)

# Test 1: Import constants
print("\n[Test 1] Importing constants...")
try:
    from config.constants import APP_NAME, CURRENT_VERSION, YOUTUBE_CATEGORIES
    print(f"[OK] Imported APP_NAME = '{APP_NAME}', VERSION = '{CURRENT_VERSION}'")
    print(f"[OK] Found {len(YOUTUBE_CATEGORIES)} YouTube categories")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

# Test 2: Import settings
print("\n[Test 2] Importing settings...")
try:
    from config.settings import load_config, save_config, get_config_path
    config_path = get_config_path()
    print(f"[OK] Imported config functions")
    print(f"[OK] Config path: {config_path}")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

# Test 3: Import exceptions
print("\n[Test 3] Importing exceptions...")
try:
    from exceptions.app_exceptions import SingleInstanceException
    print("[OK] Imported SingleInstanceException")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

# Test 4: Test config loading
print("\n[Test 4] Testing config loading...")
try:
    cfg = load_config()
    print(f"[OK] Loaded config (keys: {len(cfg)})")
    print(f"[OK] Config data: {cfg}")
except Exception as e:
    print(f"[WARN] {e} (This is OK if config doesn't exist yet)")

# Test 5: Check asset files
print("\n[Test 5] Checking asset files...")
asset_files = ["assets/logo_Piu.ico", "assets/logo_Piu_resized.png"]
for asset in asset_files:
    if os.path.exists(asset):
        print(f"[OK] Found: {asset}")
    else:
        print(f"[FAIL] Missing: {asset}")

print("\n" + "=" * 50)
print("Structure Test Complete!")
print("=" * 50)

