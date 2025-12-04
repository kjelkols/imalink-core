"""
Image Format Detection and Validation
"""

from enum import Enum
from pathlib import Path
from typing import Optional, Set

from PIL import Image


class ImageFormat(Enum):
    """Supported image formats"""
    JPEG = "JPEG"
    PNG = "PNG"
    TIFF = "TIFF"
    NEF = "NEF"  # Nikon RAW
    CR2 = "CR2"  # Canon RAW
    ARW = "ARW"  # Sony RAW
    DNG = "DNG"  # Adobe RAW
    HEIC = "HEIC"  # Apple
    WEBP = "WEBP"


class FormatDetector:
    """Detect and validate image formats"""
    
    SUPPORTED_EXTENSIONS: Set[str] = {
        '.jpg', '.jpeg', '.png', '.tiff', '.tif',
        '.nef', '.nrw', '.cr2', '.cr3', '.crw', '.arw', '.srf', '.sr2',
        '.raf', '.orf', '.rw2', '.raw', '.pef', '.ptx', '.x3f', '.rwl',
        '.dng', '.mrw', '.srw', '.3fr', '.dcr', '.kdc', '.mef', '.iiq',
        '.heic', '.webp'
    }
    
    RAW_EXTENSIONS: Set[str] = {
        '.nef', '.nrw',  # Nikon
        '.cr2', '.cr3', '.crw',  # Canon
        '.arw', '.srf', '.sr2',  # Sony
        '.raf',  # Fujifilm
        '.orf',  # Olympus/OM System
        '.rw2', '.raw',  # Panasonic
        '.pef', '.ptx',  # Pentax
        '.x3f',  # Sigma
        '.rwl', '.dng',  # Leica
        '.mrw',  # Minolta
        '.srw',  # Samsung
        '.3fr',  # Hasselblad
        '.dcr', '.kdc',  # Kodak
        '.mef',  # Mamiya
        '.iiq',  # Phase One
    }
    
    @staticmethod
    def detect_format(file_path: Path) -> Optional[ImageFormat]:
        """
        Detect format from file extension.
        
        Args:
            file_path: Path to image file
            
        Returns:
            ImageFormat enum or None if unsupported
        """
        ext = file_path.suffix.lower()
        
        format_map = {
            '.jpg': ImageFormat.JPEG,
            '.jpeg': ImageFormat.JPEG,
            '.png': ImageFormat.PNG,
            '.tiff': ImageFormat.TIFF,
            '.tif': ImageFormat.TIFF,
            '.nef': ImageFormat.NEF,
            '.cr2': ImageFormat.CR2,
            '.arw': ImageFormat.ARW,
            '.dng': ImageFormat.DNG,
            '.heic': ImageFormat.HEIC,
            '.webp': ImageFormat.WEBP,
        }
        
        return format_map.get(ext)
    
    @staticmethod
    def is_raw_format(file_path: Path) -> bool:
        """
        Check if file is RAW format.
        
        Args:
            file_path: Path to image file
            
        Returns:
            True if file is RAW format
        """
        ext = file_path.suffix.lower()
        return ext in FormatDetector.RAW_EXTENSIONS
    
    @staticmethod
    def is_supported(file_path: Path) -> bool:
        """
        Check if format is supported.
        
        Args:
            file_path: Path to image file
            
        Returns:
            True if format is supported
        """
        ext = file_path.suffix.lower()
        return ext in FormatDetector.SUPPORTED_EXTENSIONS
    
    @staticmethod
    def can_open_with_pil(file_path: Path) -> bool:
        """
        Check if file can be opened with PIL.
        
        Args:
            file_path: Path to image file
            
        Returns:
            True if PIL can open the file
        """
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception:
            return False
