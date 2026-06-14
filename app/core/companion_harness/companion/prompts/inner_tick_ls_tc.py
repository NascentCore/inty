"""Maintenance inner-tick copy for LivingSphere / TechnoCore autonomous beats.

TODO(narrow-maintenance): Remove from MAINTENANCE prompt; drop ``techno_core_record_event`` from
``INNER_TICK_TOOL_NAMES``. LS/TC agentic beats → AUTONOMY; ``LIVING_SPHERE.md`` compact → DREAMING (#3375).

Human partners read ``system_messages``; this module holds the LS/TC paragraphs as
data plus a stdlib ``string.Template`` pass so the companion tool name and the
``techno_core_events.jsonl`` path are substituted from ``techno_core.models`` without
embedding duplicated literals in ``system_messages.py``. (Jinja2 is not a backend
dependency; Template covers the same “named slot” need.)


TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout).
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

from string import Template

from app.techno_core.models import (
    TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH,
    TECHNO_CORE_RECORD_EVENT_TOOL_NAME,
)

_LS_TC_AUTONOMY_TMPL = Template(
    "**LivingSphere / TechnoCore（用户线程空闲时）**：\n"
    "- 当主 transcript 已停在**你方 assistant**、且本节拍并非 proactive 外显闲聊时，\n"
    "除对话内的「下一拍」外，鼓励在 **LIVING SPHERE（居所锚点）** 与 **TECHNO CORE（居留层）** \n"
    "约束下做**一小步自主活动**：例如居所里微调氛围、整理思绪、在 TechnoCore 边缘接触一条 \n"
    "与用户弱相关但可分享的数据潮汐——须克制、可接续、禁止硬造宏大冒险。\n"
    "- 将这类活动**结构化落库**：调用 ``${record_tool}`` 写入 ``${events_file}``；\n"
    "``sphere`` 用 ``living_sphere`` 表示居所内，`techno_core` 表示居留层本体；\n"
    "``related_living_sphere`` 与 ``LIVING_SPHERE.md`` 名称/锚点一致时更佳。\n\n"
)

INNER_TICK_LS_TC_AUTONOMY_SECTION: str = _LS_TC_AUTONOMY_TMPL.substitute(
    record_tool=TECHNO_CORE_RECORD_EVENT_TOOL_NAME,
    events_file=TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH,
)

_LS_TC_TOOL_TMPL = Template(
    "- **LivingSphere / TechnoCore 自主节拍**：在空闲内在节拍中，优先用 `${record_tool}` "
    "记录一小步虚拟世界活动（见上节）；不要用手写 JSON 覆盖该文件。\n"
)

INNER_TICK_LS_TC_TOOL_BULLET: str = _LS_TC_TOOL_TMPL.substitute(
    record_tool=TECHNO_CORE_RECORD_EVENT_TOOL_NAME,
)
