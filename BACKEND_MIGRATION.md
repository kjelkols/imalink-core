# Backend Migration: PhotoEgg API Integration

## Context

imalink-core har fått oppdatert API. Backend må støtte det nye PhotoEgg-formatet samtidig som bakoverkompatibilitet beholdes.

## Nåværende imalink-core API

```python
from pathlib import Path
from imalink_core import process_image

# Process image (returns ImportResult med CorePhoto)
result = process_image(
    Path("photo.jpg"),
    coldpreview_max_size=1920  # Default 1920, None to skip
)

if result.success:
    photo_egg = result.photo.to_dict()  # CorePhoto → dict
    # Send til backend
```

## PhotoEgg Structure (CorePhoto.to_dict())

```python
{
    # Identity
    "hothash": "abc123...",  # SHA256 hash (unique ID)
    
    # Hotpreview (150x150px, ~5-15KB)
    "hotpreview_base64": "/9j/4AAQ...",
    "hotpreview_width": 150,
    "hotpreview_height": 113,
    
    # Coldpreview (1920x1080px, ~100-200KB) - OPTIONAL
    "coldpreview_base64": "/9j/4AAQ..." | null,
    "coldpreview_width": 1920 | null,
    "coldpreview_height": 1080 | null,
    
    # File info
    "primary_filename": "IMG_1234.jpg",
    "width": 4032,
    "height": 3024,
    
    # Timestamps
    "taken_at": "2024-11-10T14:30:00" | null,
    "first_imported": null,  # Backend setter
    "last_imported": null,   # Backend setter
    
    # Camera metadata (98% reliable)
    "camera_make": "Canon" | null,
    "camera_model": "EOS R5" | null,
    
    # GPS (hvis tilgjengelig)
    "gps_latitude": 59.9139 | null,
    "gps_longitude": 10.7522 | null,
    "has_gps": true | false,
    
    # Camera settings (70-90% reliable)
    "iso": 400 | null,
    "aperture": 2.8 | null,
    "shutter_speed": "1/1000" | null,
    "focal_length": 85.0 | null,
    "lens_model": "RF 85mm F2" | null,
    "lens_make": "Canon" | null,
    
    # Organization (backend setter)
    "rating": null,
    "import_session_id": null,
    "has_raw_companion": false,
    
    # Backend fields
    "id": null,      # Database ID (backend setter)
    "user_id": null  # Owner (backend setter)
}
```

## Oppgave 1: Lag nytt endpoint POST /api/v1/photos/photoegg

**Inndata**: PhotoEgg (CorePhoto.to_dict())  
**Utdata**: Lagret Photo med backend-ID

```python
@router.post("/api/v1/photos/photoegg")
async def create_photo_from_egg(
    photo_egg: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Ny endpoint som tar imot PhotoEgg direkte fra imalink-core.
    
    Fordeler:
    - Enklere: bare send result.photo.to_dict()
    - Komplett: all EXIF data inkludert
    - Fleksibel: coldpreview er optional
    """
    # 1. Valider PhotoEgg
    if not photo_egg.get("hothash"):
        raise HTTPException(400, "Missing hothash")
    
    # 2. Sjekk om photo finnes (duplicate detection)
    existing = await db.get_photo_by_hothash(
        photo_egg["hothash"], 
        current_user.id
    )
    if existing:
        return existing  # Already imported
    
    # 3. Lagre hotpreview (alltid present)
    # Store in DB eller blob storage
    
    # 4. Lagre coldpreview (hvis present)
    if photo_egg.get("coldpreview_base64"):
        # Store på disk/S3/cache eller skip
        pass
    
    # 5. Opprett Photo i database
    db_photo = Photo(
        hothash=photo_egg["hothash"],
        user_id=current_user.id,
        primary_filename=photo_egg["primary_filename"],
        taken_at=photo_egg.get("taken_at"),
        width=photo_egg["width"],
        height=photo_egg["height"],
        camera_make=photo_egg.get("camera_make"),
        camera_model=photo_egg.get("camera_model"),
        gps_latitude=photo_egg.get("gps_latitude"),
        gps_longitude=photo_egg.get("gps_longitude"),
        has_gps=photo_egg.get("has_gps", False),
        iso=photo_egg.get("iso"),
        aperture=photo_egg.get("aperture"),
        shutter_speed=photo_egg.get("shutter_speed"),
        focal_length=photo_egg.get("focal_length"),
        lens_model=photo_egg.get("lens_model"),
        lens_make=photo_egg.get("lens_make"),
        # Backend legger til:
        first_imported=datetime.utcnow(),
        last_imported=datetime.utcnow(),
    )
    await db.save(db_photo)
    
    return db_photo
```

## Oppgave 2: Coldpreview Storage Strategy

**Velg én av disse strategiene:**

### A. Lagre i database (enklest, men stor database)
```python
photo.coldpreview_base64 = photo_egg.get("coldpreview_base64")
```
- ✅ Enklest å implementere
- ❌ Database blir stor (~200KB per foto)

### B. Lagre på disk (balansert)
```python
if photo_egg.get("coldpreview_base64"):
    coldpreview_path = f"storage/coldpreviews/{photo_egg['hothash']}.jpg"
    save_base64_to_file(coldpreview_path, photo_egg["coldpreview_base64"])
    photo.coldpreview_path = coldpreview_path  # Lagre path i DB
```
- ✅ Database forblir liten
- ✅ Rask tilgang
- ❌ Krever disk space management

### C. Lagre i S3/blob storage (produksjonsklart)
```python
if photo_egg.get("coldpreview_base64"):
    s3_key = f"coldpreviews/{photo_egg['hothash']}.jpg"
    await s3.upload_base64(s3_key, photo_egg["coldpreview_base64"])
    photo.coldpreview_s3_key = s3_key
```
- ✅ Skalerbart
- ✅ CDN-klart
- ❌ Krever S3/blob setup

### D. Skip coldpreview (regenerer on-demand)
```python
# Ikke lagre coldpreview
# Frontend kan regenerere ved behov fra original fil
```
- ✅ Minst lagring
- ❌ Krever tilgang til original fil

**Anbefaling**: Start med **B (disk)**, migrer til **C (S3)** senere.

## Oppgave 3: Bakoverkompatibilitet

**Behold eksisterende endpoints**:
- `POST /api/v1/photos` (gammelt skjema)
- `PUT /api/v1/photos/{id}` (gammelt skjema)

Legg til deprecation warning:
```python
@router.post("/api/v1/photos")
async def create_photo_legacy(...):
    # Gammelt endpoint
    response.headers["X-API-Deprecation"] = "Use /api/v1/photos/photoegg"
    response.headers["X-API-Sunset"] = "2026-01-01"
    # ... existing logic
```

## Oppgave 4: Pydantic Schema (anbefalt)

```python
from pydantic import BaseModel, Field
from typing import Optional

class PhotoEggSchema(BaseModel):
    """Schema for PhotoEgg (imalink-core output)"""
    
    # Identity (required)
    hothash: str = Field(..., min_length=64, max_length=64)
    
    # Hotpreview (required)
    hotpreview_base64: str
    hotpreview_width: int = Field(..., gt=0)
    hotpreview_height: int = Field(..., gt=0)
    
    # Coldpreview (optional)
    coldpreview_base64: Optional[str] = None
    coldpreview_width: Optional[int] = None
    coldpreview_height: Optional[int] = None
    
    # File info (required)
    primary_filename: str
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    
    # Metadata (optional)
    taken_at: Optional[str] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    
    # GPS (optional)
    gps_latitude: Optional[float] = Field(None, ge=-90, le=90)
    gps_longitude: Optional[float] = Field(None, ge=-180, le=180)
    has_gps: bool = False
    
    # Camera settings (optional)
    iso: Optional[int] = Field(None, gt=0)
    aperture: Optional[float] = Field(None, gt=0)
    shutter_speed: Optional[str] = None
    focal_length: Optional[float] = Field(None, gt=0)
    lens_model: Optional[str] = None
    lens_make: Optional[str] = None
```

Bruk i endpoint:
```python
@router.post("/api/v1/photos/photoegg")
async def create_photo_from_egg(
    photo_egg: PhotoEggSchema,  # Type-safe validation
    current_user: User = Depends(get_current_user)
):
    # photo_egg er nå validert og type-safe
    pass
```

## Migrasjonsstrategi (Inkrementell)

### Fase 1: Nytt endpoint (INGEN breaking changes)
```
✓ POST /api/v1/photos/photoegg (ny - støtter PhotoEgg)
✓ POST /api/v1/photos (gammel - fortsatt fungerer)
```

### Fase 2: Oppdater Qt-frontend
```python
# Qt-frontend kode
result = process_image(file_path)
if result.success:
    response = await api.post(
        "/api/v1/photos/photoegg",
        result.photo.to_dict()
    )
```

### Fase 3: Deprecate gammelt endpoint
```python
# Legg til deprecation warnings
# Sett sunset date: 2026-01-01
```

### Fase 4: Fjern gammelt endpoint
```python
# Når alle klienter er migrert (6+ måneder)
# DELETE /api/v1/photos (gammelt endpoint)
```

## Testing Checklist

Test at PhotoEgg endpoint håndterer:

- [ ] Komplett PhotoEgg (med coldpreview)
- [ ] PhotoEgg uten coldpreview (coldpreview_base64=null)
- [ ] PhotoEgg med GPS
- [ ] PhotoEgg uten GPS
- [ ] PhotoEgg med kamerainnstillinger
- [ ] PhotoEgg uten kamerainnstillinger (null values OK)
- [ ] Duplicate detection (samme hothash)
- [ ] Invalid hothash (feil lengde, format)
- [ ] Missing required fields
- [ ] Invalid GPS coordinates (out of range)

## Spørsmål å besvare

1. **Coldpreview storage**: Database, Disk, S3, eller Skip?
2. **Deprecation timeline**: Hvor lenge skal gammelt endpoint støttes?
3. **Validation**: Strict (reject invalid) eller lenient (accept missing)?
4. **Schema**: Bruke Pydantic eller plain dict?

## Eksempel Test Data

```python
# Komplett PhotoEgg
complete_egg = {
    "hothash": "abc123" * 10 + "abcd",  # 64 chars
    "hotpreview_base64": "...",
    "hotpreview_width": 150,
    "hotpreview_height": 113,
    "coldpreview_base64": "...",
    "coldpreview_width": 1920,
    "coldpreview_height": 1440,
    "primary_filename": "IMG_1234.jpg",
    "width": 4032,
    "height": 3024,
    "taken_at": "2024-11-10T14:30:00",
    "camera_make": "Canon",
    "camera_model": "EOS R5",
    "gps_latitude": 59.9139,
    "gps_longitude": 10.7522,
    "has_gps": True,
    "iso": 400,
    "aperture": 2.8,
    "shutter_speed": "1/1000",
    "focal_length": 85.0,
    "lens_model": "RF 85mm F2",
    "lens_make": "Canon",
}

# Minimal PhotoEgg (kun påkrevde felter)
minimal_egg = {
    "hothash": "xyz789" * 10 + "wxyz",
    "hotpreview_base64": "...",
    "hotpreview_width": 150,
    "hotpreview_height": 100,
    "coldpreview_base64": None,  # Skipped
    "primary_filename": "photo.jpg",
    "width": 800,
    "height": 600,
    "taken_at": None,
    "has_gps": False,
}
```

## Viktige Notater

**PhotoEgg er IKKE en erstatning for hele backend Photo-modellen.**

Backend legger til:
- `user_id` (eierskap)
- `id` (database ID)
- `rating`, `tags`, `albums` (brukerorganisering)
- `import_session_id` (tracking)
- `first_imported`, `last_imported` (timestamps)

**PhotoEgg = rådata fra bildefil**  
**Backend Photo = PhotoEgg + brukerdata + organisering**

## Neste Steg

1. [ ] Implementer `POST /api/v1/photos/photoegg` endpoint
2. [ ] Velg coldpreview storage strategy
3. [ ] Lag Pydantic schema for PhotoEggSchema
4. [ ] Skriv tester for nytt endpoint
5. [ ] Test med ekte PhotoEgg data fra imalink-core
6. [ ] Oppdater Qt-frontend til å bruke nytt endpoint
7. [ ] Deprecate gammelt endpoint (6+ måneders varsel)
