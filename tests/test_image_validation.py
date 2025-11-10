"""
Tests for image validation

Tests file validation before processing:
- File existence
- File size limits
- Format support
- Dimension constraints
"""

import pytest
from pathlib import Path
from imalink_core.validation.image_validator import ImageValidator


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "images"


class TestFileValidation:
    """Test basic file validation"""
    
    def test_validate_existing_file(self):
        """Should validate existing JPEG file"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        is_valid, error = ImageValidator.validate_file(file_path)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_nonexistent_file(self):
        """Should reject nonexistent file"""
        is_valid, error = ImageValidator.validate_file(Path("nonexistent.jpg"))
        
        assert is_valid is False
        assert error is not None
        assert "not found" in error.lower()
    
    def test_validate_directory_as_file(self):
        """Should reject directory"""
        is_valid, error = ImageValidator.validate_file(FIXTURES_DIR)
        
        assert is_valid is False
        assert error is not None
        assert "not a file" in error.lower()


class TestFormatValidation:
    """Test image format validation"""
    
    def test_validate_jpeg(self):
        """Should accept JPEG format"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        is_valid, error = ImageValidator.validate_file(file_path)
        
        assert is_valid is True
    
    def test_validate_png(self):
        """Should accept PNG format"""
        file_path = FIXTURES_DIR / "png_basic.png"
        is_valid, error = ImageValidator.validate_file(file_path)
        
        assert is_valid is True


class TestDimensionValidation:
    """Test image dimension constraints"""
    
    def test_validate_normal_dimensions(self):
        """Should accept normal image dimensions (800x600)"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        is_valid, error = ImageValidator.validate_file(file_path)
        
        assert is_valid is True
    
    def test_validate_small_dimensions(self):
        """Should accept small but valid dimensions (100x100)"""
        file_path = FIXTURES_DIR / "tiny_100x100.jpg"
        is_valid, error = ImageValidator.validate_file(file_path)
        
        # 100x100 is within MIN_DIMENSIONS
        assert is_valid is True
    
    def test_validate_landscape_dimensions(self):
        """Should accept landscape dimensions (1200x800)"""
        file_path = FIXTURES_DIR / "jpeg_landscape.jpg"
        is_valid, error = ImageValidator.validate_file(file_path)
        
        assert is_valid is True


class TestQuickValidation:
    """Test is_valid() convenience method"""
    
    def test_is_valid_shortcut(self):
        """Should provide quick validation check"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        
        assert ImageValidator.is_valid(file_path) is True
    
    def test_is_valid_for_invalid_file(self):
        """Should return False for invalid file"""
        assert ImageValidator.is_valid(Path("nonexistent.jpg")) is False
