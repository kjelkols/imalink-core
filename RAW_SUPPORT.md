# RAW File Support

imalink-core now supports RAW camera files (CR2, NEF, ARW, DNG, etc.) through the `rawpy` library.

## Installation

RAW support is optional. Install it with:

```bash
uv pip install rawpy
```

Or install imalink-core with RAW support:

```bash
uv pip install "imalink-core[raw]"
```

## Supported RAW Formats

imalink-core supports **all major RAW formats** through LibRaw (900+ camera models):

**Nikon:** NEF, NRW  
**Canon:** CR2, CR3 (R5/R6/R7), CRW (older)  
**Sony:** ARW, SRF, SR2  
**Fujifilm:** RAF  
**Olympus/OM System:** ORF  
**Panasonic:** RW2, RAW  
**Pentax:** PEF, PTX  
**Sigma:** X3F (Foveon sensor)  
**Leica:** RWL, DNG  
**Minolta:** MRW  
**Samsung:** SRW (NX-series)  
**Hasselblad:** 3FR  
**Kodak:** DCR, KDC  
**Mamiya:** MEF  
**Phase One:** IIQ (limited support)  
**Adobe/Universal:** DNG

## API Usage

**The API interface is identical for RAW and JPEG/PNG files** - no changes needed!

### Upload RAW File

```bash
# Same endpoint, same parameters
curl -X POST http://localhost:8765/v1/process \
  -F "file=@photo.NEF" \
  -F "coldpreview_size=2560"
```

### Response

RAW files return the same PhotoCreateSchema JSON as JPEG/PNG:

```json
{
  "hothash": "abc123...",
  "hotpreview_base64": "/9j/4AAQSkZJRg...",
  "coldpreview_base64": "/9j/4AAQSkZJRg...",
  "width": 6000,
  "height": 4000,
  "camera_make": "Nikon",
  "camera_model": "D850",
  "iso": 800,
  "aperture": 2.8,
  "taken_at": "2024-12-04T15:30:00Z"
}
```

## How It Works

1. **Detection**: Core detects RAW files by extension (NEF, CR2, etc.)
2. **Conversion**: `rawpy` converts RAW → RGB array
3. **Processing**: Converted image processed like any JPEG:
   - EXIF extraction
   - Preview generation (hot + cold)
   - Hothash calculation

**Zero API changes** - RAW support is completely transparent to clients.

## Architecture

```
RAW File Upload
    ↓
RawProcessor.is_raw_file(filename)
    ↓
RawProcessor.convert_raw_to_image(bytes)
    ↓
PIL Image (RGB)
    ↓
Normal Processing Pipeline
    ↓
PhotoCreateSchema JSON
```

## Error Handling

If `rawpy` is not installed:

```json
{
  "error": "RAW file support not installed. Install with: uv pip install rawpy"
}
```

If RAW file is corrupt:

```json
{
  "error": "Failed to process RAW file: LibRaw error: invalid file format"
}
```

## Testing

Test RAW support:

```bash
# Run RAW tests
uv run pytest tests/test_raw_processing.py -v

# Test with your own RAW file
curl -X POST http://localhost:8765/v1/process \
  -F "file=@/path/to/photo.NEF" \
  -F "coldpreview_size=2560"
```

## Performance

RAW processing is slower than JPEG (2-5x):

- **JPEG**: ~50-100ms
- **RAW**: ~200-500ms (depending on file size)

This is expected - RAW files contain unprocessed sensor data that must be:
1. Demosaiced (Bayer pattern → RGB)
2. White balanced
3. Color corrected
4. Tone mapped

## Camera Compatibility

RAW support uses LibRaw (via rawpy), which supports **900+ camera models** including:

**DSLR/Mirrorless:**
- Nikon D850, D7500, Z6, Z7, Z8, Z9
- Canon 5D Mark IV, EOS R, EOS R5, EOS R6, EOS R7
- Sony A7R III, A7R IV, A7R V, A9, A1
- Fujifilm X-T3, X-T4, X-T5, X-H2, X-Pro3
- Olympus OM-D E-M1, E-M5 | OM System OM-1
- Panasonic Lumix GH5, GH6, S5, S1
- Pentax K-1, K-3
- Sigma fp, fp L

**Medium Format:**
- Hasselblad X1D, X2D, 907X
- Fujifilm GFX 50S, GFX 100
- Phase One IQ3, IQ4 (limited)

**Compact/Premium:**
- Leica Q2, Q3, M10, M11
- Ricoh GR III, GR IIIx
- Sigma dp Quattro series

**Legacy (2000-2010):**
- Nikon D70, D200, D300
- Canon 5D, 7D, 40D, 50D
- Minolta DiMAGE A2, Alpha 7D
- Samsung GX-10, GX-20
- Kodak DCS series

If your camera's RAW format works with Adobe Lightroom or Capture One, it will work with imalink-core.

## EXIF Data

EXIF extraction works the same for RAW files:

- BasicMetadata: Camera make/model, dimensions, GPS, timestamp
- CameraSettings: ISO, aperture, shutter, focal length

RAW files often have **richer EXIF data** than JPEGs since they come directly from camera.

## Development

Add RAW test fixtures:

```bash
# Copy your camera's RAW file
cp ~/photos/test.NEF tests/fixtures/images/

# Run tests
uv run pytest tests/test_raw_processing.py::TestRawProcessor::test_convert_real_raw -v -s
```

## Production Deployment

Install rawpy on server:

```bash
ssh kjell@core.trollfjell.com
cd /home/kjell/imalink-core
uv pip install rawpy
sudo systemctl restart imalink-core
```

Check it's working:

```bash
curl -X POST https://core.trollfjell.com/v1/process \
  -F "file=@photo.NEF" \
  -F "coldpreview_size=2560"
```

## Limitations

1. **No lens correction**: RAW files processed without lens distortion correction
2. **Default color profile**: Uses sRGB color space (not Adobe RGB or ProPhoto)
3. **No custom processing**: Uses rawpy defaults (can't customize demosaic algorithm, etc.)

These limitations match the project's goal: **extract metadata and generate previews**, not replace Lightroom/Capture One.

## Future Enhancements

Potential improvements:
- Custom white balance adjustment
- Exposure compensation
- Lens correction profiles
- Multiple RAW processing profiles (quality vs speed)

Not planned (out of scope):
- Full RAW editing capabilities
- Custom color profiles
- Advanced noise reduction

## Questions?

See `tests/test_raw_processing.py` for examples and `src/imalink_core/image/raw_processor.py` for implementation.
