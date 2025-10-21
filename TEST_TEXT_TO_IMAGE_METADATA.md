# Text-to-Image Request Metadata Integration Test

This test verifies that when generating images through the text-to-image API, the original request parameters are properly stored in the resources table.

## Test Overview

The test performs the following steps:

1. **Creates a test user** - Uses the guest authentication endpoint
2. **Calls text-to-image API** - Generates images with specific test parameters
3. **Retrieves created resources** - Fetches all resources for the user
4. **Verifies request metadata** - Checks that the original request data is stored in `resource_metadata.request_data`

## Test Parameters

The test uses these specific parameters to verify data integrity:

- **Prompt**: "A beautiful sunset over mountains"
- **Negative Prompt**: "blurry, low quality"  
- **Enhance Prompt**: `true`
- **Count**: `2` (generates 2 images)

## Running the Test

### Prerequisites

1. Backend service must be running at `http://localhost:8000`
2. Required Python packages: `httpx`, `pytest`

### Method 1: Direct Python execution

```bash
python test_text_to_image_request_metadata.py
```

### Method 2: Using pytest

```bash
# Run the specific test
pytest tests/test_text_to_image_request_metadata.py::test_text_to_image_request_metadata -v

# Run with integration marker
pytest -m integration tests/test_text_to_image_request_metadata.py -v
```

### Method 3: Run all integration tests

```bash
pytest -m integration -v
```

## Expected Output

The test will output:

```
✅ Resource https://cdn.example.com/image1.jpg has correct request metadata:
   Prompt: A beautiful sunset over mountains
   Negative Prompt: blurry, low quality
   Enhance Prompt: True
   Count: 2

✅ Resource https://cdn.example.com/image2.jpg has correct request metadata:
   Prompt: A beautiful sunset over mountains
   Negative Prompt: blurry, low quality
   Enhance Prompt: True
   Count: 2

✅ Test passed! All 2 generated images have correct request metadata stored.
```

## What the Test Verifies

1. **API Response**: Text-to-image endpoint returns successful response with image URLs
2. **Resource Creation**: Resources are created in the database for each generated image
3. **Metadata Structure**: Each resource has proper `resource_metadata` structure
4. **Request Data Storage**: The `request_data` field contains the original request parameters
5. **Data Integrity**: All request parameters match exactly what was sent to the API

## Troubleshooting

- **Connection Error**: Ensure backend is running on `http://localhost:8000`
- **Authentication Error**: Check that guest user creation is working
- **Resource Not Found**: Verify that resources endpoint is accessible
- **Metadata Missing**: Check that the text-to-image endpoint is saving request data correctly