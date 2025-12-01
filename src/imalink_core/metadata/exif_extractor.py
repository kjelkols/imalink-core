"""
EXIF Metadata Extraction Module

Provides reliable extraction of EXIF metadata from image files.
"""

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


@dataclass
class BasicMetadata:
    """
    Core metadata that is highly reliable (98%+ across all cameras).
    
    Attributes:
        taken_at: ISO 8601 timestamp when photo was taken
        width: Image width in pixels
        height: Image height in pixels
        camera_make: Camera manufacturer
        camera_model: Camera model
        gps_latitude: GPS latitude in decimal degrees
        gps_longitude: GPS longitude in decimal degrees
        gps_altitude: GPS altitude in meters
        gps_timestamp: GPS time when photo was taken (ISO 8601)
        gps_datestamp: GPS date when photo was taken (YYYY:MM:DD)
        gps_map_datum: Geodetic survey data used (e.g., WGS-84)
    """
    taken_at: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_altitude: Optional[float] = None
    gps_timestamp: Optional[str] = None
    gps_datestamp: Optional[str] = None
    gps_map_datum: Optional[str] = None


@dataclass
class CameraSettings:
    """
    Camera settings that are moderately reliable (70-90% from DSLRs).
    
    This is best-effort extraction. Missing values are expected and normal.
    
    Attributes:
        iso: ISO speed (e.g., 100, 400, 1600)
        aperture: F-stop value (e.g., 2.8, 5.6)
        shutter_speed: Exposure time (e.g., "1/1000")
        focal_length: Lens focal length in mm (e.g., 50, 85)
        lens_model: Lens name/model
        lens_make: Lens manufacturer
        flash: Flash status
        exposure_program: Exposure mode
        metering_mode: Metering mode
        white_balance: White balance setting
    """
    iso: Optional[int] = None
    aperture: Optional[float] = None
    shutter_speed: Optional[str] = None
    focal_length: Optional[float] = None
    lens_model: Optional[str] = None
    lens_make: Optional[str] = None
    flash: Optional[str] = None
    exposure_program: Optional[str] = None
    metering_mode: Optional[str] = None
    white_balance: Optional[str] = None


class ExifExtractor:
    """Extracts EXIF metadata from images"""
    
    @staticmethod
    def extract_basic(image_path: Path) -> BasicMetadata:
        """
        Extract core metadata that is highly reliable.
        
        Args:
            image_path: Path to image file
            
        Returns:
            BasicMetadata object with core metadata
        """
        result = BasicMetadata()
        
        try:
            with Image.open(image_path) as img:
                # Get dimensions
                result.width, result.height = img.size
                
                # Get EXIF data
                exif = img.getexif()
                if not exif:
                    return result
                
                # Extract timestamp (98%+ reliable)
                for datetime_tag in [36867, 36868, 306]:  # DateTimeOriginal, DateTimeDigitized, DateTime
                    if datetime_tag in exif:
                        dt_str = exif[datetime_tag]
                        if dt_str:
                            result.taken_at = ExifExtractor._standardize_datetime(dt_str)
                            break
                
                # Extract camera make and model (98%+ reliable)
                if 271 in exif:  # Make
                    result.camera_make = exif[271].strip() if exif[271] else None
                if 272 in exif:  # Model
                    result.camera_model = exif[272].strip() if exif[272] else None
                
                # Extract GPS data
                lat, lon, alt, ts, ds, datum = ExifExtractor._extract_gps_from_exif(exif)
                result.gps_latitude = lat
                result.gps_longitude = lon
                result.gps_altitude = alt
                result.gps_timestamp = ts
                result.gps_datestamp = ds
                result.gps_map_datum = datum
                
        except Exception as e:
            # Silent failure - return partial data
            pass
        
        return result
    
    @staticmethod
    def extract_basic_from_bytes(image_bytes: bytes) -> BasicMetadata:
        """
        Extract core metadata from image bytes.
        
        Args:
            image_bytes: Raw image file bytes
            
        Returns:
            BasicMetadata object with core metadata
        """
        result = BasicMetadata()
        
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                # Get dimensions
                result.width, result.height = img.size
                
                # Get EXIF data
                exif = img.getexif()
                if not exif:
                    return result
                
                # Extract timestamp (98%+ reliable)
                for datetime_tag in [36867, 36868, 306]:  # DateTimeOriginal, DateTimeDigitized, DateTime
                    if datetime_tag in exif:
                        dt_str = exif[datetime_tag]
                        if dt_str:
                            result.taken_at = ExifExtractor._standardize_datetime(dt_str)
                            break
                
                # Extract camera make/model
                if 271 in exif:  # Make
                    result.camera_make = str(exif[271]).strip()
                if 272 in exif:  # Model
                    result.camera_model = str(exif[272]).strip()
                
                # Extract GPS data (98%+ reliable if present)
                lat, lon, alt, ts, ds, datum = ExifExtractor._extract_gps_from_exif(exif)
                result.gps_latitude = lat
                result.gps_longitude = lon
                result.gps_altitude = alt
                result.gps_timestamp = ts
                result.gps_datestamp = ds
                result.gps_map_datum = datum
                
        except Exception as e:
            # Silent failure - return partial data
            pass
        
        return result
    
    @staticmethod
    def extract_camera_settings(image_path: Path) -> CameraSettings:
        """
        Extract camera settings (best-effort).
        
        Args:
            image_path: Path to image file
            
        Returns:
            CameraSettings object with camera settings
        """
        result = CameraSettings()
        
        try:
            with Image.open(image_path) as img:
                exif = img.getexif()
                if not exif:
                    return result
                
                # Try to get EXIF IFD (most camera settings are here)
                try:
                    exif_ifd = exif.get_ifd(0x8769)  # EXIF IFD
                    # Merge EXIF IFD into main exif dict for easier access
                    for tag_id, value in exif_ifd.items():
                        if tag_id not in exif:
                            exif[tag_id] = value
                except (KeyError, AttributeError):
                    pass  # No EXIF IFD, continue with main EXIF
                
                # ISO (85%+ reliable)
                if 34855 in exif:
                    result.iso = exif[34855]
                
                # Aperture (85%+ reliable)
                if 33437 in exif:  # FNumber
                    f_num = exif[33437]
                    if isinstance(f_num, tuple):
                        result.aperture = round(f_num[0] / f_num[1], 1)
                    else:
                        result.aperture = f_num
                
                # Shutter speed (85%+ reliable)
                if 33434 in exif:  # ExposureTime
                    exp = exif[33434]
                    if isinstance(exp, tuple):
                        if exp[0] == 1:
                            result.shutter_speed = f"1/{exp[1]}"
                        else:
                            result.shutter_speed = str(round(exp[0] / exp[1], 3))
                    else:
                        result.shutter_speed = str(exp)
                
                # Focal length (85%+ reliable)
                if 37386 in exif:  # FocalLength
                    focal = exif[37386]
                    if isinstance(focal, tuple):
                        result.focal_length = round(focal[0] / focal[1], 1)
                    else:
                        result.focal_length = focal
                
                # Lens info (60-70% reliable)
                if 42036 in exif:  # LensModel
                    result.lens_model = exif[42036]
                if 42035 in exif:  # LensMake
                    result.lens_make = exif[42035]
                
                # Flash (75%+ reliable)
                if 37385 in exif:  # Flash
                    flash_val = exif[37385]
                    result.flash = 'Fired' if (flash_val & 1) else 'No Flash'
                
                # Exposure program (70%+ reliable)
                if 34850 in exif:  # ExposureProgram
                    programs = {
                        0: 'Not Defined', 1: 'Manual', 2: 'Program AE',
                        3: 'Aperture Priority', 4: 'Shutter Priority',
                        5: 'Creative Program', 6: 'Action Program',
                        7: 'Portrait Mode', 8: 'Landscape Mode'
                    }
                    result.exposure_program = programs.get(exif[34850], 'Unknown')
                
                # Metering mode (70%+ reliable)
                if 37383 in exif:  # MeteringMode
                    metering = {
                        0: 'Unknown', 1: 'Average', 2: 'Center Weighted Average',
                        3: 'Spot', 4: 'Multi-Spot', 5: 'Multi-Segment', 6: 'Partial'
                    }
                    result.metering_mode = metering.get(exif[37383], 'Unknown')
                
                # White balance (70%+ reliable)
                if 41987 in exif:  # WhiteBalance
                    wb = exif[41987]
                    result.white_balance = 'Auto' if wb == 0 else 'Manual'
                    
        except Exception as e:
            # Silent failure - return partial data
            pass
        
        return result
    
    @staticmethod
    def extract_camera_settings_from_bytes(image_bytes: bytes) -> CameraSettings:
        """
        Extract camera settings from image bytes (best-effort).
        
        Args:
            image_bytes: Raw image file bytes
            
        Returns:
            CameraSettings object with available settings
        """
        result = CameraSettings()
        
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                exif = img.getexif()
                if not exif:
                    return result
                
                # Try to get EXIF IFD (most camera settings are here)
                try:
                    exif_ifd = exif.get_ifd(0x8769)  # EXIF IFD
                    # Merge EXIF IFD into main exif dict for easier access
                    for tag_id, value in exif_ifd.items():
                        if tag_id not in exif:
                            exif[tag_id] = value
                except (KeyError, AttributeError):
                    pass  # No EXIF IFD, continue with main EXIF
                
                # ISO (80-90% reliable)
                if 34855 in exif:  # ISOSpeedRatings
                    result.iso = int(exif[34855])
                
                # Aperture (85-90% reliable)
                if 33437 in exif:  # FNumber
                    result.aperture = float(exif[33437])
                
                # Shutter speed (85-90% reliable)
                if 33434 in exif:  # ExposureTime
                    exp_time = exif[33434]
                    exp_float = float(exp_time)  # Convert any type to float
                    # Convert decimal to fraction string for better readability
                    if exp_float < 1:
                        result.shutter_speed = f"1/{int(round(1/exp_float))}"
                    else:
                        result.shutter_speed = f"{exp_float:.3f}"
                
                # Focal length (80-85% reliable)
                if 37386 in exif:  # FocalLength
                    focal = exif[37386]
                    result.focal_length = float(focal)
                
                # Lens info (60-70% reliable)
                if 42036 in exif:  # LensModel
                    result.lens_model = exif[42036]
                if 42035 in exif:  # LensMake
                    result.lens_make = exif[42035]
                
                # Flash (75%+ reliable)
                if 37385 in exif:  # Flash
                    flash_val = exif[37385]
                    result.flash = 'Fired' if (flash_val & 1) else 'No Flash'
                
                # Exposure program (70%+ reliable)
                if 34850 in exif:  # ExposureProgram
                    programs = {
                        0: 'Not Defined', 1: 'Manual', 2: 'Program AE', 
                        3: 'Aperture Priority', 4: 'Shutter Priority',
                        5: 'Creative (Slow Speed)', 6: 'Action (High Speed)',
                        7: 'Portrait', 8: 'Landscape'
                    }
                    result.exposure_program = programs.get(exif[34850], 'Unknown')
                
                # Metering mode (70%+ reliable)
                if 37383 in exif:  # MeteringMode
                    metering = {
                        0: 'Unknown', 1: 'Average', 2: 'Center Weighted Average',
                        3: 'Spot', 4: 'Multi-Spot', 5: 'Multi-Segment', 6: 'Partial'
                    }
                    result.metering_mode = metering.get(exif[37383], 'Unknown')
                
                # White balance (70%+ reliable)
                if 41987 in exif:  # WhiteBalance
                    wb = exif[41987]
                    result.white_balance = 'Auto' if wb == 0 else 'Manual'
                    
        except Exception as e:
            # Silent failure - return partial data
            pass
        
        return result
    
    @staticmethod
    def _extract_gps_from_exif(exif) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[str], Optional[str], Optional[str]]:
        """
        Extract GPS data from EXIF.
        
        Returns:
            Tuple of (latitude, longitude, altitude, timestamp, datestamp, map_datum)
        """
        try:
            # Get GPS IFD
            try:
                gps_ifd = exif.get_ifd(0x8825)  # GPSInfo
            except (KeyError, AttributeError):
                return None, None, None, None, None, None
            
            if not gps_ifd:
                return None, None, None, None, None, None
            
            # Extract GPS coordinates
            gps_latitude = gps_ifd.get(2)  # GPSLatitude
            gps_latitude_ref = gps_ifd.get(1)  # GPSLatitudeRef
            gps_longitude = gps_ifd.get(4)  # GPSLongitude
            gps_longitude_ref = gps_ifd.get(3)  # GPSLongitudeRef
            
            lat = None
            lon = None
            if gps_latitude and gps_longitude:
                # Convert to decimal degrees
                lat = ExifExtractor._convert_to_decimal(gps_latitude, gps_latitude_ref)
                lon = ExifExtractor._convert_to_decimal(gps_longitude, gps_longitude_ref)
                
                # Validate coordinates
                if lat is not None and lon is not None:
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        lat, lon = None, None
                    # Filter "Null Island" (0, 0)
                    elif lat == 0 and lon == 0:
                        lat, lon = None, None
            
            # Extract altitude
            altitude = None
            if 6 in gps_ifd:  # GPSAltitude
                alt_value = gps_ifd[6]
                if isinstance(alt_value, tuple):
                    altitude = alt_value[0] / alt_value[1]
                else:
                    altitude = float(alt_value)
                    
                # Handle altitude reference (0 = above sea level, 1 = below)
                if 5 in gps_ifd and gps_ifd[5] == b'\x01':
                    altitude = -altitude
            
            # Extract GPS timestamp
            timestamp = None
            if 7 in gps_ifd:  # GPSTimeStamp
                time_tuple = gps_ifd[7]
                if len(time_tuple) == 3:
                    hour = int(time_tuple[0])
                    minute = int(time_tuple[1])
                    second = int(time_tuple[2])
                    timestamp = f"{hour:02d}:{minute:02d}:{second:02d}"
            
            # Extract GPS datestamp
            datestamp = None
            if 29 in gps_ifd:  # GPSDateStamp
                datestamp = gps_ifd[29]
            
            # Extract map datum
            map_datum = None
            if 18 in gps_ifd:  # GPSMapDatum
                map_datum = gps_ifd[18]
            
            return lat, lon, altitude, timestamp, datestamp, map_datum
            
        except Exception:
            return None, None, None, None, None, None
    
    @staticmethod
    def _convert_to_decimal(coord_tuple, ref) -> Optional[float]:
        """
        Convert GPS coordinate to decimal degrees.
        
        Supports DMS, DM, and decimal formats.
        """
        try:
            if not coord_tuple:
                return None
            
            # Handle single decimal value
            if len(coord_tuple) == 1:
                decimal = float(coord_tuple[0])
            # Handle DMS or DM format
            elif len(coord_tuple) >= 2:
                # Extract degrees
                degrees = coord_tuple[0]
                if isinstance(degrees, tuple):
                    degrees = degrees[0] / degrees[1]
                else:
                    degrees = float(degrees)
                
                # Extract minutes
                minutes = coord_tuple[1]
                if isinstance(minutes, tuple):
                    minutes = minutes[0] / minutes[1]
                else:
                    minutes = float(minutes)
                
                # Extract seconds (if present)
                seconds = 0
                if len(coord_tuple) >= 3:
                    seconds = coord_tuple[2]
                    if isinstance(seconds, tuple):
                        seconds = seconds[0] / seconds[1]
                    else:
                        seconds = float(seconds)
                
                # Convert to decimal
                decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            else:
                return None
            
            # Apply reference direction
            if ref in ['S', 'W']:
                decimal = -decimal
            
            return decimal
            
        except Exception:
            return None
    
    @staticmethod
    def _standardize_datetime(dt_str: str) -> str:
        """
        Convert EXIF datetime to ISO 8601 format.
        
        Handles multiple datetime formats from different cameras.
        """
        if not dt_str or not isinstance(dt_str, str):
            return dt_str
        
        # Remove timezone info for simplicity
        dt_str_clean = dt_str.split('+')[0].split('Z')[0].strip()
        
        # Try different datetime formats
        formats = [
            "%Y:%m:%d %H:%M:%S",      # Standard EXIF
            "%Y-%m-%d %H:%M:%S",      # ISO with space
            "%Y-%m-%dT%H:%M:%S",      # ISO 8601
            "%Y:%m:%d %H:%M:%S.%f",   # EXIF with subseconds
            "%Y-%m-%d %H:%M:%S.%f",   # ISO with subseconds
            "%Y:%m:%d",               # Date only EXIF
            "%Y-%m-%d",               # Date only ISO
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(dt_str_clean, fmt)
                return dt.isoformat()
            except ValueError:
                continue
        
        # If all formats fail, return original
        return dt_str
