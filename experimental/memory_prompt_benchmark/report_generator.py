# CREATED_BY_AGENT
"""
报告生成模块

生成 Markdown 格式的对比报告
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from chat_simulator import SimulationResult
from config import get_config
from db_service import UserInfo
from memory_extractor import ExtractedMemory


def generate_report(
    users: List[UserInfo],
    memories: List[ExtractedMemory],
    results: List[SimulationResult],
    output_dir: Optional[Path] = None,
) -> Path:
    """
    生成评测报告

    Args:
        users: 用户信息列表
        memories: 提取的记忆列表
        results: 模拟结果列表
        output_dir: 输出目录（可选，默认使用带时间戳的目录）

    Returns:
        报告文件路径
    """
    config = get_config()

    # 创建输出目录
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = config.results_dir / timestamp

    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成报告内容
    report_content = _generate_markdown_report(users, memories, results)

    # 保存报告
    report_path = output_dir / "report.md"
    report_path.write_text(report_content, encoding="utf-8")

    # 保存原始数据（JSON 格式）
    raw_data = _generate_raw_data(users, memories, results)
    raw_data_path = output_dir / "raw_data.json"
    raw_data_path.write_text(
        json.dumps(raw_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return report_path


def _generate_markdown_report(
    users: List[UserInfo],
    memories: List[ExtractedMemory],
    results: List[SimulationResult],
) -> str:
    """生成 Markdown 报告内容"""
    lines = []

    # 标题
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("# 记忆提示词评测报告")
    lines.append("")
    lines.append(f"**评测时间**: {timestamp}")
    lines.append(f"**测试用户数**: {len(users)}")
    lines.append("")

    # 汇总信息
    lines.append("## 测试概览")
    lines.append("")
    lines.append("| 用户 | 邮箱 | 消息数 | 聊天历史字数 |")
    lines.append("|------|------|--------|-------------|")

    for i, user in enumerate(users):
        memory = memories[i] if i < len(memories) else None
        history_len = memory.chat_history_length if memory else 0
        email = user.email or "-"
        nickname = user.nickname or user.id[:8]
        lines.append(f"| {nickname} | {email} | {user.message_count} | {history_len} |")

    lines.append("")

    # 每个用户的详细结果
    for i, result in enumerate(results):
        user = users[i] if i < len(users) else None
        memory = memories[i] if i < len(memories) else None

        lines.append(f"---")
        lines.append("")
        user_label = (
            user.nickname or user.email or result.user_id[:8]
            if user
            else result.user_id[:8]
        )
        lines.append(f"## 用户: {user_label}")
        lines.append("")

        # 用户信息
        if user:
            lines.append("### 用户信息")
            lines.append("")
            lines.append(f"- **ID**: `{user.id}`")
            lines.append(f"- **邮箱**: {user.email or '未设置'}")
            lines.append(f"- **昵称**: {user.nickname or '未设置'}")
            lines.append(f"- **历史消息数**: {user.message_count}")
            lines.append("")

        # 提取的记忆
        if memory:
            lines.append("### 提取的用户记忆")
            lines.append("")
            lines.append("#### 用户画像摘要（嵌入提示词）")
            lines.append("")
            lines.append("```")
            lines.append(memory.summary_for_prompt)
            lines.append("```")
            lines.append("")

            lines.append("<details>")
            lines.append("<summary>完整分析结果（点击展开）</summary>")
            lines.append("")
            lines.append(memory.full_analysis)
            lines.append("")
            lines.append("</details>")
            lines.append("")

        # 对话对比
        lines.append(f"### 对话对比（角色: {result.agent_name}）")
        lines.append("")

        for j, (with_mem, without_mem) in enumerate(
            zip(result.responses_with_memory, result.responses_without_memory)
        ):
            lines.append(f"#### 问题 {j + 1}: {with_mem.question}")
            lines.append("")
            lines.append("**有记忆的回复:**")
            lines.append("")
            lines.append(f"> {with_mem.response}")
            lines.append("")
            lines.append("**无记忆的回复:**")
            lines.append("")
            lines.append(f"> {without_mem.response}")
            lines.append("")

    # 结论
    lines.append("---")
    lines.append("")
    lines.append("## 分析结论")
    lines.append("")
    lines.append("请根据以上对比结果，分析有记忆和无记忆情况下对话效果的差异：")
    lines.append("")
    lines.append("1. **个性化程度**：有记忆的回复是否更能体现对用户的了解？")
    lines.append("2. **情感连接**：有记忆的回复是否更能建立情感联系？")
    lines.append("3. **对话连贯性**：记忆是否帮助角色更好地理解用户的需求和偏好？")
    lines.append(
        "4. **实用建议**：基于测试结果，记忆提示词的提取和使用有哪些改进空间？"
    )
    lines.append("")

    return "\n".join(lines)


def _generate_raw_data(
    users: List[UserInfo],
    memories: List[ExtractedMemory],
    results: List[SimulationResult],
) -> dict:
    """生成原始数据（JSON 格式）"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "users": [],
    }

    for i, result in enumerate(results):
        user = users[i] if i < len(users) else None
        memory = memories[i] if i < len(memories) else None

        user_data = {
            "user_id": result.user_id,
            "user_email": result.user_email,
            "agent_name": result.agent_name,
            "memory": (
                {
                    "summary_for_prompt": memory.summary_for_prompt if memory else None,
                    "full_analysis": memory.full_analysis if memory else None,
                    "chat_history_length": memory.chat_history_length if memory else 0,
                }
                if memory
                else None
            ),
            "conversations": [],
        }

        for j, (with_mem, without_mem) in enumerate(
            zip(result.responses_with_memory, result.responses_without_memory)
        ):
            user_data["conversations"].append(
                {
                    "question_index": j,
                    "question": with_mem.question,
                    "response_with_memory": with_mem.response,
                    "response_without_memory": without_mem.response,
                }
            )

        data["users"].append(user_data)

    return data


def load_results_from_json(json_path: Path) -> dict:
    """从 JSON 文件加载结果数据"""
    if not json_path.exists():
        raise FileNotFoundError(f"结果文件不存在: {json_path}")
    return json.loads(json_path.read_text(encoding="utf-8"))


def regenerate_report_from_json(results_dir: Path) -> Path:
    """从 JSON 数据重新生成报告"""
    json_path = results_dir / "raw_data.json"
    data = load_results_from_json(json_path)

    # 重建数据结构
    users = []
    memories = []
    results = []

    for user_data in data.get("users", []):
        # 重建 UserInfo
        users.append(
            UserInfo(
                id=user_data["user_id"],
                email=user_data.get("user_email"),
                nickname=None,
                message_count=0,
            )
        )

        # 重建 ExtractedMemory
        mem_data = user_data.get("memory")
        if mem_data:
            memories.append(
                ExtractedMemory(
                    summary_for_prompt=mem_data.get("summary_for_prompt", ""),
                    full_analysis=mem_data.get("full_analysis", ""),
                    chat_history_length=mem_data.get("chat_history_length", 0),
                )
            )
        else:
            memories.append(
                ExtractedMemory(
                    summary_for_prompt="",
                    full_analysis="",
                    chat_history_length=0,
                )
            )

        # 重建 SimulationResult
        from chat_simulator import ChatResponse

        responses_with = []
        responses_without = []
        for conv in user_data.get("conversations", []):
            responses_with.append(
                ChatResponse(
                    question=conv["question"],
                    response=conv["response_with_memory"],
                    has_memory=True,
                )
            )
            responses_without.append(
                ChatResponse(
                    question=conv["question"],
                    response=conv["response_without_memory"],
                    has_memory=False,
                )
            )

        results.append(
            SimulationResult(
                user_id=user_data["user_id"],
                user_email=user_data.get("user_email"),
                agent_name=user_data.get("agent_name", "Unknown"),
                memory_summary=(
                    mem_data.get("summary_for_prompt", "") if mem_data else ""
                ),
                responses_with_memory=responses_with,
                responses_without_memory=responses_without,
            )
        )

    # 生成报告
    report_content = _generate_markdown_report(users, memories, results)
    report_path = results_dir / "report.md"
    report_path.write_text(report_content, encoding="utf-8")

    return report_path
