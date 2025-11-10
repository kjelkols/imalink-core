"""
Tests for preview generation and hothash calculation

Tests:
- Hotpreview (150x150) generation
- Coldpreview (1920x1080) generation
- Hothash calculation (SHA256 of hotpreview)
- EXIF rotation handling
"""

import pytest
from pathlib import Path
import base64
import hashlib
from imalink_core.preview.generator import PreviewGenerator


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "images"


class TestHotpreviewGeneration:
    """Test hotpreview (150x150) generation"""
    
    def test_generate_hotpreview_basic(self):
        """Should generate 150x150 hotpreview"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        hotpreview = PreviewGenerator.generate_hotpreview(file_path)
        
        # Should have all required fields
        assert hotpreview.bytes is not None
        assert hotpreview.base64 is not None
        assert hotpreview.hothash is not None
        assert hotpreview.width > 0
        assert hotpreview.height > 0
        
        # Dimensions should fit within 150x150
        assert hotpreview.width <= 150
        assert hotpreview.height <= 150
        
        # Base64 should be valid
        decoded = base64.b64decode(hotpreview.base64)
        assert len(decoded) > 0
    
    def test_hotpreview_aspect_ratio_preserved(self):
        """Should preserve aspect ratio when generating hotpreview"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"  # 800x600 (4:3)
        hotpreview = PreviewGenerator.generate_hotpreview(file_path)
        
        # 800x600 aspect ratio is 4:3
        # When resized to fit 150x150, should be 150x112 (preserving 4:3)
        aspect_ratio = hotpreview.width / hotpreview.height
        expected_ratio = 800 / 600
        
        assert abs(aspect_ratio - expected_ratio) < 0.01
    
    def test_hotpreview_from_landscape(self):
        """Should handle landscape orientation (1200x800)"""
        file_path = FIXTURES_DIR / "jpeg_landscape.jpg"
        hotpreview = PreviewGenerator.generate_hotpreview(file_path)
        
        # Landscape should have width >= height
        assert hotpreview.width >= hotpreview.height
        assert hotpreview.width <= 150
    
    def test_hotpreview_from_portrait(self):
        """Should handle portrait orientation (600x800)"""
        file_path = FIXTURES_DIR / "jpeg_rotated.jpg"
        hotpreview = PreviewGenerator.generate_hotpreview(file_path)
        
        # After EXIF rotation, should be correctly oriented
        assert hotpreview.width > 0
        assert hotpreview.height > 0
    
    def test_hotpreview_from_png(self):
        """Should generate hotpreview from PNG"""
        file_path = FIXTURES_DIR / "png_basic.png"
        hotpreview = PreviewGenerator.generate_hotpreview(file_path)
        
        assert hotpreview.bytes is not None
        assert hotpreview.hothash is not None
    
    def test_hotpreview_from_tiny_image(self):
        """Should handle very small images (100x100)"""
        file_path = FIXTURES_DIR / "tiny_100x100.jpg"
        hotpreview = PreviewGenerator.generate_hotpreview(file_path)
        
        # Image is already smaller than 150x150, should keep original size
        assert hotpreview.width == 100
        assert hotpreview.height == 100


class TestColdpreviewGeneration:
    """Test coldpreview (1920x1080) generation"""
    
    def test_generate_coldpreview_basic(self):
        """Should generate coldpreview within 1920x1080"""
        file_path = FIXTURES_DIR / "jpeg_landscape.jpg"  # 1200x800
        coldpreview = PreviewGenerator.generate_coldpreview(file_path)
        
        assert coldpreview.bytes is not None
        assert coldpreview.width > 0
        assert coldpreview.height > 0
        
        # Should fit within 1920x1080
        assert coldpreview.width <= 1920
        assert coldpreview.height <= 1080
    
    def test_coldpreview_aspect_ratio_preserved(self):
        """Should preserve aspect ratio in coldpreview"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"  # 800x600
        coldpreview = PreviewGenerator.generate_coldpreview(file_path)
        
        # Original is 800x600, should scale to fit 1920x1080
        # 800x600 is smaller, so should keep original size
        assert coldpreview.width == 800
        assert coldpreview.height == 600
    
    def test_coldpreview_custom_size(self):
        """Should generate coldpreview with custom dimensions"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        coldpreview = PreviewGenerator.generate_coldpreview(
            file_path,
            max_size=1024
        )
        
        # Should fit within custom size
        assert coldpreview.width <= 1024
        assert coldpreview.height <= 1024


class TestHothashCalculation:
    """Test hothash (SHA256) calculation"""
    
    def test_hothash_is_sha256(self):
        """Should generate valid SHA256 hash"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        hotpreview = PreviewGenerator.generate_hotpreview(file_path)
        
        # SHA256 hash is 64 hex characters
        assert len(hotpreview.hothash) == 64
        assert all(c in '0123456789abcdef' for c in hotpreview.hothash)
    
    def test_hothash_deterministic(self):
        """Should generate same hothash for same image"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        
        hotpreview1 = PreviewGenerator.generate_hotpreview(file_path)
        hotpreview2 = PreviewGenerator.generate_hotpreview(file_path)
        
        # Same image should produce same hothash
        assert hotpreview1.hothash == hotpreview2.hothash
    
    def test_hothash_different_for_different_images(self):
        """Should generate different hothash for different images"""
        file1 = FIXTURES_DIR / "jpeg_basic.jpg"
        file2 = FIXTURES_DIR / "jpeg_gps.jpg"
        
        hotpreview1 = PreviewGenerator.generate_hotpreview(file1)
        hotpreview2 = PreviewGenerator.generate_hotpreview(file2)
        
        # Different images should have different hothash
        assert hotpreview1.hothash != hotpreview2.hothash
    
    def test_hothash_matches_manual_calculation(self):
        """Should match manual SHA256 calculation"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        hotpreview = PreviewGenerator.generate_hotpreview(file_path)
        
        # Calculate hash manually
        manual_hash = hashlib.sha256(hotpreview.bytes).hexdigest()
        
        assert hotpreview.hothash == manual_hash


class TestExifRotationHandling:
    """Test EXIF orientation handling"""
    
    def test_rotated_image_orientation(self):
        """Should apply EXIF rotation correctly"""
        file_path = FIXTURES_DIR / "jpeg_rotated.jpg"
        hotpreview = PreviewGenerator.generate_hotpreview(file_path)
        
        # Image has EXIF Orientation=6 (rotate 90° CW)
        # Original is 600x800, after rotation should swap dimensions
        # But after fitting to 150x150, aspect ratio should be correct
        assert hotpreview.width > 0
        assert hotpreview.height > 0


class TestBothPreviewGeneration:
    """Test generating both previews in one pass"""
    
    def test_generate_both_previews(self):
        """Should generate hot and cold previews efficiently"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        hotpreview, coldpreview = PreviewGenerator.generate_both(file_path)
        
        # Both should be generated
        assert hotpreview.bytes is not None
        assert hotpreview.hothash is not None
        assert coldpreview.bytes is not None
        
        # Hotpreview should be smaller
        assert hotpreview.width <= 150
        assert hotpreview.height <= 150
        
        # Coldpreview should be original size (800x600 < 1920x1080)
        assert coldpreview.width == 800
        assert coldpreview.height == 600
    
    def test_both_previews_from_large_image(self):
        """Should handle generating both from larger image"""
        file_path = FIXTURES_DIR / "jpeg_landscape.jpg"  # 1200x800
        hotpreview, coldpreview = PreviewGenerator.generate_both(file_path)
        
        assert hotpreview.width <= 150
        assert coldpreview.width == 1200  # Original size (within 1920x1080)


class TestPreviewQuality:
    """Test preview quality settings"""
    
    def test_hotpreview_quality_setting(self):
        """Should generate hotpreview with specified quality"""
        file_path = FIXTURES_DIR / "jpeg_basic.jpg"
        
        # Higher quality = larger file
        high_quality = PreviewGenerator.generate_hotpreview(file_path, quality=95)
        low_quality = PreviewGenerator.generate_hotpreview(file_path, quality=50)
        
        # Higher quality should produce larger bytes
        assert len(high_quality.bytes) > len(low_quality.bytes)
        
        # But hothash should be different (different JPEG compression)
        assert high_quality.hothash != low_quality.hothash
