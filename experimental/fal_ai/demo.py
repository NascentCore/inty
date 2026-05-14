#!/usr/bin/env python3
"""
fal.ai Z-Image Turbo 演示脚本
CREATED_BY_AGENT

使用方法:
    # 设置 API Key 环境变量
    export FAL_KEY="your-api-key"

    # 基础用法
    python demo.py "A cute cat sitting on a sofa"

    # 指定参数
    python demo.py "A sunset over mountains" --size landscape_16_9 --num-images 2
"""

import argparse

from client import ZImageTurboClient
from config import ACCELERATION_LEVELS, IMAGE_SIZES, OUTPUT_FORMATS


def main():
    parser = argparse.ArgumentParser(
        description="fal.ai Z-Image Turbo 图像生成演示",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("prompt", type=str, help="生成图像的文本提示")

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="fal.ai API Key（也可通过环境变量 FAL_KEY 设置）",
    )

    parser.add_argument(
        "--size",
        type=str,
        default="landscape_4_3",
        choices=IMAGE_SIZES,
        help="图像尺寸（默认: landscape_4_3）",
    )

    parser.add_argument(
        "--steps",
        type=int,
        default=8,
        help="推理步数（默认: 8）",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="随机种子（可选，用于复现结果）",
    )

    parser.add_argument(
        "--num-images",
        type=int,
        default=1,
        help="生成图像数量（默认: 1）",
    )

    parser.add_argument(
        "--format",
        type=str,
        default="png",
        choices=OUTPUT_FORMATS,
        help="输出格式（默认: png）",
    )

    parser.add_argument(
        "--acceleration",
        type=str,
        default="none",
        choices=ACCELERATION_LEVELS,
        help="加速级别（默认: none）",
    )

    parser.add_argument(
        "--no-safety-check",
        action="store_true",
        help="禁用安全检查",
    )

    parser.add_argument(
        "--expand-prompt",
        action="store_true",
        help="启用提示扩展（会增加费用）",
    )

    args = parser.parse_args()

    print("正在生成图像...")
    print(f"提示词: {args.prompt}")
    print(f"图像尺寸: {args.size}")
    print(f"推理步数: {args.steps}")
    print(f"图像数量: {args.num_images}")
    print("-" * 50)

    client = ZImageTurboClient(api_key=args.api_key)

    result = client.generate(
        prompt=args.prompt,
        image_size=args.size,
        num_inference_steps=args.steps,
        seed=args.seed,
        num_images=args.num_images,
        enable_safety_checker=not args.no_safety_check,
        enable_prompt_expansion=args.expand_prompt,
        output_format=args.format,
        acceleration=args.acceleration,
    )

    print("-" * 50)
    print("生成完成！")
    print(f"使用的种子: {result.seed}")
    print(f"实际提示词: {result.prompt}")
    print()
    print("生成的图像:")
    for i, img in enumerate(result.images, 1):
        print(f"  [{i}] {img.url}")
        print(f"      尺寸: {img.width}x{img.height}")
        print(f"      类型: {img.content_type}")


if __name__ == "__main__":
    main()
