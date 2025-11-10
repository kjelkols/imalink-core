"""
High-level API for ImaLink Core

Convenience functions for processing images.
"""

from pathlib import Path
from typing import List, Callable, Optional

from .metadata.exif_extractor import ExifExtractor
from .models.import_result import ImportResult
from .models.photo import CorePhoto
from .preview.generator import PreviewGenerator
from .validation.image_validator import ImageValidator


def process_image(
    image_path: Path,
    coldpreview_size: Optional[int] = None
) -> ImportResult:
    """
    Convert physical image file to PhotoEgg JSON.
    
    Core's single responsibility: (filepath, coldpreview_size) → PhotoEgg
    
    PhotoEgg always includes:
    - Hotpreview (150x150px thumbnail)
    - Complete EXIF metadata
    - Hothash (unique identifier)
    
    PhotoEgg optionally includes:
    - Coldpreview (larger preview, 150px to original size)
    
    Args:
        image_path: Path to physical image file
        coldpreview_size: Target size for coldpreview in pixels.
                         None (default) = skip coldpreview, only hotpreview.
                         If specified, must be >= 150 (can be any size up to original).
        
    Returns:
        ImportResult with PhotoEgg data (coldpreview_base64 may be None)
        
    Example:
        >>> from pathlib import Path
        >>> from imalink_core import process_image
        >>> 
        >>> # Minimal PhotoEgg (hotpreview only, default)
        >>> result = process_image(Path("photo.jpg"))
        >>> 
        >>> # Full PhotoEgg with coldpreview
        >>> result = process_image(Path("photo.jpg"), coldpreview_size=2560)
        >>> 
        >>> # Smaller coldpreview
        >>> result = process_image(Path("photo.jpg"), coldpreview_size=1024)
    """
    # Validate coldpreview_size if provided
    if coldpreview_size is not None and coldpreview_size < 150:
        return ImportResult(
            success=False,
            error=f"coldpreview_size must be >= 150 (hotpreview size), got {coldpreview_size}"
        )
    
    # Validate file
    is_valid, error = ImageValidator.validate_file(image_path)
    if not is_valid:
        return ImportResult(success=False, error=error)
    
    try:
        # Extract metadata
        metadata = ExifExtractor.extract_basic(image_path)
        camera_settings = ExifExtractor.extract_camera_settings(image_path)
        
        # Generate hotpreview (always required)
        hotpreview = PreviewGenerator.generate_hotpreview(image_path)
        
        # Generate coldpreview (optional)
        if coldpreview_size is not None:
            coldpreview = PreviewGenerator.generate_coldpreview(
                image_path,
                max_size=coldpreview_size
            )
            coldpreview_base64 = coldpreview.base64
            coldpreview_width = coldpreview.width
            coldpreview_height = coldpreview.height
            coldpreview_bytes = coldpreview.bytes
        else:
            coldpreview_base64 = None
            coldpreview_width = None
            coldpreview_height = None
            coldpreview_bytes = None
        
        # Build CorePhoto object
        photo = CorePhoto(
            hothash=hotpreview.hothash,
            hotpreview_base64=hotpreview.base64,
            hotpreview_width=hotpreview.width,
            hotpreview_height=hotpreview.height,
            coldpreview_base64=coldpreview_base64,
            coldpreview_width=coldpreview_width,
            coldpreview_height=coldpreview_height,
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
            coldpreview_bytes=coldpreview_bytes,
        )
    
    except Exception as e:
        return ImportResult(
            success=False,
            error=f"Processing failed: {str(e)}"
        )


def batch_process(
    image_paths: List[Path],
    coldpreview_size: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, ImportResult], None]] = None
) -> List[ImportResult]:
    """
    Process multiple images with optional progress tracking.
    
    Args:
        image_paths: List of paths to image files
        coldpreview_size: Target size for coldpreview in pixels.
                         None (default) = skip coldpreview, only hotpreview.
                         If specified, must be >= 150 (can be any size up to original).
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
        >>> # Minimal PhotoEggs (hotpreview only, default)
        >>> results = batch_process(images, progress_callback=on_progress)
        >>> 
        >>> # Full PhotoEggs with coldpreview
        >>> results = batch_process(images, coldpreview_size=2560, 
        ...                         progress_callback=on_progress)
        >>> 
        >>> successful = [r for r in results if r.success]
        >>> print(f"\\nImported {len(successful)}/{len(results)} photos")
    """
    results = []
    total = len(image_paths)
    
    for i, path in enumerate(image_paths, 1):
        result = process_image(path, coldpreview_size=coldpreview_size)
        results.append(result)
        
        if progress_callback:
            progress_callback(i, total, result)
    
    return results
