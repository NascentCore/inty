import enum
import os
import time
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings, play

load_dotenv()
print(os.getenv("ELEVENLABS_API_KEY"))
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

MP3_22KHZ_32KBPS = "mp3_22050_32"
MODEL_ID = "eleven_flash_v2_5"
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
#十一V3风格prompting[热心]您好！不适用于其他型号。
#更多控制机制请参见：
# https://elevenlabs.io/docs/best-practices/prompting/controls
# 在线问题描述可以自然地提供语音播报的情感，比如：
TEXT = """
Her voice trembling with sadness "You're leaving?"
He exclaimed triumphantly "That's it!"
"""


class LatencyOptimizationLevel(enum.IntEnum):
    DEFAULT = 0  # No latency optimizations
    NORMAL = 1  # Normal latency optimizations
    STRONG = 2  # Strong latency optimizations
    MAX = 3  # Max latency optimizations
    MAX_WITH_TEXT_NORMALIZER = 4  # Max latency optimizations, but also with text normalizer turned off for even more latency savings (best latency, but can mispronounce eg numbers and dates).


voice_settings = VoiceSettings(
# 值越低意味着声音变得更加动态性和随机性。
# 最强的值会导致声音单调。
    stability=0.5,
# 与声音克隆中的原始接收器相比，风格夸张。
    style=1.0,
#越来越快。
    speed=1.2,
)


def get_file_suffix(
    voice_id: str,
    model_id: str,
    output_format: str,
    latency_optimization_level: LatencyOptimizationLevel,
    voice_settings: VoiceSettings,
) -> str:
    return f"voice_id:{voice_id}-model_id:{model_id}-output_format:{output_format}-latency_optimization_level:{latency_optimization_level}-voice_settings:{voice_settings}"


start_time = time.time()
audio_stream = client.text_to_speech.convert(
    text=TEXT,
    voice_id=VOICE_ID,
    model_id=MODEL_ID,
    output_format=MP3_22KHZ_32KBPS,
    optimize_streaming_latency=LatencyOptimizationLevel.MAX_WITH_TEXT_NORMALIZER,
    voice_settings=voice_settings,
)
audio_bytes = b"".join(audio_stream)
end_time = time.time()
print(f"Time taken: {end_time - start_time} seconds")


with open(
    f"output-{get_file_suffix(VOICE_ID, MODEL_ID, MP3_22KHZ_32KBPS, LatencyOptimizationLevel.MAX_WITH_TEXT_NORMALIZER, voice_settings)}.mp3",
    "wb",
) as f:
    f.write(audio_bytes)

play(audio_bytes)
