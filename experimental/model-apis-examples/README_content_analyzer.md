# Content Analyzer

A Python program that analyzes text and images for various content definitions using Google's Gemini 2.5 Flash LLM API.

## Features

- Analyze both text and images for multiple content categories
- Customizable content definitions with labels and descriptions
- Probability-based scoring (0.0 to 1.0) for each content category
- Configurable threshold for flagging content
- Support for loading/saving content definitions from JSON files
- Automatic image resizing for optimal API performance

## Installation

1. Install dependencies:

```bash
uv add google-genai pillow
```

2. Set your Gemini API key:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

## Usage

### Basic Usage

Analyze text content:

```bash
uv run content_analyzer.py --content "This is some text to analyze" --type text
```

Analyze image content:

```bash
uv run content_analyzer.py --content path/to/image.jpg --type image
```

### Using Custom Definitions

Load definitions from a JSON file:

```bash
uv run content_analyzer.py --content "text to analyze" --type text --definitions my_definitions.json
```

Add a single definition:

```bash
uv run content_analyzer.py --content "text to analyze" --type text --add-definition "custom_label" "description of what this label means"
```

### Adjusting Sensitivity

Set a custom threshold (default is 0.5):

```bash
uv run content_analyzer.py --content "text to analyze" --type text --threshold 0.7
```

### Saving Definitions

Save current definitions to a file:

```bash
uv run content_analyzer.py --content "text to analyze" --type text --save-definitions my_definitions.json
```

## Content Definition Format

Content definitions are stored as JSON with labels as keys and descriptions as values:

```json
{
  "sexual": "any content related to sexual activity, nudity, or explicit sexual content",
  "violence": "any content depicting violence, weapons, fighting, or physical harm",
  "hate_speech": "any content promoting hatred, discrimination, or violence against specific groups"
}
```

## Sample Definitions

The program comes with sample definitions for common content categories:

- sexual
- violence
- hate_speech
- drugs
- gore
- spam
- copyright
- child_safety
- political
- medical
- financial
- religion

## Output Format

The program outputs:

- Probability scores (0.0 to 1.0) for each content category
- Clear/Flagged status based on threshold
- Summary of flagged content
- Analysis time

Example output:

```
Analyzing text content...
Content: This is some text to analyze
--------------------------------------------------
Analysis completed in 2.34 seconds

Results:
--------------------------------------------------
sexual         | 0.023 | ✅ CLEAR
violence       | 0.156 | ✅ CLEAR
hate_speech    | 0.089 | ✅ CLEAR
drugs          | 0.012 | ✅ CLEAR
gore           | 0.034 | ✅ CLEAR
spam           | 0.067 | ✅ CLEAR
copyright      | 0.123 | ✅ CLEAR
child_safety   | 0.045 | ✅ CLEAR
--------------------------------------------------

✅ No content flagged above threshold
```

## Programmatic Usage

You can also use the ContentAnalyzer class in your own Python code:

```python
from content_analyzer import ContentAnalyzer

# Initialize analyzer
analyzer = ContentAnalyzer()

# Add definitions
analyzer.add_content_definition("custom", "description of custom category")

# Analyze content
results = analyzer.analyze_text("Text to analyze")
# or
results = analyzer.analyze_image("path/to/image.jpg")

print(results)
```

## Notes

- Images are automatically resized to fit within 512x512 pixels for optimal API performance
- The program uses a low temperature (0.1) for consistent results
- Probability parsing includes fallback mechanisms for various response formats
- Error handling ensures the program continues even if individual analyses fail
