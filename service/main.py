"""
FastAPI service for imalink-core

Exposes image processing as HTTP API for language-agnostic access.
"""

from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from imalink_schemas import PhotoCreateSchema, ImageFileCreateSchema
from imalink_core.metadata.exif_extractor import ExifExtractor
from imalink_core.preview.generator import PreviewGenerator
from PIL import Image, ImageOps

# Initialize FastAPI app
app = FastAPI(
    title="ImaLink Core API",
    description="Image processing service - converts images to PhotoCreateSchema JSON",
    version="1.0.0",
)

# CORS - allow backend to call this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None


# API Endpoints
@app.get("/")
def root():
    """API root - health check"""
    return {
        "service": "ImaLink Core API",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.post("/v1/process", response_model=PhotoCreateSchema, responses={400: {"model": ErrorResponse}})
async def process_image_endpoint(
    file: UploadFile = File(..., description="Image file to process"),
    coldpreview_size: Optional[int] = Form(None, description="Size for coldpreview (e.g., 2560). None = skip coldpreview. Must be >= 150.")
):
    """
    Process uploaded image file and return PhotoCreateSchema JSON.
    
    PhotoCreateSchema is the canonical output format: a JSON object containing all extractable
    image data (metadata, previews, hothash) with Base64-encoded JPEG previews.
    
    Upload image via multipart/form-data (standard file upload).
    
    Core's single responsibility: (image file, coldpreview_size) → PhotoCreateSchema JSON
    
    Response always includes:
    - Hotpreview (150x150px thumbnail) as Base64-encoded JPEG
    - Complete EXIF metadata (timestamps, GPS, camera info)
    - Hothash (SHA256 of hotpreview - unique identifier)
    
    PhotoCreateSchema optionally includes:
    - Coldpreview (larger preview) as Base64-encoded JPEG
    
    Args:
        file: Uploaded image file (multipart/form-data)
        coldpreview_size: Optional size for coldpreview (form field)
        
    Returns:
        PhotoCreateSchema: Photo data JSON validated by Pydantic model
        
    Raises:
        HTTPException 400: If file processing fails
        HTTPException 422: If validation fails (e.g., coldpreview_size < 150)
        
    Example:
        curl -X POST http://localhost:8765/v1/process \\
          -F "file=@photo.jpg" \\
          -F "coldpreview_size=2560"
    """
    # Validate coldpreview_size if provided
    if coldpreview_size is not None and coldpreview_size < 150:
        raise HTTPException(
            status_code=400,
            detail=f"coldpreview_size must be >= 150 (hotpreview size), got {coldpreview_size}"
        )
    
    try:
        # Read uploaded file into memory
        image_bytes = await file.read()
        
        # Validate it's an image and open it
        try:
            img = Image.open(BytesIO(image_bytes))
            img.verify()  # Check if it's a valid image
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image file: {str(e)}"
            )
        
        # Re-open image for processing (verify() closes it) and apply EXIF rotation
        img = Image.open(BytesIO(image_bytes))
        try:
            img = ImageOps.exif_transpose(img)  # Rotate based on EXIF orientation
        except Exception:
            pass  # No EXIF orientation or already correct
        
        # Extract metadata from bytes
        metadata = ExifExtractor.extract_basic_from_bytes(image_bytes)
        camera_settings = ExifExtractor.extract_camera_settings_from_bytes(image_bytes)
        
        # Generate hotpreview from image
        try:
            hotpreview = PreviewGenerator.generate_hotpreview_from_image(img)
        except ValueError as e:
            # Image too small (< 4x4 pixels)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image: {str(e)}"
            )
        
        # Generate coldpreview (optional)
        if coldpreview_size is not None:
            try:
                coldpreview = PreviewGenerator.generate_coldpreview_from_image(
                    img,
                    max_size=coldpreview_size
                )
                coldpreview_base64 = coldpreview.base64
                coldpreview_width = coldpreview.width
                coldpreview_height = coldpreview.height
            except ValueError as e:
                # Image too small (< 4x4 pixels)
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid image: {str(e)}"
                )
        else:
            coldpreview_base64 = None
            coldpreview_width = None
            coldpreview_height = None
        
        # Build exif_dict with all EXIF metadata (include None values for frontend display)
        exif_dict: Dict[str, Any] = {
            "camera_make": metadata.camera_make,
            "camera_model": metadata.camera_model,
            "iso": camera_settings.iso,
            "aperture": camera_settings.aperture,
            "shutter_speed": camera_settings.shutter_speed,
            "focal_length": camera_settings.focal_length,
            "lens_model": camera_settings.lens_model,
            "lens_make": camera_settings.lens_make,
            "flash": camera_settings.flash,
            "exposure_program": camera_settings.exposure_program,
            "metering_mode": camera_settings.metering_mode,
            "white_balance": camera_settings.white_balance,
            "gps_altitude": metadata.gps_altitude,
            "gps_timestamp": metadata.gps_timestamp,
            "gps_datestamp": metadata.gps_datestamp,
            "gps_map_datum": metadata.gps_map_datum,
        }
        
        # Build image_file_list
        image_file = ImageFileCreateSchema(
            filename=file.filename or "unknown.jpg",
            file_size=len(image_bytes),
            format=file.content_type or "image/jpeg",
            is_raw=False  # TODO: Detect RAW format
        )
        
        # Add has_gps to exif_dict (convenience field)
        has_gps = metadata.gps_latitude is not None and metadata.gps_longitude is not None
        exif_dict["has_gps"] = has_gps
        
        # Build PhotoCreateSchema
        # Note: metadata.taken_at is already ISO string from _standardize_datetime
        photo = PhotoCreateSchema(
            hothash=hotpreview.hothash,
            hotpreview_base64=hotpreview.base64,
            hotpreview_width=hotpreview.width,
            hotpreview_height=hotpreview.height,
            coldpreview_base64=coldpreview_base64,
            coldpreview_width=coldpreview_width,
            coldpreview_height=coldpreview_height,
            image_file_list=[image_file],
            taken_at=metadata.taken_at,  # Already ISO string
            width=metadata.width,
            height=metadata.height,
            gps_latitude=metadata.gps_latitude,
            gps_longitude=metadata.gps_longitude,
            exif_dict=exif_dict  # Always return dict (empty or with data)
        )
        
        return photo
    
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Processing failed: {str(e)}"
        )


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
