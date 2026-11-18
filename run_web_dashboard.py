"""Launcher script for BERTopic PoC Streamlit Web Dashboard.

Validates virtual environment, checks artifacts availability,
and launches Streamlit on http://localhost:8501.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts/phase1"


def check_environment() -> Path:
    """Ensure python binary from .venv or current python is used."""
    venv_python = ROOT_DIR / ".venv/Scripts/python.exe"
    if venv_python.is_file():
        return venv_python
    return Path(sys.executable)


def verify_artifacts() -> bool:
    """Verify that required locked artifacts exist before starting."""
    required = [
        ARTIFACTS_DIR / "run_manifest.json",
        ARTIFACTS_DIR / "consolidated/topic_statistics.csv",
        ARTIFACTS_DIR / "consolidated/candidates.jsonl",
        ARTIFACTS_DIR / "consolidated/reviews.jsonl",
        ARTIFACTS_DIR / "evaluation/metrics.json",
        ARTIFACTS_DIR / "evaluation/report.md",
    ]
    missing = [str(p.relative_to(ROOT_DIR)) for p in required if not p.is_file()]
    if missing:
        print("[LỖI] Thiếu các tệp artifacts cần thiết:")
        for m in missing:
            print(f"  - {m}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Khởi chạy BERTopic PoC Web Dashboard")
    parser.add_argument("--port", type=int, default=8501, help="Cổng chạy Streamlit (mặc định: 8501)")
    parser.add_argument("--no-browser", action="store_true", help="Không tự động mở trình duyệt")
    parser.add_argument("--check-only", action="store_true", help="Chỉ kiểm tra môi trường và artifacts rồi thoát")
    args = parser.parse_args()

    print("==================================================================")
    print("      KHỞI CHẠY BERTOPIC CUSTOMER CONVERSATION WEB DASHBOARD      ")
    print("==================================================================")
    print(f"Thư mục dự án: {ROOT_DIR}")
    print(f"Cổng dịch vụ:  {args.port}")

    # 1. Check artifacts
    if not verify_artifacts():
        sys.exit(1)
    print("-> Tất cả artifacts Schema 1.0.0 đã sẵn sàng (Zero-Fit Mode).")

    # 2. Check Python interpreter
    py_exec = check_environment()
    print(f"-> Sử dụng Python: {py_exec}")

    if args.check_only:
        print("-> Kiểm tra hoàn tất thành công (check-only mode).")
        return

    url = f"http://localhost:{args.port}"
    print("------------------------------------------------------------------")
    print(f"Ứng dụng Streamlit đang khởi động tại: {url}")
    print("Nhấn Ctrl+C để dừng máy chủ.")
    print("------------------------------------------------------------------")

    if not args.no_browser:
        # Schedule browser opening slightly after process starts
        import threading
        def open_browser():
            time.sleep(2.0)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    # Launch streamlit via python -m streamlit run app.py
    cmd = [
        str(py_exec),
        "-m",
        "streamlit",
        "run",
        str(ROOT_DIR / "app.py"),
        f"--server.port={args.port}",
        "--server.headless=true",
        "--theme.base=light",
    ]

    try:
        subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
    except KeyboardInterrupt:
        print("\n-> Đã dừng Web Dashboard theo yêu cầu người dùng.")


if __name__ == "__main__":
    main()
