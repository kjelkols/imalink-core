# ImaLink Core

**Core image processing library for the ImaLink photo management ecosystem**

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

ImaLink Core is a platform-independent Python library that provides all image processing functionality for the ImaLink ecosystem:

- **EXIF metadata extraction** - Reliable extraction of camera settings, GPS, timestamps
- **Preview generation** - Generate hotpreview (150x150) and coldpreview (1920x1080) thumbnails
- **Hothash calculation** - SHA256-based perceptual duplicate detection
- **Image validation** - Format detection and file validation
- **RAW format support** - Optional support for NEF, CR2, ARW, DNG files

## 🚀 Installation

```bash
# Basic installation
pip install imalink-core

# With RAW format support
pip install imalink-core[raw]

# Development installation
pip install imalink-core[dev]
```

## 📖 Quick Start

### Process a single image

```python
from pathlib import Path
from imalink_core import process_image

# Process image - extracts metadata, generates previews, calculates hothash
result = process_image(Path("photo.jpg"))

if result.success:
    photo = result.photo  # CorePhoto object
    print(f"Hothash: {photo.hothash}")
    print(f"Hotpreview: {photo.hotpreview_width}x{photo.hotpreview_height}px")
    print(f"Taken at: {result.metadata.taken_at}")
    print(f"Camera: {result.metadata.camera_make} {result.metadata.camera_model}")
    print(f"GPS: {result.metadata.gps_latitude}, {result.metadata.gps_longitude}")
    
    # Hotpreview is embedded in CorePhoto object
    if photo.hotpreview_base64:
        print(f"Hotpreview ready for API transmission: {len(photo.hotpreview_base64)} bytes")
else:
    print(f"Error: {result.error}")
```

### Batch processing

```python
from pathlib import Path
from imalink_core import batch_process

# Find all images
photos = list(Path("./photos").rglob("*.jpg"))

# Process with progress callback
def on_progress(current, total, result):
    if result.success:
        print(f"[{current}/{total}] ✓ {result.photo.primary_filename}")

results = batch_process(photos, progress_callback=on_progress)

# Summary
successful = [r for r in results if r.success]
print(f"\nImported {len(successful)}/{len(results)} photos")
```

### Extract metadata only

```python
from pathlib import Path
from imalink_core import ExifExtractor

# Extract basic metadata (98%+ reliable)
metadata = ExifExtractor.extract_basic(Path("photo.jpg"))
print(f"Taken: {metadata.taken_at}")
print(f"Dimensions: {metadata.width}x{metadata.height}")
print(f"Camera: {metadata.camera_make} {metadata.camera_model}")

# Extract camera settings (70-90% reliable, best-effort)
settings = ExifExtractor.extract_camera_settings(Path("photo.jpg"))
print(f"ISO: {settings.iso}")
print(f"Aperture: f/{settings.aperture}")
print(f"Shutter: {settings.shutter_speed}")
print(f"Focal length: {settings.focal_length}mm")
```

### Generate previews

```python
from pathlib import Path
from imalink_core import PreviewGenerator

# Generate both previews in one pass
hotpreview, coldpreview = PreviewGenerator.generate_both(Path("photo.jpg"))

print(f"Hotpreview: {hotpreview.width}x{hotpreview.height}px")
print(f"Hothash: {hotpreview.hothash}")
print(f"Coldpreview: {coldpreview.width}x{coldpreview.height}px")

# Save previews
with open("hot.jpg", "wb") as f:
    f.write(hotpreview.bytes)
with open("cold.jpg", "wb") as f:
    f.write(coldpreview.bytes)
```

## 🏗️ Architecture

```
imalink_core/
├── metadata/        # EXIF extraction and GPS parsing
├── preview/         # Preview generation and hothash calculation
├── image/           # Image format detection and RAW handling
├── models/          # Data models (Photo, ImageFile, etc.)
├── validation/      # Image validation
└── api.py           # High-level convenience functions
```

## 📊 Data Models

### Photo Model

The `Photo` model is the canonical representation shared across the ImaLink ecosystem:

```python
from imalink_core.models import CorePhoto

photo = CorePhoto(
    hothash="abc123...",
    primary_filename="IMG_1234.jpg",
    taken_at="2025-01-15T14:30:00Z",
    width=6000,
    height=4000,
    camera_make="Nikon",
    camera_model="D850",
    gps_latitude=59.9139,
    gps_longitude=10.7522,
    has_gps=True,
    iso=400,
    aperture=2.8,
    focal_length=85.0,
)

# Convert to dict for JSON serialization
data = photo.to_dict()

# Load from dict (e.g., API response)
photo = CorePhoto.from_dict(data)
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=imalink_core --cov-report=html

# Run specific test
pytest tests/test_metadata/test_exif_extractor.py
```

## 🤝 Integration

### Backend Integration (FastAPI)

```python
from imalink_core import process_image
from pathlib import Path

async def import_photo(file_path: Path, user_id: int):
    # Process with imalink-core
    result = process_image(file_path)
    
    if not result.success:
        raise ValueError(f"Import failed: {result.error}")
    
    # Store in database
    photo = await db.create_photo({
        "user_id": user_id,
        "hothash": result.hothash,
        **result.photo.to_dict()
    })
    
    # Store previews in object storage
    await storage.store_hotpreview(result.hothash, result.hotpreview_base64)
    await storage.store_coldpreview(result.hothash, result.coldpreview_bytes)
    
    return photo
```

## 📚 Documentation

- [API Reference](docs/api_reference.md)
- [Examples](examples/)
- [Architecture](docs/architecture.md)

## 🛠️ Development

```bash
# Clone repository
git clone https://github.com/kjelkols/imalink-core.git
cd imalink-core

# Install in development mode with all extras
pip install -e ".[all]"

# Run tests
pytest

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [imalink-backend](https://github.com/kjelkols/imalink) - FastAPI backend
- [imalink-web](https://github.com/kjelkols/imalink-web) - Modern web frontend (coming soon)

## 🙏 Acknowledgments

Built with:
- [Pillow](https://python-pillow.org/) - Image processing
- [rawpy](https://pypi.org/project/rawpy/) - RAW format support (optional)
