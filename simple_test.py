"""Simple test - no dependencies"""
print("Hello from Kaggle!")
print("Code executed successfully!")

import subprocess
try:
    result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print(f"GPU: {result.stdout.strip()}")
except:
    print("No GPU or nvidia-smi not available")
