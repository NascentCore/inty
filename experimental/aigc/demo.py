#!/usr/bin/env python3
"""
Demo script for the AI Character Generator
Shows how to use the system with a simple example
"""

import os
import logging
from character_agent import CharacterAgent
from models import CharacterGenerationRequest


def main():
    """Run a demo of the character generation system"""

    from loguru import logger

    logger.info("Starting AI Character Generator Demo")

    print("🎭 AI Character Generator Demo")
    print("=" * 50)

    # Check if API key is set
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY environment variable not set")
        print("❌ GEMINI_API_KEY environment variable not set!")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your_api_key_here'")
        return

    logger.info("GEMINI_API_KEY environment variable found")

    # Create a demo character request
    demo_request = CharacterGenerationRequest(
        brief_description="A mysterious wizard who lives in a floating tower",
        genre="fantasy",
        tone="mysterious",
        image_style="fantasy_art",
        num_images=2,
    )

    logger.info("Demo character request created")
    logger.debug(f"Description: {demo_request.brief_description}")
    logger.debug(f"Genre: {demo_request.genre}")
    logger.debug(f"Tone: {demo_request.tone}")
    logger.debug(f"Image style: {demo_request.image_style}")
    logger.debug(f"Num images: {demo_request.num_images}")

    print(f"📝 Generating character: {demo_request.brief_description}")
    print(f"🎨 Genre: {demo_request.genre}")
    print(f"🎭 Tone: {demo_request.tone}")
    print(f"🖼️  Image Style: {demo_request.image_style}")
    print("-" * 50)

    try:
        # Initialize the character agent
        logger.info("Initializing Character Agent for demo...")
        agent = CharacterAgent()
        logger.info("Character Agent initialized successfully")

        # Generate the character
        print("🔄 Generating character profile...")
        logger.info("Starting character generation process...")
        response = agent.generate_character(demo_request)

        if response.success:
            character = response.character
            logger.info(f"Character generated successfully: {character.name}")

            print(f"✅ Character generated successfully!")
            print(
                f"⏱️  Generation time: {response.generation_time:.2f} seconds"
            )
            print("-" * 50)

            # Display character summary
            logger.info("Generating character summary for display...")
            summary = agent.get_character_summary(character)
            print("📋 Character Summary:")
            print(f"   Name: {summary['name']}")
            print(f"   Age: {summary['age']}")
            print(f"   Gender: {summary['gender']}")
            print(f"   Occupation: {summary['occupation']}")
            print(f"   Personality: {summary['personality']}")
            print(f"   Encounter Location: {summary['encounter_location']}")
            print(f"   Encounter Type: {summary['encounter_type']}")
            print(f"   Key Traits: {', '.join(summary['key_traits'])}")
            print(f"   Main Motivation: {summary['main_motivation']}")
            print(f"   Images Generated: {summary['image_count']}")

            logger.info("Character summary displayed successfully")
            print("-" * 50)

            # Show encounter scenario
            logger.info("Displaying encounter scenario...")
            print("🎬 Encounter Scenario:")
            print(f"   Location: {character.encounter.location}")
            print(f"   Mood: {character.encounter.mood}")
            print(f"   Type: {character.encounter.encounter_type}")
            print(f"   User Role: {character.encounter.user_role}")
            print()
            print("   Scene Description:")
            print(f"   {character.encounter.scene_description}")
            print()
            print("   Initial Dialogue:")
            print(f'   "{character.encounter.initial_dialogue}"')

            logger.info("Encounter scenario displayed successfully")
            print("-" * 50)

            # Show background highlights
            logger.info("Displaying background highlights...")
            print("📖 Background Highlights:")
            print(f"   Origin: {character.background.origin}")
            print(f"   Skills: {', '.join(character.background.skills[:3])}")
            print(f"   Quirks: {', '.join(character.background.quirks[:2])}")
            print(f"   Fears: {', '.join(character.background.fears[:2])}")
            print(f"   Dreams: {', '.join(character.background.dreams[:2])}")

            logger.info("Background highlights displayed successfully")
            print("-" * 50)

            # Export character to file
            logger.info("Exporting character to files...")
            print("💾 Exporting character...")

            # JSON export
            try:
                logger.info("Creating JSON export...")
                json_export = agent.export_character(character, format="json")
                with open("demo_character.json", "w") as f:
                    f.write(json_export)
                print("   ✅ JSON export: demo_character.json")
                logger.info("JSON export created successfully")
            except Exception as e:
                logger.error(f"Failed to create JSON export: {e}")
                print(f"   ❌ JSON export failed: {e}")

            # Text export
            try:
                logger.info("Creating text export...")
                text_export = agent.export_character(character, format="text")
                with open("demo_character.txt", "w") as f:
                    f.write(text_export)
                print("   ✅ Text export: demo_character.txt")
                logger.info("Text export created successfully")
            except Exception as e:
                logger.error(f"Failed to create text export: {e}")
                print(f"   ❌ Text export failed: {e}")

            print("-" * 50)
            print("🎉 Demo completed successfully!")
            print(
                "📁 Check demo_character.json and demo_character.txt for full character details"
            )
            logger.info("Demo completed successfully")

        else:
            logger.error(f"Character generation failed: {response.error}")
            print(f"❌ Character generation failed: {response.error}")

    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        logger.exception("Full exception details:")
        print(f"❌ Demo failed: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
