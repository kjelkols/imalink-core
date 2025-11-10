"""
Tests for high-level process_image() API

Tests the complete processing pipeline:
- Validation → EXIF extraction → Preview generation → Hothash
"""

import pytest
from pathlib import Path
from imalink_core import process_image
from imalink_core.models.import_result import ImportResult


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "images"


class TestProcessImageSuccess:
    """Test successful image processing"""
    
    def test_process_jpeg_basic(self):
        """Should process basic JPEG successfully"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        assert isinstance(result, ImportResult)
        assert result.success is True
        assert result.error is None
        
        # Should have all components
        assert result.hothash is not None
        assert result.photo is not None
        assert result.metadata is not None
        assert result.camera_settings is not None
        assert result.hotpreview_base64 is not None
        assert result.coldpreview_bytes is not None
    
    def test_process_jpeg_with_gps(self):
        """Should process JPEG with GPS correctly"""
        file_path = FIXTURES_DIR / "jpeg_gps.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        assert result.success is True
        
        # GPS should be extracted
        assert result.photo.has_gps is True
        assert result.photo.gps_latitude is not None
        assert result.photo.gps_longitude is not None
        
        # Oslo coordinates
        assert 59.0 < result.photo.gps_latitude < 60.0
        assert 10.0 < result.photo.gps_longitude < 11.0
    
    def test_process_jpeg_without_exif(self):
        """Should handle JPEG without EXIF gracefully"""
        file_path = FIXTURES_DIR / "jpeg_no_exif.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        assert result.success is True
        
        # Should still have previews and hothash
        assert result.hothash is not None
        assert result.hotpreview_base64 is not None
        
        # But no EXIF metadata
        assert result.photo.camera_make is None
        assert result.photo.taken_at is None
        assert result.photo.has_gps is False
    
    def test_process_png(self):
        """Should process PNG successfully"""
        file_path = FIXTURES_DIR / "png_basic.png"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        assert result.success is True
        assert result.hothash is not None
        
        # PNG has no EXIF, but processing succeeds
        assert result.photo.camera_make is None
    
    def test_process_tiny_image(self):
        """Should process very small image"""
        file_path = FIXTURES_DIR / "tiny_100x100.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        assert result.success is True
        assert result.photo.width == 100
        assert result.photo.height == 100


class TestProcessImageFailure:
    """Test error handling"""
    
    def test_process_nonexistent_file(self):
        """Should fail gracefully for nonexistent file"""
        result = process_image(Path("nonexistent.jpg"), coldpreview_max_size=1920)
        
        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()
        
        # Should not have photo data
        assert result.photo is None
        assert result.hothash is None
    
    def test_failed_property(self):
        """Should have failed property"""
        result = process_image(Path("nonexistent.jpg"), coldpreview_max_size=1920)
        
        assert result.failed is True


class TestCorePhotoPopulation:
    """Test that CorePhoto object is properly populated"""
    
    def test_corephoto_has_all_fields(self):
        """Should populate all CorePhoto fields from real image"""
        file_path = FIXTURES_DIR / "gps_sample.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        assert result.success is True
        photo = result.photo
        
        # Hothash and previews
        assert photo.hothash is not None
        assert len(photo.hothash) == 64  # SHA256 hex
        assert photo.hotpreview_base64 is not None
        assert photo.hotpreview_width > 0
        assert photo.hotpreview_height > 0
        assert photo.coldpreview_base64 is not None
        assert photo.coldpreview_width > 0
        assert photo.coldpreview_height > 0
        
        # File info
        assert photo.primary_filename == "gps_sample.jpg"
        assert photo.width == 640
        assert photo.height == 480
        
        # Metadata (GPS sample has GPS data)
        assert photo.camera_make == "NIKON"
        assert photo.camera_model == "COOLPIX P6000"
        assert photo.has_gps is True
        assert photo.gps_latitude is not None
        assert photo.gps_longitude is not None
    
    def test_corephoto_serialization(self):
        """Should serialize CorePhoto to dict"""
        file_path = FIXTURES_DIR / "orientation_6.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        photo_dict = result.photo.to_dict()
        
        assert isinstance(photo_dict, dict)
        assert photo_dict['hothash'] is not None
        assert photo_dict['width'] == 450
        assert photo_dict['height'] == 600


class TestMetadataAccuracy:
    """Test metadata extraction accuracy"""
    
    def test_metadata_from_nikon_gps(self):
        """Should extract Nikon Coolpix GPS metadata correctly"""
        file_path = FIXTURES_DIR / "gps_sample.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        assert result.metadata.camera_make == "NIKON"
        assert result.metadata.camera_model == "COOLPIX P6000"
        # GPS coordinates from Tuscany, Italy
        assert result.metadata.gps_latitude is not None
        assert result.metadata.gps_longitude is not None
        # CorePhoto has has_gps field
        assert result.photo.has_gps is True
    
    def test_metadata_from_orientation(self):
        """Should extract metadata from image with EXIF orientation"""
        file_path = FIXTURES_DIR / "orientation_6.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        # Image has orientation data and should be processed successfully
        assert result.success is True
        assert result.metadata.width == 450
        assert result.metadata.height == 600
    
    def test_metadata_graceful_degradation(self):
        """Should handle images with incomplete EXIF gracefully"""
        file_path = FIXTURES_DIR / "jpeg_no_exif.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        # Should still succeed even without EXIF
        assert result.success is True
        # Camera settings are optional (70-90% reliability tier)
        # No assertions about ISO, aperture, etc. - they may be None


class TestPreviewInclusion:
    """Test that both previews are included in result"""
    
    def test_hotpreview_included(self):
        """Should include hotpreview in base64"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        assert result.hotpreview_base64 is not None
        assert len(result.hotpreview_base64) > 0
        
        # Should be valid base64
        import base64
        decoded = base64.b64decode(result.hotpreview_base64)
        assert len(decoded) > 0
    
    def test_coldpreview_included(self):
        """Should include coldpreview as bytes"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        result = process_image(file_path, coldpreview_max_size=1920)
        
        assert result.coldpreview_bytes is not None
        assert len(result.coldpreview_bytes) > 0
        
        # Coldpreview should be larger than hotpreview
        import base64
        hotpreview_size = len(base64.b64decode(result.hotpreview_base64))
        coldpreview_size = len(result.coldpreview_bytes)
        
        assert coldpreview_size > hotpreview_size
    
    def test_skip_coldpreview(self):
        """Should skip coldpreview when coldpreview_max_size=None"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        result = process_image(file_path, coldpreview_max_size=None)
        
        # Should succeed
        assert result.success is True
        
        # Hotpreview should still be present
        assert result.hotpreview_base64 is not None
        assert result.photo.hotpreview_base64 is not None
        assert result.photo.hothash is not None
        
        # Coldpreview should be None
        assert result.coldpreview_bytes is None
        assert result.photo.coldpreview_base64 is None
        assert result.photo.coldpreview_width is None
        assert result.photo.coldpreview_height is None
    
    def test_custom_coldpreview_size(self):
        """Should generate coldpreview with custom size"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        result = process_image(file_path, coldpreview_max_size=1024)
        
        assert result.success is True
        
        # Coldpreview should exist and fit within 1024px
        assert result.photo.coldpreview_base64 is not None
        assert result.photo.coldpreview_width <= 1024
        assert result.photo.coldpreview_height <= 1024

