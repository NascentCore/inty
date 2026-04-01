#!/usr/bin/env python3
"""
Debugging script for the AI Character Generator
Helps diagnose and troubleshoot issues
"""

import os
import sys
import logging
from pathlib import Path
from config import Config
from logging_config import setup_verbose_logging


def check_environment():
    """Check environment setup"""
    print("🔍 Checking Environment Setup")
    print("=" * 50)

    # Check Python version
    print(f"Python version: {sys.version}")

    # Check environment variables
    print("\n📋 Environment Variables:")
    required_vars = ["GEMINI_API_KEY"]
    optional_vars = ["DEBUG", "LOG_LEVEL", "LOG_TO_FILE", "LOG_FILE"]

    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {'*' * len(value)} (set)")
        else:
            print(f"  ❌ {var}: Not set")

    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  📝 {var}: {value}")
        else:
            print(f"  ⚪ {var}: Not set (using default)")

    # Check current working directory
    print(f"\n📁 Current working directory: {os.getcwd()}")

    # Check if logs directory exists
    logs_dir = Path("logs")
    if logs_dir.exists():
        print(f"  ✅ Logs directory exists: {logs_dir}")
        log_files = list(logs_dir.glob("*.log"))
        if log_files:
            print(f"  📄 Found {len(log_files)} log files:")
            for log_file in log_files:
                size = log_file.stat().st_size
                print(f"    - {log_file.name} ({size} bytes)")
        else:
            print("  📄 No log files found")
    else:
        print(f"  ❌ Logs directory does not exist: {logs_dir}")


def check_dependencies():
    """Check if all required dependencies are installed"""
    print("\n📦 Checking Dependencies")
    print("=" * 50)

    required_packages = [
        "google.generativeai",
        "fastapi",
        "uvicorn",
        "pydantic",
        "python-dotenv",
        "requests",
    ]

    for package in required_packages:
        __import__(package)
        print(f"  ✅ {package}: Installed")


def test_configuration():
    """Test configuration loading"""
    print("\n⚙️  Testing Configuration")
    print("=" * 50)

    try:
        # Test config validation
        Config.validate()
        print("  ✅ Configuration validation passed")

        # Show config values
        print(f"  📝 Debug mode: {Config.DEBUG}")
        print(f"  📝 Host: {Config.HOST}")
        print(f"  📝 Port: {Config.PORT}")
        print(f"  📝 Max images: {Config.MAX_IMAGES_PER_CHARACTER}")
        print(f"  📝 Character model: {Config.CHARACTER_GENERATION_MODEL}")
        print(f"  📝 Image model: {Config.IMAGE_GENERATION_MODEL}")

    except Exception as e:
        print(f"  ❌ Configuration validation failed: {e}")


def test_gemini_connection():
    """Test Gemini API connection"""
    print("\n🔌 Testing Gemini API Connection")
    print("=" * 50)

    if not os.getenv("GEMINI_API_KEY"):
        print("  ❌ GEMINI_API_KEY not set")
        return

    try:
        import google.generativeai as genai

        # Configure Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # Test with a simple request
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content("Hello, this is a test.")

        if response.text:
            print("  ✅ Gemini API connection successful")
            print(f"  📝 Response preview: {response.text[:100]}...")
        else:
            print("  ❌ Gemini API returned empty response")

    except Exception as e:
        print(f"  ❌ Gemini API connection failed: {e}")


def check_logging():
    """Check logging configuration"""
    print("\n📝 Checking Logging Configuration")
    print("=" * 50)

    try:
        # Setup verbose logging for testing
        setup_verbose_logging()

        from loguru import logger

        logger.info("Test log message - INFO level")
        logger.debug("Test log message - DEBUG level")
        logger.warning("Test log message - WARNING level")
        logger.error("Test log message - ERROR level")

        print("  ✅ Logging test messages sent")
        print("  📄 Check logs/character_generator_verbose.log for details")

    except Exception as e:
        print(f"  ❌ Logging test failed: {e}")


def test_models():
    """Test Pydantic models"""
    print("\n🏗️  Testing Pydantic Models")
    print("=" * 50)

    try:
        from models import CharacterGenerationRequest

        # Test request model
        request = CharacterGenerationRequest(
            brief_description="Test character", genre="fantasy", tone="neutral"
        )
        print("  ✅ CharacterGenerationRequest model works")

        # Test that we can serialize/deserialize
        request_json = request.model_dump_json()
        print(f"  ✅ Request serialization works ({len(request_json)} chars)")

    except Exception as e:
        print(f"  ❌ Model test failed: {e}")


def generate_test_character():
    """Generate a test character to check the full pipeline"""
    print("\n🎭 Testing Character Generation Pipeline")
    print("=" * 50)

    if not os.getenv("GEMINI_API_KEY"):
        print("  ❌ GEMINI_API_KEY not set - skipping character generation test")
        return

    try:
        from character_agent import CharacterAgent
        from models import CharacterGenerationRequest

        # Create a simple test request
        request = CharacterGenerationRequest(
            brief_description="A test character for debugging",
            genre="fantasy",
            tone="neutral",
            num_images=1,
        )

        print("  🔄 Generating test character...")
        agent = CharacterAgent()
        response = agent.generate_character(request)

        if response.success:
            character = response.character
            print(f"  ✅ Test character generated: {character.name}")
            print(f"  📊 Generation time: {response.generation_time:.2f} seconds")
            print(f"  📄 Character age: {character.age}")
            print(f"  📄 Character occupation: {character.background.occupation}")
            print(f"  📄 Images generated: {len(character.images)}")
        else:
            print(f"  ❌ Test character generation failed: {response.error}")

    except Exception as e:
        print(f"  ❌ Character generation test failed: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Run all debugging checks"""
    print("🐛 AI Character Generator - Debugging Tool")
    print("=" * 60)

    # Run all checks
    check_environment()
    check_dependencies()
    test_configuration()
    test_gemini_connection()
    check_logging()
    test_models()
    generate_test_character()

    print("\n" + "=" * 60)
    print("🎉 Debugging complete!")
    print("\n📋 Next steps:")
    print("1. Check the output above for any ❌ errors")
    print("2. Review logs/character_generator_verbose.log for detailed information")
    print("3. If Gemini API tests failed, verify your API key")
    print("4. If dependencies are missing, run: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
