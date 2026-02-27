# CREATED_BY_AGENT
"""
记忆提示词评测 CLI 工具

Usage:
    python benchmark.py run --top 20
    python benchmark.py run --emails "user1@example.com,user2@example.com"
    python benchmark.py run --top 10 --memory-prompt prompts/custom.txt
    python benchmark.py list-users --top 50
    python benchmark.py report --dir results/20260122_123456
"""

from pathlib import Path
from typing import Annotated, List, Optional

import cyclopts
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from chat_simulator import SimulationResult, run_comparison_simulation
from config import get_config
from db_service import (
    UserInfo,
    format_chat_history_for_analysis,
    get_random_agent,
    get_top_users_by_message_count,
    get_user_all_chat_history,
    get_users_by_emails,
)
from memory_extractor import (
    ExtractedMemory,
    extract_user_memory,
    load_custom_memory_prompt,
)
from report_generator import generate_report, regenerate_report_from_json

app = cyclopts.App(
    name="memory-benchmark",
    help="记忆提示词评测工具",
)
console = Console()


@app.command()
def run(
    emails: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name=["--emails", "-e"],
            help="逗号分隔的用户邮箱列表",
        ),
    ] = None,
    top: Annotated[
        int,
        cyclopts.Parameter(
            name=["--top", "-t"],
            help="按消息数选择前 N 个用户（默认 20）",
        ),
    ] = 20,
    memory_prompt: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name=["--memory-prompt", "-p"],
            help="自定义记忆提取提示词文件路径",
        ),
    ] = None,
    model: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name=["--model", "-m"],
            help="指定 LLM 模型（默认使用配置文件中的模型）",
        ),
    ] = None,
) -> None:
    """
    运行记忆提示词评测

    流程：
    1. 选择测试用户
    2. 获取用户聊天历史
    3. 提取用户记忆
    4. 与新角色进行对比对话（有记忆 vs 无记忆）
    5. 生成评测报告
    """
    console.print("\n[bold blue]=== 记忆提示词评测 ===[/bold blue]\n")

    # 1. 选择用户
    users: List[UserInfo] = []
    if emails:
        email_list = [e.strip() for e in emails.split(",") if e.strip()]
        console.print(f"[cyan]通过邮箱选择用户: {len(email_list)} 个[/cyan]")
        users = get_users_by_emails(email_list)
        if not users:
            console.print("[red]未找到指定邮箱的用户[/red]")
            return
    else:
        console.print(f"[cyan]按消息数选择前 {top} 个用户[/cyan]")
        users = get_top_users_by_message_count(limit=top)
        if not users:
            console.print("[red]未找到有聊天记录的用户[/red]")
            return

    console.print(f"[green]找到 {len(users)} 个用户[/green]\n")

    # 显示用户列表
    _print_users_table(users)
    console.print()

    # 加载自定义提示词（如果指定）
    custom_prompt = None
    if memory_prompt:
        prompt_path = Path(memory_prompt)
        if not prompt_path.is_absolute():
            prompt_path = Path(__file__).parent / prompt_path
        try:
            custom_prompt = load_custom_memory_prompt(prompt_path)
            console.print(f"[cyan]使用自定义记忆提示词: {prompt_path}[/cyan]\n")
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
            return

    # 获取测试角色
    console.print("[cyan]获取测试角色...[/cyan]")
    agent_info = get_random_agent()
    if not agent_info:
        console.print("[red]未找到可用的测试角色[/red]")
        return
    console.print(f"[green]测试角色: {agent_info['name']}[/green]\n")

    # 处理每个用户
    memories: List[ExtractedMemory] = []
    results: List[SimulationResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for i, user in enumerate(users):
            user_label = user.nickname or user.email or user.id[:8]
            task_id = progress.add_task(
                f"[{i + 1}/{len(users)}] 处理用户: {user_label}",
                total=None,
            )

            try:
                # 获取聊天历史
                progress.update(
                    task_id, description=f"[{i + 1}/{len(users)}] 获取聊天历史..."
                )
                histories = get_user_all_chat_history(user.id)
                if not histories:
                    console.print(
                        f"  [yellow]用户 {user_label} 没有聊天记录，跳过[/yellow]"
                    )
                    progress.remove_task(task_id)
                    continue

                chat_history_text = format_chat_history_for_analysis(histories)
                console.print(f"  [dim]聊天历史: {len(chat_history_text)} 字符[/dim]")

                # 提取记忆
                progress.update(
                    task_id, description=f"[{i + 1}/{len(users)}] 提取用户记忆..."
                )
                memory = extract_user_memory(
                    chat_history_text=chat_history_text,
                    memory_prompt=custom_prompt,
                    model=model,
                )
                memories.append(memory)
                console.print(
                    f"  [dim]记忆摘要: {len(memory.summary_for_prompt)} 字符[/dim]"
                )

                # 运行对比模拟
                progress.update(
                    task_id, description=f"[{i + 1}/{len(users)}] 运行对话模拟..."
                )
                result = run_comparison_simulation(
                    agent_info=agent_info,
                    user_id=user.id,
                    user_email=user.email,
                    user_memory=memory.summary_for_prompt,
                    model=model,
                )
                results.append(result)
                console.print(f"  [green]完成 8 组对话对比[/green]")

            except Exception as e:
                console.print(f"  [red]处理失败: {e}[/red]")
                import traceback

                console.print(f"  [dim]{traceback.format_exc()}[/dim]")

            finally:
                progress.remove_task(task_id)

    if not results:
        console.print("\n[red]没有成功处理任何用户[/red]")
        return

    # 生成报告
    console.print("\n[cyan]生成评测报告...[/cyan]")
    # 只传递成功处理的用户
    successful_users = [users[i] for i in range(len(users)) if i < len(results)]
    report_path = generate_report(successful_users, memories, results)
    console.print(f"[green]报告已保存: {report_path}[/green]")
    console.print(f"[green]原始数据: {report_path.parent / 'raw_data.json'}[/green]")

    console.print("\n[bold blue]=== 评测完成 ===[/bold blue]")


@app.command()
def list_users(
    top: Annotated[
        int,
        cyclopts.Parameter(
            name=["--top", "-t"],
            help="显示前 N 个用户（按消息数排序）",
        ),
    ] = 50,
) -> None:
    """列出消息数最多的用户"""
    console.print(f"\n[cyan]获取消息数最多的 {top} 个用户...[/cyan]\n")

    users = get_top_users_by_message_count(limit=top)
    if not users:
        console.print("[red]未找到有聊天记录的用户[/red]")
        return

    _print_users_table(users)
    console.print(f"\n[dim]共 {len(users)} 个用户[/dim]")


@app.command()
def report(
    dir: Annotated[
        str,
        cyclopts.Parameter(
            name=["--dir", "-d"],
            help="结果目录路径（包含 raw_data.json）",
        ),
    ],
) -> None:
    """从结果目录重新生成报告"""
    results_dir = Path(dir)
    if not results_dir.is_absolute():
        results_dir = Path(__file__).parent / results_dir

    if not results_dir.exists():
        console.print(f"[red]目录不存在: {results_dir}[/red]")
        return

    json_path = results_dir / "raw_data.json"
    if not json_path.exists():
        console.print(f"[red]找不到结果文件: {json_path}[/red]")
        return

    console.print(f"[cyan]从 {json_path} 重新生成报告...[/cyan]")

    try:
        report_path = regenerate_report_from_json(results_dir)
        console.print(f"[green]报告已生成: {report_path}[/green]")
    except Exception as e:
        console.print(f"[red]生成报告失败: {e}[/red]")


def _print_users_table(users: List[UserInfo]) -> None:
    """打印用户表格"""
    table = Table(
        title="用户列表",
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("序号", style="dim", width=6)
    table.add_column("ID", style="cyan", width=20)
    table.add_column("邮箱", width=30)
    table.add_column("昵称", width=15)
    table.add_column("消息数", justify="right", width=10)

    for i, user in enumerate(users, 1):
        table.add_row(
            str(i),
            user.id[:18] + "..." if len(user.id) > 20 else user.id,
            user.email or "-",
            user.nickname or "-",
            str(user.message_count),
        )

    console.print(table)


if __name__ == "__main__":
    app()
