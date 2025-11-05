# Model Architecture: Core vs Backend vs Frontend

## Problem Statement

Vi må avklare hva som skal være i hver modell:
- **CorePhoto** (imalink-core): Data som kan ekstraheres fra bildefil
- **Photo** (backend database): Data som lagres og administreres
- **Frontend consumption**: Hva frontend trenger for visning

## Current Issue

Design-dokumentet sier at CorePhoto er "canonical representation shared across the ImaLink ecosystem", men dette er feil. CorePhoto skal bare brukes i core library for å ekstrahera data fra bilder.

## Proposed Architecture

### 1. CorePhoto (imalink-core library)

**Formål**: Representere ALT som kan ekstraheres fra en bildefil

**Inneholder**:
- ✅ **Hotpreview** (150x150) - for gallery view
- ✅ **Coldpreview** (1920x1080) - for detail view
- ✅ **EXIF metadata** - all data fra kamera
- ✅ **GPS coordinates** - fra EXIF
- ✅ **Camera settings** - ISO, aperture, shutter, focal length
- ✅ **Dimensions** - width, height
- ✅ **File info** - filename, size, format
- ✅ **Hothash** - SHA256 av hotpreview (unik ID)

**Brukes av**: 
- Import-prosessen (ekstrahera data fra nye bilder)
- Backup/restore (regenerere data fra filer)
- Batch processing (oppdatere metadata)

**Sendes IKKE direkte til frontend** - backend konverterer til sin egen model

---

### 2. Photo (backend database model)

**Formål**: Lagre og administrere foto-data i database

**Inneholder**:
- ✅ **Database fields**:
  - `id` (primary key)
  - `user_id` (owner)
  - `import_session_id`
  - `created_at`, `updated_at`
  
- ✅ **Hotpreview** (lagret i database eller S3):
  - `hotpreview_base64` eller `hotpreview_url`
  - `hotpreview_width`, `hotpreview_height`
  
- ❌ **IKKE coldpreview** (for stort å lagre i database):
  - Coldpreview genereres on-demand fra originalfil
  - Eller caches separat
  
- ✅ **Metadata** (fra CorePhoto ved import):
  - `taken_at`, `width`, `height`
  - `camera_make`, `camera_model`
  - `gps_latitude`, `gps_longitude`
  - `iso`, `aperture`, `shutter_speed`, `focal_length`
  
- ✅ **User organization**:
  - `rating` (0-5 stars)
  - `title`, `description`
  - `tags` (relation to Tag table)
  - `is_favorite`
  
- ✅ **Relations**:
  - `image_files` (relation to ImageFile table)
  - `photo_stacks` (grouping)
  - `albums` (collections)

**API respons til frontend**: Serialisert Photo model (JSON)

---

### 3. Frontend Display Model

**Formål**: Vise foto i UI

**Trenger for gallery view**:
- ✅ `id`, `hothash`
- ✅ `hotpreview_base64` (eller URL)
- ✅ `primary_filename`
- ✅ `taken_at`
- ✅ `rating`, `is_favorite`
- ✅ Minimal data for quick loading

**Trenger for detail view**:
- ✅ Alt fra gallery view
- ✅ **Coldpreview** (hentes on-demand):
  - Frontend requester: `GET /api/photos/{id}/coldpreview`
  - Backend genererer fra originalfil eller cache
  - Returnerer coldpreview_base64
- ✅ Full metadata for visning
- ✅ Camera info, GPS, camera settings
- ✅ User fields (title, description, tags)

---

## Data Flow

### Import Flow
```
1. User imports image file
2. imalink-core.process_image() → CorePhoto
   - Includes hotpreview (150x150)
   - Includes coldpreview (1920x1080)
3. Backend receives CorePhoto
4. Backend saves to database:
   - Stores hotpreview in Photo table (small, ~10-20KB)
   - Stores metadata in Photo table
   - Discards coldpreview (too large)
   - Stores original file in file storage
5. Frontend gets Photo (with hotpreview)
```

### Gallery View Flow
```
1. Frontend: GET /api/photos?page=1&limit=50
2. Backend: Returns array of Photo objects
   - Each includes hotpreview_base64 (small)
3. Frontend: Displays thumbnails using hotpreview
```

### Detail View Flow
```
1. User clicks photo in gallery
2. Frontend: GET /api/photos/{id}
   - Returns Photo with full metadata
   - Still includes hotpreview
3. Frontend: GET /api/photos/{id}/coldpreview
   - Backend checks cache
   - If not cached: regenerate from original file
   - Returns coldpreview_base64 (larger, ~100-200KB)
4. Frontend: Displays large preview
```

---

## Key Differences

### CorePhoto vs Photo

| Field | CorePhoto (core) | Photo (backend) | Reason |
|-------|------------------|-----------------|--------|
| `id` | ❌ No | ✅ Yes | Backend assigns DB ID |
| `user_id` | ❌ No | ✅ Yes | Backend manages ownership |
| `hotpreview_base64` | ✅ Yes | ✅ Yes | Small, used in gallery |
| `coldpreview_base64` | ✅ Yes | ❌ No | Too large for DB storage |
| `taken_at` | ✅ Yes (from EXIF) | ✅ Yes (can be user-corrected) | Backend allows overrides |
| `title`, `description` | ❌ No | ✅ Yes | User-added, not from file |
| `tags` | ❌ No | ✅ Yes | User organization |
| `rating` | ❌ No | ✅ Yes | User organization |
| `camera_make` | ✅ Yes (from EXIF) | ✅ Yes | Copied from CorePhoto |
| `gps_latitude/longitude` | ✅ Yes (from EXIF) | ✅ Yes | Copied from CorePhoto |
| `photo_stacks` | ❌ No | ✅ Yes | Backend grouping logic |

---

## Motivation for Differences

### Why CorePhoto includes coldpreview but Photo doesn't

1. **Size**: Coldpreview er ~100-200KB per foto
   - 10,000 photos = 1-2GB bare for coldpreviews
   - Database blir for stor
   - Queries blir trege

2. **Usage**: Coldpreview trengs bare ved detail view
   - Ikke ved gallery view (bruker hotpreview)
   - Ikke ved search/filter
   - Kan genereres on-demand

3. **Storage strategy**:
   - CorePhoto: Include alt som KAN ekstraheres (API fullständighet)
   - Backend: Lagre bare det som er nødvendig for core operations
   - Coldpreview: Cache separat eller regenerer fra originalfil

### Why Photo includes user fields but CorePhoto doesn't

1. **Source**: User fields kommer fra brukerens interaksjon, ikke fra bildefil
   - `title`, `description`: Bruker skriver inn
   - `rating`, `is_favorite`: Bruker setter
   - `tags`: Bruker organiserer

2. **Scope**: CorePhoto er "what's in the file", Photo er "what the user knows"

### Why Photo includes database fields but CorePhoto doesn't

1. **Lifecycle**: Database fields administreres av backend
   - `id`: Generated by database
   - `user_id`: Set by auth system
   - `created_at`, `updated_at`: Managed by ORM

2. **Separation**: CorePhoto er domain model, Photo er persistence model

---

## Implementation Recommendations

### 1. Update PHOTO_MODEL_DESIGN.md

Remove the statement: "The Photo model is the canonical representation shared across the ImaLink ecosystem"

Replace with:
```markdown
## Model Architecture

ImaLink has three distinct photo models:

1. **CorePhoto** (imalink-core): Complete data extractable from image file
   - Used during import/processing
   - Includes both hotpreview (150x150) and coldpreview (1920x1080)
   - No database or user organization fields

2. **Photo** (backend database): Persisted photo data
   - Database entity with id, user_id, timestamps
   - Includes hotpreview for gallery view
   - Excludes coldpreview (too large, generated on-demand)
   - Includes user organization (rating, title, description, tags)

3. **PhotoResponse** (backend API): JSON sent to frontend
   - Serialized Photo model
   - Coldpreview fetched separately via /coldpreview endpoint
```

### 2. CorePhoto Design Priorities

Focus on what can be extracted from files:

**Phase 1**: Core extraction (CURRENT STATE ✅)
- ✅ Hotpreview (150x150)
- ✅ Coldpreview (1920x1080)
- ✅ Basic EXIF (taken_at, camera, GPS)
- ✅ Camera settings (ISO, aperture, etc.)

**Phase 2**: Enhanced metadata (DESIGN DOCUMENT)
- Location with precision tracking
- Timestamp with source tracking
- CaptureInfo with PhotoOrigin (camera, scanned, etc.)
- Scanner vs camera separation

**Phase 3**: Advanced extraction
- IPTC keywords
- Copyright/creator info
- Professional metadata

### 3. Backend Photo Model

Keep separate concerns:

```python
class Photo(Base):
    """Backend database model"""
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    hothash = Column(String, unique=True, index=True)
    
    # Hotpreview (stored in DB or S3)
    hotpreview_base64 = Column(Text)  # or hotpreview_url
    hotpreview_width = Column(Integer)
    hotpreview_height = Column(Integer)
    
    # NO coldpreview in database!
    
    # Metadata (copied from CorePhoto during import)
    taken_at = Column(DateTime)
    width = Column(Integer)
    height = Column(Integer)
    camera_make = Column(String)
    camera_model = Column(String)
    gps_latitude = Column(Float)
    gps_longitude = Column(Float)
    
    # User organization (not in CorePhoto)
    rating = Column(Integer)
    title = Column(String)
    description = Column(Text)
    is_favorite = Column(Boolean, default=False)
    
    # Relations
    image_files = relationship('ImageFile', back_populates='photo')
    tags = relationship('Tag', secondary='photo_tags')
    
    @classmethod
    def from_core_photo(cls, core: CorePhoto, user_id: int) -> 'Photo':
        """Create Photo from CorePhoto during import"""
        return cls(
            user_id=user_id,
            hothash=core.hothash,
            hotpreview_base64=core.hotpreview_base64,
            hotpreview_width=core.hotpreview_width,
            hotpreview_height=core.hotpreview_height,
            # Copy metadata
            taken_at=core.taken_at,
            width=core.width,
            height=core.height,
            camera_make=core.camera_make,
            camera_model=core.camera_model,
            gps_latitude=core.gps_latitude,
            gps_longitude=core.gps_longitude,
            # User fields initialized to defaults
            rating=None,
            title=None,
            description=None,
        )
```

### 4. Backend API Endpoints

```python
# Gallery view - returns photos with hotpreview
GET /api/photos?page=1&limit=50
Response: {
    "photos": [
        {
            "id": 123,
            "hothash": "abc123...",
            "hotpreview_base64": "...",  # Small, included
            "taken_at": "2023-07-15T14:32:18",
            "rating": 4,
            "is_favorite": true,
            # No coldpreview here!
        }
    ]
}

# Detail view - fetch coldpreview separately
GET /api/photos/123/coldpreview
Response: {
    "coldpreview_base64": "...",  # Large, on-demand
    "coldpreview_width": 1920,
    "coldpreview_height": 1080,
    "cached": false  # Was generated on-the-fly
}
```

### 5. Coldpreview Strategy

Options for backend:

**Option A: Generate on-demand** (simplest)
```python
@router.get("/photos/{photo_id}/coldpreview")
async def get_coldpreview(photo_id: int):
    photo = get_photo(photo_id)
    original_file = get_original_file(photo)
    
    # Use imalink-core to regenerate
    core_photo = process_image(original_file)
    
    return {
        "coldpreview_base64": core_photo.coldpreview_base64,
        "coldpreview_width": core_photo.coldpreview_width,
        "coldpreview_height": core_photo.coldpreview_height,
    }
```

**Option B: Cache in separate storage** (better performance)
```python
@router.get("/photos/{photo_id}/coldpreview")
async def get_coldpreview(photo_id: int):
    # Check cache (Redis, S3, local file)
    cached = coldpreview_cache.get(photo_id)
    if cached:
        return cached
    
    # Generate and cache
    photo = get_photo(photo_id)
    original_file = get_original_file(photo)
    core_photo = process_image(original_file)
    
    result = {
        "coldpreview_base64": core_photo.coldpreview_base64,
        "coldpreview_width": core_photo.coldpreview_width,
        "coldpreview_height": core_photo.coldpreview_height,
    }
    
    coldpreview_cache.set(photo_id, result)
    return result
```

**Option C: Store in S3/object storage** (production)
```python
# During import
core_photo = process_image(file)
upload_to_s3(f"coldpreviews/{core_photo.hothash}.jpg", 
             base64.b64decode(core_photo.coldpreview_base64))

# During fetch
@router.get("/photos/{photo_id}/coldpreview")
async def get_coldpreview(photo_id: int):
    photo = get_photo(photo_id)
    url = f"https://s3.amazonaws.com/imalink/coldpreviews/{photo.hothash}.jpg"
    return {"coldpreview_url": url}
```

---

## Summary

### CorePhoto (imalink-core)
- **Rolle**: "Alt som kan ekstraheres fra en bildefil"
- **Inkluderer**: hotpreview, coldpreview, EXIF metadata
- **Brukes**: Under import, batch processing, backup/restore
- **Sendes IKKE til frontend direkte**

### Photo (backend database)
- **Rolle**: "Data som lagres og administreres"
- **Inkluderer**: hotpreview (small), metadata, user organization
- **Ekskluderer**: coldpreview (too large)
- **Sendes**: Til frontend som JSON API response

### Coldpreview Strategy
- **Problem**: For stort å lagre i database (100-200KB per foto)
- **Løsning**: Generate on-demand eller cache separat
- **Frontend**: Henter via separat API call `/photos/{id}/coldpreview`

### Key Insight
CorePhoto er et "rikt" objekt som inneholder ALT som KAN ekstraheres, men backend velger å lagre bare det som er praktisk. Dette gir maksimal fleksibilitet:
- Import-prosessen har full tilgang til alle data
- Backend optimaliserer lagring
- Coldpreview kan regenereres når nødvendig
