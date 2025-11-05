# CorePhoto Model Design - Photographer's Perspective

## Model Architecture

ImaLink has three distinct photo models with different purposes:

### 1. CorePhoto (imalink-core library)
**Purpose**: Complete data extractable from image file

**Includes**:
- Hotpreview (150x150) - small thumbnail for gallery view
- Coldpreview (1920x1080) - larger preview for detail view
- All EXIF metadata (camera, GPS, settings)
- File information

**Used by**: Import process, batch processing, backup/restore

**Does NOT include**: Database fields (id, user_id), user organization (rating, title, tags)

### 2. Photo (backend database model)
**Purpose**: Persisted photo data in database

**Includes**:
- Database fields (id, user_id, timestamps)
- Hotpreview (stored in DB or S3) - small enough
- Metadata copied from CorePhoto (camera, GPS, etc.)
- User organization (rating, title, description, tags)

**Does NOT include**: Coldpreview (too large ~100-200KB, generated on-demand)

**Sent to frontend**: As JSON API response

### 3. Coldpreview Strategy
**Problem**: Too large to store in database (100-200KB per photo)

**Solution**: 
- Generated on-demand from original file
- Or cached separately (Redis, S3, local storage)
- Frontend fetches via separate endpoint: `GET /api/photos/{id}/coldpreview`

**Why this works**:
- Coldpreview only needed for detail view (not gallery)
- Can regenerate from original file when needed
- Keeps database queries fast
- Reduces storage costs

### Key Design Principle
CorePhoto is a "rich" object containing ALL extractable data. Backend chooses what to persist based on practical concerns (size, usage patterns). This gives maximum flexibility:
- Import process has access to all data
- Backend optimizes storage
- Coldpreview can be regenerated when necessary

---

## Problem Statement

As a photographer, I need to:
1. **Trust my data** - Know what's from camera EXIF vs user input
2. **Handle missing data** - Not all photos have EXIF, GPS, or correct timestamps
3. **Search efficiently** - Quick filtering by time and location
4. **Understand precision** - Exact GPS vs "somewhere in London"
5. **Handle different photo origins** - Digital camera, scanned slides, screenshots, web downloads
6. **Distinguish camera from scanner** - Scanner model is not the camera that took the photo
7. **Handle time/GPS inaccuracies** - Wrong camera clock, GPS drift, timezone issues
8. **Group related photos** - Bursts, versions, film rolls
9. **Track edits and derivations** - Original vs processed, crops, different versions
10. **Manage professional metadata** - Copyright, licensing, client work

## Data Sources & Precision

### Location Data Hierarchy
```
1. EXIF GPS (highest precision)
   - lat/lon with decimals: 59.913868, 10.752245
   - Source: Camera with GPS
   - Display: Pin on map
   - Search: Exact coordinates

2. User City/Place (medium precision)
   - Text: "London", "Oslo sentrum", "Eiffel Tower"
   - Source: User manual entry
   - Display: City name/icon
   - Search: Text match + radius

3. Derived/Guessed (low precision)
   - Reverse geocoding from EXIF GPS
   - Clustered with nearby photos
   - Source: Automatic
   - Display: Show as "approximate"

4. No location
   - Must handle gracefully
   - Allow user to add later
```

### Timestamp Hierarchy
```
1. EXIF Taken At (highest precision)
   - ISO 8601: 2023-07-15T14:32:18+02:00
   - Source: Camera clock
   - Accurate if camera clock set correctly

2. File Modified (fallback)
   - May be wrong (file copied/edited)
   - Better than nothing

3. User Specified
   - "Summer 2023"
   - "Around Christmas 2022"
   - Precision flag needed

4. Unknown
   - Allow null
   - Show as "Date unknown" in UI
```

## Proposed Model Structure

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

class DataSource(Enum):
    """Where did this data come from?"""
    EXIF = "exif"           # From camera EXIF
    USER = "user"           # User manual entry
    DERIVED = "derived"     # Calculated/guessed
    FILE = "file"           # From file metadata
    UNKNOWN = "unknown"     # Not set

class PhotoOrigin(Enum):
    """How was this photo created/captured?"""
    # Digital originals
    CAMERA = "camera"              # Digital camera (DSLR, mirrorless, compact)
    PHONE = "phone"                # Mobile phone camera
    SCREENSHOT = "screenshot"      # Screen capture
    WEB_DOWNLOAD = "web_download"  # Downloaded from website/social media
    AI_GENERATED = "ai_generated"  # AI/generated image
    
    # Analog digitized
    SCANNED_SLIDE = "scanned_slide"       # Scanned dia/slide
    SCANNED_NEGATIVE = "scanned_negative" # Scanned film negative
    SCANNED_PRINT = "scanned_print"       # Scanned photo print
    SCANNED_DOCUMENT = "scanned_document" # Scanned newspaper/magazine
    
    # Unknown/Legacy
    UNKNOWN = "unknown"

class LocationPrecision(Enum):
    """How precise is the location?"""
    EXACT = "exact"         # GPS coordinates (< 10m)
    CITY = "city"           # City/neighborhood (~1-10km)
    REGION = "region"       # Region/country (~100km+)
    APPROXIMATE = "approximate"  # Guessed/derived
    UNKNOWN = "unknown"

class TimePrecision(Enum):
    """How precise is the timestamp?"""
    EXACT = "exact"         # Precise to second
    MINUTE = "minute"       # Precise to minute
    HOUR = "hour"          # Precise to hour
    DAY = "day"            # Precise to day
    MONTH = "month"        # Precise to month
    YEAR = "year"          # Precise to year
    APPROXIMATE = "approximate"  # Rough estimate
    UNKNOWN = "unknown"

@dataclass
class Location:
    """Location with source and precision tracking"""
    # GPS coordinates (if available)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Human-readable location (always available)
    place_name: Optional[str] = None  # "London", "Eiffel Tower"
    city: Optional[str] = None
    country: Optional[str] = None
    
    # Metadata
    source: DataSource = DataSource.UNKNOWN
    precision: LocationPrecision = LocationPrecision.UNKNOWN
    
    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None
    
    @property
    def display_name(self) -> str:
        """Best available location name for display"""
        if self.place_name:
            return self.place_name
        if self.city:
            return self.city
        if self.country:
            return self.country
        if self.has_coordinates:
            return f"{self.latitude:.4f}, {self.longitude:.4f}"
        return "Unknown location"

@dataclass
class Timestamp:
    """Timestamp with source and precision tracking"""
    # The actual datetime
    datetime: Optional[datetime] = None
    
    # Metadata
    source: DataSource = DataSource.UNKNOWN
    precision: TimePrecision = TimePrecision.UNKNOWN
    
    # Timezone info
    timezone_offset: Optional[str] = None  # "+02:00"
    
    @property
    def is_set(self) -> bool:
        return self.datetime is not None
    
    @property
    def display_precision(self) -> str:
        """Human readable precision indicator"""
        if not self.is_set:
            return "Date unknown"
        
        precision_map = {
            TimePrecision.EXACT: "",  # Show full datetime
            TimePrecision.DAY: "ca. ",
            TimePrecision.MONTH: "sometime in ",
            TimePrecision.YEAR: "around ",
            TimePrecision.APPROXIMATE: "~",
        }
        return precision_map.get(self.precision, "")

@dataclass
class CaptureInfo:
    """
    Information about how the photo was captured/created.
    
    Separates original camera from scanning device.
    """
    # Photo origin
    origin: PhotoOrigin = PhotoOrigin.UNKNOWN
    
    # Original camera (if known) - What actually took the photo
    camera_make: Optional[str] = None    # "Nikon", "Canon"
    camera_model: Optional[str] = None   # "D850", "EOS R5"
    camera_source: DataSource = DataSource.UNKNOWN  # EXIF or user entered?
    
    # Scanner/digitization device (if applicable)
    scanner_make: Optional[str] = None   # "Epson"
    scanner_model: Optional[str] = None  # "Perfection V600"
    scan_date: Optional[datetime] = None # When was it scanned?
    scan_dpi: Optional[int] = None       # Scan resolution
    
    # Camera settings (from EXIF, only for digital originals)
    iso: Optional[int] = None
    aperture: Optional[float] = None
    shutter_speed: Optional[str] = None
    focal_length: Optional[float] = None
    lens_model: Optional[str] = None
    lens_make: Optional[str] = None
    
    @property
    def is_digital_original(self) -> bool:
        """Is this a digital photo from a camera/phone?"""
        return self.origin in [
            PhotoOrigin.CAMERA,
            PhotoOrigin.PHONE,
        ]
    
    @property
    def is_scanned(self) -> bool:
        """Was this scanned from analog source?"""
        return self.origin in [
            PhotoOrigin.SCANNED_SLIDE,
            PhotoOrigin.SCANNED_NEGATIVE,
            PhotoOrigin.SCANNED_PRINT,
            PhotoOrigin.SCANNED_DOCUMENT,
        ]
    
    @property
    def display_camera(self) -> str:
        """Best available camera name for display"""
        if self.camera_make and self.camera_model:
            result = f"{self.camera_make} {self.camera_model}"
            if self.camera_source == DataSource.USER:
                result += " (user)"
            return result
        elif self.camera_model:
            return self.camera_model
        
        # Fallback for scanned images
        if self.is_scanned and self.scanner_model:
            return f"Scanned with {self.scanner_model}"
        
        return "Unknown camera"

@dataclass
class CorePhoto:
    """
    Core Photo model - complete data extractable from image file.
    
    Used by imalink-core during import/processing. Contains ALL data that can
    be extracted from the image file, including both hotpreview and coldpreview.
    
    Backend Photo model will be different:
    - Includes: hotpreview (small, stored in DB)
    - Excludes: coldpreview (large, generated on-demand)
    - Adds: user fields (rating, title, description, tags)
    - Adds: database fields (id, user_id, timestamps)
    
    Design principles:
    1. Always track data source (EXIF, user, derived)
    2. Always track precision (exact, approximate, unknown)
    3. Support missing data gracefully
    4. Enable efficient searching by time/location
    5. Allow user overrides of automatic data
    """
    
    # === IDENTITY ===
    hothash: str  # SHA256 of hotpreview (unique ID)
    
    # === PREVIEWS ===
    hotpreview_base64: Optional[str] = None
    hotpreview_width: Optional[int] = None
    hotpreview_height: Optional[int] = None
    coldpreview_base64: Optional[str] = None
    coldpreview_width: Optional[int] = None
    coldpreview_height: Optional[int] = None
    
    # === FILES ===
    primary_filename: Optional[str] = None
    image_files: List[CoreImageFile] = field(default_factory=list)
    
    # === TIME (Critical for sorting/searching) ===
    taken_at: Timestamp = field(default_factory=Timestamp)
    
    # System timestamps
    first_imported: Optional[datetime] = None
    last_imported: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    
    # === LOCATION (Critical for searching) ===
    location: Location = field(default_factory=Location)
    
    # === IMAGE PROPERTIES ===
    width: Optional[int] = None
    height: Optional[int] = None
    
    # === CAPTURE INFO (How was this photo made?) ===
    capture: CaptureInfo = field(default_factory=CaptureInfo)
    
    # === USER ORGANIZATION (NOT in CorePhoto, only in backend Photo model) ===
    # rating: Optional[int] = None  # Backend only
    # title: Optional[str] = None   # Backend only
    # description: Optional[str] = None  # Backend only
    # tags: List[str] = field(default_factory=list)  # Backend only
    
    # === FLAGS ===
    has_raw_companion: bool = False
    is_favorite: bool = False  # Note: Might move to backend only
    
    # === BACKEND DATABASE FIELDS (NOT in CorePhoto) ===
    # id: Optional[int] = None  # Backend assigns DB ID
    # user_id: Optional[int] = None  # Backend manages ownership
    # import_session_id: Optional[int] = None  # Backend tracks imports
```

## Benefits

1. **Clarity**: Always know where data came from
2. **Precision**: Know how accurate the data is
3. **Flexibility**: User can override/supplement EXIF data
4. **Search**: Can filter by "exact GPS only" or "approximate location OK"
5. **UI**: Can show different icons/indicators based on precision
6. **Trust**: Photographer knows what's camera data vs guesses

## Model Separation Benefits

1. **CorePhoto completeness**: Contains ALL extractable data for maximum flexibility
2. **Backend optimization**: Stores only what's practical (hotpreview yes, coldpreview no)
3. **Clear boundaries**: File data vs user data vs database data
4. **Regeneration capability**: Can recreate coldpreview from original file when needed
5. **Storage efficiency**: 10K photos with coldpreview = 1.5GB saved in database

## UI Examples

### Gallery View
```
📷 IMG_1234.jpg
⭐⭐⭐⭐⭐
📍 Oslo sentrum (user)      <- Shows source
📅 15 Jul 2023, 14:32       <- EXIF timestamp
```

### Search
```
🔍 Find photos:
   Time: [EXIF only ✓] [User specified ✓] [Unknown ☐]
   Location: [Exact GPS ✓] [City ✓] [Approximate ☐]
   Origin: [Camera ✓] [Phone ✓] [Scanned ☐] [Screenshot ☐]
```

### Detail View
```
Location:
  📍 Eiffel Tower
  Source: User added
  Precision: City (~5km)
  [Add GPS coordinates...]

Taken at:
  📅 15 July 2023, 14:32:18
  Source: Camera EXIF
  Precision: Exact (second)
  Timezone: +02:00

Captured with:
  📷 Nikon D850
  Source: EXIF
  Origin: Digital camera
  ISO 400, f/2.8, 1/250s, 85mm
```

### Scanned Photo Example
```
Captured with:
  📷 Unknown camera (user can add)
  Origin: Scanned slide
  Scanned with: Epson Perfection V600
  Scan date: 2024-03-15
  Scan DPI: 2400

Taken at:
  📅 ca. Summer 1985
  Source: User estimated
  Precision: Approximate (season)
```

## Use Cases

### 1. Digital Camera Photo
```python
photo = CorePhoto(
    hothash="abc123...",
    taken_at=Timestamp(
        datetime=datetime(2023, 7, 15, 14, 32, 18),
        source=DataSource.EXIF,
        precision=TimePrecision.EXACT
    ),
    location=Location(
        latitude=59.9139,
        longitude=10.7522,
        source=DataSource.EXIF,
        precision=LocationPrecision.EXACT
    ),
    capture=CaptureInfo(
        origin=PhotoOrigin.CAMERA,
        camera_make="Nikon",
        camera_model="D850",
        camera_source=DataSource.EXIF,
        iso=400,
        aperture=2.8,
        focal_length=85.0
    )
)
```

### 2. Scanned Slide from 1985
```python
photo = CorePhoto(
    hothash="def456...",
    taken_at=Timestamp(
        datetime=datetime(1985, 7, 1),  # Best guess
        source=DataSource.USER,
        precision=TimePrecision.MONTH
    ),
    location=Location(
        place_name="Oslo",
        source=DataSource.USER,
        precision=LocationPrecision.CITY
    ),
    capture=CaptureInfo(
        origin=PhotoOrigin.SCANNED_SLIDE,
        camera_make="Unknown",  # Can be filled in by user later
        scanner_make="Epson",
        scanner_model="Perfection V600",
        scan_date=datetime(2024, 3, 15),
        scan_dpi=2400
    )
)
```

### 3. Phone Screenshot
```python
photo = CorePhoto(
    hothash="ghi789...",
    taken_at=Timestamp(
        datetime=datetime(2024, 1, 20, 10, 15, 0),
        source=DataSource.FILE,  # From file metadata
        precision=TimePrecision.EXACT
    ),
    location=Location(
        source=DataSource.UNKNOWN
    ),
    capture=CaptureInfo(
        origin=PhotoOrigin.SCREENSHOT,
        camera_make="Apple",
        camera_model="iPhone 15 Pro",
        camera_source=DataSource.EXIF
    )
)
```

## Search Examples

### Find all scanned slides
```python
photos = db.query(CorePhoto).filter(
    CorePhoto.capture.origin == PhotoOrigin.SCANNED_SLIDE
)
```

### Find photos with exact GPS only
```python
photos = db.query(CorePhoto).filter(
    CorePhoto.location.precision == LocationPrecision.EXACT,
    CorePhoto.location.source == DataSource.EXIF
)
```

### Find all digital originals (exclude scans/screenshots)
```python
photos = db.query(CorePhoto).filter(
    CorePhoto.capture.origin.in_([
        PhotoOrigin.CAMERA,
        PhotoOrigin.PHONE
    ])
)
```

## Additional Edge Cases & Requirements

### 1. Time Corrections
**Problem**: Camera clock wrong (very common!)
```python
# Original EXIF: 2023-01-01 12:00:00 (factory default)
# Actual time: 2024-07-15 12:00:00

@dataclass
class TimeCorrection:
    """Track manual time corrections"""
    offset_seconds: int  # +47174400 seconds (548 days)
    applied_by: str     # User who made correction
    applied_at: datetime
    reason: str         # "Camera clock not set"
    
# Add to Timestamp:
corrections: List[TimeCorrection] = field(default_factory=list)
```

**Use case**: Bulk correct all photos from a trip where camera was in wrong timezone

### 2. GPS Accuracy
**Problem**: GPS can be inaccurate (tunnels, buildings, poor signal)
```python
# Add to Location:
gps_accuracy_meters: Optional[float] = None  # ±10m, ±50m, ±500m
altitude: Optional[float] = None
altitude_accuracy_meters: Optional[float] = None
```

**Use case**: Filter out photos with GPS accuracy > 100m when creating maps

### 3. Related Photo Groups
**Problem**: Multiple photos that belong together

```python
class GroupType(Enum):
    BURST = "burst"           # Rapid sequence (sports/action)
    FILM_ROLL = "film_roll"   # Images from same film roll
    VERSION = "version"       # Same photo, different edits
    
@dataclass
class PhotoGroup:
    """Group related photos together"""
    group_id: str
    group_type: GroupType
    sequence_number: int  # Position in group (1, 2, 3...)
    total_in_group: int   # Total photos in this group
    is_cover: bool = False  # Show this one in gallery view
    
    # For film rolls
    film_roll_name: Optional[str] = None  # "Kodak Portra 400 #42"
    frame_number: Optional[str] = None    # "12/36"

# Add to CorePhoto:
groups: List[PhotoGroup] = field(default_factory=list)
```

**Use case**: 
- Show "1 of 100" in gallery for burst sequences
- Group all frames from same film roll
- Link all versions of same photo

### 4. Derivations & Processing
**Problem**: Edited/processed/cropped versions

```python
@dataclass
class ProcessingInfo:
    """Track how photo was processed"""
    is_processed: bool = False
    processing_software: Optional[str] = None  # "Adobe Lightroom 13.0"
    processing_date: Optional[datetime] = None
    
    # Original photo reference
    derived_from_hothash: Optional[str] = None
    
    # What was done
    is_cropped: bool = False
    is_color_adjusted: bool = False
    is_filtered: bool = False
    
    # Processing presets/settings
    preset_name: Optional[str] = None  # "Portra 400 Look"
    
# Add to CorePhoto:
processing: ProcessingInfo = field(default_factory=ProcessingInfo)
```

**Use case**: 
- Find all original/unprocessed photos only
- Link processed versions to originals
- Track editing history

### 5. File Naming
**Problem**: Original filename often lost after rename

```python
# Add to CorePhoto:
original_filename: Optional[str] = None  # "DSC_1234.jpg" from camera
current_filename: str                    # "2023-07-15_Oslo_Sunset.jpg"
filename_history: List[str] = field(default_factory=list)
```

**Use case**: Always preserve camera's original filename for reference

### 6. Professional Metadata
**Problem**: Commissioned work, licensing, copyright

```python
@dataclass  
class ProfessionalInfo:
    """Professional photography metadata"""
    # Copyright
    copyright_holder: Optional[str] = None
    copyright_year: Optional[int] = None
    
    # Licensing
    license_type: Optional[str] = None  # "CC-BY", "All Rights Reserved", etc
    usage_rights: Optional[str] = None
    
    # Commercial work
    photographer_name: Optional[str] = None
    client_name: Optional[str] = None
    project_name: Optional[str] = None
    job_identifier: Optional[str] = None
    
    # Publication
    published_in: Optional[str] = None  # Magazine/website name
    publication_date: Optional[datetime] = None
    
# Add to CorePhoto:
professional: Optional[ProfessionalInfo] = None
```

**Use case**: Track client work, manage licensing, maintain copyright info

### 7. Selection & Culling
**Problem**: Photographers need to mark picks/rejects

```python
class ColorLabel(Enum):
    """Lightroom-style color labels"""
    NONE = "none"
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"

# Add to CorePhoto:
is_pick: bool = False       # Selected as good photo
is_rejected: bool = False   # Marked for deletion
color_label: ColorLabel = ColorLabel.NONE
flag_status: Optional[str] = None  # Custom flags
```

**Use case**: 
- "Show only picks" for portfolio selection
- "Hide rejected" during culling
- Color code by category/priority

### 8. Keywords & IPTC
**Problem**: Professional metadata standards (IPTC)

```python
# Add to CorePhoto:
keywords: List[str] = field(default_factory=list)  # IPTC keywords
category: Optional[str] = None
subject_code: Optional[str] = None
```

**Use case**: Standard metadata for stock photography, journalism

### 9. Camera Settings Edge Cases
**Problem**: Not all EXIF is reliable

```python
# Add to CaptureInfo:
exif_confidence: float = 1.0  # 0.0-1.0, how reliable is EXIF?

# Flags for problematic EXIF
is_exif_modified: bool = False  # EXIF edited after capture
is_exif_synthesized: bool = False  # EXIF added by software (not camera)
```

**Use case**: Warn user if EXIF may be unreliable

## Recommended Implementation Priority

### Phase 1 (Core - Must Have)
1. ✅ Location with source/precision tracking
2. ✅ Timestamp with source/precision tracking  
3. ✅ CaptureInfo with PhotoOrigin
4. ✅ Camera vs scanner separation

### Phase 2 (High Priority)
5. Time corrections (very common issue)
6. GPS accuracy tracking
7. File naming (original + current)
8. Basic grouping (burst, film roll)

### Phase 3 (Medium Priority)
9. Processing/derivation tracking
10. Professional metadata
11. Selection tools (pick/reject/color labels)

### Phase 4 (Nice to Have)
12. IPTC/keywords (standard compliance)
13. EXIF confidence scoring
14. Advanced version tracking

**Note**: Composite images (panorama, HDR, focus stacking) are handled by backend PhotoStack, not imalink-core. Core only stores the final processed results with appropriate metadata.

## Migration Strategy

1. **Phase 1**: Add new fields, keep old ones
2. **Phase 2**: Migrate data to new structure
3. **Phase 3**: Remove old fields

This allows gradual adoption without breaking existing code.
