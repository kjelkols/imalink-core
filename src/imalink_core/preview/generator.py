"""
Preview Generation Module

Generates thumbnails and calculates hothash for image files.
"""

import base64
import hashlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageOps


@dataclass
class HotPreview:
    """
    150x150px thumbnail with hothash.
    
    Attributes:
        bytes: Raw JPEG bytes (no EXIF metadata) - for internal processing
        base64: Base64-encoded string - REQUIRED for JSON/API transmission
                This is the ONLY format for image data in PhotoEgg JSON
        hothash: SHA256 hex digest of bytes (unique identifier)
        width: Actual width in pixels
        height: Actual height in pixels
    """
    bytes: bytes
    base64: str  # REQUIRED: Industry standard for binary data in JSON
    hothash: str
    width: int
    height: int


@dataclass
class ColdPreview:
    """
    Variable size preview for viewing.
    
    Attributes:
        bytes: Raw JPEG bytes (no EXIF metadata) - for internal processing
        base64: Base64-encoded string - REQUIRED for JSON/API transmission
                This is the ONLY format for image data in PhotoEgg JSON
        width: Actual width in pixels
        height: Actual height in pixels
    """
    bytes: bytes
    base64: str  # REQUIRED: Industry standard for binary data in JSON
    width: int
    height: int


class PreviewGenerator:
    """Generate previews with EXIF-aware rotation"""
    
    DEFAULT_HOT_SIZE = (150, 150)
    DEFAULT_COLD_SIZE = (1920, 1080)
    
    @staticmethod
    def generate_hotpreview(
        image_path: Path,
        size: Tuple[int, int] = DEFAULT_HOT_SIZE,
        quality: int = 85
    ) -> HotPreview:
        """
        Generate 150x150 thumbnail + hothash.
        
        Process:
        1. Open image
        2. Apply EXIF orientation (rotate pixels)
        3. Resize to 150x150 (aspect ratio preserved)
        4. Save as JPEG (no EXIF)
        5. Calculate SHA256 hash (hothash)
        
        Args:
            image_path: Path to image file
            size: Thumbnail size (default 150x150)
            quality: JPEG quality 0-100 (default 85)
            
        Returns:
            HotPreview object with bytes, base64, hothash
        """
        # Open and rotate based on EXIF orientation
        img = Image.open(image_path)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass  # No EXIF orientation or already correct
        
        # Generate thumbnail (maintains aspect ratio)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Get actual dimensions after resize
        width, height = img.size
        
        # Convert to JPEG bytes
        buffer = BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=quality)
        preview_bytes = buffer.getvalue()
        
        # Generate hothash (SHA256 of preview bytes)
        hothash = hashlib.sha256(preview_bytes).hexdigest()
        
        # Base64 encode for API transmission
        preview_b64 = base64.b64encode(preview_bytes).decode()
        
        return HotPreview(
            bytes=preview_bytes,
            base64=preview_b64,
            hothash=hothash,
            width=width,
            height=height
        )
    
    @staticmethod
    def generate_coldpreview(
        image_path: Path,
        max_size: int = 1920,
        quality: int = 90
    ) -> ColdPreview:
        """
        Generate 1920x1080 preview for viewing.
        
        Process:
        1. Open image
        2. Apply EXIF orientation (rotate pixels)
        3. Resize to max_size (aspect ratio preserved)
        4. Save as JPEG (no EXIF)
        
        Args:
            image_path: Path to image file
            max_size: Maximum dimension in pixels (default 1920)
            quality: JPEG quality 0-100 (default 90)
            
        Returns:
            ColdPreview object with bytes and dimensions
        """
        # Open and rotate based on EXIF orientation
        img = Image.open(image_path)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass  # No EXIF orientation or already correct
        
        # Resize to max dimension while maintaining aspect ratio
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Get actual dimensions after resize
        width, height = img.size
        
        # Convert to JPEG bytes
        buffer = BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=quality)
        preview_bytes = buffer.getvalue()
        
        # Base64 encode for API transmission
        preview_b64 = base64.b64encode(preview_bytes).decode()
        
        return ColdPreview(
            bytes=preview_bytes,
            base64=preview_b64,
            width=width,
            height=height
        )
    
    @staticmethod
    def generate_both(image_path: Path) -> Tuple[HotPreview, ColdPreview]:
        """
        Generate both previews in one pass (optimization).
        
        Opens the image once and generates both previews.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (HotPreview, ColdPreview)
        """
        hotpreview = PreviewGenerator.generate_hotpreview(image_path)
        coldpreview = PreviewGenerator.generate_coldpreview(image_path)
        return hotpreview, coldpreview


class HothashCalculator:
    """Calculate SHA256 hothash from image bytes"""
    
    @staticmethod
    def calculate(image_bytes: bytes) -> str:
        """
        Calculate SHA256 hash from image bytes.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            SHA256 hex digest (64 characters)
        """
        return hashlib.sha256(image_bytes).hexdigest()
    
    @staticmethod
    def verify(image_bytes: bytes, expected_hash: str) -> bool:
        """
        Verify hothash matches expected value.
        
        Args:
            image_bytes: Raw image bytes
            expected_hash: Expected SHA256 hex digest
            
        Returns:
            True if hash matches
        """
        return HothashCalculator.calculate(image_bytes) == expected_hash
