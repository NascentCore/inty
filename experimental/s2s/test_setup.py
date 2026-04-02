#!/usr/bin/env python3
"""
Test script to verify setup for OpenAI Speech-to-Speech Demo
"""

import os
import sys

from dotenv import load_dotenv


def test_imports():
    """Test if all required packages can be imported."""
    print("🔍 Testing imports...")

    import openai  # noqa: F401

    print("✅ openai - OK")

    import sounddevice  # noqa: F401

    print("✅ sounddevice - OK")

    import numpy  # noqa: F401

    print("✅ numpy - OK")

    return True


def test_audio_devices():
    """Test if audio devices are available."""
    print("\n🎵 Testing audio devices...")

    try:
        import sounddevice as sd

        # List available devices
        devices = sd.query_devices()
        print(f"Found {len(devices)} audio devices")

        # Get default devices (this is more reliable)
        try:
            default_input = sd.query_devices(kind="input")
            default_output = sd.query_devices(kind="output")

            print(f"✅ Default Input: {default_input['name']}")
            print(f"✅ Default Output: {default_output['name']}")
            return True
        except Exception as e:
            print(f"❌ Error getting default devices: {e}")
            return False

        return True

    except Exception as e:
        print(f"❌ Error testing audio devices: {e}")
        return False


def test_openai_api():
    """Test OpenAI API key and connectivity."""
    print("\n🔑 Testing OpenAI API...")
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("   Fix: copy .env.example to .env and fill OPENAI_API_KEY")
        return False
    if api_key == "YOUR_OPENAI_API_KEY_HERE":
        print("❌ OPENAI_API_KEY is still placeholder value")
        print("   Fix: replace placeholder in .env with a real key")
        return False

    if len(api_key) < 20:
        print("❌ API key seems too short")
        return False

    print(f"✅ API key found (length: {len(api_key)})")

    # Test basic API connectivity
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        # Try a simple API call to test connectivity
        response = client.models.list()
        print("✅ OpenAI API connectivity - OK")
        return True

    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 OpenAI Speech-to-Speech Demo - Setup Test")
    print("=" * 50)

    all_tests_passed = True

    # Test imports
    if not test_imports():
        all_tests_passed = False

    # Test audio devices
    if not test_audio_devices():
        all_tests_passed = False

    # Test OpenAI API
    if not test_openai_api():
        all_tests_passed = False

    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 All tests passed! You're ready to run the demo.")
        print("\nTo start the demo:")
        print("  python main.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  1. Install missing packages: pip install -r requirements.txt")
        print("  2. Set your API key: export OPENAI_API_KEY='your-key'")
        print("  3. Check microphone permissions")
        sys.exit(1)


if __name__ == "__main__":
    main()
