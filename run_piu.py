"""
Quick launcher for Piu.py with error handling
"""
import subprocess
import sys

print("=" * 50)
print("Starting Piu application...")
print("=" * 50)

try:
    subprocess.run([sys.executable, "Piu.py"], check=True)
except KeyboardInterrupt:
    print("\n\n[INFO] Application closed by user")
except Exception as e:
    print(f"\n[ERROR] Could not start: {e}")

