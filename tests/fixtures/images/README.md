# Test Fixture Images

Real JPEG images with authentic EXIF metadata from various cameras.

## Source

Downloaded from https://github.com/ianare/exif-samples  
Licensed under MIT - free to use for testing.

## Real Images (with authentic EXIF)

### Basic Metadata
- `Canon_40D.jpg` - Canon EOS 40D, timestamp, 100x68px (7.8KB)
- `Nikon_D70.jpg` - Nikon D70, timestamp, 100x66px (14KB)
- `fuji_full_exif.jpg` - Fujifilm FinePix E500, timestamp, 80x60px (2.2KB)

### With GPS Data
- `gps_sample.jpg` - Nikon Coolpix P6000 with GPS (Tuscany, Italy)
  - GPS: 43.467448°N, 11.885127°E
  - Focal length: 24mm
  - 640x480px (158KB)

### With EXIF Orientation
- `orientation_6.jpg` - EXIF Orientation=6 (Rotate 90° CW), 450x600px (135KB)

### Synthetic Images (limited EXIF)
- `jpeg_*.jpg`, `png_basic.png` - Generated for format/dimension testing
- Created by `generate_test_fixtures.py`

## Total Size
~320KB (real images) + ~55KB (synthetic) = ~375KB total
