# ImaLink Core

**Image processing HTTP service for the ImaLink photo management ecosystem**

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

ImaLink Core is a FastAPI HTTP service that provides all image processing functionality for the ImaLink ecosystem:

- **EXIF metadata extraction** - Reliable extraction of camera settings, GPS, timestamps
- **Preview generation** - Generate hotpreview (150x150) and coldpreview (variable size) thumbnails
- **Hothash calculation** - SHA256-based perceptual duplicate detection
- **Image validation** - Format detection and file validation
- **RAW format support** - Process 900+ camera models (NEF, CR2, CR3, ARW, RAF, ORF, PEF, DNG, etc.) - see [RAW_SUPPORT.md](RAW_SUPPORT.md)
- **Base64 encoding** - All image data uses Base64 for JSON compatibility (industry standard)
- **Language-agnostic** - HTTP API works with any programming language

## 🚀 Quick Start

### Start the service

```bash
# Clone repository
git clone https://github.com/kjelkols/imalink-core.git
cd imalink-core

# Install dependencies
pip install -e .

# Start service
python -m service.main
```

Service runs on: `http://localhost:8765`

### Upload an image

```bash
# Process JPEG/PNG
curl -X POST http://localhost:8765/v1/process \
  -F "file=@photo.jpg" \
  -F "coldpreview_size=2560"

# Process RAW file (requires rawpy: uv pip install rawpy)
curl -X POST http://localhost:8765/v1/process \
  -F "file=@photo.NEF" \
  -F "coldpreview_size=2560"
```
    
    # Both previews are embedded in CorePhoto object as Base64 strings
    # Base64 is the industry standard for binary data in JSON
    if photo.hotpreview_base64:
**Response (PhotoCreateSchema JSON):**
```json
{
  "hothash": "abc123...",
  "hotpreview_base64": "/9j/4AAQSkZJRg...",
  "hotpreview_width": 150,
  "hotpreview_height": 150,
  "coldpreview_base64": null,
  "primary_filename": "photo.jpg",
  "width": 4000,
  "height": 3000,
  "taken_at": "2024-07-15T14:30:00Z",
  "camera_make": "Nikon",
  "gps_latitude": 59.9139,
  "has_gps": true
}
```

### Integration Examples

<details>
<summary><b>TypeScript/JavaScript (Browser)</b></summary>

```typescript
// HTML: <input type="file" id="fileInput">

const fileInput = document.getElementById('fileInput') as HTMLInputElement;
const file = fileInput.files[0];

const formData = new FormData();
formData.append('file', file);
formData.append('coldpreview_size', '2560');  // optional

const response = await fetch('http://localhost:8765/v1/process', {
  method: 'POST',
  body: formData
});

const photoData = await response.json();
```
</details>

<details>
<summary><b>Python</b></summary>

```python
import requests

with open('photo.jpg', 'rb') as f:
    files = {'file': f}
    data = {'coldpreview_size': 2560}  # optional
    
    response = requests.post(
        'http://localhost:8765/v1/process',
        files=files,
        data=data
    )
    
photo_data = response.json()
```
</details>

See `service/README.md` for more integration examples.

## 🏗️ Architecture

```
imalink-core/
├── service/         # FastAPI HTTP service
├── src/imalink_core/
│   ├── metadata/    # EXIF extraction and GPS parsing
│   ├── preview/     # Preview generation and hothash calculation
│   ├── image/       # Image format detection and RAW handling
│   ├── models/      # Data models (CorePhoto, ImageFile, etc.)
│   └── validation/  # Image validation
└── tests/           # Test suite
```

## 📊 PhotoCreateSchema Response

HTTP API returns PhotoCreateSchema JSON with complete image data:

```json
{
  "hothash": "abc123...",
  "hotpreview_base64": "/9j/4AAQSkZJRg...",
  "hotpreview_width": 150,
  "hotpreview_height": 150,
  "coldpreview_base64": null,
  "primary_filename": "IMG_1234.jpg",
  "width": 6000,
  "height": 4000,
  "taken_at": "2025-01-15T14:30:00Z",
  "camera_make": "Nikon",
  "camera_model": "D850",
  "gps_latitude": 59.9139,
  "gps_longitude": 10.7522,
  "has_gps": true,
  "iso": 400,
  "aperture": 2.8,
  "shutter_speed": "1/250",
  "focal_length": 85.0,
  "lens_model": "NIKKOR 85mm f/1.8G"
}
```

## 🐳 Docker Deployment

```bash
# Build image
docker build -f service/Dockerfile -t imalink-core-api .

# Run container
docker run -p 8765:8765 -v /path/to/photos:/photos imalink-core-api
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
