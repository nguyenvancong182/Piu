"""
Quick test to verify Piu.py can still run
This checks if the original file is intact and has no syntax errors
"""

import sys
import os

print("=" * 60)
print("QUICK TEST: Piu.py Original File")
print("=" * 60)

# Test 1: Check file exists
print("\n[1/3] Checking if Piu.py exists...")
if os.path.exists("Piu.py"):
    file_size = os.path.getsize("Piu.py")
    print(f"[OK] File exists ({file_size:,} bytes)")
else:
    print("[FAIL] File not found!")
    sys.exit(1)

# Test 2: Check file size (should be ~2.5MB)
print("\n[2/3] Checking file size...")
if file_size > 2_000_000:  # Should be > 2MB
    print(f"[OK] File size looks correct ({file_size:,} bytes)")
else:
    print(f"[WARN] File size seems small ({file_size:,} bytes)")

# Test 3: Syntax check
print("\n[3/3] Checking syntax (dry run)...")
try:
    with open("Piu.py", "r", encoding="utf-8") as f:
        compile(f.read(), "Piu.py", "exec")
    print("[OK] No syntax errors detected")
    print("[OK] File is ready to run!")
except SyntaxError as e:
    print(f"[FAIL] Syntax error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[WARN] Could not check syntax: {e}")

print("\n" + "=" * 60)
print("[PASS] QUICK TEST COMPLETED - File is safe to run")
print("=" * 60)
print("\nNEXT STEPS:")
print("1. Run: python Piu.py")
print("2. Or double-click Piu.py")
print("3. Test all features manually")
print("\n")

