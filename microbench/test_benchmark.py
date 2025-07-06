#!/usr/bin/env python3
"""Quick test script to verify double_bandwidth works"""

import subprocess
import os

# First check if double_bandwidth exists
if not os.path.exists("./double_bandwidth"):
    print("Building double_bandwidth...")
    result = subprocess.run(["make", "double_bandwidth"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Build failed: {result.stderr}")
        exit(1)
    print("Build successful!")

# Run a quick test
print("\nRunning quick test with 4 threads, 50% read ratio...")
cmd = [
    "./double_bandwidth",
    "-t", "4",
    "-r", "0.5",
    "-d", "2",  # 2 seconds only
    "-s", "100M"  # Smaller buffer for quick test
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    print(f"Return code: {result.returncode}")
    print(f"\nOutput:\n{result.stdout}")
    if result.stderr:
        print(f"\nErrors:\n{result.stderr}")
except Exception as e:
    print(f"Error: {e}")

print("\nTest complete. If successful, you can run the full visualization.")