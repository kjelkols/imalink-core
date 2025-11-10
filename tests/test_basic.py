"""
Basic tests for imalink-core

Run with: pytest tests/
"""

import pytest
from pathlib import Path
from imalink_core import (
    ExifExtractor,
    PreviewGenerator,
    CorePhoto,
    ImageValidator,
    process_image,
    __version__
)


def test_version():
    """Test that version is defined"""
    assert __version__ == "1.0.0"


def test_exif_extractor_basic():
    """Test ExifExtractor basic metadata"""
    # Should handle non-existent file gracefully
    metadata = ExifExtractor.extract_basic(Path("nonexistent.jpg"))
    assert metadata is not None
    assert metadata.taken_at is None


def test_exif_extractor_camera_settings():
    """Test ExifExtractor camera settings"""
    # Should handle non-existent file gracefully
    settings = ExifExtractor.extract_camera_settings(Path("nonexistent.jpg"))
    assert settings is not None
    assert settings.iso is None


def test_image_validator():
    """Test ImageValidator"""
    # Non-existent file should fail validation
    is_valid, error = ImageValidator.validate_file(Path("nonexistent.jpg"))
    assert not is_valid
    assert "not found" in error.lower()


def test_photo_model():
    """Test CorePhoto model creation and serialization"""
    photo = CorePhoto(
        hothash="abc123def456",
        primary_filename="test.jpg",
        width=1920,
        height=1080,
    )
    
    assert photo.hothash == "abc123def456"
    assert photo.display_filename == "test.jpg"
    
    # Test to_dict/from_dict round-trip
    data = photo.to_dict()
    assert isinstance(data, dict)
    assert data['hothash'] == "abc123def456"
    
    photo2 = CorePhoto.from_dict(data)
    assert photo2.hothash == photo.hothash
    assert photo2.primary_filename == photo.primary_filename


def test_process_image_nonexistent():
    """Test process_image with non-existent file"""
    result = process_image(Path("nonexistent.jpg"), coldpreview_max_size=1920)
    
    assert not result.success
    assert result.error is not None
    assert "not found" in result.error.lower()


# Skip actual image processing tests if no test images available
# Add real test images to tests/fixtures/ for full testing
