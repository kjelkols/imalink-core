# ImaLink Core - AI Coding Agent Instructions

## Project Overview

**imalink-core** is a platform-independent Python library (3.11+) serving as the **interface layer between physical image files and metadata structures**. It handles all image processing for the ImaLink photo management ecosystem, ensuring error-free data transfer between:

- **Physical files** (user's own archive structure on disk)
- **Local frontend** (Qt/desktop app for real file handling)
- **Backend database** (metadata-only storage)

This **decouples** the user's file organization from the database - files can remain in any structure on user's disk while metadata is centrally managed.

**Critical distinction**: This is a **library**, not an application. Currently used as a Python library by Qt-frontend for client-side processing. Future architecture will expose this as PhotoEgg API service to support language-agnostic frontends (Next.js/Electron, etc.). Backend server-side import may be added later.

CorePhoto contains ALL extractable data from images during processing. Consumers selectively persist data based on their needs.

**Core is stateless**: Performs purely algorithmic operations (EXIF extraction, preview generation, hashing). No state management, no storage decisions. Consumers decide what to persist and where.

## Architecture & Data Flow

### Role as Interface Layer

imalink-core serves as the **canonical processing layer** between:

1. **User's file system** (any structure: folders, external drives, NAS)
2. **Processing layer** (this library - extracts, validates, transforms)
3. **Metadata database** (backend - stores only metadata + identifiers)

**Key benefit**: Decoupling - users keep their own file organization while metadata is centrally managed and searchable.

### Primary Usage Pattern: Local Frontend (Desktop Qt App)

```python
# User selects file from their disk: C:/Photos/Vacation/IMG_1234.jpg

# Minimal PhotoEgg (hotpreview only, default - fastest)
result = process_image(Path(user_selected_file))

# Full PhotoEgg with coldpreview
result = process_image(Path(user_selected_file), coldpreview_size=2560)

# Smaller coldpreview
result = process_image(Path(user_selected_file), coldpreview_size=1024)

if result.success:
    # Send CorePhoto metadata to backend API
    response = api.upload_metadata(result.photo.to_dict())
    
    # Original file stays on user's disk
    # Backend stores only metadata, not the file
```

**Future architecture**: PhotoEgg API service - wrap imalink-core in FastAPI to support language-agnostic frontends (Next.js/Electron, C#, Swift, etc.). Single endpoint: local file path + options → PhotoEgg JSON. This will replace direct library usage but maintain identical processing logic.

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

```python
# Core's single responsibility: (filepath, coldpreview_size) → PhotoEgg JSON

# Minimal PhotoEgg (default - hotpreview only)
process_image(path)

# Full PhotoEgg with coldpreview
process_image(path, coldpreview_size=2560)

# Smaller coldpreview
process_image(path, coldpreview_size=1024)

# Batch processing
batch_process(paths, coldpreview_size=None, progress_callback=...)  # Minimal
batch_process(paths, coldpreview_size=2560, progress_callback=...)  # Full

Path → validate → extract EXIF → generate previews → calculate hothash → PhotoEgg
```

**API Parameters**:
- `coldpreview_size`: Optional[int] = None
  - None (default): Minimal PhotoEgg - skip coldpreview, only hotpreview (fastest)
  - Any size >= 150: Full PhotoEgg with coldpreview (e.g., 1024, 2560, or up to original size)
  - Validation: If specified, must be >= 150 (hotpreview size)

Key components (all in `src/imalink_core/`):
- `validation/image_validator.py` - File validation (size, format, dimensions)
- `metadata/exif_extractor.py` - Two-tier extraction (BasicMetadata 98% reliable, CameraSettings 70-90%)
- `preview/generator.py` - EXIF-aware thumbnails with rotation handling
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
- Graceful degradation for missing files (returns None/empty, not crashes)
- Example: `ExifExtractor.extract_basic(Path("nonexistent.jpg"))` returns empty metadata
- Test fixtures in `tests/fixtures/images/` - 7 synthetic images (~55KB total)
- Run `uv run python tests/generate_test_fixtures.py` to regenerate test images
- Note: Generated test images have limited EXIF support - use real photos for comprehensive testing

### EXIF Reliability Tiers
Critical for understanding metadata handling (documented in `exif_extractor.py`):
- **BasicMetadata**: 98%+ reliable (dimensions, timestamp, camera make/model, GPS)
- **CameraSettings**: 70-90% reliable (ISO, aperture, shutter, focal length)
- Always check `Optional` fields - missing data is normal and expected

## Common Development Tasks

### Running Tests
```bash
pytest                                    # All tests
pytest --cov=imalink_core --cov-report=html  # With coverage
pytest tests/test_basic.py                # Specific file
```

### Code Quality
```bash
black src/ tests/           # Format (line-length=100)
ruff check src/ tests/      # Lint
mypy src/                   # Type check
```

### Installing with uv
```bash
# Install package in development mode
uv pip install -e .

# With RAW support
uv pip install -e ".[raw]"     # Adds rawpy for NEF/CR2/ARW/DNG

# Development dependencies
uv pip install -e ".[dev]"     # pytest, black, ruff, mypy

# All extras
uv pip install -e ".[all]"     # Everything

# Sync from pyproject.toml (preferred)
uv sync                         # Install all dependencies
uv sync --extra dev            # Include dev dependencies
uv sync --extra all            # Include all extras
```

## Integration Patterns

### Current Integration: Qt Frontend (Direct Library Usage)
```python
# Qt-frontend imports imalink-core as Python library
from pathlib import Path
from imalink_core import process_image

def import_from_user_disk(file_path: Path, backend_api):
    """Process file locally, send only metadata to backend"""
    # Default: Minimal PhotoEgg (hotpreview only, fastest)
    result = process_image(file_path)
    
    # Or with coldpreview (specify size as needed):
    # result = process_image(file_path, coldpreview_size=2560)
    
    if result.success:
        # Send metadata to backend - file stays on user's disk
        response = backend_api.create_photo({
            "hothash": result.hothash,
            "hotpreview_base64": result.hotpreview_base64,
            "file_path": str(file_path),  # Track location on user's machine
            **result.photo.to_dict()
        })
        
        # User can now find this photo via backend search
        # but file remains in: C:/Users/John/Photos/Vacation/IMG_1234.jpg
```

### Future Integration: PhotoEgg API (Language-Agnostic)
```typescript
// Next.js/Electron frontend calls PhotoEgg service via HTTP
// Single endpoint: file path + options → PhotoEgg JSON
const response = await fetch('http://localhost:8765/v1/process', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    file_path: 'dsc_1234.jpg',  // or full path: C:/Photos/dsc_1234.jpg
    coldpreview_size: null  // null (default) or specify size (e.g., 2560)
  })
});

const photoEgg = await response.json();
// {
//   hothash: "abc123...",
//   hotpreview: { base64: "...", width: 150, height: 150 },
//   coldpreview: { base64: "...", width: 2560, height: 1920 },  // if requested
//   metadata: { taken_at: "2024-07-15T14:30:00Z", camera: {...}, gps: {...} },
//   file: { filename: "dsc_1234.jpg", size: 4567890, format: "jpeg" }
// }
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

- `src/imalink_core/api.py` - Primary entry point, study `process_image()` flow
- `src/imalink_core/models/photo.py` - CorePhoto structure, to_dict/from_dict patterns
- `PHOTO_MODEL_DESIGN.md` - Critical: explains 3-layer architecture from photographer's perspective
- `MODEL_LAYERS_ANALYSIS.md` - Why CorePhoto is NOT the canonical API model
- `BACKEND_MIGRATION.md` - Guide for integrating PhotoEgg API in backend server
- `examples/simple_import.py` - Minimal usage example
- `examples/batch_import.py` - Batch processing with progress callbacks

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

## Documentation Style
- Docstrings: Google style with Args/Returns sections
- Examples in docstrings use `>>>` for interactive sessions
- Architecture decisions explained in `PHOTO_MODEL_DESIGN.md` and `MODEL_LAYERS_ANALYSIS.md`
