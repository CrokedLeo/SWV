"""
API routes for object detection
"""
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from backend.config.settings import settings
from backend.models.schemas import DetectionResponse, DetectionBox
from backend.services.detection import get_detector, ImageProcessor
from backend.security import verify_api_key, FileSecurityValidator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["detection"])


@router.post("/detect", response_model=DetectionResponse)
async def detect_objects(
    file: UploadFile = File(...),
    confidence: float = 0.5,
    api_key: None = Depends(verify_api_key)
) -> DetectionResponse:
    """
    Detect objects in uploaded image using YOLO
    
    - **file**: Image file (JPEG, PNG, etc.)
    - **confidence**: Confidence threshold (0-1)
    
    Returns detection results with bounding boxes
    """
    request_id = str(uuid.uuid4())
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        ext = file.filename.split('.')[-1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        # Read file
        contents = await file.read()
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024*1024):.1f}MB"
            )
        
        # Validate file signature (magic numbers)
        is_valid, error_msg = FileSecurityValidator.validate_file(contents, file.filename or "")
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Load and process image
        image = ImageProcessor.load_from_bytes(contents)
        image = ImageProcessor.resize_image(image)
        
        # Run detection
        detector = get_detector(settings.YOLO_MODEL)
        detections, processing_time, (img_width, img_height) = detector.detect(image, conf=confidence)
        
        # Convert detections to response models
        detection_boxes = [DetectionBox(**d) for d in detections]
        
        response = DetectionResponse(
            request_id=request_id,
            timestamp=datetime.utcnow(),
            image_width=img_width,
            image_height=img_height,
            detections=detection_boxes,
            total_detections=len(detection_boxes),
            processing_time_ms=processing_time,
            model_used=settings.YOLO_MODEL
        )
        
        logger.info(f"Request {request_id}: Found {len(detection_boxes)} objects in {processing_time:.2f}ms")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request {request_id}: Detection failed - {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Detection failed: {str(e)}"
        )


@router.get("/info")
async def get_info():
    """Get application info"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "yolo_model": settings.YOLO_MODEL,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE / (1024 * 1024),
        "allowed_formats": list(settings.ALLOWED_EXTENSIONS)
    }


@router.post("/batch-detect")
async def batch_detect(
    files: list[UploadFile] = File(...),
    confidence: float = 0.5,
    api_key: None = Depends(verify_api_key)
):
    """
    Batch detect objects in multiple images
    
    Returns list of detection results
    """
    results = []
    
    try:
        detector = get_detector(settings.YOLO_MODEL)
        
        for file in files:
            try:
                request_id = str(uuid.uuid4())
                
                contents = await file.read()
                if len(contents) > settings.MAX_UPLOAD_SIZE:
                    continue
                
                # Validate file signature (magic numbers)
                is_valid, error_msg = FileSecurityValidator.validate_file(contents, file.filename or "")
                if not is_valid:
                    logger.warning(f"Batch detection: skipping invalid file {file.filename}: {error_msg}")
                    continue
                
                image = ImageProcessor.load_from_bytes(contents)
                image = ImageProcessor.resize_image(image)
                
                detections, processing_time, (img_width, img_height) = detector.detect(image, conf=confidence)
                
                detection_boxes = [DetectionBox(**d) for d in detections]
                
                response = {
                    "filename": file.filename,
                    "request_id": request_id,
                    "total_detections": len(detection_boxes),
                    "processing_time_ms": processing_time,
                    "detections": detection_boxes
                }
                results.append(response)
                
            except Exception as e:
                logger.error(f"Failed to process {file.filename}: {e}")
                results.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        return {"batch_results": results}
        
    except Exception as e:
        logger.error(f"Batch detection failed: {e}")
        raise HTTPException(status_code=500, detail="Batch detection failed")
