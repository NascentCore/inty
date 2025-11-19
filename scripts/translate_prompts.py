#!/usr/bin/env python3
"""
Translate prompts_data.yaml to multiple languages using Gemini structured output.

Usage:
    python scripts/translate_prompts.py es fr de ja zh-CN
    python scripts/translate_prompts.py --output-dir translations es fr de
    python scripts/translate_prompts.py --combined es fr de
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from google.genai import types
from pydantic import BaseModel, Field

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.agent.prompts import PROMPTS_DATA_PATH
from app.utils.gemini import get_genai_client


class TranslationResponse(BaseModel):
    """Structured response schema for translation."""

    translation: str = Field(description="The translated text")


def translate_text(
    text: str, target_lang: str, source_lang: str = "en", client=None
) -> str:
    """
    Translate text to target language using Gemini structured output.

    Args:
        text: Text to translate
        target_lang: Target language code (e.g., 'es', 'fr', 'de', 'ja', 'zh-CN')
        source_lang: Source language code (default: 'en')
        client: Gemini client (will be created if not provided)

    Returns:
        Translated text
    """
    if client is None:
        client = get_genai_client()

    # Get language name for better prompt
    lang_names = {
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "ja": "Japanese",
        "zh-CN": "Simplified Chinese",
        "zh-TW": "Traditional Chinese",
        "ko": "Korean",
        "pt": "Portuguese",
        "it": "Italian",
        "ru": "Russian",
    }
    target_lang_name = lang_names.get(target_lang, target_lang)

    prompt = f"""Translate the following text from {source_lang} to {target_lang_name} ({target_lang}).

Requirements:
1. Preserve all placeholders exactly as they are (e.g., {{char}}, {{user}}, {{time_no_messages}})
2. Maintain the same formatting, structure, and line breaks
3. Keep all special characters, brackets, and punctuation
4. Translate the meaning accurately while preserving the technical structure
5. Do not add or remove any content

Text to translate:
{text}"""

    response_text = ""
    try:
        # Use structured output with JSON schema
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,  # Lower temperature for more consistent translations
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_schema=TranslationResponse.model_json_schema(),
            ),
        )

        # Extract text from response
        if not response.candidates or len(response.candidates) == 0:
            raise ValueError("Gemini did not return any candidates")

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            raise ValueError("No content in response")

        # Get the JSON text from the response
        for part in candidate.content.parts:
            if hasattr(part, "text") and part.text:
                response_text += part.text

        if not response_text:
            raise ValueError("No text in response parts")

        # Parse JSON response
        translation_data = json.loads(response_text)
        translation = translation_data.get("translation", "")

        if not translation:
            raise ValueError("Translation field is empty in response")

        return translation

    except json.JSONDecodeError as e:
        print(
            f"Error parsing JSON response for {target_lang}: {e}",
            file=sys.stderr,
        )
        if response_text:
            print(f"Response text: {response_text[:500]}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error translating to {target_lang}: {e}", file=sys.stderr)
        if response_text:
            print(f"Response text: {response_text[:500]}", file=sys.stderr)
        raise


def translate_prompts(
    prompts_data: dict[str, Any],
    target_lang: str,
    source_lang: str = "en",
    client=None,
) -> dict[str, str]:
    """
    Translate all prompt values in the prompts data.

    Args:
        prompts_data: Dictionary of prompts
        target_lang: Target language code
        source_lang: Source language code
        client: Gemini client (will be created if not provided)

    Returns:
        Dictionary with translated prompts
    """
    if client is None:
        client = get_genai_client()

    translated_data = {}
    total = len(prompts_data)

    for idx, (key, value) in enumerate(prompts_data.items(), 1):
        if not isinstance(value, str):
            print(
                f"Warning: Skipping non-string value for key '{key}'",
                file=sys.stderr,
            )
            translated_data[key] = value
            continue

        print(
            f"[{idx}/{total}] Translating {key} to {target_lang}...",
            file=sys.stderr,
        )
        try:
            translated_data[key] = translate_text(
                value, target_lang, source_lang, client
            )
        except Exception as e:
            print(f"Error translating {key}: {e}", file=sys.stderr)
            # Keep original text if translation fails
            translated_data[key] = value

    return translated_data


def save_translated_yaml(
    data: dict[str, str],
    output_path: Path,
    lang_code: str | None = None,
) -> None:
    """
    Save translated prompts to YAML file.

    Args:
        data: Translated prompts data
        output_path: Path to save the YAML file
        lang_code: Language code to include in filename (optional)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data, f, allow_unicode=True, default_flow_style=False, sort_keys=False
        )

    print(f"Saved translated prompts to: {output_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Translate prompts_data.yaml to multiple languages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate to Spanish, French, German, Japanese, and Chinese
  python scripts/translate_prompts.py es fr de ja zh-CN
  
  # Save to custom directory
  python scripts/translate_prompts.py --output-dir translations es fr
  
  # Save all languages to a single combined file
  python scripts/translate_prompts.py --combined es fr de
  
Language codes:
  Common codes: es (Spanish), fr (French), de (German), ja (Japanese),
                 zh-CN (Simplified Chinese), zh-TW (Traditional Chinese),
                 ko (Korean), pt (Portuguese), it (Italian), ru (Russian)

Note:
  This script uses Gemini API with structured output for translation.
  It requires proper Google Cloud credentials configured via service account.
        """,
    )

    parser.add_argument(
        "languages",
        nargs="+",
        help="Target language codes (e.g., es fr de ja zh-CN)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("app/core/agent"),
        help="Directory to save translated files (default: app/core/agent)",
    )

    parser.add_argument(
        "--combined",
        action="store_true",
        help="Save all languages to a single combined YAML file",
    )

    parser.add_argument(
        "--source-lang",
        default="en",
        help="Source language code (default: en)",
    )

    parser.add_argument(
        "--input-file",
        type=Path,
        default=PROMPTS_DATA_PATH,
        help=f"Input YAML file (default: {PROMPTS_DATA_PATH})",
    )

    args = parser.parse_args()

    # Load source prompts
    print(f"Loading prompts from: {args.input_file}", file=sys.stderr)
    with args.input_file.open(encoding="utf-8") as f:
        source_data = yaml.safe_load(f)

    if not isinstance(source_data, dict):
        print(f"Error: Expected dictionary, got {type(source_data)}", file=sys.stderr)
        sys.exit(1)

    # Create a single client to reuse across translations
    client = get_genai_client()

    if args.combined:
        # Save all languages to a single file
        combined_data = {}
        for lang in args.languages:
            print(f"\nTranslating to {lang}...", file=sys.stderr)
            translated = translate_prompts(source_data, lang, args.source_lang, client)
            combined_data[lang] = translated

        output_path = args.output_dir / "prompts_data_multilang.yaml"
        save_translated_yaml(combined_data, output_path)
    else:
        # Save each language to a separate file
        for lang in args.languages:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Translating to {lang}...", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)

            translated = translate_prompts(source_data, lang, args.source_lang, client)

            output_path = args.output_dir / f"prompts_data_{lang}.yaml"
            save_translated_yaml(translated, output_path, lang)

    print("\nTranslation complete!", file=sys.stderr)


if __name__ == "__main__":
    main()
