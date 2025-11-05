"""
Import Result Model

Represents the result of importing a single image file.
"""

from dataclasses import dataclass
from typing import Optional

from ..metadata.exif_extractor import BasicMetadata, CameraSettings
from .photo import CorePhoto


@dataclass
class ImportResult:
    """
    Result from importing a single image.
    
    Contains all extracted data and indicates success/failure.
    """
    success: bool
    hothash: Optional[str] = None
    photo: Optional[CorePhoto] = None
    metadata: Optional[BasicMetadata] = None
    camera_settings: Optional[CameraSettings] = None
    hotpreview_base64: Optional[str] = None
    coldpreview_bytes: Optional[bytes] = None
    error: Optional[str] = None
    
    @property
    def is_duplicate(self) -> bool:
        """Check if import failed due to duplicate"""
        return not self.success and self.error and "duplicate" in self.error.lower()
    
    @property
    def failed(self) -> bool:
        """Check if import failed"""
        return not self.success
