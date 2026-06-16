"""
YOLO detection service
"""
import logging
import time
from typing import Tuple, List
import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class YOLODetector:
    """Handles YOLO model loading and inference"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = "yolov8n.pt"):
        """Initialize YOLO detector (singleton pattern)"""
        if self._model is None:
            logger.info(f"Loading YOLO model: {model_name}")
            try:
                self._model = YOLO(model_name)
                logger.info(f"Model {model_name} loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise
    
    def detect(self, image: np.ndarray, conf: float = 0.5) -> Tuple[List[dict], float, Tuple[int, int]]:
        """
        Run detection on image
        
        Args:
            image: Input image as numpy array
            conf: Confidence threshold
            
        Returns:
            Tuple of (detections, processing_time_ms, (width, height))
        """
        start_time = time.time()
        
        try:
            # Run inference
            results = self._model(image, conf=conf, verbose=False)
            processing_time = (time.time() - start_time) * 1000
            
            # Parse results
            detections = []
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None:
                    boxes = result.boxes.cpu()
                    
                    for box, conf_score, cls_id in zip(
                        boxes.xyxy, 
                        boxes.conf, 
                        boxes.cls
                    ):
                        detection = {
                            "x_min": float(box[0]),
                            "y_min": float(box[1]),
                            "x_max": float(box[2]),
                            "y_max": float(box[3]),
                            "confidence": float(conf_score),
                            "class_id": int(cls_id),
                            "class_name": result.names[int(cls_id)]
                        }
                        detections.append(detection)
            
            img_height, img_width = image.shape[:2]
            return detections, processing_time, (img_width, img_height)
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            raise


class ImageProcessor:
    """Handle image loading and preprocessing"""
    
    @staticmethod
    def load_from_bytes(image_bytes: bytes) -> np.ndarray:
        """Load image from bytes"""
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image")
            # Convert BGR to RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            return img
        except Exception as e:
            logger.error(f"Failed to load image from bytes: {e}")
            raise
    
    @staticmethod
    def load_from_file(file_path: str) -> np.ndarray:
        """Load image from file"""
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
        """Save image to file"""
        try:
            # Convert RGB back to BGR for saving
            img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(file_path, img_bgr)
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            raise
    
    @staticmethod
    def resize_image(image: np.ndarray, max_width: int = 1280, max_height: int = 720) -> np.ndarray:
        """Resize image if it exceeds max dimensions"""
        height, width = image.shape[:2]
        
        if width > max_width or height > max_height:
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        return image


def get_detector(model_name: str = "yolov8n.pt") -> YOLODetector:
    """Get singleton YOLO detector instance"""
    return YOLODetector(model_name)
