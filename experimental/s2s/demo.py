from __future__ import annotations

import base64
import asyncio
from typing import Any, cast

from audio_util import CHANNELS, SAMPLE_RATE, AudioPlayerAsync
from openai import AsyncOpenAI
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection


async def main():
    client = AsyncOpenAI()
    audio_player = AudioPlayerAsync()
    last_audio_item_id: str | None = None
    connection_ready = asyncio.Event()
    connection: AsyncRealtimeConnection | None = None

    async def handle_realtime_connection():
        nonlocal connection, last_audio_item_id
        async with client.beta.realtime.connect(
            model="gpt-4o-realtime-preview"
        ) as conn:
            connection = conn
            connection_ready.set()
# 启用服务器端语音活动检测
            await conn.session.update(
                session={"turn_detection": {"type": "server_vad"}}
            )

            acc_items: dict[str, Any] = {}

            async for event in conn:
                if event.type == "session.created":
                    session = event.session
                    print(f"Session created: {session.id}")
                    continue

                if event.type == "session.updated":
                    session = event.session
                    continue

                if event.type == "response.audio.delta":
                    if event.item_id != last_audio_item_id:
                        audio_player.reset_frame_count()
                        last_audio_item_id = event.item_id

                    bytes_data = base64.b64decode(event.delta)
                    audio_player.add_data(bytes_data)
                    continue

                if event.type == "response.audio_transcript.delta":
                    try:
                        text = acc_items[event.item_id]
                    except KeyError:
                        acc_items[event.item_id] = event.delta
                    else:
                        acc_items[event.item_id] = text + event.delta

                    print(f"AI: {acc_items[event.item_id]}", end="", flush=True)
                    continue

    async def send_mic_audio():
        import sounddevice as sd

        print("Starting audio recording...")
        print("Press Ctrl+C to stop")

        device_info = sd.query_devices()
        print(f"Using audio device: {device_info}")

        read_size = int(SAMPLE_RATE * 0.02)

        stream = sd.InputStream(
            channels=CHANNELS,
            samplerate=SAMPLE_RATE,
            dtype="int16",
        )
        stream.start()
# 等待连接准备好
        await connection_ready.wait()

        try:
            while True:
                if stream.read_available < read_size:
                    await asyncio.sleep(0)
                    continue

                data, _ = stream.read(read_size)
# 向连接发送音频数据
                if connection:
                    await connection.input_audio_buffer.append(
                        audio=base64.b64encode(cast(Any, data)).decode("utf-8")
                    )

                await asyncio.sleep(0)
        except KeyboardInterrupt:
            print("\nStopping recording...")
        finally:
            stream.stop()
            stream.close()
# 启动两个任务
    connection_task = asyncio.create_task(handle_realtime_connection())
    audio_task = asyncio.create_task(send_mic_audio())

    try:
# 等待两个任务完成
        await asyncio.gather(connection_task, audio_task)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())
