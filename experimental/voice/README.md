# TTS（文本转语音）演示

## 双子座`uv run --no-project gemini.py`您可能需要安装额外的依赖项。这会写出一个`.wav`可以播放的文件。

官方示例代码
<img width="380" height="358" alt="image" src="https://github.com/user-attachments/assets/ed3b97fe-0e2c-49ef-8bda-2b588b5d5a34" />

## ElevenLabs 演示

使用 ElevenLabs API 将文本转换为语音。```bash
# Copy API Key from https://tricorder.feishu.cn/wiki/ToKJwUzKiicUf6kZOugcjRbZnih
cp .env.example .env
brew install ffmpeg
python -m venv .venv
pip install -r requirements.txt
python tts/elevenlabs.py
```延迟大约1秒。还不错。

<https://elevenlabs.io/v3>的演示，您可以通过标记来影响语音模式。

！[图片](https://github.com/user-attachments/assets/3a2963a4-deb6-4451-8562-e4edb591bd68)

### 无效库

https://elevenlabs.io/app/voice-library

<img width="3022" height="1804" alt="image" src="https://github.com/user-attachments/assets/bf055def-3f5b-4e8e-aebf-33d6b23eb296" />

### 音频格式

在 11albs SDK 上使用以下 prompt 生成游标
音频格式列表：```text
What's the differences between these audio format?
```MP3 格式：

- **mp3_22050_32**：22.05 kHz 采样率，32 kbps 比特率 - 质量较低，文件大小较小
- **mp3_44100_32**：44.1 kHz 采样率，32 kbps 比特率 - CD 质量采样率，但比特率低
- **mp3_44100_64**：44.1 kHz 采样率，64 kbps 比特率 - 质量优于 32 kbps
- **mp3_44100_96**：44.1 kHz 采样率，96 kbps 比特率 - 对于大多数用例而言质量良好
- **mp3_44100_128**：44.1 kHz 采样率，128 kbps 比特率 - 标准质量，广泛兼容
- **mp3_44100_192**：44.1 kHz 采样率，192 kbps 比特率 - 高品质，较大文件大小

PCM 格式 (Uncompressed)：

- **pcm_8000**：8 kHz 采样率 - 电话质量，非常小的文件- **pcm_16000**：16 kHz 采样率 - 比电话更好，适合语音
- **pcm_22050**：22.05 kHz 采样率 - 网络音频标准
- **pcm_24000**：24 kHz 采样率 - 适合语音应用
- **pcm_44100**：44.1 kHz 采样率 - CD 质量，uncompressed
- **pcm_48000**：48 kHz 采样率 - Professional 音频质量

Compressed 格式：

- **ulaw_8000**：μ-law compression at 8 kHz - 电话标准
- **alaw_8000**：A-law compression at 8 kHz - 欧洲电话标准

Opus 格式（现代、高效）：

- **opus_48000_32**：48 kHz 采样率，32 kbps - 非常高效的 compression- **opus_48000_64**：48 kHz 采样率，64 kbps - 质量好，尺寸小
- **opus_48000_96**：48 kHz 采样率，96 kbps - 高品质
- **opus_48000_128**：48 kHz 采样率，128 kbps - 卓越的品质
- **opus_48000_192**：48 kHz 采样率，192 kbps - 最高质量

建议：

- **对于网络/语音**：`mp3_22050_32`（您当前的选择）- 质量和尺寸的良好平衡
- **为了高品质**：`mp3_44100_128` or `opus_48000_128`- **为了最大程度的兼容性**：`mp3_44100_128`- **对于最小文件大小**：`opus_48000_32`- **对于pr专业用途**：`pcm_48000`（uncompressed，最大的文件）

目前的选择`mp3_22050_32`对于语音应用程序来说非常好，因为它 pr 提供足够的质量，同时保持文件大小较小！