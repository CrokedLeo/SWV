"""
YOLO detection service using ONNX Runtime (Apache 2.0 licensed)
No AGPL/GPL dependencies - uses pre-exported ONNX model
"""
import logging
import time
import os
import urllib.request
import zipfile
from typing import Tuple, List, Optional
import cv2
import numpy as np
import uuid
from pathlib import Path

from backend.services.resilience import circuit_breaker, health_monitor

logger = logging.getLogger(__name__)

COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush"
]

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

ONNX_MODEL_URL = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.onnx"
ONNX_MODEL_PATH = MODEL_DIR / "yolov8n.onnx"

MODEL_INPUT_SIZE = 640


def _download_model() -> bool:
    if ONNX_MODEL_PATH.exists():
        return True
    logger.info(f"Downloading YOLO ONNX model (~14MB) to {ONNX_MODEL_PATH}...")
    try:
        urllib.request.urlretrieve(ONNX_MODEL_URL, str(ONNX_MODEL_PATH))
        logger.info("Model downloaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        return False


class YOLODetector:
    _instance = None
    _session = None
    _model_name: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = "yolov8n.onnx"):
        if self._session is not None:
            return
        try:
            import onnxruntime as ort
        except ImportError:
            raise RuntimeError(
                "onnxruntime is required. Install with: pip install onnxruntime"
            )

        model_path = MODEL_DIR / model_name
        if not model_path.exists():
            if not _download_model():
                raise FileNotFoundError(
                    f"Model not found at {model_path} and download failed. "
                    "Download manually from: https://github.com/ultralytics/assets/releases"
                )
            model_path = ONNX_MODEL_PATH

        logger.info(f"Loading YOLO model: {model_path}")
        try:
            self._session = ort.InferenceSession(
                str(model_path),
                providers=["CPUExecutionProvider"]
            )
            self._model_name = model_name
            logger.info(f"Model {model_name} loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def _letterbox(self, image: np.ndarray) -> Tuple[np.ndarray, float, float, float]:
        h, w = image.shape[:2]
        scale = min(MODEL_INPUT_SIZE / w, MODEL_INPUT_SIZE / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        dw = (MODEL_INPUT_SIZE - new_w) / 2
        dh = (MODEL_INPUT_SIZE - new_h) / 2
        canvas = np.full((MODEL_INPUT_SIZE, MODEL_INPUT_SIZE, 3), 114, dtype=np.uint8)
        canvas[dh:dh + new_h, dw:dw + new_w] = resized
        return canvas, scale, dw, dh

    def _nms(self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.45) -> List[int]:
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-10)
            order = order[np.where(iou <= iou_threshold)[0] + 1]
        return keep

    def detect(self, image: np.ndarray, conf: float = 0.5) -> Tuple[List[dict], float, Tuple[int, int]]:
        endpoint = "yolo_inference"
        try:
            if not circuit_breaker.can_execute(endpoint):
                raise RuntimeError(
                    f"YOLO inference circuit breaker is OPEN. "
                    f"Service overloaded. Please retry after 30 seconds."
                )

            start_time = time.time()
            orig_h, orig_w = image.shape[:2]

            letterbox_img, scale, dw, dh = self._letterbox(image)
            input_tensor = letterbox_img.astype(np.float32) / 255.0
            input_tensor = np.transpose(input_tensor, (2, 0, 1))[np.newaxis, ...]

            outputs = self._session.run(
                None,
                {self._session.get_inputs()[0].name: input_tensor}
            )
            output = outputs[0]
            output = np.transpose(output, (0, 2, 1))
            output = output[0]

            cx = output[:, 0]
            cy = output[:, 1]
            w = output[:, 2]
            h = output[:, 3]

            x1 = ((cx - w / 2) - dw) / scale
            y1 = ((cy - h / 2) - dh) / scale
            x2 = ((cx + w / 2) - dw) / scale
            y2 = ((cy + h / 2) - dh) / scale

            x1 = np.clip(x1, 0, orig_w)
            y1 = np.clip(y1, 0, orig_h)
            x2 = np.clip(x2, 0, orig_w)
            y2 = np.clip(y2, 0, orig_h)

            scores = output[:, 4:]
            scores = 1 / (1 + np.exp(-scores))
            class_ids = np.argmax(scores, axis=1)
            max_scores = scores[np.arange(len(scores)), class_ids]

            mask = max_scores >= conf
            x1, y1, x2, y2 = x1[mask], y1[mask], x2[mask], y2[mask]
            class_ids = class_ids[mask]
            max_scores = max_scores[mask]

            if len(x1) == 0:
                processing_time = (time.time() - start_time) * 1000
                circuit_breaker.record_success(endpoint)
                health_monitor.update_status(endpoint, True, details={"processing_time_ms": processing_time, "detections": 0})
                return [], processing_time, (orig_w, orig_h)

            boxes = np.stack([x1, y1, x2, y2], axis=1)
            keep = self._nms(boxes, max_scores)

            detections = []
            for idx in keep:
                detections.append({
                    "x_min": float(boxes[idx][0]),
                    "y_min": float(boxes[idx][1]),
                    "x_max": float(boxes[idx][2]),
                    "y_max": float(boxes[idx][3]),
                    "confidence": float(max_scores[idx]),
                    "class_id": int(class_ids[idx]),
                    "class_name": COCO_CLASSES[class_ids[idx]] if class_ids[idx] < len(COCO_CLASSES) else f"class_{class_ids[idx]}"
                })

            processing_time = (time.time() - start_time) * 1000
            circuit_breaker.record_success(endpoint)
            health_monitor.update_status(
                endpoint, True,
                details={"processing_time_ms": processing_time, "detections": len(detections)}
            )

            return detections, processing_time, (orig_w, orig_h)

        except Exception as e:
            circuit_breaker.record_failure(endpoint)
            error_msg = str(e)[:100]
            logger.error(f"YOLO detection failed: {error_msg}")
            health_monitor.update_status(endpoint, False, error_message=error_msg)
            raise


class ImageProcessor:
    @staticmethod
    def load_from_bytes(image_bytes: bytes) -> np.ndarray:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            return img
        except Exception as e:
            logger.error(f"Failed to load image from bytes: {e}")
            raise

    @staticmethod
    def load_from_file(file_path: str) -> np.ndarray:
        try:
            img = cv2.imread(file_path)
            if img is None:
                raise ValueError(f"Failed to load image from {file_path}")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            return img
        except Exception as e:
            logger.error(f"Failed to load image from file: {e}")
            raise

    @staticmethod
    def save_image(image: np.ndarray, file_path: str) -> None:
        try:
            img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(file_path, img_bgr)
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            raise

    @staticmethod
    def resize_image(image: np.ndarray, max_width: int = 1280, max_height: int = 720) -> np.ndarray:
        height, width = image.shape[:2]
        if width > max_width or height > max_height:
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        return image


def get_detector(model_name: str = "yolov8n.onnx") -> YOLODetector:
    """Get singleton YOLO detector instance"""
    return YOLODetector(model_name)
