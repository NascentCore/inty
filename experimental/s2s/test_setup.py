#！/usr/bin/env python3
"""
Test script to verify setup for OpenAI Speech-to-Speech Demo
"""

import os
import sys


def test_imports():
    """Test if all required packages can be imported."""
    print("🔍 Testing imports...")

    try:
        import openai  # noqa: F401

        print("✅ openai - OK")
    except ImportError:
        print("❌ openai - NOT FOUND")
        return False

    try:
        import sounddevice  # noqa: F401

        print("✅ sounddevice - OK")
    except ImportError:
        print("❌ sounddevice - NOT FOUND")
        return False

    try:
        import numpy  # noqa: F401

        print("✅ numpy - OK")
    except ImportError:
        print("❌ numpy - NOT FOUND")
        return False

    return True


def test_audio_devices():
    """Test if audio devices are available."""
    print("\n🎵 Testing audio devices...")

    try:
        import sounddevice as sd
# 可用的上市设备
        devices = sd.query_devices()
        print(f"Found {len(devices)} audio devices")
# 获取默认设备（这样更可靠）
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

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your-api-key-here'")
        return False

    if len(api_key) < 20:
        print("❌ API key seems too short")
        return False

    print(f"✅ API key found (length: {len(api_key)})")
# 基本测试API连接
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
# 尝试一个简单的 API 调用来测试连接
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
# 测试导入
    if not test_imports():
        all_tests_passed = False
#音频测试设备
    if not test_audio_devices():
        all_tests_passed = False
# 测试 OpenAI API
    if not test_openai_api():
        all_tests_passed = False

    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 All tests passed! You're ready to run the demo.")
        print("\nTo start the demo:")
        print("  python simple_s2s_demo.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  1. Install missing packages: pip install -r requirements.txt")
        print("  2. Set your API key: export OPENAI_API_KEY='your-key'")
        print("  3. Check microphone permissions")
        sys.exit(1)


if __name__ == "__main__":
    main()
