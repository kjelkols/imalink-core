"""
Image Validation Module

Validates image files before processing.
"""

from pathlib import Path
from typing import Tuple, Optional

from PIL import Image

from ..image.formats import FormatDetector


class ImageValidator:
    """Validate image files before processing"""
    
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
    MIN_DIMENSIONS = (100, 100)
    MAX_DIMENSIONS = (50000, 50000)
    
    @staticmethod
    def validate_file(file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate image file.
        
        Checks:
        - File exists
        - File size within limits
        - Format is supported
        - Image can be opened
        - Dimensions are reasonable
        
        Args:
            file_path: Path to image file
            
        Returns:
            (is_valid, error_message) tuple
        """
        # Check file exists
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        
        if not file_path.is_file():
            return False, f"Not a file: {file_path}"
        
        # Check file size
        try:
            size = file_path.stat().st_size
        except OSError as e:
            return False, f"Cannot access file: {e}"
        
        if size > ImageValidator.MAX_FILE_SIZE:
            size_mb = size / 1024 / 1024
            max_mb = ImageValidator.MAX_FILE_SIZE / 1024 / 1024
            return False, f"File too large: {size_mb:.1f} MB (max {max_mb:.0f} MB)"
        
        if size == 0:
            return False, "File is empty"
        
        # Check format
        if not FormatDetector.is_supported(file_path):
            return False, f"Unsupported format: {file_path.suffix}"
        
        # Try to open with PIL
        try:
            with Image.open(file_path) as img:
                # Check dimensions
                w, h = img.size
                
                min_w, min_h = ImageValidator.MIN_DIMENSIONS
                if w < min_w or h < min_h:
                    return False, f"Image too small: {w}x{h}px (min {min_w}x{min_h}px)"
                
                max_w, max_h = ImageValidator.MAX_DIMENSIONS
                if w > max_w or h > max_h:
                    return False, f"Image too large: {w}x{h}px (max {max_w}x{max_h}px)"
        
        except Exception as e:
            return False, f"Cannot open image: {e}"
        
        # All checks passed
        return True, None
    
    @staticmethod
    def is_valid(file_path: Path) -> bool:
        """
        Quick check if file is valid.
        
        Args:
            file_path: Path to image file
            
        Returns:
            True if file is valid
        """
        valid, _ = ImageValidator.validate_file(file_path)
        return valid
