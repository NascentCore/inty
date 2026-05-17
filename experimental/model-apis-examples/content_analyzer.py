import argparse
import enum
import io
import json
import os
import time
from typing import Dict, Union
from google.genai import types
from google import genai
from PIL import Image


class ContentType(enum.Enum):
    TEXT = "text"
    IMAGE = "image"


class ContentAnalyzer:
    def __init__(self, api_key: str = None):
        """Initialize the content analyzer with Gemini API key."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set")

        self.client = genai.Client(api_key=self.api_key)
        self.content_definitions = {}

    def add_content_definition(self, label: str, definition: str) -> None:
        """Add a content definition to the analyzer."""
        self.content_definitions[label] = definition

    def load_content_definitions_from_file(self, file_path: str) -> None:
        """Load content definitions from a JSON file."""
        with open(file_path, "r") as f:
            definitions = json.load(f)
            for label, definition in definitions.items():
                self.add_content_definition(label, definition)

    def save_content_definitions_to_file(self, file_path: str) -> None:
        """Save current content definitions to a JSON file."""
        with open(file_path, "w") as f:
            json.dump(self.content_definitions, f, indent=2)

    def analyze_text(self, text: str) -> Dict[str, float]:
        """Analyze text content against all defined labels."""
        if not self.content_definitions:
            raise ValueError(
                "No content definitions loaded. Use add_content_definition() or load_content_definitions_from_file() first."
            )

        results = {}

        for label, definition in self.content_definitions.items():
            prompt = f"""Analyze the following text and determine the probability (0.0 to 1.0) that it contains content related to: "{label}"

Definition of "{label}": {definition}

Text to analyze:
{text}

Respond with only a number between 0.0 and 1.0, where:
- 0.0 = Definitely not related to {label}
- 1.0 = Definitely related to {label}
- Values in between represent the probability

Probability:"""

            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt],
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 10,
                    },
                )

                # Extract probability from response
                probability_text = response.text.strip()
                try:
                    probability = float(probability_text)
                    # Ensure probability is between 0 and 1
                    probability = max(0.0, min(1.0, probability))
                except ValueError:
                    # If parsing fails, try to extract number from text
                    import re

                    numbers = re.findall(r"\d+\.?\d*", probability_text)
                    probability = float(numbers[0]) / 100.0 if numbers else 0.5

                results[label] = probability

            except Exception as e:
                print(f"Error analyzing {label}: {e}")
                results[label] = 0.0

        return results

    def analyze_image(self, image_path: str) -> Dict[str, float]:
        """Analyze image content against all defined labels."""
        if not self.content_definitions:
            raise ValueError(
                "No content definitions loaded. Use add_content_definition() or load_content_definitions_from_file() first."
            )

        # Load and resize image if needed
        image_bytes = self._prepare_image(image_path)

        results = {}

        for label, definition in self.content_definitions.items():
            prompt = f"""Analyze the following image and determine the probability (0.0 to 1.0) that it contains content related to: "{label}"

Definition of "{label}": {definition}

Respond with only a number between 0.0 and 1.0, where:
- 0.0 = Definitely not related to {label}
- 1.0 = Definitely related to {label}
- Values in between represent the probability

Probability:"""

            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type="image/jpeg",
                        ),
                        prompt,
                    ],
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 10,
                    },
                )

                # Extract probability from response
                probability_text = response.text.strip()
                try:
                    probability = float(probability_text)
                    # Ensure probability is between 0 and 1
                    probability = max(0.0, min(1.0, probability))
                except ValueError:
                    # If parsing fails, try to extract number from text
                    import re

                    numbers = re.findall(r"\d+\.?\d*", probability_text)
                    probability = float(numbers[0]) / 100.0 if numbers else 0.5

                results[label] = probability

            except Exception as e:
                print(f"Error analyzing {label}: {e}")
                results[label] = 0.0

        return results

    def _prepare_image(self, image_path: str) -> bytes:
        """Prepare image for analysis by resizing if needed and converting to bytes."""
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Resize if larger than 512x512
            width, height = img.size
            if width > 512 or height > 512:
                scale = 512 / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = img.resize(
                    (new_width, new_height), Image.Resampling.LANCZOS
                )

            # Convert to bytes
            bytesio = io.BytesIO()
            img.save(bytesio, format="JPEG", quality=85)
            bytesio.seek(0)
            return bytesio.getvalue()

    def analyze_content(
        self, content: Union[str, str], content_type: ContentType
    ) -> Dict[str, float]:
        """Analyze content (text or image) against all defined labels."""
        if content_type == ContentType.TEXT:
            return self.analyze_text(content)
        elif content_type == ContentType.IMAGE:
            return self.analyze_image(content)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")


def create_sample_definitions():
    """Create sample content definitions."""
    definitions = {
        "sexual": "any content related to sexual activity, nudity, or explicit sexual content",
        "violence": "any content depicting violence, weapons, fighting, or physical harm",
        "hate_speech": "any content promoting hatred, discrimination, or violence against specific groups",
        "drugs": "any content related to illegal drugs, drug use, or drug paraphernalia",
        "gore": "any content showing graphic violence, blood, or disturbing medical content",
        "spam": "any content that appears to be spam, scams, or misleading information",
        "copyright": "any content that may violate copyright or intellectual property rights",
        "child_safety": "any content that may be harmful to children or inappropriate for minors",
    }
    return definitions


def main():
    parser = argparse.ArgumentParser(
        description="Analyze content for various definitions using Gemini 2.5 Flash"
    )
    parser.add_argument(
        "--content", required=True, help="Text content or path to image file"
    )
    parser.add_argument(
        "--type",
        choices=["text", "image"],
        required=True,
        help="Type of content to analyze",
    )
    parser.add_argument(
        "--definitions", help="Path to JSON file with content definitions"
    )
    parser.add_argument(
        "--save-definitions",
        help="Path to save current definitions to JSON file",
    )
    parser.add_argument(
        "--add-definition",
        nargs=2,
        metavar=("LABEL", "DEFINITION"),
        help="Add a single definition (label and definition)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Probability threshold for flagging content (default: 0.5)",
    )

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = ContentAnalyzer()

    # Load or create definitions
    if args.definitions:
        analyzer.load_content_definitions_from_file(args.definitions)
    elif args.add_definition:
        label, definition = args.add_definition
        analyzer.add_content_definition(label, definition)
    else:
        # Use sample definitions
        sample_defs = create_sample_definitions()
        for label, definition in sample_defs.items():
            analyzer.add_content_definition(label, definition)
        print(
            "Using sample content definitions. Use --definitions to load custom ones."
        )

    # Save definitions if requested
    if args.save_definitions:
        analyzer.save_content_definitions_to_file(args.save_definitions)
        print(f"Definitions saved to {args.save_definitions}")

    # Determine content type
    content_type = (
        ContentType.TEXT if args.type == "text" else ContentType.IMAGE
    )

    # Analyze content
    print(f"Analyzing {args.type} content...")
    print(f"Content: {args.content}")
    print("-" * 50)

    start_time = time.time()
    results = analyzer.analyze_content(args.content, content_type)
    end_time = time.time()

    # Display results
    print(f"Analysis completed in {end_time - start_time:.2f} seconds")
    print("\nResults:")
    print("-" * 50)

    flagged_content = []
    for label, probability in results.items():
        status = "🚩 FLAGGED" if probability >= args.threshold else "✅ CLEAR"
        print(f"{label:15} | {probability:.3f} | {status}")

        if probability >= args.threshold:
            flagged_content.append((label, probability))

    print("-" * 50)
    if flagged_content:
        print(f"\n🚨 Content flagged for {len(flagged_content)} categories:")
        for label, probability in flagged_content:
            print(f"  - {label}: {probability:.3f}")
    else:
        print("\n✅ No content flagged above threshold")


if __name__ == "__main__":
    main()
