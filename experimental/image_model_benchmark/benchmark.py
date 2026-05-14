# CREATED_BY_AGENT
"""
图像生成模型评测 CLI 工具

Usage:
    python benchmark.py run --all
    python benchmark.py run --model seedream
    python benchmark.py run --scenario edit_appearance
    python benchmark.py list-models
    python benchmark.py list-scenarios
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import cyclopts
from config import MODELS, BenchmarkConfig, ModelConfig, get_config
from models.base import ImageGenerationResult, ImageModel
from models.dashscope import QwenImageEditModel
from models.openrouter import FluxModel, SeedreamModel
from models.vertexai import GeminiFlashImageModel, NanoBananaProModel
from rich.console import Console
from rich.table import Table
from scenarios import (
    Scenario,
    ScenarioType,
    ScenarioVariant,
    get_all_scenarios,
    get_scenario,
    load_test_images,
)

app = cyclopts.App(
    name="image-benchmark",
    help="图像生成模型评测工具",
)
console = Console()


def create_model(model_config: ModelConfig, config: BenchmarkConfig) -> ImageModel:
    """根据配置创建模型实例"""
    if model_config.name == "seedream":
        if not config.openrouter_api_key:
            raise ValueError("需要设置 OPENROUTER_API_KEY 环境变量")
        return SeedreamModel(api_key=config.openrouter_api_key)
    elif model_config.name == "flux":
        if not config.openrouter_api_key:
            raise ValueError("需要设置 OPENROUTER_API_KEY 环境变量")
        return FluxModel(api_key=config.openrouter_api_key)
    elif model_config.name == "gemini-flash":
        if not config.gcp_credentials_path:
            raise ValueError("需要设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量")
        return GeminiFlashImageModel(
            credentials_path=config.gcp_credentials_path,
            project_id=config.gcp_project_id,
            location=config.gcp_location,
        )
    elif model_config.name == "nano-banana":
        if not config.gcp_credentials_path:
            raise ValueError("需要设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量")
        return NanoBananaProModel(
            credentials_path=config.gcp_credentials_path,
            project_id=config.gcp_project_id,
            location=config.gcp_location,
        )
    elif model_config.name == "qwen-image-edit":
        if not config.dashscope_api_key:
            raise ValueError("需要设置 DASHSCOPE_API_KEY 环境变量")
        return QwenImageEditModel(api_key=config.dashscope_api_key)
    else:
        raise ValueError(f"未知模型: {model_config.name}")


async def run_single_benchmark(
    model: ImageModel,
    scenario: Scenario,
    variant: ScenarioVariant,
    test_images: list[bytes],
) -> ImageGenerationResult:
    """运行单个评测"""
    prompt = scenario.get_prompt(variant)
    console.print(f"  [dim]Prompt: {prompt[:80]}...[/dim]")

    result = await model.generate(
        prompt=prompt,
        reference_images=test_images,
    )

    return result


def save_result_image(
    result: ImageGenerationResult,
    output_dir: Path,
    model_name: str,
    scenario_name: str,
    variant_name: str,
) -> Optional[Path]:
    """保存生成的图片"""
    if not result.success or not result.image_data:
        return None

    # 创建文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{model_name}_{scenario_name}_{variant_name}_{timestamp}.jpg"
    filepath = output_dir / filename

    with open(filepath, "wb") as f:
        f.write(result.image_data)

    return filepath


def print_results_table(
    results: list[tuple[str, str, str, ImageGenerationResult]],
    scenario_name: str,
    variant_name: str,
) -> None:
    """打印结果表格"""
    table = Table(
        title=f"评测结果: {scenario_name} - {variant_name}",
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("模型", style="cyan", width=20)
    table.add_column("耗时(ms)", justify="right", width=12)
    table.add_column("大小(KB)", justify="right", width=10)
    table.add_column("状态", justify="center", width=8)
    table.add_column("错误信息", width=30)

    for model_name, _, _, result in results:
        status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
        time_str = f"{result.total_time_ms:,.0f}"
        size_str = f"{result.image_size_kb:.1f}" if result.success else "-"
        error_str = (
            result.error_message[:27] + "..."
            if result.error_message and len(result.error_message) > 30
            else (result.error_message or "")
        )

        table.add_row(model_name, time_str, size_str, status, error_str)

    console.print(table)


@app.command()
def report(
    results_dir: Annotated[str, cyclopts.Parameter(name=["--dir", "-d"])],
    output: Annotated[str, cyclopts.Parameter(name=["--output", "-o"])] = "report.md",
) -> None:
    """
    从结果目录生成 Markdown 报告

    Args:
        results_dir: 结果目录路径（包含 results.json）
        output: 输出文件名（默认 report.md）
    """
    results_path = Path(results_dir)
    json_path = results_path / "results.json"

    if not json_path.exists():
        console.print(f"[red]找不到结果文件: {json_path}[/red]")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    if not results:
        console.print("[red]结果文件为空[/red]")
        return

    # 生成报告
    report_content = _generate_markdown_report(results, results_path)

    # 保存报告
    output_path = results_path / output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    console.print(f"[green]报告已生成: {output_path}[/green]")


def _generate_markdown_report(results: list[dict], results_dir: Path) -> str:
    """生成 Markdown 报告内容"""
    lines: list[str] = []

    # 标题
    timestamp = results[0].get("timestamp", "")[:10] if results else ""
    lines.append("# 图像生成模型评测报告")
    lines.append("")
    lines.append(f"**评测时间**: {timestamp}")
    lines.append("")

    # 汇总统计
    lines.append("## 汇总结果")
    lines.append("")

    # 按模型分组统计
    model_stats: dict[str, dict] = {}
    for r in results:
        model_name = r.get("model_name", r.get("model", ""))
        if model_name not in model_stats:
            model_stats[model_name] = {
                "total_time": [],
                "success_count": 0,
                "total_count": 0,
                "image_sizes": [],
            }
        stats = model_stats[model_name]
        stats["total_count"] += 1
        if r.get("success"):
            stats["success_count"] += 1
            stats["total_time"].append(r.get("total_time_ms", 0))
            stats["image_sizes"].append(r.get("image_size_kb", 0))

    # 汇总表格
    lines.append("| 模型 | 平均耗时 | 成功率 | 平均图片大小 |")
    lines.append("|------|---------|--------|-------------|")

    # 按平均耗时排序
    sorted_models = sorted(
        model_stats.items(),
        key=lambda x: (
            (sum(x[1]["total_time"]) / len(x[1]["total_time"]))
            if x[1]["total_time"]
            else float("inf")
        ),
    )

    for model_name, stats in sorted_models:
        avg_time = (
            sum(stats["total_time"]) / len(stats["total_time"])
            if stats["total_time"]
            else 0
        )
        success_rate = (
            stats["success_count"] / stats["total_count"] * 100
            if stats["total_count"]
            else 0
        )
        avg_size = (
            sum(stats["image_sizes"]) / len(stats["image_sizes"])
            if stats["image_sizes"]
            else 0
        )

        time_str = f"{avg_time/1000:.1f}s" if avg_time else "-"
        rate_str = f"{success_rate:.0f}%"
        size_str = f"{avg_size:.0f}KB" if avg_size else "-"

        lines.append(f"| {model_name} | {time_str} | {rate_str} | {size_str} |")

    lines.append("")

    # 按场景和变体分组
    scenarios: dict[str, dict[str, list[dict]]] = {}
    for r in results:
        scenario = r.get("scenario", "")
        variant = r.get("variant", "")
        if scenario not in scenarios:
            scenarios[scenario] = {}
        if variant not in scenarios[scenario]:
            scenarios[scenario][variant] = []
        scenarios[scenario][variant].append(r)

    # 场景名称映射
    scenario_names = {
        "edit_appearance": "修改外观",
        "two_persons_dance": "双人跳舞",
    }

    # 详细结果
    lines.append("## 详细结果")
    lines.append("")

    for scenario, variants in scenarios.items():
        scenario_display = scenario_names.get(scenario, scenario)
        lines.append(f"### 场景: {scenario_display}")
        lines.append("")

        for variant, variant_results in variants.items():
            lines.append(f"#### 变体: {variant}")
            lines.append("")

            # 结果表格
            lines.append("| 模型 | 耗时 | 大小 | 状态 |")
            lines.append("|------|------|------|------|")

            for r in variant_results:
                model_name = r.get("model_name", r.get("model", ""))
                time_ms = r.get("total_time_ms", 0)
                size_kb = r.get("image_size_kb", 0)
                success = r.get("success", False)

                time_str = f"{time_ms/1000:.1f}s"
                size_str = f"{size_kb:.0f}KB" if success else "-"
                status = "✓" if success else "✗"

                lines.append(f"| {model_name} | {time_str} | {size_str} | {status} |")

            lines.append("")

            # 图片展示
            lines.append("**生成结果对比:**")
            lines.append("")

            # 查找对应的图片文件
            for r in variant_results:
                if not r.get("success"):
                    continue
                model = r.get("model", "")
                model_name = r.get("model_name", model)

                # 查找匹配的图片文件
                pattern = f"{model}_{scenario}_{variant}_*.jpg"
                matching_files = list(results_dir.glob(pattern))
                if matching_files:
                    img_file = matching_files[0].name
                    lines.append(f"**{model_name}**")
                    lines.append("")
                    lines.append(f"![{model_name}]({img_file})")
                    lines.append("")

            lines.append("---")
            lines.append("")

    # 结论
    lines.append("## 结论")
    lines.append("")

    if sorted_models:
        fastest_model = sorted_models[0][0]
        lines.append(f"根据本次评测，**{fastest_model}** 在响应速度方面表现最佳。")
        lines.append("")

    return "\n".join(lines)


@app.command()
def list_models() -> None:
    """列出所有支持的模型"""
    table = Table(title="支持的模型", show_header=True, header_style="bold blue")
    table.add_column("名称", style="cyan")
    table.add_column("显示名称")
    table.add_column("Model ID")
    table.add_column("Provider")

    for name, config in MODELS.items():
        table.add_row(name, config.display_name, config.model_id, config.provider.value)

    console.print(table)


@app.command()
def list_scenarios() -> None:
    """列出所有测试场景"""
    table = Table(title="测试场景", show_header=True, header_style="bold blue")
    table.add_column("类型", style="cyan")
    table.add_column("名称")
    table.add_column("描述")
    table.add_column("所需图片")
    table.add_column("变体数")

    for scenario in get_all_scenarios():
        table.add_row(
            scenario.type.value,
            scenario.name,
            scenario.description,
            ", ".join(scenario.required_images),
            str(len(scenario.variants)),
        )

    console.print(table)

    console.print("\n[bold]场景变体详情:[/bold]")
    for scenario in get_all_scenarios():
        console.print(f"\n[cyan]{scenario.name}[/cyan]:")
        for variant in scenario.variants:
            console.print(f"  - {variant.name}: {variant.description}")


@app.command()
def run(
    all_models: Annotated[bool, cyclopts.Parameter(name=["--all", "-a"])] = False,
    model: Annotated[Optional[str], cyclopts.Parameter(name=["--model", "-m"])] = None,
    scenario: Annotated[
        Optional[str], cyclopts.Parameter(name=["--scenario", "-s"])
    ] = None,
    variant_index: Annotated[
        Optional[int], cyclopts.Parameter(name=["--variant", "-v"])
    ] = None,
    save_images: Annotated[bool, cyclopts.Parameter(name="--save")] = True,
) -> None:
    """
    运行评测

    Args:
        all_models: 运行所有模型
        model: 指定模型名称
        scenario: 指定场景类型 (edit_appearance 或 two_persons_dance)
        variant_index: 指定变体索引（从0开始）
        save_images: 是否保存生成的图片
    """
    config = get_config()

    # 验证配置（警告但不阻止运行）
    errors = config.validate()
    if errors:
        console.print("[yellow]配置警告:[/yellow]")
        for error in errors:
            console.print(f"  - {error}")
        console.print("[dim]部分模型可能无法使用[/dim]\n")

    # 确定要测试的模型
    models_to_test: list[ModelConfig] = []
    if all_models:
        models_to_test = list(MODELS.values())
    elif model:
        if model not in MODELS:
            console.print(f"[red]未知模型: {model}[/red]")
            console.print(f"可用模型: {', '.join(MODELS.keys())}")
            return
        models_to_test = [MODELS[model]]
    else:
        console.print("[yellow]请指定 --all 或 --model[/yellow]")
        return

    # 确定要测试的场景
    scenarios_to_test: list[Scenario] = []
    if scenario:
        try:
            scenario_type = ScenarioType(scenario)
            scenarios_to_test = [get_scenario(scenario_type)]
        except ValueError:
            console.print(f"[red]未知场景: {scenario}[/red]")
            console.print(f"可用场景: {', '.join(s.value for s in ScenarioType)}")
            return
    else:
        scenarios_to_test = get_all_scenarios()

    # 运行评测
    asyncio.run(
        _run_benchmarks(
            config=config,
            models_to_test=models_to_test,
            scenarios_to_test=scenarios_to_test,
            variant_index=variant_index,
            save_images=save_images,
        )
    )


async def _run_benchmarks(
    config: BenchmarkConfig,
    models_to_test: list[ModelConfig],
    scenarios_to_test: list[Scenario],
    variant_index: Optional[int],
    save_images: bool,
) -> None:
    """执行评测"""
    console.print("\n[bold blue]=== 图像生成模型评测 ===[/bold blue]\n")

    # 创建输出目录
    output_dir = config.results_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    if save_images:
        output_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"结果输出目录: {output_dir}\n")

    all_results: list[dict] = []

    for scenario in scenarios_to_test:
        console.print(f"\n[bold cyan]场景: {scenario.name}[/bold cyan]")
        console.print(f"描述: {scenario.description}")

        # 加载测试图片
        try:
            test_images = load_test_images(scenario, config.test_images_dir)
            console.print(f"已加载 {len(test_images)} 张测试图片")
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
            console.print("[yellow]请将测试图片放到 test_images/ 目录下[/yellow]")
            continue

        # 确定要测试的变体
        variants = scenario.variants
        if variant_index is not None:
            if 0 <= variant_index < len(variants):
                variants = [variants[variant_index]]
            else:
                console.print(f"[red]变体索引超出范围: {variant_index}[/red]")
                continue

        for variant in variants:
            console.print(
                f"\n[magenta]变体: {variant.name}[/magenta] - {variant.description}"
            )

            scenario_results: list[tuple[str, str, str, ImageGenerationResult]] = []

            for model_config in models_to_test:
                console.print(f"\n  [cyan]{model_config.display_name}[/cyan]")

                try:
                    model = create_model(model_config, config)
                    result = await run_single_benchmark(
                        model=model,
                        scenario=scenario,
                        variant=variant,
                        test_images=test_images,
                    )

                    # 保存图片
                    if save_images and result.success:
                        img_path = save_result_image(
                            result=result,
                            output_dir=output_dir,
                            model_name=model_config.name,
                            scenario_name=scenario.type.value,
                            variant_name=variant.name,
                        )
                        if img_path:
                            console.print(
                                f"  [green]图片已保存: {img_path.name}[/green]"
                            )

                    scenario_results.append(
                        (
                            model_config.display_name,
                            scenario.type.value,
                            variant.name,
                            result,
                        )
                    )

                    # 记录结果
                    all_results.append(
                        {
                            "model": model_config.name,
                            "scenario": scenario.type.value,
                            "variant": variant.name,
                            **result.to_dict(),
                        }
                    )

                    if result.success:
                        console.print(
                            f"  [green]成功[/green] - {result.total_time_ms:.0f}ms, {result.image_size_kb:.1f}KB"
                        )
                    else:
                        console.print(f"  [red]失败[/red] - {result.error_message}")

                except Exception as e:
                    console.print(f"  [red]错误: {e}[/red]")

            # 打印当前变体的结果表格
            if scenario_results:
                console.print()
                print_results_table(scenario_results, scenario.name, variant.name)

    # 保存 JSON 结果
    if save_images and all_results:
        json_path = output_dir / "results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        console.print(f"\n[green]结果已保存到: {json_path}[/green]")

    console.print("\n[bold blue]=== 评测完成 ===[/bold blue]")


if __name__ == "__main__":
    app()
