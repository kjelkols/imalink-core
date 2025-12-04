"""
RAW Image Processing Tests

Tests for RAW file format support (CR2, NEF, ARW, DNG, etc.)
"""

import pytest
from pathlib import Path

from imalink_core.image.raw_processor import RawProcessor
from imalink_core.image.formats import FormatDetector


class TestRawProcessor:
    """Test RAW file processing"""
    
    def test_is_available(self):
        """Test rawpy availability check"""
        # Should return bool without crashing
        available = RawProcessor.is_available()
        assert isinstance(available, bool)
    
    def test_is_raw_file(self):
        """Test RAW file detection by extension"""
        # Nikon
        assert RawProcessor.is_raw_file("photo.NEF") is True
        assert RawProcessor.is_raw_file("photo.nef") is True
        assert RawProcessor.is_raw_file("photo.NRW") is True
        
        # Canon
        assert RawProcessor.is_raw_file("photo.CR2") is True
        assert RawProcessor.is_raw_file("photo.cr2") is True
        assert RawProcessor.is_raw_file("photo.CR3") is True
        assert RawProcessor.is_raw_file("photo.CRW") is True
        
        # Sony
        assert RawProcessor.is_raw_file("photo.ARW") is True
        assert RawProcessor.is_raw_file("photo.arw") is True
        assert RawProcessor.is_raw_file("photo.SRF") is True
        assert RawProcessor.is_raw_file("photo.SR2") is True
        
        # Adobe/Universal
        assert RawProcessor.is_raw_file("photo.DNG") is True
        assert RawProcessor.is_raw_file("photo.dng") is True
        
        # Olympus
        assert RawProcessor.is_raw_file("photo.ORF") is True
        
        # Panasonic
        assert RawProcessor.is_raw_file("photo.RW2") is True
        assert RawProcessor.is_raw_file("photo.RAW") is True
        
        # Fujifilm
        assert RawProcessor.is_raw_file("photo.RAF") is True
        
        # Pentax
        assert RawProcessor.is_raw_file("photo.PEF") is True
        assert RawProcessor.is_raw_file("photo.PTX") is True
        
        # Sigma
        assert RawProcessor.is_raw_file("photo.X3F") is True
        
        # Leica
        assert RawProcessor.is_raw_file("photo.RWL") is True
        
        # Minolta
        assert RawProcessor.is_raw_file("photo.MRW") is True
        
        # Samsung
        assert RawProcessor.is_raw_file("photo.SRW") is True
        
        # Hasselblad
        assert RawProcessor.is_raw_file("photo.3FR") is True
        
        # Kodak
        assert RawProcessor.is_raw_file("photo.DCR") is True
        assert RawProcessor.is_raw_file("photo.KDC") is True
        
        # Mamiya
        assert RawProcessor.is_raw_file("photo.MEF") is True
        
        # Phase One
        assert RawProcessor.is_raw_file("photo.IIQ") is True
        
        # Not RAW
        assert RawProcessor.is_raw_file("photo.jpg") is False
        assert RawProcessor.is_raw_file("photo.JPEG") is False
        assert RawProcessor.is_raw_file("photo.png") is False
    
    def test_convert_raw_without_rawpy(self):
        """Test RAW conversion when rawpy not installed"""
        if RawProcessor.is_available():
            pytest.skip("rawpy is installed, can't test unavailable scenario")
        
        success, img, error = RawProcessor.convert_raw_to_image(b"fake raw data")
        assert success is False
        assert img is None
        assert "rawpy not installed" in error
    
    @pytest.mark.skipif(not RawProcessor.is_available(), reason="rawpy not installed")
    def test_convert_invalid_raw(self):
        """Test RAW conversion with invalid data"""
        success, img, error = RawProcessor.convert_raw_to_image(b"not a raw file")
        assert success is False
        assert img is None
        assert error is not None
    
    @pytest.mark.skipif(not RawProcessor.is_available(), reason="rawpy not installed")
    def test_convert_real_raw(self):
        """Test RAW conversion with real RAW file"""
        # Check for test RAW files
        fixtures_dir = Path(__file__).parent / "fixtures" / "images"
        
        raw_files = list(fixtures_dir.glob("*.NEF")) + \
                   list(fixtures_dir.glob("*.CR2")) + \
                   list(fixtures_dir.glob("*.ARW")) + \
                   list(fixtures_dir.glob("*.DNG"))
        
        if not raw_files:
            pytest.skip("No RAW test files found in fixtures/images/")
        
        # Test with first available RAW file
        raw_file = raw_files[0]
        with open(raw_file, 'rb') as f:
            raw_bytes = f.read()
        
        success, img, error = RawProcessor.convert_raw_to_image(raw_bytes)
        
        assert success is True, f"RAW conversion failed: {error}"
        assert img is not None
        assert error is None
        
        # Check image is valid PIL Image
        assert img.mode in ['RGB', 'RGBA']
        assert img.width > 0
        assert img.height > 0
        
        print(f"\n✅ RAW Conversion Success: {raw_file.name}")
        print(f"   Dimensions: {img.width}x{img.height}")
        print(f"   Mode: {img.mode}")
    
    @pytest.mark.skipif(not RawProcessor.is_available(), reason="rawpy not installed")
    def test_get_raw_info(self):
        """Test extracting RAW file info"""
        fixtures_dir = Path(__file__).parent / "fixtures" / "images"
        
        raw_files = list(fixtures_dir.glob("*.NEF")) + \
                   list(fixtures_dir.glob("*.CR2")) + \
                   list(fixtures_dir.glob("*.ARW")) + \
                   list(fixtures_dir.glob("*.DNG"))
        
        if not raw_files:
            pytest.skip("No RAW test files found in fixtures/images/")
        
        raw_file = raw_files[0]
        with open(raw_file, 'rb') as f:
            raw_bytes = f.read()
        
        info = RawProcessor.get_raw_info(raw_bytes)
        
        assert info is not None
        assert 'width' in info
        assert 'height' in info
        assert info['width'] > 0
        assert info['height'] > 0
        
        print(f"\n✅ RAW Info: {raw_file.name}")
        print(f"   Dimensions: {info['width']}x{info['height']}")
        print(f"   Camera: {info.get('camera_make')} {info.get('camera_model')}")
        print(f"   ISO: {info.get('iso')}")


class TestFormatDetectorRAW:
    """Test RAW format detection in FormatDetector"""
    
    def test_raw_extensions_detected(self):
        """Test that RAW extensions are in supported formats"""
        # Major brands
        assert '.nef' in FormatDetector.RAW_EXTENSIONS
        assert '.cr2' in FormatDetector.RAW_EXTENSIONS
        assert '.cr3' in FormatDetector.RAW_EXTENSIONS
        assert '.arw' in FormatDetector.RAW_EXTENSIONS
        assert '.dng' in FormatDetector.RAW_EXTENSIONS
        assert '.orf' in FormatDetector.RAW_EXTENSIONS
        assert '.rw2' in FormatDetector.RAW_EXTENSIONS
        assert '.raf' in FormatDetector.RAW_EXTENSIONS
        assert '.pef' in FormatDetector.RAW_EXTENSIONS
        assert '.x3f' in FormatDetector.RAW_EXTENSIONS
        
        # Additional formats
        assert '.rwl' in FormatDetector.RAW_EXTENSIONS
        assert '.mrw' in FormatDetector.RAW_EXTENSIONS
        assert '.srw' in FormatDetector.RAW_EXTENSIONS
        assert '.3fr' in FormatDetector.RAW_EXTENSIONS
        assert '.iiq' in FormatDetector.RAW_EXTENSIONS
    
    def test_raw_is_supported(self):
        """Test that RAW files are marked as supported"""
        assert FormatDetector.is_supported(Path("photo.NEF")) is True
        assert FormatDetector.is_supported(Path("photo.CR2")) is True
        assert FormatDetector.is_supported(Path("photo.CR3")) is True
        assert FormatDetector.is_supported(Path("photo.ARW")) is True
        assert FormatDetector.is_supported(Path("photo.DNG")) is True
        assert FormatDetector.is_supported(Path("photo.ORF")) is True
        assert FormatDetector.is_supported(Path("photo.RW2")) is True
        assert FormatDetector.is_supported(Path("photo.RAF")) is True
        assert FormatDetector.is_supported(Path("photo.PEF")) is True
        assert FormatDetector.is_supported(Path("photo.X3F")) is True
        assert FormatDetector.is_supported(Path("photo.3FR")) is True
        assert FormatDetector.is_supported(Path("photo.IIQ")) is True
    
    def test_raw_format_detection(self):
        """Test RAW format is correctly identified"""
        assert FormatDetector.is_raw_format(Path("photo.NEF")) is True
        assert FormatDetector.is_raw_format(Path("photo.CR2")) is True
        assert FormatDetector.is_raw_format(Path("photo.CR3")) is True
        assert FormatDetector.is_raw_format(Path("photo.ARW")) is True
        assert FormatDetector.is_raw_format(Path("photo.DNG")) is True
        assert FormatDetector.is_raw_format(Path("photo.ORF")) is True
        assert FormatDetector.is_raw_format(Path("photo.RW2")) is True
        assert FormatDetector.is_raw_format(Path("photo.RAF")) is True
        assert FormatDetector.is_raw_format(Path("photo.PEF")) is True
        assert FormatDetector.is_raw_format(Path("photo.X3F")) is True
        assert FormatDetector.is_raw_format(Path("photo.3FR")) is True
        assert FormatDetector.is_raw_format(Path("photo.IIQ")) is True
        assert FormatDetector.is_raw_format(Path("photo.MRW")) is True
        assert FormatDetector.is_raw_format(Path("photo.SRW")) is True
        
        # Not RAW
        assert FormatDetector.is_raw_format(Path("photo.jpg")) is False
        assert FormatDetector.is_raw_format(Path("photo.png")) is False
