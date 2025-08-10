# AI Character Generator

An intelligent AI agent that generates comprehensive fictional character profiles using the Gemini API. This system creates detailed characters with consistent physical appearances, engaging backgrounds, and meaningful encounter scenarios for role-play sessions.

## Testing

```
python -m pytest test_character_generation.py
```

## Features

### 🎭 Complete Character Profiles

- **Physical Appearance**: Detailed descriptions with consistent features across all generated images
- **Personality & Background**: Rich backstories, motivations, fears, dreams, and character quirks
- **Encounter Scenarios**: Inventive meeting scenarios between the character and human users
- **Character Images**: Multiple consistent images in various styles and scenes

### 🎨 Multiple Genres & Styles

- **Genres**: Fantasy, Sci-Fi, Mystery, Romance, Adventure, Slice of Life, Horror
- **Tones**: Neutral, Serious, Humorous, Mysterious, Edgy, Cheerful, Wise
- **Image Styles**: Realistic, Fantasy Art, Anime, Cyberpunk, Cartoon, Painting

### 🔧 Technical Features

- **REST API**: FastAPI-based web service with comprehensive endpoints
- **CLI Interface**: Command-line tool for easy character generation
- **Export Formats**: JSON and human-readable text formats
- **Validation**: Comprehensive character validation and consistency checks

## Quick Start

### Prerequisites

- Python 3.8+
- Gemini API key from Google AI Studio

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd aigc
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   export GEMINI_API_KEY="your_gemini_api_key_here"
   ```

### Usage

#### Command Line Interface

Generate a character with default settings:

```bash
python cli.py "A mysterious wizard who lives in a floating tower"
```

Generate with custom parameters:

```bash
python cli.py "A cyberpunk hacker with neon hair" \
  --genre sci-fi \
  --tone edgy \
  --image-style cyberpunk \
  --num-images 4 \
  --export-format text \
  --output my_character.txt
```

Show only character summary:

```bash
python cli.py "A wise librarian" --summary-only
```

#### Web API

Start the API server:

```bash
python api.py
```

The API will be available at `http://localhost:8000`

**Generate a character:**

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "brief_description": "A mysterious wizard who lives in a floating tower",
    "genre": "fantasy",
    "tone": "mysterious",
    "image_style": "fantasy_art",
    "num_images": 4
  }'
```

**Get example requests:**

```bash
curl "http://localhost:8000/examples"
```

**View API documentation:**
Visit `http://localhost:8000/docs` for interactive API documentation.

## API Endpoints

| Endpoint          | Method | Description                               |
| ----------------- | ------ | ----------------------------------------- |
| `/`               | GET    | API information and available endpoints   |
| `/health`         | GET    | Health check                              |
| `/generate`       | POST   | Generate a complete character profile     |
| `/generate/async` | POST   | Generate character asynchronously         |
| `/examples`       | GET    | Get example character generation requests |
| `/docs`           | GET    | Interactive API documentation             |

## Character Profile Structure

Each generated character includes:

### Basic Information

- **Name**: Unique character name
- **Age**: Character's age
- **Gender**: Character's gender identity
- **Physical Appearance**: Detailed physical description

### Background & Personality

- **Origin**: Where the character is from
- **Occupation**: What they do
- **Personality Traits**: Key personality characteristics
- **Motivations**: What drives them
- **Fears**: What they're afraid of
- **Dreams**: Their aspirations
- **Skills**: What they're good at
- **Quirks**: Unique behaviors or habits
- **Backstory**: Detailed life history

### Encounter Scenario

- **Scene Description**: Where and how the user meets the character
- **Location**: Specific meeting place
- **Mood**: Atmospheric description
- **Initial Dialogue**: First words the character says
- **User Role**: What role the user plays
- **Encounter Type**: Type of interaction (casual, adventure, mystery, romance)

### Generated Images

- **Multiple Images**: Consistent character appearances in different scenes
- **Scene Context**: Description of each image's setting
- **Image Style**: Artistic style used

## Configuration

The system can be configured through environment variables:

| Variable                   | Default                        | Description                                 |
| -------------------------- | ------------------------------ | ------------------------------------------- |
| `GEMINI_API_KEY`           | Required                       | Your Gemini API key                         |
| `DEBUG`                    | `True`                         | Enable debug mode                           |
| `HOST`                     | `0.0.0.0`                      | API server host                             |
| `PORT`                     | `8000`                         | API server port                             |
| `MAX_IMAGES_PER_CHARACTER` | `4`                            | Maximum images per character                |
| `IMAGE_QUALITY`            | `high`                         | Image generation quality                    |
| `LOG_LEVEL`                | `INFO`                         | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_TO_FILE`              | `False`                        | Enable file logging                         |
| `LOG_FILE`                 | `logs/character_generator.log` | Log file path                               |

## Testing

Run the test suite to validate the system:

```bash
python test_character_generation.py
```

This will test:

- Character generation with different genres and tones
- Character validation
- Export formats
- API functionality

### Debugging

Use the debugging tool to diagnose issues:

```bash
python debug.py
```

This comprehensive debugging script will:

- Check environment setup and dependencies
- Test configuration loading
- Verify Gemini API connection
- Test logging configuration
- Validate Pydantic models
- Run a full character generation test

### Logging

The system includes comprehensive logging for debugging:

**Enable verbose logging:**

```bash
export LOG_LEVEL=DEBUG
export LOG_TO_FILE=True
python cli.py "Your character description" --verbose
```

**View logs:**

- Console: Real-time logs during execution
- File: `logs/character_generator.log` (when enabled)
- Error logs: `logs/character_generator_errors.log` (when enabled)
- Verbose logs: `logs/character_generator_verbose.log` (debug mode)

**Log Levels:**

- `DEBUG`: Detailed debugging information
- `INFO`: General operational information
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failed operations
- `CRITICAL`: Critical errors that may cause system failure

## Architecture

```
aigc/
├── config.py              # Configuration management
├── models.py              # Pydantic data models
├── gemini_client.py       # Gemini API client
├── character_agent.py     # Main character generation agent
├── api.py                 # FastAPI web server
├── cli.py                 # Command-line interface
├── test_character_generation.py  # Test suite
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the API documentation at `/docs`
2. Review the test examples
3. Open an issue on GitHub

---

**Note**: This system requires a valid Gemini API key to function. The image generation currently creates placeholder URLs - in a production environment, you would integrate with actual image generation services.
