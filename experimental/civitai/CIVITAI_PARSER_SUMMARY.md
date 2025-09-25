# Civitai Model Parser - Complete Solution

## Overview

I've created a minimal Python parser to extract key information from Civitai model pages. The parser successfully extracts all requested information and additional useful data from URLs like `https://civitai.com/models/1224788/prefect-illustrious-xl`.

## Files Created

1. **`civitai_parser.py`** - Basic parser with core functionality
2. **`civitai_parser_enhanced.py`** - Enhanced version with better extraction capabilities
3. **`requirements_parser.txt`** - Dependencies
4. **`example_usage.py`** - Example usage script
5. **`README_parser.md`** - Documentation

## Key Information Extracted

### Required Information ✅

- **Download Links**: Direct download URLs with file size and type
- **Details Section**: Technical details like model type, stats, reviews, etc.
- **About Info**: Model description and information
- **Model Name**: The name of the AI model
- **Tags**: Categories and tags associated with the model

### Additional Useful Information ✅

- **Stats**: Download counts, likes, comments, etc.
- **Creator**: Model creator information
- **License**: License information
- **Suggested Settings**: Recommended generation settings
- **Version Info**: Model version information
- **Model Versions**: All available versions
- **Structured Data**: JSON-LD structured data

## Example Output

```json
{
  "url": "https://civitai.com/models/1224788/prefect-illustrious-xl",
  "model_name": "Prefect illustrious XL",
  "tags": [
    "Checkpoint",
    "v3",
    "base models",
    "styles",
    "anime",
    "Checkpoint Merge",
    "girls",
    "woman",
    "Merge",
    "base model"
  ],
  "download_links": [
    {
      "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/14538/prefectIllustriousXl.Ry5O.safetensors",
      "text": "prefect_illustrious_xl_v3.fp16.safetensors",
      "file_size": "6.61 GB",
      "file_type": "SafeTensor"
    }
  ],
  "details": {
    "Type": "Checkpoint Merge",
    "Stats": "460",
    "Reviews": "Very Positive(139)",
    "Published": "Aug 4, 2025",
    "Base Model": "Illustrious",
    "Hash": "AutoV21A66B7E7F5"
  },
  "about": "If you like my work, drop a 5 review and hit the heart icon...",
  "stats": {
    "downloads": "4.2m",
    "likes": "3.1k"
  },
  "creator": "Goofy_Ai",
  "license": "Illustrious License",
  "suggested_settings": {
    "suggested_settings": "CLIP skip 1, Samplers: Eular A, DPM++ 2M, CFG: 5-6..."
  },
  "version_info": {
    "version": "3.0"
  },
  "model_versions": [
    {
      "version": "3.0",
      "text": "v3"
    },
    {
      "version": "2.0",
      "text": "v2.0p"
    }
  ]
}
```

## Features

### Robust Extraction

- Handles both static HTML and dynamic JavaScript content
- Extracts from structured data (JSON-LD) and HTML elements
- Filters out navigation elements and irrelevant content
- Handles various page layouts and structures

### Error Handling

- Network connection issues
- Invalid URLs
- Parsing errors
- Missing content

### User-Friendly

- Clean JSON output
- Comprehensive documentation
- Example usage scripts
- Easy to extend and customize

## Usage

### Basic Usage

```python
from civitai_parser_enhanced import CivitaiParserEnhanced

parser = CivitaiParserEnhanced()
url = "https://civitai.com/models/1224788/prefect-illustrious-xl"
result = parser.parse_model_page(url)
print(json.dumps(result, indent=2))
```

### Installation

```bash
pip install -r requirements_parser.txt
```

## Technical Implementation

### Key Methods

- `parse_model_page()`: Main parsing method
- `_extract_download_links()`: Extracts download URLs and metadata
- `_extract_tags()`: Filters and extracts model tags
- `_extract_details()`: Gets technical details
- `_extract_structured_data()`: Extracts JSON-LD data

### Dependencies

- `requests`: HTTP requests
- `beautifulsoup4`: HTML parsing
- `lxml`: XML/HTML parser backend

## Limitations & Notes

- Parser relies on HTML structure and may need updates if Civitai changes their website
- Some information might not be available for all models
- Designed for public model pages
- Uses realistic User-Agent to avoid being blocked

## Files Summary

| File                         | Purpose                                 |
| ---------------------------- | --------------------------------------- |
| `civitai_parser.py`          | Basic parser implementation             |
| `civitai_parser_enhanced.py` | Enhanced version with better extraction |
| `requirements_parser.txt`    | Python dependencies                     |
| `example_usage.py`           | Usage examples                          |
| `README_parser.md`           | Detailed documentation                  |

## Success Metrics

✅ **All requested information extracted successfully**

- Download links with file size and type
- Details section information
- About/description information
- Model name
- Tags/categories

✅ **Additional useful information included**

- Creator information
- License details
- Suggested settings
- Version information
- Statistics
- Structured data

✅ **Robust and user-friendly**

- Error handling
- Clean JSON output
- Comprehensive documentation
- Easy to use and extend

The parser successfully extracts all the key information requested and provides additional useful data in a clean, structured JSON format.
