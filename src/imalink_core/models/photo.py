"""
Photo Model - Core data structure for ImaLink ecosystem

This model is shared across backend, frontend, and processing layers.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class PhotoFormat(Enum):
    """Supported image formats"""
    JPEG = "jpeg"
    PNG = "png"
    TIFF = "tiff"
    RAW = "raw"
    HEIC = "heic"
    WEBP = "webp"


@dataclass
class CoreImageFile:
    """
    Represents a file associated with a photo.
    
    Multiple files can have the same hothash (e.g., JPEG + RAW).
    """
    filename: str
    file_size: int
    format: PhotoFormat
    is_raw: bool
    import_session_id: Optional[int] = None
    imported_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['format'] = self.format.value
        if self.imported_at:
            data['imported_at'] = self.imported_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoreImageFile':
        """Create from dictionary (e.g., API response)"""
        # Parse format enum
        if 'format' in data and isinstance(data['format'], str):
            data['format'] = PhotoFormat(data['format'])
        
        # Parse datetime
        if 'imported_at' in data and isinstance(data['imported_at'], str):
            data['imported_at'] = datetime.fromisoformat(data['imported_at'])
        
        return cls(**data)


@dataclass
class CorePhoto:
    """
    Core Photo model - canonical representation in ImaLink.
    
    This is shared across:
    - imalink-core (processing)
    - imalink-backend (storage)
    - imalink-web (display)
    - imalink-qt-frontend (display)
    
    Backend API returns this structure, frontend expects it.
    
    CRITICAL: All image data uses Base64 encoding - the industry standard
    for binary data in JSON. No other format is supported.
    """
    # Identity (required)
    hothash: str  # SHA256 of hotpreview (unique ID)
    
    # Hotpreview (150x150 JPEG thumbnail for galleries)
    # Base64 is REQUIRED - only format for binary data in JSON
    hotpreview_base64: Optional[str] = None  # Base64-encoded JPEG (REQUIRED format)
    hotpreview_width: Optional[int] = None   # Actual width after resize
    hotpreview_height: Optional[int] = None  # Actual height after resize
    
    # Coldpreview (variable size JPEG for detail view)
    # Base64 is REQUIRED - only format for binary data in JSON
    coldpreview_base64: Optional[str] = None  # Base64-encoded JPEG (REQUIRED format)
    coldpreview_width: Optional[int] = None   # Actual width after resize
    coldpreview_height: Optional[int] = None  # Actual height after resize
    
    # Files
    primary_filename: Optional[str] = None
    image_files: List[CoreImageFile] = field(default_factory=list)
    
    # Timestamps
    taken_at: Optional[datetime] = None
    first_imported: Optional[datetime] = None
    last_imported: Optional[datetime] = None
    
    # Dimensions
    width: Optional[int] = None
    height: Optional[int] = None
    
    # Core metadata
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    
    # GPS
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    has_gps: bool = False
    
    # Camera settings
    iso: Optional[int] = None
    aperture: Optional[float] = None
    shutter_speed: Optional[str] = None
    focal_length: Optional[float] = None
    lens_model: Optional[str] = None
    lens_make: Optional[str] = None
    
    # Organization
    rating: Optional[int] = None  # 0-5 stars
    import_session_id: Optional[int] = None
    
    # Flags
    has_raw_companion: bool = False
    
    # Backend fields (optional - only used in backend)
    id: Optional[int] = None  # Database ID
    user_id: Optional[int] = None  # Owner
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary suitable for JSON serialization
        """
        data = asdict(self)
        
        # Convert datetime objects to ISO strings
        if self.taken_at:
            data['taken_at'] = self.taken_at.isoformat()
        if self.first_imported:
            data['first_imported'] = self.first_imported.isoformat()
        if self.last_imported:
            data['last_imported'] = self.last_imported.isoformat()
        
        # Convert ImageFile objects
        data['image_files'] = [f.to_dict() for f in self.image_files]
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorePhoto':
        """
        Create CorePhoto from dictionary (e.g., API response).
        
        Args:
            data: Dictionary with photo data
            
        Returns:
            CorePhoto object
        """
        # Make a copy to avoid modifying original
        data = data.copy()
        
        # Parse datetime fields
        for field_name in ['taken_at', 'first_imported', 'last_imported']:
            if field_name in data and isinstance(data[field_name], str):
                try:
                    data[field_name] = datetime.fromisoformat(data[field_name])
                except ValueError:
                    data[field_name] = None
        
        # Parse CoreImageFile objects
        if 'image_files' in data and isinstance(data['image_files'], list):
            data['image_files'] = [
                CoreImageFile.from_dict(f) if isinstance(f, dict) else f
                for f in data['image_files']
            ]
        
        return cls(**data)
    
    @property
    def display_filename(self) -> str:
        """Get filename to display in UI"""
        return self.primary_filename or f"{self.hothash[:8]}.jpg"
    
    @property
    def has_location(self) -> bool:
        """Check if photo has GPS coordinates"""
        return self.gps_latitude is not None and self.gps_longitude is not None
    
    @property
    def camera_info(self) -> Optional[str]:
        """Get formatted camera info string"""
        if self.camera_make and self.camera_model:
            return f"{self.camera_make} {self.camera_model}"
        elif self.camera_model:
            return self.camera_model
        return None
