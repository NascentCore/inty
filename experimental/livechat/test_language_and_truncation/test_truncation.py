"""
复现问题2: AI 回复长句子被截断

测试流程:
1. 连接服务端
2. 发送带自然停顿的长句音频 (停顿 > silence_duration_ms=500ms)
3. 对比发送无停顿的同样内容
4. 检查 AI 回复是否被提前截断

Usage:
    python test_truncation.py --token <auth_token> --agent-id <agent_id>
    python test_truncation.py --token xxx --agent-id xxx --base-url ws://localhost:8000
"""

import argparse
import asyncio
from pathlib import Path

from test_utils import (
    IntyLiveChatClient,
    detect_language,
    save_test_report,
    wav_info,
)

TEST_AUDIO_DIR = Path(__file__).resolve().parent / "test_audio"

# 测试场景
TRUNCATION_SCENARIOS = [
    {
        "name": "cn_long_normal",
        "audio": "cn_long.wav",
        "description": "中文长句(自然TTS停顿,停顿<500ms)",
        "expect_truncation": False,
    },
    {
        "name": "cn_long_with_pause",
        "audio": "cn_long_pause.wav",
        "description": "中文长句+600ms人工静音段(触发VAD截断)",
        "expect_truncation": True,
    },
    {
        "name": "en_long_normal",
        "audio": "en_long.wav",
        "description": "英文长句(自然TTS停顿,停顿<500ms)",
        "expect_truncation": False,
    },
    {
        "name": "en_long_with_pause",
        "audio": "en_long_pause.wav",
        "description": "英文长句+600ms人工静音段(触发VAD截断)",
        "expect_truncation": True,
    },
]


def check_truncation(ai_text: str) -> dict:
    """
    检查 AI 回复是否被截断

    启发式检测:
    1. 文本以逗号、省略号等结尾 (未完成)
    2. 文本明显短于预期 (长句回复应该较长)
    3. 文本中有不完整的句子结构
    """
    text = (ai_text or "").strip()
    if not text:
        return {"is_truncated": True, "reason": "空回复", "confidence": "high"}

    # 截断特征
    truncation_markers = [
        text.endswith(","),  # 逗号结尾
        text.endswith("，"),  # 中文逗号结尾
        text.endswith("and"),  # and 结尾
        text.endswith("or"),  # or 结尾
        text.endswith("的"),  # 中文"的"结尾(不完整)
        text.endswith("了"),  # 中文"了"结尾(不完整)
        text.endswith("..."),  # 省略号
        text.endswith("…"),  # 中文省略号
        text.endswith("、"),  # 顿号结尾
        text.endswith("；"),  # 分号结尾
        len(text) < 10,  # 极短回复
    ]

    if any(truncation_markers):
        reasons = []
        if text.endswith(",") or text.endswith("，"):
            reasons.append("逗号结尾(句子未完成)")
        if text.endswith("and") or text.endswith("or"):
            reasons.append(f"连接词结尾: '{text.split()[-1]}'")
        if text.endswith("的") or text.endswith("了"):
            reasons.append(f"助词结尾(句子不完整): '{text[-1]}'")
        if text.endswith("...") or text.endswith("…"):
            reasons.append("省略号结尾")
        if len(text) < 10:
            reasons.append(f"极短回复({len(text)}字符)")

        return {
            "is_truncated": True,
            "reason": "; ".join(reasons),
            "confidence": "high" if len(reasons) > 1 else "medium",
            "text_length": len(text),
        }

    return {
        "is_truncated": False,
        "reason": "正常",
        "confidence": "medium",
        "text_length": len(text),
    }


async def run_scenario(
    client: IntyLiveChatClient,
    scenario: dict,
) -> dict:
    """运行单个截断测试场景"""
    print(f"\n{'='*60}")
    print(f"场景: {scenario['description']}")
    print(f"音频: {scenario['audio']}")
    print(f"期望截断: {scenario['expect_truncation']}")
    print(f"{'='*60}")

    wav_path = TEST_AUDIO_DIR / scenario["audio"]
    if not wav_path.exists():
        print(f"  [SKIP] 音频文件不存在: {wav_path}")
        return {"error": "audio_not_found"}

    info = wav_info(wav_path)
    print(
        f"  音频时长: {info['duration_ms']:.0f}ms, 采样率: {info['sample_rate']}Hz"
    )

    await client.send_audio_wav(wav_path)
    ai_text = await client.wait_for_turn_complete(timeout=30.0)

    if not ai_text:
        print(f"  [WARNING] 未收到 AI 回复")
        return {"error": "no_response"}

    result = check_truncation(ai_text)
    print(f"\n  AI 回复 ({len(ai_text)} 字符):")
    print(f"  {ai_text[:200]}{'...' if len(ai_text) > 200 else ''}")
    print(
        f"\n  截断检测: {'[TRUNCATED]' if result['is_truncated'] else '[OK]'} "
        f"({result['reason']}, 置信度: {result['confidence']})"
    )

    if scenario["expect_truncation"] and not result["is_truncated"]:
        print(f"  [INFO] 期望截断但未检测到(可能静音段不够长)")
    elif not scenario["expect_truncation"] and result["is_truncated"]:
        print(f"  [FAIL] 不期望截断但检测到截断!")

    return result


async def main():
    parser = argparse.ArgumentParser(description="复现长句截断问题")
    parser.add_argument("--token", required=True, help="认证 token")
    parser.add_argument("--agent-id", required=True, help="Agent ID")
    parser.add_argument(
        "--base-url", default="ws://localhost:8000", help="服务端地址"
    )
    parser.add_argument(
        "--language", default="Chinese", help="回复语言 (默认: Chinese)"
    )
    args = parser.parse_args()

    # 检查音频文件
    missing = [
        s["audio"]
        for s in TRUNCATION_SCENARIOS
        if not (TEST_AUDIO_DIR / s["audio"]).exists()
    ]
    if missing:
        print(f"缺少测试音频文件: {missing}")
        print("请先运行 generate_test_audio.py")
        return

    all_results = {}

    for scenario in TRUNCATION_SCENARIOS:
        client = IntyLiveChatClient(
            base_url=args.base_url,
            token=args.token,
            agent_id=args.agent_id,
            response_language_name=args.language,
        )

        print(f"\n连接服务端: {client.ws_url}")
        if not await client.connect():
            print("连接失败!")
            continue

        try:
            result = await run_scenario(client, scenario)
            all_results[scenario["name"]] = {
                "scenario": scenario["description"],
                "audio": scenario["audio"],
                "expect_truncation": scenario["expect_truncation"],
                "result": result,
            }
        finally:
            await client.send_end()
            await asyncio.sleep(1)
            await client.disconnect()

        # 每个场景之间等待一下
        await asyncio.sleep(2)

    # 汇总
    print(f"\n{'='*60}")
    print(f"截断测试汇总:")
    print(f"{'='*60}")

    false_positives = []
    false_negatives = []

    for name, r in all_results.items():
        result = r.get("result", {})
        is_truncated = result.get("is_truncated", False)
        expected = r["expect_truncation"]

        status = "OK"
        if expected and not is_truncated:
            status = "MISS (期望截断但未检测到)"
            false_negatives.append(name)
        elif not expected and is_truncated:
            status = "FAIL (不期望截断但检测到)"
            false_positives.append(name)

        print(f"  {name}: {status} - {r['scenario']}")

    if false_positives:
        print(f"\n  [WARNING] 误报截断(不期望截断但检测到): {false_positives}")
    if false_negatives:
        print(
            f"\n  [INFO] 漏报截断(期望截断但未检测到,可能静音段不够): {false_negatives}"
        )

    # 保存最后一个场景的日志作为示例
    save_test_report(
        "truncation",
        client.log,
        extra={
            "config": {
                "response_language_name": args.language,
                "agent_id": args.agent_id,
            },
            "scenarios": all_results,
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
