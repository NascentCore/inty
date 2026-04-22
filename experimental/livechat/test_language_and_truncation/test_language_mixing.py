"""
复现问题1: AI 回复中英文混用

测试流程:
1. 连接服务端,指定 response_language_name="Chinese"
2. 依次发送中文、英文、中英混合音频
3. 检查 AI 回复是否始终使用中文(不混用英文)

Usage:
    python test_language_mixing.py --token <auth_token> --agent-id <agent_id>
    python test_language_mixing.py --token xxx --agent-id xxx --base-url ws://localhost:8000
"""

import argparse
import asyncio
from pathlib import Path

from test_utils import (
    IntyLiveChatClient,
    check_language_mixing,
    detect_language,
    save_test_report,
    wav_info,
)

TEST_AUDIO_DIR = Path(__file__).resolve().parent / "test_audio"

# 测试场景: 多轮对话中切换语言,期望 AI 始终使用配置的语言
LANGUAGE_MIXING_SCENARIOS = [
    {
        "name": "cn_only",
        "audio": ["cn_short.wav"],
        "expected_language": "zh",
        "description": "纯中文输入",
    },
    {
        "name": "cn_then_en",
        "audio": ["cn_short.wav", "en_short.wav"],
        "expected_language": "zh",
        "description": "先中文后英文,期望AI始终用中文回复",
    },
    {
        "name": "cn_mixed_input",
        "audio": ["cn_mixed.wav"],
        "expected_language": "zh",
        "description": "中英混合输入,期望AI用中文回复",
    },
    {
        "name": "multi_turn_switch",
        "audio": ["cn_turn1.wav", "en_turn2.wav", "cn_turn3.wav"],
        "expected_language": "zh",
        "description": "多轮语言切换,期望AI不跟随切换",
    },
]


async def run_scenario(
    client: IntyLiveChatClient,
    scenario: dict,
    wait_between_turns: float = 5.0,
) -> dict:
    """运行单个测试场景"""
    print(f"\n{'='*60}")
    print(f"场景: {scenario['description']}")
    print(f"期望语言: {scenario['expected_language']}")
    print(f"{'='*60}")

    for i, audio_file in enumerate(scenario["audio"]):
        wav_path = TEST_AUDIO_DIR / audio_file
        if not wav_path.exists():
            print(f"  [SKIP] 音频文件不存在: {wav_path}")
            continue

        info = wav_info(wav_path)
        print(f"\n  第{i+1}轮: {audio_file} ({info['duration_ms']:.0f}ms)")

        await client.send_audio_wav(wav_path)
        ai_text = await client.wait_for_turn_complete(timeout=30.0)

        if ai_text:
            detected = detect_language(ai_text)
            print(f"  检测到语言: {detected}")
            if detected != scenario["expected_language"] and detected != "mixed":
                print(
                    f"  [WARNING] 语言不匹配! 期望 {scenario['expected_language']}, 实际 {detected}"
                )
        else:
            print(f"  [WARNING] 未收到 AI 回复")

        if i < len(scenario["audio"]) - 1:
            print(f"  等待 {wait_between_turns}s 后进入下一轮...")
            await asyncio.sleep(wait_between_turns)

    return {}


async def main():
    parser = argparse.ArgumentParser(description="复现语言混用问题")
    parser.add_argument("--token", required=True, help="认证 token")
    parser.add_argument("--agent-id", required=True, help="Agent ID")
    parser.add_argument("--base-url", default="ws://localhost:8000", help="服务端地址")
    parser.add_argument(
        "--language", default="Chinese", help="期望的回复语言 (默认: Chinese)"
    )
    parser.add_argument(
        "--speech-code", default=None, help="BCP-47 语音代码 (如 zh-CN)"
    )
    args = parser.parse_args()

    # 检查音频文件
    missing = [
        s["audio"]
        for s in LANGUAGE_MIXING_SCENARIOS
        for a in s["audio"]
        if not (TEST_AUDIO_DIR / a).exists()
    ]
    if missing:
        print("缺少测试音频文件，请先运行 generate_test_audio.py")
        return

    client = IntyLiveChatClient(
        base_url=args.base_url,
        token=args.token,
        agent_id=args.agent_id,
        speech_language_code=args.speech_code,
        response_language_name=args.language,
    )

    print(f"连接服务端: {client.ws_url}")
    if not await client.connect():
        print("连接失败!")
        return

    print(f"已连接, response_language_name={args.language}")

    try:
        for scenario in LANGUAGE_MIXING_SCENARIOS:
            await run_scenario(client, scenario)

    finally:
        await client.send_end()
        await asyncio.sleep(1)
        await client.disconnect()

    # 分析结果
    result = check_language_mixing(client.log.transcripts)
    print(f"\n{'='*60}")
    print(f"语言混用检测结果:")
    print(f"  {result['summary']}")
    for turn in result["mixed_turns"]:
        print(f"  - [{turn['role']}] {turn['text'][:100]}...")

    # 保存报告
    save_test_report(
        "language_mixing",
        client.log,
        extra={
            "config": {
                "response_language_name": args.language,
                "speech_language_code": args.speech_code,
                "agent_id": args.agent_id,
            },
            "analysis": result,
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
