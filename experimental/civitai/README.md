# Civitai Model Parser

A minimal Python parser to extract key information from Civitai model pages.

## Features

Extracts the following information from Civitai model pages:

- **Model Name**: The name of the AI model
- **Tags**: Categories and tags associated with the model
- **Download Links**: Direct download links with file size and type information
- **Details**: Technical details like model type, stats, reviews, etc.
- **About**: Description and information about the model
- **Stats**: Download counts, likes, comments, etc.
- **Creator**: Model creator information
- **License**: License information
- **Suggested Settings**: Recommended generation settings
- **Version Info**: Model version information

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements_parser.txt
```

## Usage

### Basic Usage

```python
from civitai_parser import CivitaiParser

# Initialize the parser
parser = CivitaiParser()

# Parse a model page
url = "https://civitai.com/models/1224788/prefect-illustrious-xl"
result = parser.parse_model_page(url)

# Print results
print(json.dumps(result, indent=2))
```

### Example Script

Run the example script to test the parser:

```bash
python example_usage.py
```

This will:

1. Parse the example Civitai model page
2. Save the results to a JSON file
3. Display key information in the console

## Output Format

The parser returns a JSON object with the following structure:

```json
{
  "url": "https://civitai.com/models/1224788/prefect-illustrious-xl",
  "model_name": "Prefect illustrious XL",
  "tags": ["anime", "woman", "girls", "styles", "base models"],
  "download_links": [
    {
      "url": "https://civitai.com/download/...",
      "text": "Download (6.46 GB)",
      "file_size": "6.46 GB",
      "file_type": "SafeTensor"
    }
  ],
  "details": {
    "Type": "Checkpoint Merge",
    "Stats": "460",
    "Reviews": "Very Positive (138)",
    "Published": "Aug 4, 2025",
    "Base Model": "Illustrious"
  },
  "about": "Model description and information...",
  "stats": {
    "downloads": "4.2m",
    "likes": "3.1k"
  },
  "creator": "GOGoofy_Ai",
  "license": "Illustrious License",
  "suggested_settings": {
    "suggested_settings": "CLIP skip 1, Samplers: Eular A, DPM++ 2M, CFG: 5-6..."
  },
  "version_info": {
    "version": "3.0"
  }
}
```

## Error Handling

The parser includes error handling for:

- Network connection issues
- Invalid URLs
- Parsing errors
- Missing content

If an error occurs, the result will contain an `error` field with the error message.

## Dependencies

- `requests`: For HTTP requests
- `beautifulsoup4`: For HTML parsing
- `lxml`: XML/HTML parser backend

## Notes

- The parser uses a realistic User-Agent to avoid being blocked
- It handles both relative and absolute URLs
- Duplicate tags are automatically removed
- File sizes and types are extracted from download links
- The parser is designed to be robust and handle various page layouts

## Limitations

- The parser relies on HTML structure and may need updates if Civitai changes their website layout
- Some information might not be available for all models
- The parser is designed for public model pages and may not work with private/restricted content
