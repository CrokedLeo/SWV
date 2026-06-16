"""
Download YOLO ONNX model for SWV
The model is licensed under Apache 2.0 (ONNX Runtime) and uses
a pre-exported YOLOv8 ONNX model file.
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.detection import _download_model, ONNX_MODEL_PATH, MODEL_DIR

def main():
    print("SWV - YOLO ONNX Model Downloader")
    print("=" * 40)

    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"Model directory: {MODEL_DIR}")

    if ONNX_MODEL_PATH.exists():
        size_mb = ONNX_MODEL_PATH.stat().st_size / (1024 * 1024)
        print(f"Model already exists: {ONNX_MODEL_PATH.name} ({size_mb:.1f} MB)")
        choice = input("Download again? (y/N): ").strip().lower()
        if choice != "y":
            print("Skipping download.")
            return

    print("Downloading YOLOv8n ONNX model (~14 MB)...")
    success = _download_model()
    if success:
        size_mb = ONNX_MODEL_PATH.stat().st_size / (1024 * 1024)
        print(f"Downloaded: {ONNX_MODEL_PATH.name} ({size_mb:.1f} MB)")
        print("Model ready for inference.")
    else:
        print("Download failed.")
        print("Try manually downloading from:")
        print("  https://github.com/ultralytics/assets/releases")
        sys.exit(1)

if __name__ == "__main__":
    main()
