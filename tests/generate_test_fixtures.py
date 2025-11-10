#!/usr/bin/env python3
"""
Generate minimal test images for imalink-core tests.

Creates small synthetic images with specific EXIF metadata for testing.
Run once to populate tests/fixtures/images/
"""

from PIL import Image, ImageDraw
from datetime import datetime
from pathlib import Path
import struct


def create_basic_image(width: int, height: int, color: tuple, text: str = "") -> Image.Image:
    """Create a simple colored image with optional text"""
    img = Image.new('RGB', (width, height), color)
    
    if text:
        draw = ImageDraw.Draw(img)
        # Draw text in center
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((width - text_width) // 2, (height - text_height) // 2)
        draw.text(position, text, fill='white')
    
    return img


def add_minimal_exif(img: Image.Image, camera_make: str = "Nikon", camera_model: str = "D850") -> Image.Image:
    """Add minimal EXIF data that PIL can write"""
    from PIL import Image
    from PIL.ExifTags import TAGS
    
    # PIL's EXIF handling is simpler - we'll skip complex EXIF for now
    # and just ensure basic fields work
    return img


def generate_fixtures():
    """Generate all test fixture images"""
    
    fixture_dir = Path(__file__).parent / "fixtures" / "images"
    fixture_dir.mkdir(exist_ok=True, parents=True)
    
    print(f"Generating test fixtures in {fixture_dir}")
    
    # 1. Basic JPEG with full EXIF
    print("  - jpeg_basic.jpg (800x600, full EXIF)")
    img = create_basic_image(800, 600, (70, 130, 180), "Basic JPEG")
    exif_bytes = create_exif_data()
    img.save(
        fixture_dir / "jpeg_basic.jpg",
        quality=85,
        exif=exif_bytes
    )
    
    # 2. JPEG without EXIF
    print("  - jpeg_no_exif.jpg (800x600, no EXIF)")
    img = create_basic_image(800, 600, (180, 130, 70), "No EXIF")
    img.save(fixture_dir / "jpeg_no_exif.jpg", quality=85)
    
    # 3. JPEG with GPS data (Oslo coordinates)
    print("  - jpeg_gps.jpg (800x600, with GPS)")
    img = create_basic_image(800, 600, (100, 180, 100), "GPS Data")
    exif_bytes = create_exif_data(
        gps=(59.9139, 10.7522)  # Oslo, Norway
    )
    img.save(
        fixture_dir / "jpeg_gps.jpg",
        quality=85,
        exif=exif_bytes
    )
    
    # 4. JPEG with rotation (Orientation=6, rotate 90 CW)
    print("  - jpeg_rotated.jpg (600x800, EXIF rotation)")
    img = create_basic_image(600, 800, (180, 100, 180), "Rotated")
    exif_bytes = create_exif_data(orientation=6)  # Rotate 90 CW
    img.save(
        fixture_dir / "jpeg_rotated.jpg",
        quality=85,
        exif=exif_bytes
    )
    
    # 5. PNG (no EXIF support)
    print("  - png_basic.png (800x600)")
    img = create_basic_image(800, 600, (150, 150, 150), "PNG Format")
    img.save(fixture_dir / "png_basic.png")
    
    # 6. Tiny image (edge case)
    print("  - tiny_100x100.jpg (100x100)")
    img = create_basic_image(100, 100, (200, 100, 50), "Tiny")
    exif_bytes = create_exif_data(
        camera_make="Canon",
        camera_model="EOS R5",
        iso=1600,
        aperture=1.8,
        focal_length=50
    )
    img.save(
        fixture_dir / "tiny_100x100.jpg",
        quality=75,
        exif=exif_bytes
    )
    
    # 7. Image with different camera settings
    print("  - jpeg_landscape.jpg (1200x800)")
    img = create_basic_image(1200, 800, (50, 100, 150), "Landscape")
    exif_bytes = create_exif_data(
        taken_at="2023:12:25 10:15:30",
        camera_make="Sony",
        camera_model="A7R IV",
        iso=100,
        aperture=11.0,
        focal_length=24,
        gps=(67.8558, 20.2253)  # Abisko, Sweden
    )
    img.save(
        fixture_dir / "jpeg_landscape.jpg",
        quality=90,
        exif=exif_bytes
    )
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in fixture_dir.glob("*"))
    print(f"\nGenerated {len(list(fixture_dir.glob('*')))} test images")
    print(f"Total size: {total_size / 1024:.1f} KB")
    
    # Create README
    readme = fixture_dir / "README.md"
    readme.write_text("""# Test Fixture Images

These images are synthetically generated for testing imalink-core.

## Files

- `jpeg_basic.jpg` - Standard JPEG with full EXIF (Nikon D850)
- `jpeg_no_exif.jpg` - JPEG without any EXIF metadata
- `jpeg_gps.jpg` - JPEG with GPS coordinates (Oslo, Norway)
- `jpeg_rotated.jpg` - JPEG with EXIF Orientation=6 (rotate 90° CW)
- `png_basic.png` - PNG file (no EXIF support)
- `tiny_100x100.jpg` - Small 100x100 image (edge case)
- `jpeg_landscape.jpg` - Landscape photo (Sony A7R IV, GPS: Abisko)

## Regenerating

Run: `python tests/generate_test_fixtures.py`
""")
    
    print(f"\nDone! Test images created in {fixture_dir}")
    print("Run: pytest tests/ to use them")


if __name__ == "__main__":
    generate_fixtures()
