# ImaLink Core - API Contracts

This document defines the HTTP API contracts for imalink-core service.

## Service Information

- **Base URL**: `http://localhost:8765` (development)
- **Protocol**: HTTP/1.1
- **Content-Type**: 
  - Request: `multipart/form-data` (file upload)
  - Response: `application/json`
- **Port**: 8765 (default)

## API Endpoints

### 1. Process Image - `POST /v1/process`

**Purpose**: Upload image file, receive PhotoEgg JSON with previews and metadata.

**Request**:
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Parameters**:

| Parameter | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| `file` | File | Yes | Image file (JPEG, PNG, etc.) | Must be valid image format |
| `coldpreview_size` | int | No | Max dimension for coldpreview in pixels | If provided: >= 150 |

**Example Request (curl)**:
```bash
# Basic request (hotpreview only)
curl -X POST http://localhost:8765/v1/process \
  -F "file=@photo.jpg"

# With coldpreview
curl -X POST http://localhost:8765/v1/process \
  -F "file=@photo.jpg" \
  -F "coldpreview_size=2560"
```

**Example Request (JavaScript)**:
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('coldpreview_size', '2560');  // optional

const response = await fetch('http://localhost:8765/v1/process', {
  method: 'POST',
  body: formData
});

const photoEgg = await response.json();
```

**Success Response** (`200 OK`):

```json
{
  "hothash": "abc123def456...",
  "hotpreview_base64": "/9j/4AAQSkZJRg...",
  "hotpreview_width": 150,
  "hotpreview_height": 112,
  "coldpreview_base64": "/9j/4AAQSkZJRg..." | null,
  "coldpreview_width": 2560 | null,
  "coldpreview_height": 1920 | null,
  "primary_filename": "IMG_1234.jpg",
  "width": 4000,
  "height": 3000,
  "taken_at": "2024-07-15T14:30:00" | null,
  "camera_make": "Nikon" | null,
  "camera_model": "D850" | null,
  "gps_latitude": 59.9139 | null,
  "gps_longitude": 10.7522 | null,
  "has_gps": true,
  "iso": 400 | null,
  "aperture": 2.8 | null,
  "shutter_speed": "1/500" | null,
  "focal_length": 85.0 | null,
  "lens_model": "AF-S NIKKOR 85mm f/1.4G" | null,
  "lens_make": "Nikon" | null
}
```

**Error Responses**:

| Status Code | Description | Example |
|-------------|-------------|---------|
| `400 Bad Request` | Invalid image file | `{"detail": "Invalid image file: cannot identify image file"}` |
| `400 Bad Request` | Image too small | `{"detail": "Invalid image: Image too small: 3x3px. Minimum size is 4x4px"}` |
| `400 Bad Request` | Invalid coldpreview_size | `{"detail": "coldpreview_size must be >= 150 (hotpreview size), got 100"}` |
| `422 Unprocessable Entity` | Missing file parameter | `{"detail": [{"loc": ["body", "file"], "msg": "field required"}]}` |

---

### 2. Health Check - `GET /health`

**Purpose**: Check service availability.

**Request**:
- **Method**: `GET`
- **Parameters**: None

**Example Request**:
```bash
curl http://localhost:8765/health
```

**Success Response** (`200 OK`):
```json
{
  "status": "healthy"
}
```

---

### 3. Root - `GET /`

**Purpose**: API information.

**Request**:
- **Method**: `GET`
- **Parameters**: None

**Success Response** (`200 OK`):
```json
{
  "service": "ImaLink Core API",
  "version": "1.0.0",
  "status": "healthy"
}
```

---

## PhotoEgg JSON Schema

The PhotoEgg is the canonical output format from imalink-core.

### Field Definitions

#### Required Fields (Always Present)

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `hothash` | string | SHA256 hash of hotpreview JPEG bytes | Unique identifier (64 hex chars) |
| `hotpreview_base64` | string | Base64-encoded JPEG thumbnail | Always present, ~5-15KB |
| `hotpreview_width` | int | Width in pixels | Max 150px (aspect ratio preserved) |
| `hotpreview_height` | int | Height in pixels | Max 150px (aspect ratio preserved) |
| `primary_filename` | string | Original filename from upload | E.g., "IMG_1234.jpg" |
| `width` | int | Original image width in pixels | From image dimensions |
| `height` | int | Original image height in pixels | From image dimensions |
| `has_gps` | bool | Whether GPS coordinates are available | `true` if lat/lon present |

#### Optional Fields (May Be Null)

| Field | Type | Description | Reliability |
|-------|------|-------------|-------------|
| `coldpreview_base64` | string \| null | Base64-encoded larger preview | Only if requested, ~100-200KB |
| `coldpreview_width` | int \| null | Coldpreview width | Only if coldpreview generated |
| `coldpreview_height` | int \| null | Coldpreview height | Only if coldpreview generated |
| `taken_at` | string \| null | ISO 8601 timestamp | 98% reliable (EXIF DateTimeOriginal) |
| `camera_make` | string \| null | Camera manufacturer | 98% reliable (e.g., "Nikon", "Canon") |
| `camera_model` | string \| null | Camera model | 98% reliable (e.g., "D850") |
| `gps_latitude` | float \| null | Latitude in decimal degrees | 95% reliable (if GPS present) |
| `gps_longitude` | float \| null | Longitude in decimal degrees | 95% reliable (if GPS present) |
| `iso` | int \| null | ISO sensitivity | 70-90% reliable (e.g., 400, 1600) |
| `aperture` | float \| null | F-number | 70-90% reliable (e.g., 2.8, 5.6) |
| `shutter_speed` | string \| null | Shutter speed | 70-90% reliable (e.g., "1/500") |
| `focal_length` | float \| null | Focal length in mm | 70-90% reliable (e.g., 85.0) |
| `lens_model` | string \| null | Lens model name | 60-80% reliable |
| `lens_make` | string \| null | Lens manufacturer | 60-80% reliable |

### Field Value Constraints

- **hothash**: Exactly 64 hexadecimal characters (SHA256)
- **hotpreview_base64**: Valid Base64 string, decodes to JPEG with header `\xFF\xD8`
- **hotpreview_width/height**: Between 4 and 150 pixels (inclusive)
- **coldpreview_base64**: Valid Base64 string (if present), decodes to JPEG
- **coldpreview_width/height**: Between 150 and original size (if requested)
- **width/height**: Minimum 4 pixels (images < 4x4 rejected)
- **taken_at**: ISO 8601 format (e.g., `"2024-07-15T14:30:00"`)
- **gps_latitude**: -90.0 to +90.0
- **gps_longitude**: -180.0 to +180.0
- **iso**: Positive integer (typically 100-102400)
- **aperture**: Positive float (typically 1.0-32.0)
- **focal_length**: Positive float (typically 10.0-600.0)

---

## Processing Behavior

### Image Size Handling

1. **Original size preserved**: `width` and `height` reflect actual image dimensions
2. **Hotpreview scaling**: 
   - Max 150x150px
   - Aspect ratio preserved
   - PIL `thumbnail()` NEVER scales up
   - A 59x59px image becomes 59x59px hotpreview (not 150x150)
3. **Minimum size validation**:
   - Images < 4x4 pixels rejected as corrupt
   - Returns `400 Bad Request` with error message

### Preview Generation

1. **Hotpreview** (always generated):
   - Target: 150x150px
   - Actual: Max 150x150px (aspect ratio preserved)
   - Quality: 85% JPEG
   - EXIF stripped
   - Size: ~5-15KB Base64

2. **Coldpreview** (optional):
   - Generated only if `coldpreview_size` parameter provided
   - Target: `coldpreview_size` x `coldpreview_size` (e.g., 2560x2560)
   - Actual: Max specified size (aspect ratio preserved)
   - Quality: 90% JPEG
   - EXIF stripped
   - Size: ~100-200KB Base64 (depends on requested size)

### EXIF Orientation

All images are automatically rotated based on EXIF Orientation tag:
- Uses `PIL.ImageOps.exif_transpose()`
- Applied before preview generation
- Ensures previews have correct orientation
- Original dimensions (`width`/`height`) reflect rotated state

### Metadata Reliability

**BasicMetadata (98%+ reliable)**:
- Dimensions (width/height)
- Timestamp (taken_at)
- Camera make/model
- GPS coordinates (if present)

**CameraSettings (70-90% reliable)**:
- ISO, aperture, shutter speed
- Focal length
- Lens information

Consumer photos often lack camera settings. Always check for `null`.

---

## Base64 Encoding

**CRITICAL**: ALL image data in PhotoEgg uses Base64 encoding.

### Why Base64?
- JSON cannot contain binary data (raw bytes)
- Image files are binary (JPEG/PNG bytes)
- Base64 converts binary → text for JSON transmission
- Industry standard for embedding binary in JSON/APIs

### Usage in PhotoEgg

```javascript
// Receive PhotoEgg
const response = await fetch('/v1/process', {
  method: 'POST',
  body: formData
});
const photoEgg = await response.json();

// hotpreview_base64 is a STRING (not bytes)
console.log(typeof photoEgg.hotpreview_base64);  // "string"

// Decode Base64 to display image
const img = document.createElement('img');
img.src = `data:image/jpeg;base64,${photoEgg.hotpreview_base64}`;
document.body.appendChild(img);

// Or decode to bytes for storage
const bytes = atob(photoEgg.hotpreview_base64);  // Browser
const buffer = Buffer.from(photoEgg.hotpreview_base64, 'base64');  // Node.js
```

### Validation

Valid Base64 string:
- Contains only: `A-Z`, `a-z`, `0-9`, `+`, `/`, `=` (padding)
- Decodes to JPEG binary (starts with `\xFF\xD8`)

---

## Error Handling

### Client Errors (4xx)

**400 Bad Request** - Client submitted invalid data:
```json
{
  "detail": "Invalid image file: cannot identify image file <_io.BytesIO object>"
}
```

**422 Unprocessable Entity** - Validation error (FastAPI automatic):
```json
{
  "detail": [
    {
      "loc": ["body", "file"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Server Errors (5xx)

**500 Internal Server Error** - Unexpected server error:
```json
{
  "detail": "Processing failed: [error details]"
}
```

---

## Integration Examples

### Python (requests)

```python
import requests

# Upload image
with open('photo.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8765/v1/process',
        files={'file': ('photo.jpg', f, 'image/jpeg')},
        data={'coldpreview_size': '2560'}
    )

photo_egg = response.json()
print(f"Hothash: {photo_egg['hothash']}")
print(f"Taken at: {photo_egg['taken_at']}")
```

### JavaScript (Browser)

```javascript
// File input
const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];

// Upload
const formData = new FormData();
formData.append('file', file);
formData.append('coldpreview_size', '2560');

const response = await fetch('http://localhost:8765/v1/process', {
  method: 'POST',
  body: formData
});

const photoEgg = await response.json();

// Display hotpreview
const img = document.createElement('img');
img.src = `data:image/jpeg;base64,${photoEgg.hotpreview_base64}`;
document.body.appendChild(img);

// Send to backend
await fetch('https://backend.com/api/photos', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(photoEgg)
});
```

### Node.js (axios)

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const formData = new FormData();
formData.append('file', fs.createReadStream('photo.jpg'));
formData.append('coldpreview_size', '2560');

const response = await axios.post('http://localhost:8765/v1/process', formData, {
  headers: formData.getHeaders()
});

const photoEgg = response.data;
console.log('Hothash:', photoEgg.hothash);
```

---

## Versioning

- **Current Version**: `v1`
- **Endpoint Prefix**: `/v1/`
- **Breaking Changes**: Will increment version (e.g., `/v2/`)
- **Non-Breaking Changes**: Added fields, new optional parameters

---

## Performance Characteristics

### Processing Time (Typical)

- **Hotpreview only**: 50-150ms
- **With coldpreview (2560px)**: 150-300ms
- Varies with image size and server load

### Response Size

- **Hotpreview only**: 2-5KB JSON (~15KB with Base64)
- **With coldpreview**: 100-250KB JSON (depending on coldpreview_size)

### Limits

- **Max file size**: Limited by server configuration (default: 100MB)
- **Min image size**: 4x4 pixels
- **Supported formats**: JPEG, PNG, GIF, BMP, TIFF, WebP (anything PIL supports)

---

## Testing

### Integration Tests

Run integration tests against the service:

```bash
# Start service
uv run python -m service.main

# Run integration tests
pytest tests/test_service_api.py -v
```

### Manual Testing

```bash
# Health check
curl http://localhost:8765/health

# Process image
curl -X POST http://localhost:8765/v1/process \
  -F "file=@test.jpg" \
  -F "coldpreview_size=1024"

# Invalid image (should return 400)
echo "not an image" > fake.jpg
curl -X POST http://localhost:8765/v1/process \
  -F "file=@fake.jpg"
```

---

## Change Log

### v1.0.0 (Current)
- Initial release
- POST /v1/process endpoint
- PhotoEgg JSON format
- Multipart/form-data file upload
- Image size validation (MIN_IMAGE_SIZE = 4)
- Optional coldpreview generation
- Base64-encoded previews
- EXIF metadata extraction
