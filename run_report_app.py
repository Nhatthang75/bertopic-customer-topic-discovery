"""Launcher script for BERTopic PoC Version 1.0 (Bản Báo Cáo Nghiệm Thu)."""
from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
py_exec = ROOT_DIR / ".venv/Scripts/python.exe"
if not py_exec.is_file():
    py_exec = Path(sys.executable)

port = 8502
url = f"http://localhost:{port}"

print("==================================================================")
print("     KHỞI CHẠY BERTOPIC POC - BẢN BÁO CÁO NGHIỆM THU (V1.0)       ")
print("==================================================================")
print(f"Địa chỉ truy cập: {url}")
print("Nhấn Ctrl+C để dừng.")
print("------------------------------------------------------------------")

cmd = [
    str(py_exec),
    "-m",
    "streamlit",
    "run",
    str(ROOT_DIR / "app_v1_report.py"),
    f"--server.port={port}",
    "--server.headless=true",
]

try:
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
except KeyboardInterrupt:
    print("\n-> Đã dừng máy chủ bản báo cáo.")
