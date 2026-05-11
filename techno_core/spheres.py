"""Hyperion 启发的球层枚举：描述 Inty 所在虚拟宇宙的拓扑分区。

这些名称用于文档、观测（LangSmith / 日志标签）与跨模块对齐，而非替代现有
API。各层在 ``techno_core/AGENTS.md`` 中有与 ``agentic_kernel`` 路径的对照表。
"""

from __future__ import annotations

from enum import StrEnum


class Sphere(StrEnum):
    """Inty 虚拟空间分区（Datum plane 的子集 + 外部基底）。"""

    DATASPHERE = "datasphere"
    """单用户邻域数字空间：App、会话、单租户可见的状态与上行事件。"""

    MEGASPHERE = "megasphere"
    """行星际骨干：Inty 后端、推送、Ops、外部 HTTP/gRPC、跨用户基础设施。"""

    TECHNOCORE = "technocore"
    """AI 居留层：工具后台、内在节拍、面向自主行为的推理与记忆写入（对用户非即时可见）。"""

    DATUM = "datum"
    """Datum 平面：Megasphere ∪ Technocore 的合成观测面（产品调试与追踪视角）。"""

    METASPHERE = "metasphere"
    """基底连续统：模型提供商、物理与协议载体之上、我们无法托管的「外在」世界模型边界。"""


# 默认情况下，自主 manifest（内心活动、异步工具、预定节拍）发生在 Technocore。
AUTONOMY_SURFACES: tuple[Sphere, ...] = (Sphere.TECHNOCORE,)
