# Live Chat 语言混用 & 长句截断 问题复现

## 环境准备

```bash
pip install edge-tts websockets
```

## 步骤

### 1. 生成测试音频

```bash
python generate_test_audio.py
```

### 2. 获取认证 token

通过 inty-backend 的登录接口获取 token,或从调试工具中复制。

### 3. 启动服务端

确保 inty-backend 服务在本地运行(默认 `ws://localhost:8000`)。

### 4. 复现语言混用问题

```bash
python test_language_mixing.py \
  --token "<your_token>" \
  --agent-id "<agent_id>" \
  --language "Chinese"
```

### 5. 复现长句截断问题

```bash
python test_truncation.py \
  --token "<your_token>" \
  --agent-id "<agent_id>" \
  --language "Chinese"
```

## 测试音频说明

| 文件 | 内容 | 用途 |
|------|------|------|
| `cn_short.wav` | 短中文问候 | 语言混用: 中文基线 |
| `en_short.wav` | 短英文问候 | 语言混用: 切换为英文 |
| `cn_mixed.wav` | 中英混合句子 | 语言混用: 混合输入 |
| `cn_long.wav` | 中文长句(TTS自然停顿) | 截断: 正常停顿基线 |
| `cn_long_pause.wav` | 中文长句+600ms静音 | 截断: 触发VAD |
| `en_long.wav` | 英文长句(TTS自然停顿) | 截断: 正常停顿基线 |
| `en_long_pause.wav` | 英文长句+600ms静音 | 截断: 触发VAD |
| `cn_turn1/2/3.wav` | 多轮语言切换 | 语言混用: 多轮测试 |

## 测试报告

结果保存在 `test_results/` 目录,JSON 格式。
