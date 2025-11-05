"""
ImaLink Core - Image processing library for ImaLink ecosystem

This library provides:
- EXIF metadata extraction
- Preview generation (hotpreview 150x150, coldpreview 1920x1080)
- Hothash calculation (SHA256)
- Image validation
- RAW format support (optional)

Example:
    >>> from imalink_core import process_image
    >>> from pathlib import Path
    >>> 
    >>> result = process_image(Path("photo.jpg"))
    >>> if result.success:
    ...     print(f"Hothash: {result.hothash}")
    ...     print(f"Taken at: {result.metadata.taken_at}")
"""

from .version import __version__

# Metadata extraction
from .metadata import BasicMetadata, CameraSettings, ExifExtractor

# Preview generation
from .preview import ColdPreview, HotPreview, HothashCalculator, PreviewGenerator

# Image processing
from .image import FormatDetector, ImageFormat

# Models
from .models import ImageFile, ImportResult, Photo, PhotoFormat

# Validation
from .validation import ImageValidator

# High-level API
from .api import batch_process, process_image

__all__ = [
    # Version
    "__version__",
    # Metadata
    "ExifExtractor",
    "BasicMetadata",
    "CameraSettings",
    # Preview
    "PreviewGenerator",
    "HotPreview",
    "ColdPreview",
    "HothashCalculator",
    # Image
    "ImageFormat",
    "FormatDetector",
    # Models
    "Photo",
    "ImageFile",
    "PhotoFormat",
    "ImportResult",
    # Validation
    "ImageValidator",
    # High-level API
    "process_image",
    "batch_process",
]
