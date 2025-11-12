# ImaLink Core — AI Coding Agent Quick Instructions

Purpose: quick, actionable guidance for AI agents working on imalink-core (FastAPI image-processing service).

- Project role: a stateless HTTP processing service that accepts image bytes (multipart/form-data) and returns a PhotoEgg JSON. Do NOT read filesystem paths—frontend uploads file bytes.
- Key contract: all image binary fields are Base64 strings (e.g. `hotpreview_base64`, `coldpreview_base64`). This is non-negotiable.

Quick commands
- Start service (dev): `uv run uvicorn service.main:app --reload --port 8765` or `uv run python -m service.main`.
- Run tests: `uv run pytest` (integration tests use FastAPI TestClient). Fixtures live in `tests/fixtures/images/`.
- Format & lint: `uv run black src/ tests/` and `uv run ruff check src/ tests/`; type-check with `uv run mypy src/`.

Essential patterns & files
- API entry: `service/main.py` — POST `/v1/process` accepts `file` and optional `coldpreview_size` form field.
- Core processing: `src/imalink_core/preview/generator.py` (hot/cold preview), `src/imalink_core/metadata/exif_extractor.py` (EXIF tiers), `src/imalink_core/models/photo.py` (CorePhoto dataclass).
- Hothash: SHA256 of the hotpreview JPEG bytes (hotpreview is 150px square). Hothash generation is in preview generator — treat it as the primary identifier.

Architecture essentials
- Three layers: CorePhoto (processing) → PhotoEgg (API response JSON) → Backend Photo (persistence). CorePhoto is NOT the API model.
- PhotoEgg definition: JSON object returned from `/v1/process`. PhotoEggResponse is the Pydantic validation model.
- Decoupling principle: user keeps files anywhere on disk, backend only stores metadata + hothash identifier.
- EXIF reliability: BasicMetadata 98%+ (dimensions, GPS, camera), CameraSettings 70-90% (ISO, aperture) — always check Optional fields.
- Dataclass pattern: all models have `to_dict()` / `from_dict()` for JSON serialization with datetime → ISO string conversion.

Key docs for deep dives
- `PHOTO_MODEL_DESIGN.md` — why 3-layer architecture exists (photographer's perspective).
- `MODEL_LAYERS_ANALYSIS.md` — why CorePhoto ≠ canonical API model.
- `BACKEND_MIGRATION.md` — how backends integrate PhotoEgg endpoint.

Project-specific conventions
- Package manager: use `uv` (e.g., `uv pip install`, `uv sync`) — do not use bare `pip` for reproducible installs.
- Hot vs Cold preview: Hotpreview ALWAYS present (150px). Coldpreview is optional and must be >=150 if requested.
- MIN_IMAGE_SIZE = 4 (images smaller than 4×4 are rejected as corrupt).
- EXIF: always apply `ImageOps.exif_transpose()` before resizing.
- Error handling: public APIs return (success, data/error) patterns; avoid raising exceptions as API surface behavior.

Data shapes & examples
- PhotoEgg: JSON object with `hothash`, `hotpreview_base64`, `hotpreview_width`, `hotpreview_height`, `coldpreview_base64|null`, `primary_filename`, `width`, `height`, `taken_at` (ISO 8601), `camera_make`, `gps_latitude` (decimal degrees), `has_gps`.
- Upload example (curl):
  `curl -X POST http://localhost:8765/v1/process -F "file=@/path/IMG.jpg" -F "coldpreview_size=2560"`

Testing & fixtures
- Tests: `tests/` (unit + integration). Integration tests validate multipart uploads and Base64 outputs.
- Use included fixtures in `tests/fixtures/images/` for EXIF coverage.

Where to look first (fast path)
1. `service/main.py` — endpoint wiring and request validation.
2. `src/imalink_core/preview/generator.py` — preview generation and hothash logic.
3. `src/imalink_core/metadata/exif_extractor.py` — how EXIF is parsed and which fields are best-effort.

Small editing rules for agents
- Preserve Base64 contract and hotpreview/hothash semantics when modifying serialization.
- Keep type hints on public APIs; follow line-length 100.
- Add tests for behavior changes: happy path + one edge case (tiny image or missing EXIF).

Questions / feedback
If anything here is unclear or you'd like more detail (examples, tests to add, or CI commands), tell me which section to expand.
# ImaLink Core - AI Coding Agent Instructions

## Project Overview

**imalink-core** is a FastAPI HTTP service (Python 3.11+) serving as the **interface layer between physical image files and metadata structures**. It handles all image processing for the ImaLink photo management ecosystem, ensuring error-free data transfer between:

- **Physical files** (user's own archive structure on disk)
- **HTTP clients** (backend, desktop apps, any language)
- **Backend database** (metadata-only storage)

This **decouples** the user's file organization from the database - files can remain in any structure on user's disk while metadata is centrally managed.

**Critical distinction**: This is an **HTTP API service**, not a Python library. All integration happens via HTTP endpoints. The service runs locally (desktop apps) or as a microservice (backend infrastructure).

CorePhoto contains ALL extractable data from images during processing. Consumers selectively persist data based on their needs.

**Core is stateless**: Performs purely algorithmic operations (EXIF extraction, preview generation, hashing). No state management, no storage decisions. Consumers decide what to persist and where.

## CRITICAL: Base64 Encoding for Image Data

**ALL image data in PhotoEgg uses Base64 encoding - NO EXCEPTIONS**

### Why Base64?
- JSON can only contain text (strings, numbers, booleans, null, objects, arrays)
- JSON **CANNOT** contain binary data (raw bytes)
- Image files are binary data (JPEG/PNG bytes)
- Base64 converts binary → text, allowing images in JSON

### Fields Using Base64
- `hotpreview_base64`: Base64-encoded JPEG string (NOT bytes)
- `coldpreview_base64`: Base64-encoded JPEG string or null (NOT bytes)
- These are **strings**, not binary data

### Example
```python
# WRONG - cannot put bytes in JSON:
{"hotpreview": b'\xff\xd8\xff\xe0...'}  # ❌ Invalid JSON

# CORRECT - Base64 string in JSON:
{"hotpreview_base64": "/9j/4AAQSkZJRg..."}  # ✅ Valid JSON
```

### Industry Standard
Base64 is the universal standard for embedding binary data in JSON/APIs. No other format is supported in imalink-core.

## Architecture & Data Flow

### Role as Interface Layer

imalink-core serves as the **canonical processing layer** between:

1. **User's file system** (user selects files in frontend)
2. **Processing layer** (this service - extracts, validates, transforms)
3. **Metadata database** (backend - stores only metadata + identifiers)

**Key benefit**: Decoupling - users keep their own file organization while metadata is centrally managed and searchable.

### Primary Usage Pattern: HTTP API with File Upload

**CRITICAL: Frontend uploads image files to core via multipart/form-data**

Core does NOT access filesystem. Frontend reads files and uploads them.

```javascript
// Frontend reads file from user's disk
const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];  // User selected IMG_1234.jpg

// Upload to core (standard multipart/form-data)
const formData = new FormData();
formData.append('file', file);
formData.append('coldpreview_size', 2560);  // optional

const response = await fetch('http://localhost:8765/v1/process', {
  method: 'POST',
  body: formData  // ← Sends file BYTES, not filepath
});

const photoEgg = await response.json();
```

**Response (PhotoEgg JSON):**
```json
{
  "hothash": "abc123...",
  "hotpreview_base64": "/9j/4AAQSkZJRg...",
  "hotpreview_width": 150,
  "hotpreview_height": 150,
  "coldpreview_base64": null,
  "primary_filename": "IMG_1234.jpg",
  "width": 4000,
  "height": 3000,
  "taken_at": "2024-07-15T14:30:00Z",
  "camera_make": "Nikon",
  "gps_latitude": 59.9139,
  "has_gps": true
}
```

**curl equivalent:**
```bash
curl -X POST http://localhost:8765/v1/process \
  -F "file=@/photos/IMG_1234.jpg" \
  -F "coldpreview_size=2560"
```

**Deployment scenarios:**
- **Desktop apps**: Service runs on localhost:8765, frontend uploads local files
- **Backend**: Service can run on same server if needed
- **Development**: Run with `uv run python -m service.main`

### Three-Layer Model Architecture

Understanding the model separation is essential:

1. **CorePhoto** (`src/imalink_core/models/photo.py`) - Complete extractable data
   - ALWAYS contains hotpreview (150x150) as base64
   - OPTIONALLY contains coldpreview (any size from 150px to original) as base64
   - Used during image import/processing pipeline
   - NOT the canonical API model (common misconception - see `PHOTO_MODEL_DESIGN.md`)
   - Includes optional backend fields (`id`, `user_id`) but these are None during core processing

2. **Backend Photo** (external to this library) - Persisted database model
   - Receives CorePhoto, selectively stores fields
   - Keeps hotpreview (small ~5-15KB), handles coldpreview based on storage strategy
   - Adds user organization (rating, tags, albums)

3. **Coldpreview Strategy** - Optional in PhotoEgg
   - CorePhoto can include coldpreview during processing (~100-200KB)
   - Default: skip coldpreview (None) for fastest processing
   - Explicit choice: include coldpreview when needed
   - Backend storage strategy is external to core (disk, S3, cache, on-demand, etc.)
   - Core doesn't know or care where coldpreview is stored

### Core Processing Pipeline

**HTTP API endpoint: POST /v1/process**

**CRITICAL: Accepts multipart/form-data file upload, NOT JSON with filepath**

Request (multipart/form-data):
```bash
curl -X POST http://localhost:8765/v1/process \
  -F "file=@photo.jpg" \
  -F "coldpreview_size=2560"  # optional
```

Response: PhotoEgg JSON (see above)

Internal processing flow:
1. Receive uploaded file bytes (multipart/form-data)
2. Open image from bytes (PIL.Image.open(BytesIO(bytes)))
3. Apply EXIF rotation (ImageOps.exif_transpose)
4. Extract EXIF metadata from bytes
5. Generate previews from Image object
6. Calculate hothash
7. Return PhotoEgg JSON

**API Parameters**:
- `file`: File (multipart/form-data) - REQUIRED
- `coldpreview_size`: Optional[int] = None (form field)
  - None (default): Minimal PhotoEgg - skip coldpreview, only hotpreview (fastest)
  - Any size >= 150: Full PhotoEgg with coldpreview (e.g., 1024, 2560, or up to original size)
  - Validation: If specified, must be >= 150 (hotpreview size)

Key components (all in `src/imalink_core/`):
- `validation/image_validator.py` - File validation (size, format, dimensions) - DEPRECATED (validation happens on upload)
- `metadata/exif_extractor.py` - Two-tier extraction with bytes support:
  - `extract_basic_from_bytes(bytes)` - Extract from uploaded image bytes
  - `extract_camera_settings_from_bytes(bytes)` - Camera settings from bytes
  - Legacy file-based methods still exist for backward compatibility
- `preview/generator.py` - EXIF-aware thumbnails with Image object support:
  - `generate_hotpreview_from_image(img)` - Generate from PIL Image
  - `generate_coldpreview_from_image(img)` - Generate from PIL Image
  - **MIN_IMAGE_SIZE = 4**: Images smaller than 4x4 pixels rejected as corrupt
  - `_validate_image_size(img)` - Validates minimum image dimensions
  - PIL's `thumbnail()` never scales up - small images stay small
  - Legacy file-based methods still exist for backward compatibility
- `models/` - Data structures (CorePhoto, ImportResult, CoreImageFile)

### Hothash: The Unique Identifier

**Hothash = SHA256 hash of hotpreview JPEG bytes** (NOT original image)
- Perceptual duplicate detection (same scene = similar hash)
- Generated in `PreviewGenerator.generate_hotpreview()`
- Stripped of EXIF before hashing (consistent across file copies)
- Primary key equivalent in ImaLink ecosystem

## Development Conventions

### Package Management
- **uv**: Modern Python package manager (replaces pip/pip-tools)
- Fast, reliable dependency resolution
- Use `uv pip install` instead of `pip install`
- Use `uv sync` for installing from pyproject.toml

### Code Style
- **Type hints**: Required on all public APIs (`mypy` enforced)
- **Dataclasses**: Preferred over plain classes (see `BasicMetadata`, `CorePhoto`)
- **Line length**: 100 characters (`black` + `ruff` configured)
- **Error handling**: Return success/error tuples, never raise in public APIs
  ```python
  # Pattern used throughout:
  def validate_file(path: Path) -> Tuple[bool, Optional[str]]:
      return (False, "error message")  # NOT raise Exception
  ```

### Testing Philosophy
- Tests in `tests/` use pytest
- **66 tests total**: 51 unit tests + 15 integration tests
- Integration tests use FastAPI TestClient for end-to-end API testing
- Graceful degradation for missing files (returns None/empty, not crashes)
- Example: `ExifExtractor.extract_basic(Path("nonexistent.jpg"))` returns empty metadata
- Test fixtures in `tests/fixtures/images/` - real camera images for EXIF testing
- Image size validation: MIN_IMAGE_SIZE = 4 pixels (smaller images rejected as corrupt)

### EXIF Reliability Tiers
Critical for understanding metadata handling (documented in `exif_extractor.py`):
- **BasicMetadata**: 98%+ reliable (dimensions, timestamp, camera make/model, GPS)
- **CameraSettings**: 70-90% reliable (ISO, aperture, shutter, focal length)
- Always check `Optional` fields - missing data is normal and expected

## Common Development Tasks

### Running Tests
```bash
pytest                                    # All tests (66 total: 51 unit + 15 integration)
pytest tests/test_service_api.py          # Integration tests (FastAPI endpoint)
pytest tests/test_preview_generation.py   # Preview generation tests
pytest --cov=imalink_core --cov-report=html  # With coverage
```

**Test Structure:**
- `tests/test_service_api.py` - **Integration tests** for FastAPI `/v1/process` endpoint
  - File upload via multipart/form-data
  - PhotoEgg JSON response validation
  - Error handling (invalid files, tiny images, bad parameters)
  - Base64 encoding validation
- `tests/test_preview_generation.py` - Preview generation + hothash
- `tests/test_exif_extraction.py` - EXIF metadata extraction
- `tests/test_image_validation.py` - Image validation (legacy)
- `tests/test_basic.py` - Smoke tests

### Code Quality
```bash
black src/ tests/           # Format (line-length=100)
ruff check src/ tests/      # Lint
mypy src/                   # Type check
```

### Running the Service
```bash
# Start service
uv run python -m service.main

# Or with auto-reload for development
uv run uvicorn service.main:app --reload --port 8765

# Docker deployment
docker build -f service/Dockerfile -t imalink-core-api .
docker run -p 8765:8765 -v /photos:/photos imalink-core-api
```

## Integration Patterns

### Desktop Integration (Electron/Tauri/Qt)
```typescript
// JavaScript desktop app calls local service via HTTP
// User selects file from their file system
const fileInput = document.getElementById('fileInput') as HTMLInputElement;
const file = fileInput.files[0];

// Upload file to local core service
const formData = new FormData();
formData.append('file', file);
formData.append('coldpreview_size', '2560');  // optional

const response = await fetch('http://localhost:8765/v1/process', {
  method: 'POST',
  body: formData  // ← Standard file upload
});

const photoEgg = await response.json();
// {
//   hothash: "abc123...",
//   hotpreview_base64: "...",
//   hotpreview_width: 150,
//   hotpreview_height: 150,
//   coldpreview_base64: null,  // or base64 string if requested
//   primary_filename: "IMG_1234.jpg",
//   width: 4000,
//   height: 3000,
//   taken_at: "2024-07-15T14:30:00Z",
//   camera_make: "Nikon",
//   gps_latitude: 59.9139,
//   has_gps: true
// }

// Send PhotoEgg to remote backend
await fetch('https://backend.com/api/photos', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(photoEgg)
});
```

### Backend Integration
```python
# Backend receives CorePhoto from frontend
# Decides what to store based on its own requirements
db_photo = {
    "hothash": photo_data["hothash"],
    "hotpreview_base64": photo_data["hotpreview_base64"],
    "taken_at": photo_data["taken_at"],
    "file_path": photo_data["file_path"],  # Location on user's machine
    # ... selective fields
}

# If coldpreview was included, backend handles storage
if "coldpreview_base64" in photo_data:
    # Backend decides: save to disk, S3, cache, or discard
    storage.save_coldpreview(photo_data["hothash"], photo_data["coldpreview_base64"])
```

**See `BACKEND_MIGRATION.md` for complete backend integration guide**, including:
- New endpoint: `POST /api/v1/photos/photoegg`
- Pydantic schema for PhotoEgg validation
- Coldpreview storage strategies (Database/Disk/S3/Skip)
- Incremental migration strategy (no breaking changes)

### The Decoupling Principle

**User's file organization** (any of these):
```
C:/Photos/2024/Norway/IMG_1234.jpg
/mnt/nas/Backup/Pictures/IMG_1234.jpg
D:/Archive/Family/Summer/IMG_1234.jpg
```

**Backend only knows**:
```json
{
  "hothash": "abc123...",
  "taken_at": "2024-07-15T14:30:00Z",
  "gps_latitude": 59.9139,
  "camera_make": "Nikon"
}
```

Same hothash can exist at multiple locations - backend tracks metadata, user tracks files.

### Preview Sizes
- **Hotpreview**: 150x150px, ~5-15KB, gallery thumbnails, stored in DB
- **Coldpreview**: Variable size (150px to original), ~100-200KB typical, detail view, optional

## Key Files to Reference

- `service/main.py` - FastAPI service entry point with POST /v1/process endpoint
- `service/README.md` - API usage examples for all languages
- `src/imalink_core/api.py` - Core processing function wrapped by service
- `src/imalink_core/models/photo.py` - CorePhoto structure, to_dict/from_dict patterns
- `PHOTO_MODEL_DESIGN.md` - Critical: explains 3-layer architecture from photographer's perspective
- `MODEL_LAYERS_ANALYSIS.md` - Why CorePhoto is NOT the canonical API model
- `BACKEND_MIGRATION.md` - Guide for integrating PhotoEgg API in backend server

## Project-Specific Patterns

### Dataclass Serialization Pattern
Used consistently across all models:
```python
@dataclass
class CorePhoto:
    # fields...
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert datetime to ISO strings, handle nested objects"""
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorePhoto':
        """Parse ISO strings back to datetime, restore enums"""
```

### EXIF-Aware Image Rotation
Always use `ImageOps.exif_transpose()` before resizing (see `preview/generator.py`):
```python
img = Image.open(path)
img = ImageOps.exif_transpose(img)  # Apply EXIF rotation
img.thumbnail(size, Image.Resampling.LANCZOS)
```

### Import Result Pattern
All processing returns `ImportResult` with success flag and optional data:
```python
@dataclass
class ImportResult:
    success: bool
    photo: Optional[CorePhoto] = None
    error: Optional[str] = None
```

## Gotchas & Common Mistakes

1. **Core is stateless** - No storage, no caching, no persistence. Pure algorithmic processing.
2. **Don't treat CorePhoto as the API model** - It's for internal processing. Backend creates its own model.
3. **Coldpreview inclusion is optional** - Consumer decides whether to include in PhotoEgg (bandwidth vs completeness)
4. **GPS is optional** - Always check `has_gps` and `gps_latitude is not None`
5. **Camera settings are best-effort** - 30% of consumer photos lack ISO/aperture/etc
6. **Hothash is from preview, not original** - Same original can have different hothash if preview generation changes
7. **EXIF orientation must be applied** - Image bytes may be rotated, use `exif_transpose()`
8. **Small images stay small** - PIL's `thumbnail()` never scales up. A 59x59px image stays 59x59px (not 150x150)
9. **Tiny images rejected** - Images < 4x4 pixels are rejected as likely corrupt (MIN_IMAGE_SIZE = 4)

## Documentation Style
- Docstrings: Google style with Args/Returns sections
- Examples in docstrings use `>>>` for interactive sessions
- Architecture decisions explained in `PHOTO_MODEL_DESIGN.md` and `MODEL_LAYERS_ANALYSIS.md`
