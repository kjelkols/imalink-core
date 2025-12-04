"""
RAW Image Processing

Converts RAW camera files (CR2, NEF, ARW, DNG) to PIL Images for processing.
Uses rawpy library which wraps LibRaw.
"""

from io import BytesIO
from typing import Optional, Tuple

from PIL import Image

try:
    import rawpy
    RAWPY_AVAILABLE = True
except ImportError:
    RAWPY_AVAILABLE = False


class RawProcessor:
    """Process RAW camera files"""
    
    RAW_EXTENSIONS = {
        # Nikon
        '.nef', '.nrw',
        # Canon
        '.cr2', '.cr3', '.crw',
        # Sony
        '.arw', '.srf', '.sr2',
        # Fujifilm
        '.raf',
        # Olympus/OM System
        '.orf',
        # Panasonic
        '.rw2', '.raw',
        # Pentax
        '.pef', '.ptx',
        # Sigma
        '.x3f',
        # Leica
        '.rwl', '.dng',
        # Minolta
        '.mrw',
        # Samsung
        '.srw',
        # Hasselblad
        '.3fr',
        # Kodak
        '.dcr', '.kdc',
        # Mamiya
        '.mef',
        # Phase One
        '.iiq',
        # Adobe/Universal
        '.dng',
    }
    
    @staticmethod
    def is_available() -> bool:
        """
        Check if rawpy is installed and available.
        
        Returns:
            True if rawpy can be imported
        """
        return RAWPY_AVAILABLE
    
    @staticmethod
    def is_raw_file(filename: str) -> bool:
        """
        Check if file extension indicates RAW format.
        
        Args:
            filename: Filename with extension
            
        Returns:
            True if filename has RAW extension
        """
        ext = filename.lower()
        return any(ext.endswith(raw_ext) for raw_ext in RawProcessor.RAW_EXTENSIONS)
    
    @staticmethod
    def convert_raw_to_image(raw_bytes: bytes) -> Tuple[bool, Optional[Image.Image], Optional[str]]:
        """
        Convert RAW file bytes to PIL Image.
        
        Uses rawpy (LibRaw) to process RAW data and returns RGB PIL Image.
        
        Args:
            raw_bytes: RAW file content as bytes
            
        Returns:
            Tuple of (success, image, error_message)
            - success: True if conversion succeeded
            - image: PIL Image object if successful, None if failed
            - error_message: Error description if failed, None if successful
            
        Example:
            >>> with open('photo.NEF', 'rb') as f:
            ...     raw_bytes = f.read()
            >>> success, img, error = RawProcessor.convert_raw_to_image(raw_bytes)
            >>> if success:
            ...     img.save('photo.jpg')
        """
        if not RAWPY_AVAILABLE:
            return (False, None, "rawpy not installed - run: uv pip install rawpy")
        
        try:
            # Open RAW file from bytes
            with rawpy.imread(BytesIO(raw_bytes)) as raw:
                # Process RAW to RGB array
                # use_camera_wb=True: Use camera white balance
                # output_bps=8: 8-bit output (standard JPEG range)
                rgb_array = raw.postprocess(
                    use_camera_wb=True,
                    output_bps=8,
                    no_auto_bright=False,
                    output_color=rawpy.ColorSpace.sRGB
                )
            
            # Convert numpy array to PIL Image
            img = Image.fromarray(rgb_array)
            
            return (True, img, None)
            
        except rawpy.LibRawError as e:
            return (False, None, f"LibRaw error: {str(e)}")
        except Exception as e:
            return (False, None, f"RAW processing failed: {str(e)}")
    
    @staticmethod
    def get_raw_info(raw_bytes: bytes) -> Optional[dict]:
        """
        Extract basic info from RAW file without full processing.
        
        Args:
            raw_bytes: RAW file content as bytes
            
        Returns:
            Dictionary with RAW file info or None if failed
        """
        if not RAWPY_AVAILABLE:
            return None
        
        try:
            with rawpy.imread(BytesIO(raw_bytes)) as raw:
                return {
                    'width': raw.sizes.width,
                    'height': raw.sizes.height,
                    'raw_width': raw.sizes.raw_width,
                    'raw_height': raw.sizes.raw_height,
                    'camera_make': raw.camera_maker.decode('utf-8', errors='ignore').strip() if raw.camera_maker else None,
                    'camera_model': raw.camera_model.decode('utf-8', errors='ignore').strip() if raw.camera_model else None,
                    'iso': raw.iso_speed,
                }
        except Exception:
            return None
