"""
High-level API for ImaLink Core

Convenience functions for processing images.
"""

from pathlib import Path
from typing import List, Callable, Optional

from .metadata.exif_extractor import ExifExtractor
from .models.import_result import ImportResult
from .models.photo import Photo
from .preview.generator import PreviewGenerator
from .validation.image_validator import ImageValidator


def process_image(image_path: Path) -> ImportResult:
    """
    High-level function to process a single image.
    
    Does everything:
    1. Validates file
    2. Extracts metadata (basic + camera settings)
    3. Generates previews (hot + cold)
    4. Calculates hothash
    5. Returns ImportResult with Photo object
    
    Args:
        image_path: Path to image file
        
    Returns:
        ImportResult with success status and data
        
    Example:
        >>> from pathlib import Path
        >>> from imalink_core import process_image
        >>> 
        >>> result = process_image(Path("photo.jpg"))
        >>> if result.success:
        ...     print(f"Hothash: {result.hothash}")
        ...     print(f"Taken at: {result.metadata.taken_at}")
        ...     print(f"Camera: {result.photo.camera_info}")
        ... else:
        ...     print(f"Error: {result.error}")
    """
    # Validate file
    is_valid, error = ImageValidator.validate_file(image_path)
    if not is_valid:
        return ImportResult(success=False, error=error)
    
    try:
        # Extract metadata
        metadata = ExifExtractor.extract_basic(image_path)
        camera_settings = ExifExtractor.extract_camera_settings(image_path)
        
        # Generate previews
        hotpreview, coldpreview = PreviewGenerator.generate_both(image_path)
        
        # Build Photo object
        photo = Photo(
            hothash=hotpreview.hothash,
            hotpreview_base64=hotpreview.base64,
            hotpreview_width=hotpreview.width,
            hotpreview_height=hotpreview.height,
            primary_filename=image_path.name,
            taken_at=metadata.taken_at,
            width=metadata.width,
            height=metadata.height,
            camera_make=metadata.camera_make,
            camera_model=metadata.camera_model,
            gps_latitude=metadata.gps_latitude,
            gps_longitude=metadata.gps_longitude,
            has_gps=metadata.gps_latitude is not None,
            iso=camera_settings.iso,
            aperture=camera_settings.aperture,
            shutter_speed=camera_settings.shutter_speed,
            focal_length=camera_settings.focal_length,
            lens_model=camera_settings.lens_model,
            lens_make=camera_settings.lens_make,
        )
        
        return ImportResult(
            success=True,
            hothash=hotpreview.hothash,
            photo=photo,
            metadata=metadata,
            camera_settings=camera_settings,
            hotpreview_base64=hotpreview.base64,
            coldpreview_bytes=coldpreview.bytes,
        )
    
    except Exception as e:
        return ImportResult(
            success=False,
            error=f"Processing failed: {str(e)}"
        )


def batch_process(
    image_paths: List[Path],
    progress_callback: Optional[Callable[[int, int, ImportResult], None]] = None
) -> List[ImportResult]:
    """
    Process multiple images with optional progress tracking.
    
    Args:
        image_paths: List of paths to image files
        progress_callback: Optional callback(current, total, result)
        
    Returns:
        List of ImportResult objects
        
    Example:
        >>> from pathlib import Path
        >>> from imalink_core import batch_process
        >>> 
        >>> images = list(Path("./photos").glob("*.jpg"))
        >>> 
        >>> def on_progress(current, total, result):
        ...     if result.success:
        ...         print(f"[{current}/{total}] ✓ {result.photo.primary_filename}")
        ...     else:
        ...         print(f"[{current}/{total}] ✗ {result.error}")
        >>> 
        >>> results = batch_process(images, progress_callback=on_progress)
        >>> 
        >>> successful = [r for r in results if r.success]
        >>> print(f"\\nImported {len(successful)}/{len(results)} photos")
    """
    results = []
    total = len(image_paths)
    
    for i, path in enumerate(image_paths, 1):
        result = process_image(path)
        results.append(result)
        
        if progress_callback:
            progress_callback(i, total, result)
    
    return results
