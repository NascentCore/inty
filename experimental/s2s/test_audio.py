#!/usr/bin/env python3
"""
Simple audio test using sounddevice
"""

import numpy as np
import sounddevice as sd


def test_audio_devices():
    """Test and list available audio devices."""
    print("🎵 Audio Device Test")
    print("=" * 40)

    # List all devices
    devices = sd.query_devices()
    print(f"Found {len(devices)} audio devices:")

    for i, device in enumerate(devices):
        print(f"\n{i}: {device['name']}")
        print(f"   Inputs: {device.get('max_inputs', 0)}")
        print(f"   Outputs: {device.get('max_outputs', 0)}")
        print(
            f"   Default Sample Rate: {device.get('default_samplerate', 'N/A')}"
        )

    # Find default devices
    default_input = sd.query_devices(kind="input")
    default_output = sd.query_devices(kind="output")

    print(f"\n📱 Default Input: {default_input['name']}")
    print(f"🔊 Default Output: {default_output['name']}")

    return default_input, default_output


def test_microphone(duration=3):
    """Test microphone recording."""
    print(f"\n🎤 Testing microphone for {duration} seconds...")
    print("Speak now!")

    try:
        # Record audio
        sample_rate = 24000  # OpenAI's required rate
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32,
        )
        sd.wait()

        # Check if we got any audio
        if np.any(recording):
            print("✅ Microphone test successful!")
            print(f"   Recorded {len(recording)} samples")
            print(f"   Max amplitude: {np.max(np.abs(recording)):.3f}")
        else:
            print("⚠️  No audio detected - check microphone permissions")

        return recording

    except Exception as e:
        print(f"❌ Microphone test failed: {e}")
        return None


def test_speakers():
    """Test speaker playback."""
    print("\n🔊 Testing speakers...")

    try:
        # Generate a simple test tone
        sample_rate = 24000
        duration = 1.0
        frequency = 440  # A4 note

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = 0.3 * np.sin(2 * np.pi * frequency * t)

        # Play the tone
        sd.play(tone, sample_rate)
        sd.wait()

        print("✅ Speaker test successful!")
        return True

    except Exception as e:
        print(f"❌ Speaker test failed: {e}")
        return False


def main():
    """Run all audio tests."""
    print("🧪 Audio System Test")
    print("=" * 50)

    # Test devices
    input_device, output_device = test_audio_devices()

    # Test microphone
    recording = test_microphone()

    # Test speakers
    speakers_ok = test_speakers()

    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Input Device: {input_device['name']}")
    print(f"   Output Device: {output_device['name']}")
    print(f"   Microphone: {'✅ OK' if recording is not None else '❌ Failed'}")
    print(f"   Speakers: {'✅ OK' if speakers_ok else '❌ Failed'}")

    if recording is not None and speakers_ok:
        # Play out the recording
        sample_rate = 24000
        sd.play(recording, sample_rate)
        sd.wait()
        hear_recording = input("Did you hear the recording? Y/N: ")
        if hear_recording == "Y":
            print("✅ You heard the recording!")
        else:
            print("❌ You did not hear the recording!")

        print("\n🎉 Audio system is ready for the speech-to-speech demo!")
        print("You can now run: python simple_s2s_demo.py")
    else:
        print("\n⚠️  Some audio tests failed. Please check:")
        print("   1. Microphone permissions in System Preferences")
        print("   2. Microphone is not muted")
        print("   3. Speakers/headphones are connected")


if __name__ == "__main__":
    main()
