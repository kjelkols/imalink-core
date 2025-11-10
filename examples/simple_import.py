"""
Simple example of using imalink-core to process an image
"""

from pathlib import Path
from imalink_core import process_image


def main():
    # Replace with actual image path
    image_path = Path("example.jpg")
    
    if not image_path.exists():
        print(f"Error: {image_path} not found")
        print("Please provide a valid image path")
        return
    
    print(f"Processing {image_path}...")
    print("-" * 60)
    
    # Process the image (default: minimal PhotoEgg with hotpreview only)
    result = process_image(image_path)
    
    # Or with coldpreview (specify desired size):
    # result = process_image(image_path, coldpreview_size=2560)
    
    if result.success:
        print("✓ Success!\n")
        
        # Photo info
        photo = result.photo
        print(f"Hothash:        {photo.hothash}")
        print(f"Filename:       {photo.primary_filename}")
        print(f"Dimensions:     {photo.width}x{photo.height}px")
        
        # Metadata
        if result.metadata.taken_at:
            print(f"Taken at:       {result.metadata.taken_at}")
        
        if photo.camera_info:
            print(f"Camera:         {photo.camera_info}")
        
        # GPS
        if photo.has_gps:
            print(f"GPS:            {photo.gps_latitude}, {photo.gps_longitude}")
        
        # Camera settings
        if result.camera_settings:
            settings = result.camera_settings
            if settings.iso:
                print(f"ISO:            {settings.iso}")
            if settings.aperture:
                print(f"Aperture:       f/{settings.aperture}")
            if settings.shutter_speed:
                print(f"Shutter:        {settings.shutter_speed}")
            if settings.focal_length:
                print(f"Focal length:   {settings.focal_length}mm")
        
        print(f"\nHotpreview:     {len(result.hotpreview_base64)} bytes (base64)")
        print(f"Coldpreview:    {len(result.coldpreview_bytes)} bytes")
        
    else:
        print(f"✗ Failed: {result.error}")


if __name__ == "__main__":
    main()
