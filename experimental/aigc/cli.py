#!/usr/bin/env python3
"""
Command-line interface for the AI Character Generator
"""

import argparse
import sys
import logging
from pathlib import Path
from character_agent import CharacterAgent
from models import CharacterGenerationRequest
from config import Config


def main():
    """Main CLI function"""
    logger = logging.getLogger(__name__)
    logger.info("Starting CLI interface...")

    parser = argparse.ArgumentParser(
        description="AI Character Generator - Create detailed fictional character profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py "A mysterious wizard who lives in a floating tower"
  python cli.py "A cyberpunk hacker with neon hair" --genre sci-fi --tone edgy
  python cli.py "A wise librarian" --export-format text --output character.txt
        """,
    )

    parser.add_argument(
        "description", help="Brief description of the character to generate"
    )

    parser.add_argument(
        "--genre",
        default="fantasy",
        choices=[
            "fantasy",
            "sci-fi",
            "mystery",
            "romance",
            "adventure",
            "slice_of_life",
            "horror",
        ],
        help="Genre of the character (default: fantasy)",
    )

    parser.add_argument(
        "--tone",
        default="neutral",
        choices=[
            "neutral",
            "serious",
            "humorous",
            "mysterious",
            "edgy",
            "cheerful",
            "wise",
        ],
        help="Tone of the character (default: neutral)",
    )

    parser.add_argument(
        "--image-style",
        default="realistic",
        choices=[
            "realistic",
            "fantasy_art",
            "anime",
            "cyberpunk",
            "cartoon",
            "painting",
        ],
        help="Style for generated images (default: realistic)",
    )

    parser.add_argument(
        "--num-images",
        type=int,
        default=4,
        help="Number of images to generate (default: 4)",
    )

    parser.add_argument(
        "--export-format",
        choices=["json", "text"],
        default="json",
        help="Export format (default: json)",
    )

    parser.add_argument(
        "--output", help="Output file path (if not specified, prints to stdout)"
    )

    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Show only character summary, not full profile",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set up verbose logging if requested
    if args.verbose:
        Config.logger.setLevel(logging.DEBUG)
        logger.info("Verbose logging enabled")

    logger.info("CLI arguments parsed successfully")
    logger.debug(f"Description: {args.description}")
    logger.debug(f"Genre: {args.genre}")
    logger.debug(f"Tone: {args.tone}")
    logger.debug(f"Image style: {args.image_style}")
    logger.debug(f"Num images: {args.num_images}")
    logger.debug(f"Export format: {args.export_format}")
    logger.debug(f"Output file: {args.output}")
    logger.debug(f"Summary only: {args.summary_only}")

    try:
        # Validate configuration
        logger.info("Validating configuration...")
        Config.validate()
        logger.info("Configuration validation successful")

        # Create character generation request
        logger.info("Creating character generation request...")
        request = CharacterGenerationRequest(
            brief_description=args.description,
            genre=args.genre,
            tone=args.tone,
            image_style=args.image_style,
            num_images=args.num_images,
        )
        logger.info("Character generation request created successfully")

        print("🤖 AI Character Generator")
        print("=" * 50)
        print(f"Generating character: {args.description}")
        print(f"Genre: {args.genre}")
        print(f"Tone: {args.tone}")
        print(f"Image Style: {args.image_style}")
        print(f"Number of Images: {args.num_images}")
        print("-" * 50)

        # Initialize character agent
        logger.info("Initializing Character Agent...")
        agent = CharacterAgent()
        logger.info("Character Agent initialized successfully")

        # Generate character
        print("🔄 Generating character profile...")
        logger.info("Starting character generation process...")
        response = agent.generate_character(request)

        if not response.success:
            logger.error(f"Character generation failed: {response.error}")
            print(f"❌ Error: {response.error}")
            sys.exit(1)

        character = response.character
        logger.info(f"Character generated successfully: {character.name}")

        print(f"✅ Character generated successfully!")
        print(f"📊 Generation time: {response.generation_time:.2f} seconds")
        print("-" * 50)

        # Display results
        if args.summary_only:
            logger.info("Generating character summary...")
            summary = agent.get_character_summary(character)
            print("📋 Character Summary:")
            print(f"Name: {summary['name']}")
            print(f"Age: {summary['age']}")
            print(f"Gender: {summary['gender']}")
            print(f"Occupation: {summary['occupation']}")
            print(f"Personality: {summary['personality']}")
            print(f"Encounter Location: {summary['encounter_location']}")
            print(f"Encounter Type: {summary['encounter_type']}")
            print(f"Key Traits: {', '.join(summary['key_traits'])}")
            print(f"Main Motivation: {summary['main_motivation']}")
            print(f"Images Generated: {summary['image_count']}")
            logger.info("Character summary displayed successfully")
        else:
            # Export character
            logger.info(f"Exporting character in {args.export_format} format...")

            if args.export_format == "json":
                output_data = character.model_dump_json(indent=2)
                logger.debug(f"JSON export size: {len(output_data)} characters")
            else:  # text format
                output_data = agent.export_character(character, format="text")
                logger.debug(f"Text export size: {len(output_data)} characters")

            # Write to file or print to stdout
            if args.output:
                output_path = Path(args.output)
                logger.info(f"Writing output to file: {output_path}")

                try:
                    output_path.write_text(output_data)
                    print(f"💾 Character saved to: {output_path}")
                    logger.info(f"Character successfully saved to: {output_path}")
                except Exception as e:
                    logger.error(f"Failed to write output file: {e}")
                    print(f"❌ Error saving file: {e}")
                    sys.exit(1)
            else:
                logger.info("Printing output to stdout")
                print(output_data)

        print("=" * 50)
        print("🎉 Character generation complete!")
        logger.info("CLI execution completed successfully")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Configuration error: {e}")
        print("Please set the GEMINI_API_KEY environment variable")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("CLI execution interrupted by user")
        print("\n⏹️  Character generation cancelled")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.exception("Full exception details:")
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
