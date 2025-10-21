"""
Integration test to verify that text-to-image request data is saved in resource metadata.

This test verifies that when generating images through the text-to-image API,
the original request parameters are properly stored in the resources table.
"""

import json
import uuid
from typing import Dict, Any

import httpx
import pytest


class TestClient:
    """Simple test client for the Inty API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
        self.token = None
        self.device_id = None

    def create_user(self) -> str:
        """Create a guest user and return the token."""
        if not self.device_id:
            self.device_id = f"test-device-{uuid.uuid4().hex[:8]}"
        
        url = f"{self.base_url}/api/v1/auth/guest"
        payload = {"device_id": self.device_id}
        
        response = self.client.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        self.token = data["data"]["token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})
        
        return self.token

    def text_to_image(self, prompt: str, negative_prompt: str = None, enhance_prompt: bool = True, count: int = 1) -> Dict[str, Any]:
        """Call the text-to-image endpoint."""
        url = f"{self.base_url}/api/v1/ai/agents/text-to-image"
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "enhance_prompt": enhance_prompt,
            "count": count
        }
        
        response = self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def get_resources(self) -> list[Dict[str, Any]]:
        """Get all resources for the current user."""
        url = f"{self.base_url}/api/v1/resources/"
        
        response = self.client.get(url)
        response.raise_for_status()
        
        data = response.json()
        return data["data"]

    def get_resource_by_url(self, image_url: str) -> Dict[str, Any]:
        """Get a specific resource by its URL."""
        resources = self.get_resources()
        for resource in resources:
            if resource["url"] == image_url:
                return resource
        raise ValueError(f"Resource with URL {image_url} not found")


@pytest.mark.integration
def test_text_to_image_request_metadata():
    """
    Test that text-to-image request data is properly stored in resource metadata.
    
    This test:
    1. Creates a test user
    2. Calls the text-to-image API with specific parameters
    3. Retrieves the created resources
    4. Verifies that the request data is stored in the resource metadata
    """
    # Initialize test client
    client = TestClient("http://localhost:8000")
    
    # Create user and get token
    token = client.create_user()
    assert token is not None
    assert len(token) > 0
    
    # Define test request parameters
    test_prompt = "A beautiful sunset over mountains"
    test_negative_prompt = "blurry, low quality"
    test_enhance_prompt = True
    test_count = 2
    
    # Call text-to-image API
    response = client.text_to_image(
        prompt=test_prompt,
        negative_prompt=test_negative_prompt,
        enhance_prompt=test_enhance_prompt,
        count=test_count
    )
    
    # Verify API response
    assert response["success"] is True
    assert "data" in response
    assert "image_uris" in response["data"]
    
    image_urls = response["data"]["image_uris"]
    assert len(image_urls) == test_count
    assert all(url.startswith("https://") for url in image_urls)
    
    # Get all resources for the user
    resources = client.get_resources()
    assert len(resources) >= test_count
    
    # Find resources created by our text-to-image request
    text_to_image_resources = []
    for resource in resources:
        if resource["url"] in image_urls:
            text_to_image_resources.append(resource)
    
    # Verify we found the expected number of resources
    assert len(text_to_image_resources) == test_count
    
    # Verify each resource has the correct metadata structure
    for resource in text_to_image_resources:
        # Check basic resource structure
        assert resource["type"] == "IMAGE"
        assert resource["url"] in image_urls
        assert "resource_metadata" in resource
        assert resource["resource_metadata"] is not None
        
        metadata = resource["resource_metadata"]
        
        # Check that request_data is present in metadata
        assert "request_data" in metadata
        assert metadata["request_data"] is not None
        
        request_data = metadata["request_data"]
        
        # Verify the request data contains our test parameters
        assert request_data["prompt"] == test_prompt
        assert request_data["negative_prompt"] == test_negative_prompt
        assert request_data["enhance_prompt"] == test_enhance_prompt
        assert request_data["count"] == test_count
        
        # Verify other expected metadata fields are present
        assert "creator" in metadata
        assert "size" in metadata
        assert "content_type" in metadata
        assert "byte_size" in metadata
        assert "gcs_url" in metadata
        
        print(f"✅ Resource {resource['url']} has correct request metadata:")
        print(f"   Prompt: {request_data['prompt']}")
        print(f"   Negative Prompt: {request_data['negative_prompt']}")
        print(f"   Enhance Prompt: {request_data['enhance_prompt']}")
        print(f"   Count: {request_data['count']}")
    
    print(f"✅ Test passed! All {test_count} generated images have correct request metadata stored.")