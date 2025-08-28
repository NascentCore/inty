import os
import tempfile
from PIL import Image
import requests


def test_upload_avatar():
    base_url = "http://localhost:8000"

    guest_data = {
        "device_id": "test-device-123",
        "system_language": "en",
        "age_group": "adult",
    }

    # Create guest user
    response = requests.post("http://localhost:8000/api/v1/auth/guest", json=guest_data)
    print(f"Guest registration response status: {response.status_code}")
    print(f"Guest registration response content: {response.text}")

    # Extract token from guest response
    response_data = response.json()

    token = response_data.get("data", {}).get("token")

    headers = {"Authorization": f"Bearer {token}"}

    test_image_path = "tests/app/api/v1/endpoints/test.png"

    with open(test_image_path, "rb") as f:
        files = {"file": ("test.png", f, "image/png")}

        response = requests.post(
            f"{base_url}/api/v1/images",
            headers=headers,
            files=files,
        )

    assert (
        response.status_code == 200
    ), f"Upload failed: {response.status_code} - {response.text}"

    # Download the image from the response
    response_data = response.json()
    url = response_data.get("data").get("url")
    response = requests.get(url)
    temp_dir = tempfile.mkdtemp()
    temp_file_name = url.split("/")[-1]
    assert temp_file_name.endswith(".jpeg")
    temp_file = os.path.join(temp_dir, temp_file_name)
    with open(temp_file, "wb") as f:
        f.write(response.content)
    # validate temp file is a valid jpeg
    with Image.open(temp_file) as img:
        assert img.format == "JPEG"
