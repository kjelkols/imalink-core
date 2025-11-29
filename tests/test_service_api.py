"""
Integration tests for the FastAPI service endpoint.

Tests the complete HTTP API flow: multipart/form-data file upload -> processing -> PhotoEgg JSON response.
"""

import sys
from pathlib import Path

# Add service directory to path
service_dir = Path(__file__).parent.parent / "service"
sys.path.insert(0, str(service_dir))

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "images"


class TestProcessEndpoint:
    """Test POST /v1/process endpoint with file uploads."""

    def test_upload_jpeg_basic(self):
        """Test basic JPEG upload without coldpreview."""
        image_path = FIXTURES_DIR / "fuji_full_exif.jpg"
        
        with open(image_path, "rb") as f:
            response = client.post(
                "/v1/process",
                files={"file": ("test.jpg", f, "image/jpeg")}
            )
        
        assert response.status_code == 200
        photo_egg = response.json()
        
        # Verify PhotoEgg structure (PhotoCreateSchema)
        assert "hothash" in photo_egg
        assert "hotpreview_base64" in photo_egg
        assert "coldpreview_base64" in photo_egg
        assert "image_file_list" in photo_egg
        assert "width" in photo_egg
        assert "height" in photo_egg
        assert "exif_dict" in photo_egg
        
        # Verify hotpreview is present
        assert photo_egg["hotpreview_base64"] is not None
        assert len(photo_egg["hotpreview_base64"]) > 0
        
        # Verify coldpreview is NOT present (default behavior)
        assert photo_egg["coldpreview_base64"] is None
        
        # Verify image_file_list
        assert len(photo_egg["image_file_list"]) == 1
        assert photo_egg["image_file_list"][0]["filename"] == "test.jpg"

    def test_upload_jpeg_with_coldpreview(self):
        """Test JPEG upload WITH coldpreview requested."""
        image_path = FIXTURES_DIR / "fuji_full_exif.jpg"
        
        with open(image_path, "rb") as f:
            response = client.post(
                "/v1/process",
                files={"file": ("photo.jpg", f, "image/jpeg")},
                data={"coldpreview_size": "1024"}
            )
        
        assert response.status_code == 200
        photo_egg = response.json()
        
        # Verify coldpreview IS present
        assert photo_egg["coldpreview_base64"] is not None
        assert len(photo_egg["coldpreview_base64"]) > 0
        
        # Verify filename in image_file_list
        assert photo_egg["image_file_list"][0]["filename"] == "photo.jpg"

    def test_upload_png(self):
        """Test PNG upload."""
        image_path = FIXTURES_DIR / "png_basic.png"
        
        with open(image_path, "rb") as f:
            response = client.post(
                "/v1/process",
                files={"file": ("image.png", f, "image/png")}
            )
        
        assert response.status_code == 200
        photo_egg = response.json()
        
        assert photo_egg["hotpreview_base64"] is not None
        assert photo_egg["image_file_list"][0]["filename"] == "image.png"

    def test_upload_with_exif_data(self):
        """Test that EXIF metadata is extracted correctly."""
        image_path = FIXTURES_DIR / "fuji_full_exif.jpg"
        
        with open(image_path, "rb") as f:
            response = client.post(
                "/v1/process",
                files={"file": ("photo.jpg", f, "image/jpeg")}
            )
        
        assert response.status_code == 200
        photo_egg = response.json()
        
        # Check EXIF fields exist in exif_dict (values depend on test fixture)
        assert "taken_at" in photo_egg
        assert "gps_latitude" in photo_egg
        assert "gps_longitude" in photo_egg
        assert "exif_dict" in photo_egg
        # Camera fields are in exif_dict
        if photo_egg["exif_dict"]:
            assert "camera_make" in photo_egg["exif_dict"] or "camera_model" in photo_egg["exif_dict"]

    def test_upload_landscape_image(self):
        """Test landscape orientation."""
        image_path = FIXTURES_DIR / "jpeg_landscape.jpg"
        
        with open(image_path, "rb") as f:
            response = client.post(
                "/v1/process",
                files={"file": ("landscape.jpg", f, "image/jpeg")}
            )
        
        assert response.status_code == 200
        photo_egg = response.json()
        
        # Hotpreview should be present
        assert photo_egg["hotpreview_base64"] is not None
        
        # Original dimensions should be landscape
        assert photo_egg["width"] > photo_egg["height"]

    def test_upload_portrait_image(self):
        """Test portrait orientation."""
        image_path = FIXTURES_DIR / "jpeg_rotated.jpg"  # This is portrait orientation
        
        with open(image_path, "rb") as f:
            response = client.post(
                "/v1/process",
                files={"file": ("portrait.jpg", f, "image/jpeg")}
            )
        
        assert response.status_code == 200
        photo_egg = response.json()
        
        # Hotpreview should be present
        assert photo_egg["hotpreview_base64"] is not None
        
        # Original dimensions should be portrait
        assert photo_egg["height"] > photo_egg["width"]

    def test_hothash_deterministic(self):
        """Test that same image produces same hothash."""
        image_path = FIXTURES_DIR / "fuji_full_exif.jpg"
        
        # Upload same image twice
        with open(image_path, "rb") as f:
            response1 = client.post(
                "/v1/process",
                files={"file": ("test1.jpg", f, "image/jpeg")}
            )
        
        with open(image_path, "rb") as f:
            response2 = client.post(
                "/v1/process",
                files={"file": ("test2.jpg", f, "image/jpeg")}
            )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        photo_egg1 = response1.json()
        photo_egg2 = response2.json()
        
        # Same image = same hothash (despite different filenames)
        assert photo_egg1["hothash"] == photo_egg2["hothash"]
        
        # But filenames should be different
        assert photo_egg1["image_file_list"][0]["filename"] == "test1.jpg"
        assert photo_egg2["image_file_list"][0]["filename"] == "test2.jpg"


class TestErrorHandling:
    """Test error cases and validation."""

    def test_missing_file(self):
        """Test request without file upload."""
        response = client.post("/v1/process")
        
        assert response.status_code == 422  # Unprocessable Entity

    def test_invalid_coldpreview_size(self):
        """Test coldpreview_size below minimum (150)."""
        image_path = FIXTURES_DIR / "fuji_full_exif.jpg"
        
        with open(image_path, "rb") as f:
            response = client.post(
                "/v1/process",
                files={"file": ("test.jpg", f, "image/jpeg")},
                data={"coldpreview_size": "100"}  # Below 150
            )
        
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "150" in detail  # Error message mentions minimum size

    def test_invalid_image_format(self):
        """Test uploading a non-image file."""
        # Create a fake text file as upload
        fake_file = b"This is not an image"
        
        response = client.post(
            "/v1/process",
            files={"file": ("test.txt", fake_file, "text/plain")}
        )
        
        assert response.status_code == 400
        # Just check that we get an error response
        assert "detail" in response.json()

    def test_corrupted_image(self):
        """Test uploading corrupted image data."""
        # Create fake JPEG header but corrupted data
        fake_jpeg = b"\xff\xd8\xff\xe0" + b"corrupted data"
        
        response = client.post(
            "/v1/process",
            files={"file": ("corrupted.jpg", fake_jpeg, "image/jpeg")}
        )
        
        assert response.status_code == 400

    def test_tiny_image_rejected(self):
        """Test that images smaller than 4x4 pixels are rejected."""
        from PIL import Image
        from io import BytesIO
        
        # Create a 3x3 pixel image
        tiny_img = Image.new('RGB', (3, 3), color='red')
        buffer = BytesIO()
        tiny_img.save(buffer, format='JPEG')
        tiny_bytes = buffer.getvalue()
        
        response = client.post(
            "/v1/process",
            files={"file": ("tiny.jpg", tiny_bytes, "image/jpeg")}
        )
        
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "too small" in detail.lower() or "invalid" in detail.lower()


class TestBase64Encoding:
    """Test that previews are properly Base64 encoded."""

    def test_hotpreview_is_base64_string(self):
        """Verify hotpreview_base64 is a valid Base64 string, not bytes."""
        import base64
        
        image_path = FIXTURES_DIR / "fuji_full_exif.jpg"
        
        with open(image_path, "rb") as f:
            response = client.post(
                "/v1/process",
                files={"file": ("test.jpg", f, "image/jpeg")}
            )
        
        assert response.status_code == 200
        photo_egg = response.json()
        
        # hotpreview_base64 should be a string
        assert isinstance(photo_egg["hotpreview_base64"], str)
        
        # Should be valid Base64 (can be decoded)
        try:
            decoded = base64.b64decode(photo_egg["hotpreview_base64"])
            assert len(decoded) > 0
            # Should start with JPEG header
            assert decoded[:2] == b"\xff\xd8"
        except Exception as e:
            pytest.fail(f"Invalid Base64 encoding: {e}")

    def test_coldpreview_is_base64_string(self):
        """Verify coldpreview_base64 is a valid Base64 string when present."""
        import base64
        
        image_path = FIXTURES_DIR / "fuji_full_exif.jpg"
        
        with open(image_path, "rb") as f:
            response = client.post(
                "/v1/process",
                files={"file": ("test.jpg", f, "image/jpeg")},
                data={"coldpreview_size": "1024"}
            )
        
        assert response.status_code == 200
        photo_egg = response.json()
        
        # coldpreview_base64 should be a string
        assert isinstance(photo_egg["coldpreview_base64"], str)
        
        # Should be valid Base64
        try:
            decoded = base64.b64decode(photo_egg["coldpreview_base64"])
            assert len(decoded) > 0
            # Should start with JPEG header
            assert decoded[:2] == b"\xff\xd8"
        except Exception as e:
            pytest.fail(f"Invalid Base64 encoding: {e}")


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_endpoint(self):
        """Test GET /health endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
