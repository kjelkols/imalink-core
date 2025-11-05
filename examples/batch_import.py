"""
Example of batch processing multiple images
"""

from pathlib import Path
from imalink_core import batch_process


def main():
    # Find all images in a directory
    photo_dir = Path("./photos")
    
    if not photo_dir.exists():
        print(f"Error: Directory {photo_dir} not found")
        print("Please create a 'photos' directory with some images")
        return
    
    # Find all JPEG files
    images = list(photo_dir.glob("*.jpg")) + list(photo_dir.glob("*.jpeg"))
    
    if not images:
        print(f"No JPEG images found in {photo_dir}")
        return
    
    print(f"Found {len(images)} images")
    print("=" * 60)
    
    # Progress callback
    def on_progress(current, total, result):
        if result.success:
            photo = result.photo
            print(f"[{current}/{total}] ✓ {photo.primary_filename}")
            if photo.taken_at:
                print(f"           Taken: {photo.taken_at}")
            if photo.camera_info:
                print(f"           Camera: {photo.camera_info}")
        else:
            print(f"[{current}/{total}] ✗ {result.error}")
    
    # Process all images
    results = batch_process(images, progress_callback=on_progress)
    
    # Summary
    print("=" * 60)
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    print(f"\nResults:")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed:     {len(failed)}")
    
    # Show unique cameras
    cameras = set()
    for r in successful:
        if r.photo.camera_info:
            cameras.add(r.photo.camera_info)
    
    if cameras:
        print(f"\nCameras found:")
        for camera in sorted(cameras):
            print(f"  - {camera}")
    
    # Show GPS statistics
    with_gps = [r for r in successful if r.photo.has_gps]
    if with_gps:
        print(f"\nPhotos with GPS: {len(with_gps)}/{len(successful)}")


if __name__ == "__main__":
    main()
