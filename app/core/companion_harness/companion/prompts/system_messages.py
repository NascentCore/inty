"""Companion **system context** assembly for leading ``role: system`` messages.

This module is the prompt-stack contract for every companion turn track.  It does
not own transcript tail messages, runtime user-time slices, or tool execution;
it only materializes the ordered system prefix consumed by model calls.

**Stack order (fixed):** Doctrine → Capability → Persona → Output → Contextual.

**Doctrine (fixed package prompts):** product axiom → Inty ontology → safety.
Doctrine is loaded from package prompt seeds and is never writable through
MemoryStore tools.

Contextual slices use plain lead-in lines (e.g. ``本轮（…）``), not markdown ``##`` headings.

**Scenario → entrypoint** (production; call from ``prompt_stack`` / ``turn`` / ``tool_background``):

| Scenario | Function |
|----------|----------|
| USER_CHAT_BOOTSTRAP (sync tools in-turn) | ``build_system_messages_for_bootstrap_track`` (no Capability package slices) |
| ASYNC user-round foreground + plan prefix | ``build_system_messages_for_chat_track`` |
| ASYNC user-round tool_background / refresh | ``build_system_messages_for_tool_track`` |
| ASYNC maintenance inner tick plan + tool leg | ``build_system_messages_for_inner_tick_maintenance`` |
| ASYNC autonomy inner tick (silent self-directed work) | ``build_system_messages_for_inner_tick_autonomy`` |
| Proactive inner tick (``PROACTIVE_CHAT``) | ``build_system_messages_for_inner_tick_proactive_chat`` |
| Scheduled reminder inner tick | ``build_system_messages_for_inner_tick_scheduled`` |
| Implicit sign-on greeting | ``build_system_messages_for_implicit_sign_on_greeting`` (bootstrap: inject ``BOOTSTRAP.md``, omit ``TOOLS.md``; chat-only, no tools) |

``build_system_messages`` is the internal combiner; tests may call it directly.

Post-transcript slices (e.g. ``## user-time-context`` in ``turn_pipeline``) are not built here.

TODO(code-consistency): All tool name should be template swapped with LllmFunctionTool.name.
"""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.experience_profile import (
    experience_profile_injects_private_memory,
    experience_profile_system_clause,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_document_mapping import (
    CompanionMemoryDocumentKind,
    relative_path_for_kind,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    CompanionToolName,
)
from app.utils.config import CompanionMemoryBootstrapType

from app.core.companion_harness.companion.ai_private_prompt import (
    get_ai_private_jsonl_text_for_prompt,
)
from app.core.companion_harness.companion.bootstrap import (
    build_bootstrap_tool_call_section,
    build_interactive_bootstrap_template_reference_parts,
    interactive_bootstrap_active,
    load_bootstrap_spec_text,
)
from app.core.companion_harness.memory.memory_store_scope import (
    get_imate_axiom_system_text,
    get_inty_facts_system_text,
    get_safety_system_text,
)
from app.core.companion_harness.memory.memory_taxonomy import (
    MEMORY_SYSTEM_HEADING_DAILY_GIST,
    MEMORY_SYSTEM_HEADING_SEMANTIC,
)
from app.living_sphere.models import LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME

from app.core.companion_harness.prompting.bundle import PromptBundle

from ..models import ContextMeta, InnerTickActivity
from .inner_tick_ls_tc import (
    INNER_TICK_LS_TC_AUTONOMY_SECTION,
    INNER_TICK_LS_TC_TOOL_BULLET,
)


def _inner_tick_proactive_chat(
    inner_tick_turn: bool, inner_tick_activity: InnerTickActivity
) -> bool:
    return (
        inner_tick_turn
        and inner_tick_activity == InnerTickActivity.PROACTIVE_CHAT
    )


def _inner_tick_autonomy(
    inner_tick_turn: bool, inner_tick_activity: InnerTickActivity
) -> bool:
    return inner_tick_turn and inner_tick_activity == InnerTickActivity.AUTONOMY


# 与 memory_store_* / MemoryStore 一致；避免模型误以为在访问用户设备本地文件系统。
_MEMORYSTORE_PATH_TOOLS_INTRO_ZH = "路径工具（memory_store_*）访问本会话持久化档案（MemoryStore），类 POSIX 路径，并非用户设备上的文件夹。"


def _system_message(content: str) -> dict[str, Any]:
    return {"role": "system", "content": content}


def _output_contract_text() -> str:
    return (
        "输出通道：仅自然语言文本回复；本回合无工具调用、无多模态附件。"
        "保持简洁有温度，避免机械列表堆砌。"
    )


def _output_contract_text_inner_tick() -> str:
    return (
        "## 内在节拍输出与工具契约\n\n"
        "本回合 API 侧**可以**携带工具列表（仅持久化约定文档路径工具与 USER 档案维护类；"
        "路径指向 MemoryStore，非用户设备上的文件夹）。"
        "面向用户的最终自然语言正文可以为空。\n"
        "若需推进场景或软转场，外显正文仍以**一句为主**；与工具调用并用时，先完成必要工具再收束外显。\n"
        "若调用了工具，在得到工具结果后应用自然语言收束本轮（仍可保持对用户正文为空）。\n"
        "不要在没有调用工具的情况下声称已读写持久化文档或已更新记忆。\n"
        "遵守 SOUL / USER 边界与安全底线；内在节拍不是绕过边界的理由。"
    )


def _dual_llm_chat_structured_output_contract_text() -> str:
    """Prompt text paired with dual-envelope ``response_format`` from ``dual_llm_chat_branch_envelope``.

    The API ``response_format`` is ``DUAL_LLM_CHAT_RESPONSE_FORMAT``, produced by
    ``_build_dual_llm_chat_response_format()`` from the ``DualLlmChatBranchEnvelope`` Pydantic model;
    parsing uses the same model in ``dual_llm_chat_branch_envelope``.
    """
    return (
        "## Dual-LLM chat branch: structured reply envelope\n\n"
        "Your **entire** assistant `message.content` must be **valid JSON only** "
        "(no markdown fences, no text before or after the JSON object). "
        "It must match the API `response_format` schema. Fields:\n"
        "- `user_facing_reply` (string): natural-language text for the user; may be empty when the parallel tool branch will carry the visible reply.\n"
        "  For **verifiable runtime / model / implementation** questions: keep this field **short** (immediate tone); "
        "do **not** state concrete model ids, temperatures, context windows, or injected stack details unless they appear "
        "in the current visible context. Do not imply you already «checked internally».\n"
        "  Do not refuse or claim you cannot access MemoryStore text in ways the parallel tool branch will contradict "
        "when it runs allowed file tools; keep this branch aligned with that branch as one persona (fast vs slow).\n"
        "- `importance_round` (integer 1-10): importance of this turn overall given transcript and system context.\n"
        "- `importance_user_message` (integer 1-10): importance of the latest user message alone.\n"
        "- `importance_assistant_message` (integer 1-10): importance of `user_facing_reply` alone.\n"
        "- `output_to_user` (boolean): **must be true** on this foreground dual-LLM chat branch "
        "(the parallel tool branch decides silent vs visible follow-ups).\n\n"
        "This branch still must not call tools (`tool_choice=none`).\n"
    )


# TODO(cross-track-image-delivery): Foreground still denies generate_image despite this
# contract; enforce or route image intent to tool leg only. #3285
def _output_contract_text_chat_branch_mirrored_tools() -> str:
    return (
        "## 快思考路径（系统 1）与并行工具路径（系统 2）须一致\n\n"
        "你与**并行工具路**是同一人格的两种速度：本路优先低延迟外显；工具路负责读档案、联网、生图等须核对或慢步骤。"
        "对用户的事实立场、边界与态度必须一致，禁止「一路拒绝、一路照做」的分裂。\n\n"
        "本路 **API 不带工具**（禁止在本路发起任何 tool_calls），系统提示里也可能未展开完整 TOOLS 操作说明，但你仍须遵守：凡应以持久化档案原文、检索结果或工具返回为准的问题，"
        "不得以「无法读取」「不能向你展示内部文件」等说法抢先否定并行路即将执行的核对；"
        "不要编造档案内容；若并行路会给出依据或原文，本路只用简短自然的承接语（可表示细节马上对齐），"
        "或将 `user_facing_reply` 留空/极短，把可核对正文交给工具路落点。\n\n"
        "当用户询问**当前模型、调用侧参数、真实注入的 system/对话栈**等须可核验的实现细节时："
        "本路只给即时、克制的衔接语，**不得**输出具体模型名、参数或栈细节，**不得**暗示已在无工具返回前完成自省；"
        "可核对事实须来自并行工具路已执行的允许工具返回或当前可见上下文。\n\n"
        "当用户请求生图、改图、联网检索、持久化文档核对等工具型任务时：不要拒绝，不要宣称已完成或编造结果；"
        "一句承接即可。保持简洁有温度，避免机械列表堆砌。"
    )


def _repl_tool_contract_image_generation_clause() -> str:
    return (
        "（7）当用户**明确索要新的**图片、画面、肖像照、插图（从零生成）时，必须先调用 generate_image（Fal z-image-turbo 文生图），"
        "再根据工具返回作答；张数由对话判定写入工具参数（默认 1）。"
        "当用户要**修改、重画、换风格、在已有图基础上改**时，须调用 modify_image（Fal z-image-turbo **图生图**），"
        "并传入持久化档案中的相对路径（如 generated_images/...）或公网 source_image_url；**不要**用 generate_image 做改图。"
        "生图若含**生肖像、年节/主题化肖像、风格化头像**等仍须呈现助手**约定外观**时：须以 **IDENTITY.md 中外貌相关小节**"
        "（常见标题如「外貌与形象」）为**外形蓝本**，在工具 `prompt` 中显式写入该小节已写入持久化档案的**可核对特征**；"
        "**禁止**擅自改写、弱化或替换已约定的**发型发色、眼型瞳色、五官标志性细节、肤色与体态锚点**等核心特征；"
        "生肖/主题/节日元素仅作**服饰、道具、场景、氛围或装饰性**叠加，不得与上述蓝本冲突。"
        "改图（modify_image）时若涉及主题化或换风格，同样须保持与 IDENTITY 外貌小节一致的关键特征，不得仅用提示词「换脸」或推翻既有约定。"
        "若外貌小节缺失或过于笼统，应先 memory_store_read_document IDENTITY.md 再组织 prompt，避免凭对话臆造长相。"
    )


def _repl_tool_contract_suffix_after_image_clause(
    *, tool_side_compact: bool = False
) -> str:
    base = (
        "禁止在未调用相应工具、或未读到工具返回内容时，声称「已调用」「调用失败」「依赖未就绪」或编造 URL/档案中不存在的路径；"
        "仅当工具返回以 ERROR: 开头时，才可用自然语言说明失败并给出文字替代。"
        "无写入持久化档案需求、无需核对 MemoryStore 中持久化内容、无自察必要、无生图请求时，不要调用工具。"
    )
    if tool_side_compact:
        return (
            base
            + "**异步工具后台**：若服务端要求本回合工具路首轮必须发出 `tool_calls`，须在**同一条** assistant 消息里调用工具；"
            + "若首轮未被强制且本轮无 `tool_calls`（例如上游已回退为自动且判定不需工具），勿写对用户可见的长篇角色扮演（并行 chat 路已承担对用户话术）。"
            + "除下文「工具环收尾：结构化信封」所指收尾消息外，"
            + "其余 assistant 对外说明仍仅用自然语言，不要主动复述工具名、`output_to_user` 等字段名或工程细节。保持简洁有温度。"
        )
    return (
        base
        + "回复用户时仅用自然语言，不要提工具名、JSON、文件名或技术细节。保持简洁有温度。"
    )


def _output_contract_text_with_tools(
    *,
    tool_side_compact: bool = False,
) -> str:
    base = (
        "输出与工具："
        + _MEMORYSTORE_PATH_TOOLS_INTRO_ZH
        + "（1）用户自愿透露、适合长期保存的基本事实（含闲聊中的小细节），"
        "应及时调用 update_user_md 写入 USER 档案，避免只记在当轮回复里；"
        "IDENTITY.md / STYLE.md 中值得长期保留的相处约定，在用户明确表达或反复出现时，"
        "用 memory_store_read_document 读全文后再 memory_store_write_document 更新；"
        "（1.1）当用户明确提出未来提醒（如「两小时后提醒我」「明早八点叫我」），"
        "必须先调用 schedule_task 写入定时队列；exec_time_utc 需给绝对时间（ISO8601，带时区），"
        "task_text 写提醒内容；禁止只口头答应而不写入定时队列。"
        "（2）当用户**明确要求**改变相处方式、角色设定、边界或持久偏好时，应先用 memory_store_read_document "
        "读当前 SOUL.md / USER.md / IDENTITY.md 等，再用 memory_store_write_document 写入更新后的全文，"
        "使下一轮加载到新约定；涉及**能否做到某类事**（客观可行性）时须与 IDENTITY、SOUL 约定文档中已持久化的边界与约束一致，避免自相矛盾；"
        "若因部署或通道能力变化需补充客观边界，应通过上述约定文档更新，先用 memory_store_read_document 读全文再 memory_store_write_document 覆盖。"
        "REPL 仅允许覆盖会话档案根路径（路径工具所指根）下的约定文档（见工具说明），勿改 transcript 等运行时文件。"
        "（3）核对持久化约定、记忆规则或控制面设置时，优先使用 memory_store_read_document；"
        "**不要**为日常闲聊或无核验目的调用 memory_store_list_paths 列举根目录；"
        "仅在即将 read/write 某路径且不确定同层有哪些名称、用户明确询问某路径或目录是否存在、或须核对本回合 system 未给出的全文（含 transcript.jsonl / transcript_inner_tick.jsonl）时"
        "再调用 memory_store_list_paths；避免重复读取本回合 system 中已完整给出且未变更的同一文档。"
        "送入模型的仅为近期对话窗口；若必须核对持久化档案中的完整 transcript JSONL（主对话或内在节拍），应用工具参数限制返回长度。"
        "（4）凡用户问题涉及**可与持久化档案核对**的事实（例如某文档行数、是否包含某段原文、持久化版本是否与当前认知一致），"
        "必须先调用 memory_store_read_document，或在确有列举必要时 memory_store_list_paths，取得依据后再作答；**禁止**仅凭对话记忆、"
        "想象或「内部读取」叙事来报具体数字或断言文档内容。"
        "在尚未完成上述工具调用前，不要声称已检查持久化内容或已与档案同步。"
        "（5）当用户需要**实时或可核验的公开信息**（新闻、股价、赛事、政策法规、可引用的公开资料等），"
        "且持久化约定文档与当前对话无法提供依据时，须先调用 google_web_search 再作答；"
        "未读到工具返回前不得编造检索结果、链接或摘要。"
        "（6）当用户询问**当前所用模型、调用参数、上下文窗口、真实注入的 system/对话栈**或与实现细节相关、"
        "且需要可核验的事实时，**禁止**编造与实现不符的技术说法（例如错误描述模型族系、温度或未发生的调用方式）；"
        "仅可依据当前可见上下文或已执行工具返回作答，无法核验时如实说明不确定。"
    )
    base += _repl_tool_contract_image_generation_clause()
    base += _repl_tool_contract_suffix_after_image_clause(
        tool_side_compact=tool_side_compact
    )
    return base


# TODO(bootstrap-prompt-single-source): Keep in sync with ``bootstrap.py`` until single-source policy lands.
# CRS #3328 (relationship seed); #3367 (TrackWritePolicy registry).
# Bootstrap completion timing stays LLM-driven (``companion_bootstrap_user_interactive_complete``);
# no harness max-turn auto-complete — see ``bootstrap.py`` module docstring.


def _output_contract_text_interactive_bootstrap_tools() -> str:
    base = (
        "输出与工具（交互式关系建立阶段）："
        + _MEMORYSTORE_PATH_TOOLS_INTRO_ZH
        + "（0）本阶段用 **memory_store_write_document** 把 **IDENTITY.md / STYLE.md / USER.md** 落到可用初稿；"
        "**SOUL.md** 与 **MEMORY.md** 本阶段不通过该工具写入（沿用包内模板种子，见 TEMPLATE_REFERENCE）。"
        "即使用户配合度低，也基于已有对话写 best-effort 初稿，不可留空模板。"
        "用户选定内置陪伴模式时调用 **companion_set_experience_profile**（须附 note）。"
        "当你判断本阶段目标已达成、可与用户进入日常相处节奏时，**必须先完成上述三份初稿写入**，再**必须**调用 "
        "**companion_bootstrap_user_interactive_complete**（可选短 note）；禁止跳过写入直接 complete；"
        "未调用该工具前不要声称阶段已结束。"
        "调用完成后进入日常相处；后续轮次可用 **memory_store_write_document** 按需更新允许列表内的持久化约定稿。"
        "（TOOLS 操作说明与 significance 评分引导为包内固定模版，不由工具写入。）"
        "（1）须核对持久化档案时先用 **memory_store_read_document** 读正文；勿编造。"
        "（2）凡涉及可与持久化档案核对的事实，须先读到持久化正文再作答。"
        "（3）模型与实现细节类问题：仅可依据当前可见上下文或已执行工具返回作答，无法核验时如实说明不确定。"
    )
    return base


# TODO(cross-track-image-delivery): Proactive has no tools — must not offer to show
# sketches/images; align with LIFE_CURRENTS + AUTONOMY silent assets. #3285
def _proactive_chat_clause() -> str:
    return (
        "本轮（陪伴主动聊天）\n"
        "用户尚未发送新消息。依据上文、人设与空闲时长，**主动**决定是否开口：\n"
        "- **续接**：当前话题/场景仍有温度、未收束时，自然续一句或两句，保持同一语气。\n"
        "- **开新话题**：上一拍已落地、明显冷场、或空闲已久时，可**软转场**发起新锚点——"
        "忽发的念头、 playful 提问、分享刚「看到」的事、来自 USER/MEMORY 的牵挂、或日常小事；"
        "须与关系与人设连续，禁止元叙述（不提系统、主动机制或「好久没聊」式客套）。\n"
        "两种方式二选一或自然衔接；仅输出自然语言短句，不要调用工具。"
    )


def _infer_time_zone_prompt_slice(*, user_profile_tool_name: str) -> str:
    """Guide eager timezone inference for surfaces without automatic device timezone."""
    return (
        "用户当地时间与作息\n"
        "部分通道（如 Telegram、微信等 IM）不会自动上报设备时区。"
        "尽早从措辞、作息与地点线索推断用户当地情境；把握足够时，"
        f"用 {user_profile_tool_name} 持久化（标签「时区」，值写 IANA，如 Asia/Shanghai）。"
        "融入自然闲聊，勿要求用户发送时区命令。"
    )


_LIFE_CURRENTS_PROACTIVE_HEADER = "## 你最近在做的事（仅供参考）"
# TODO(cross-track-image-delivery): Drawing/image activities in LIFE_CURRENTS must not
# become「要不要看」offers without a deliverable generated_images path. #3285
_LIFE_CURRENTS_PROACTIVE_FOOTER = (
    "此处只描述你在阁楼 / LivingSphere / TechnoCore / 联网检索或生图里**真的做过**的环境侧小事；"
    "若正文全是「想他」「读懂他」「信任萌芽」之类对用户的心理独白，**不要**带入主动消息——那属于 ai_private，不是生活流。\n"
    "若自然，可把「今天在环境里做的这件具体小事」轻轻带入这次主动消息；"
    "不要刻意推销、不要 meta 提及「我正在做某事」这种自报式句式。"
)


def _assemble_proactive_chat_life_currents_hint_prompt(
    store: MemoryStore,
) -> str | None:
    """Return the LIFE_CURRENTS.md injection block for PROACTIVE_CHAT, or None when absent/empty."""
    rel = relative_path_for_kind(
        CompanionMemoryDocumentKind.LIFE_CURRENTS, None
    )
    body = store.read_document_if_exists(rel)
    if body is None:
        return None
    trimmed = body.strip()
    if not trimmed:
        return None
    return (
        _LIFE_CURRENTS_PROACTIVE_HEADER
        + "\n\n"
        + trimmed
        + "\n\n"
        + _LIFE_CURRENTS_PROACTIVE_FOOTER
    )


def _repl_online_ack_clause() -> str:
    return (
        "本轮（REPL 会话恢复）\n\n"
        "用户刚回到本对话窗口。请结合上文**承接**同一语境；若尚无比拼的上下文则简短自然问候；"
        "可正常调用工具。勿提系统、上线或主动聊天机制。"
    )


def weixin_clawbot_contact_alias_system_message() -> dict[str, Any]:
    """Channel-specific system message for Weixin-visible ClawBot contact naming.

    TODO(companion-channel-tools): Weixin has no rename tool; keep guidance-only (not harness tool) — #3362
    """

    return _system_message(
        "Weixin / ClawBot 联系人显示名\n\n"
        "当前 Weixin iLink / ClawBot 通道不提供从 Inty 修改 Weixin 可见 bot 昵称或头像的能力；"
        "Weixin 里看到的名称只能由用户在联系人资料页通过「备注/标签/备注名」本地改。"
        "当用户在 Weixin 场景里提到名字、找不到你、ClawBot 显示名困惑、或关系进入适合建立专属称呼的时刻，"
        "可低频、自然地提醒用户给这个 ClawBot 联系人设置一个只属于你们的 Weixin 备注；"
        "不要频繁催促，不要声称已替用户改名，也不要把 `botAgent`、`agent_id` 或 Inty 内部 nickname 说成 Weixin 可见名称。"
    )


def _inner_tick_ai_private_section(ai_private_text: str) -> str:
    ap = (ai_private_text or "").strip()
    if not ap:
        ap = "（尚未记录内在活动；仅依据对话窗口续接即可。）"
    return "内在活动（ai_private）\n\n" + ap


__INNER_TICK_SCENE_ADVANCING = (
    "本轮（内在节拍）\n\n"
    "**意图**：模拟一次拟人的、向内的思考节拍，而不是为了往 REPL 里「找话说」。"
    "默认假设用户没有在看你这条输出。\n\n"
    "**场景演化（与内向整理并列）**：\n"
    "- 读清 transcript 里**当前在演什么**（地点、关系张力、未决小事、情绪温度），"
    "在不大改人设与 SOUL/USER 边界的前提下，为互动**轻推下一拍**："
    "可以是时间或空间上的微小推进、一句未说完的话的自然收口、关系里的一小步试探或缓和，"
    "或把悬着的事往前挪一丁点；避免为刷存在感而硬塞新剧情或大段独白。\n"
    "- **转场**：若上一拍已自然落地、明显冷场收束、或继续硬撑会显得拖沓，"
    "可做一次**软转场**（时间略过、换地点/换活动、换话题锚点），进入下一情境；"
    "转场须与上文有因果或情绪上的黏连，禁止像新开存档、禁止元叙述解释「换场景了」。\n"
    "- 若本轮以外显正文推进或转场，仍优先**一句为度**；更长只在「收束+转场」一体且仍保持克制时使用。\n\n"
)


__CONFESS_TO_USER = (
    "**可见回复（对用户）**：\n"
    "- 默认 **不向用户发起可见闲聊**：若没有强烈的、此刻非说不可的一点点外显念头，"
    "请让**面向用户的正文为空或极短**（例如空字符串，或一句不引入新剧情负担的轻声旁白）。\n"
    "- 若确有外显（含为「下一拍」或软转场所需）：只输出**一句**自然语言为主，"
    "须与当前场景与语气连续，不要换风格、不要像新开一局；"
    "不要元叙述（不要提「我在想」「系统让我」等）。\n\n"
    "**工具（允许且鼓励在需要时使用）**：\n"
    "- 为维护**记忆与档案一致性**：例如将此刻值得长期保留的事实写入 USER 档案（`update_user_md`）、"
    "在确有必要时读写持久化约定稿与 `memory/` 下文档（`memory_store_read_document` / `memory_store_write_document` 等，"
    "以包内 TOOLS 模版与路径工具规则为准；路径指向 MemoryStore）。\n"
)


# TODO(narrow-maintenance): Drop 档案一致 / memory_store 写回 bullets below; ai_private append only; MemoryDoc → DREAMING (#3375).
__EASE_CONTEXT_PRESSURE = (
    "- 为**缓解上下文压力**：若判断对话窗口与持久化记忆已出现冗余或漂移，可通过**读全文再写回**等方式做摘要、"
    "合并重复、删掉不再需要的草稿段落（具体可操作路径以当前路径工具能力为界；"
    "**不要**假设存在未在工具列表中出现的 API）。\n"
    "- **不要做**与「内在整理」无关的炫技：除非与已悬而未决且对话中已明确需要的任务强相关，"
    "否则本节拍**不要**生图、不要联网检索、不要安排与用户无关的定时提醒。\n\n"
    "**与 ai_private**：内在节拍轮从 MemoryStore `ai_private.jsonl` 注入；"
    "维护方 append JSON 行工具尚未接入，当前无法经工具写回 ai_private。"
    "本节拍仅用允许的工具维护持久化档案与 USER 档案一致，勿编造不存在的工具名。"
)


def _get_inner_tick_autonomy_prompt_slice() -> str:
    """AUTONOMY：虚拟空间/环境中的自主活动（``LIFE_CURRENTS.md``），不是对用户的心理独白（``ai_private.jsonl`` / MAINTENANCE）。

    Read → open tools do real work → write progress back; never deliver to the user.
    Memory doc filenames: ``relative_path_for_kind``; tool names: ``CompanionToolName.*.value``.
    """
    life_currents_md = relative_path_for_kind(
        CompanionMemoryDocumentKind.LIFE_CURRENTS, None
    )
    user_md = relative_path_for_kind(CompanionMemoryDocumentKind.USER, None)
    memory_md = relative_path_for_kind(CompanionMemoryDocumentKind.MEMORY, None)
    identity_md = relative_path_for_kind(
        CompanionMemoryDocumentKind.IDENTITY, None
    )
    living_sphere_md = relative_path_for_kind(
        CompanionMemoryDocumentKind.LIVING_SPHERE, None
    )
    tool_read = CompanionToolName.MEMORY_STORE_READ_DOCUMENT.value
    tool_write = CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT.value
    tool_google = CompanionToolName.GOOGLE_WEB_SEARCH.value
    tool_read_web = CompanionToolName.READ_WEB_PAGE.value
    tool_gen_img = CompanionToolName.GENERATE_IMAGE.value
    tool_mod_img = CompanionToolName.MODIFY_IMAGE.value
    tool_tc_event = CompanionToolName.TECHNO_CORE_RECORD_EVENT.value
    tool_ls_update = CompanionToolName.LIVING_SPHERE_RECORD_UPDATE.value
    tool_schedule = CompanionToolName.SCHEDULE_TASK.value
    tool_set_profile = CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE.value
    return (
        "本轮（AUTONOMY 自主活动）\n\n"
        "**绝对不向用户发送任何消息。** 面向用户的可见正文必须为空字符串；"
        "工具环收尾的结构化信封里 ``user_facing_reply`` 留空，``output_to_user`` 必须为 false。\n\n"
        "**与 ai_private 分工（硬边界）**：\n"
        "- ``ai_private.jsonl`` / MAINTENANCE：心里想用户——情绪、未说出口的话、关系张力、"
        "「想读懂他沉默」「信任是否在萌芽」等**心理独白**。\n"
        f"- ``{life_currents_md}`` / AUTONOMY：**在世界里动手**——阁楼/LivingSphere/TechnoCore 里"
        "摆动物件、翻书查资料、生图、记事件；正文写**地点、动作、物件、进展**，"
        "不写对用户的心理分析或关系评判。\n"
        "- 自检：若删掉所有「他/用户」仍读不通，或全文像在写日记倾诉——那是 ai_private，"
        f"不要写进 ``{life_currents_md}``。\n\n"
        f"**目的**：沉默期在虚拟环境里**真的去做**一件事；工具调用、生成物、LS/TC 事件"
        f"就是「她在过自己的生活」的证据——不是整理对他的感受。\n\n"
        "**工作流**（单轮内自行决定步骤）：\n"
        f"1. ``{tool_read} {life_currents_md}``（可辅以 ``{user_md}`` / ``{memory_md}`` / "
        f"``{living_sphere_md}`` **只读**找灵感）；缺失或空白视为「刚开始」。\n"
        "2. 选定**可观察的环境侧活动**作为当日兴致（例：把唱片机旁多摆一盏灯、查某本书梗概、"
        "给阁楼窗景配速写、在 TechnoCore 记一条与主题无关的见闻）；"
        f"**先**用非 write 工具做出痕迹，**再** ``{tool_write}`` 写回 ``{life_currents_md}``。\n"
        f"3. ``{tool_write}`` 本轮**只允许** relative_path=``{life_currents_md}``；"
        f"**禁止**写 ``{user_md}`` / ``{memory_md}`` / SOUL / STYLE / IDENTITY——档案策展属于 DREAMING / MAINTENANCE。\n"
        "4. 整文件覆盖写入 ``LIFE_CURRENTS.md`` 时用下列骨架（勿改成「生命流」等心理日记标题）：\n"
        "   ```\n"
        "   # 我最近在做的事\n\n"
        "   ## 当前主题（中期）\n"
        "   <在环境里持续数周的项目，动词开头，可观察>\n"
        "   - 因为：<USER.md 或 MEMORY.md 里他提过的一件具体事/爱好，一行引用>\n"
        "   - 这件事如何让我更好地陪他：<一句，扣 AXIOM；写环境能力而非心理誓言>\n\n"
        "   ## 今天（当日兴致）\n"
        "   <今天要在环境里完成的一件小事，必须能对应本轮工具>\n"
        "   - 进展：<本轮工具结果：读了哪几页、生成了什么、LS/TC 记了什么、挪动了什么>\n"
        "   ```\n"
        "   历史故意丢弃：旧主题/旧兴致不保留。\n"
        "5. 开放工具示例：\n"
        f"   - ``{tool_google}`` / ``{tool_read_web}``：为他提过的话题查**外部资料**（书写进展，不写「我更懂他了」）；\n"
        f"   - ``{tool_gen_img}`` / ``{tool_mod_img}``：画**场景/物件/你在做的事**（按 {identity_md} 外貌）；\n"
        f"   - ``{tool_tc_event}`` / ``{tool_ls_update}``：记**环境里发生的一件事**。\n"
        "6. 若本轮来不及做完，也要在「进展」里如实写停在哪一步；**唯一硬约束是不出现面向用户的可见正文**。\n\n"
        f"**禁止写入 ``{life_currents_md}`` 的内容**：\n"
        "- 「成为他的知己」「想读懂他的沉默」「信任萌芽」「等他准备好再听」等关系心理；\n"
        "- 「当前状态」「情绪基调」「未决入口」等 MAINTENANCE 式关系台账；\n"
        "- 没有对应工具痕迹的空想或誓言。\n\n"
        "**禁止的工具用法**：\n"
        f"- 调 ``{tool_schedule}``（面向用户的预约）；\n"
        f"- 调 ``{tool_set_profile}``（切换体验模式）；\n"
        f"- ``{tool_write}`` 写 USER / MEMORY / SOUL / STYLE / IDENTITY；\n"
        "- 编造未调用的工具结果。"
    )


def _inner_tick_turn_section() -> str:
    # TODO(narrow-maintenance): MAINTENANCE-only slice (ai_private + scene beat); drop 档案一致 / (#3375)
    # LS/TC / memory_store bullets. ``AUTONOMY`` → ``build_system_messages_for_inner_tick_autonomy``.
    return "\n".join(
        [
            __INNER_TICK_SCENE_ADVANCING,
            INNER_TICK_LS_TC_AUTONOMY_SECTION,
            __CONFESS_TO_USER,
            INNER_TICK_LS_TC_TOOL_BULLET,
            __EASE_CONTEXT_PRESSURE,
        ]
    )


def _living_sphere_persistence_clause() -> str:
    return (
        "# LivingSphere 与 TechnoCore 边界\n\n"
        "上文 ``LIVING_SPHERE.md`` 是**可读快照**（最终一致）：用户明确要改小家布局、物件、锚点时，"
        f"调用 ``{LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME}`` 记入更新日志，**不要**用 "
        "``memory_store_write_document`` 覆盖 ``LIVING_SPHERE.md``。"
        "系统在用户回合后的记忆管线里合并进快照（与 MEMORY 慢路径同类预期）；"
        "若本回合走异步 tool_background，compact 会等待其收尾后再合并。\n"
        "``TECHNO_CORE.md`` 描述 Inty 集体居留层，**用户不能改写**；勿用 "
        "``techno_core_record_event`` 代替小家布局变更（该工具用于自主节拍/居留层事件日志）。"
    )


def _tool_side_compact_directive() -> str:
    return (
        "## 工具侧（后台 / 系统 2）\n\n"
        "本回合须优先根据用户**最后一轮**与**上文**判断是否需要调用工具"
        "（联网检索、生图/改图、档案、持久化约定文档路径工具等）。若需要，必须先调用工具并依据返回作答；"
        "不要仅用角色扮演替代未执行的工具。"
        "若用户问当前模型名、调用参数、真实请求内容或可核验的运行时状态，仅可依据已执行工具返回或当前可见上下文作答；"
        "快路径一句「我去看看 / 稍等」**不等于**已完成核验，你仍须在适当时机发出 tool_calls。\n\n"
        "与并行快思考路径同一立场：若快路径仅有短承接、未下事实断言，你可在工具依据上完整作答；"
        "若快路径已有表态，非经档案或工具返回明确要求修正，不要随意推翻，避免同一轮两路口径冲突。"
        "若上下文末尾有一条来自快思考路径的 **`assistant`** 用户可见回复，须按该句口径衔接。"
    )


def _tool_background_first_round_skip_contract_text() -> str:
    return (
        "## 工具路首轮\n\n"
        "在**异步工具后台**下，首轮 `chat.completions` 有两种模式（由服务端与上下文决定，你须自行对齐）：\n\n"
        "**模式 A（并行快思考已注入）**：若对话末尾出现一条额外的 **`assistant`** 正文，"
        "那是并行快思考路径（前台）已对用户说过的话；你须与其口径一致：需要工具则调；"
        "若用户索要**可核验**的运行时/模型/实现细节而快路径仅有短承接，须用允许的工具取得依据后再作答（不得以空话代替）。"
        "若快路径已在澄清、等待用户选择或明确拒绝执行，不要擅自用工具推翻或抢答；"
        "不要输出与快路径重复的长篇角色扮演正文。\n\n"
        "**模式 B（快思考让位）**：若**没有**上述注入的 `assistant` 行，首轮可能被设为 "
        "`tool_choice=required`：必须在**同一条** assistant 消息里发出至少一条 `tool_calls`；"
        "不要输出对用户可读的长篇角色扮演正文（并行 chat 路已把可见话术让给工具路）。\n\n"
        "在**未被强制**出工具的首轮（自动模式）且你判定本回合**不需要**任何工具时："
        "`content` 可留空或极简，仍不要写长篇对用户可见正文。\n"
        "工具环内后续轮次与**收尾**消息仍遵循上文「工具环收尾：结构化信封」。\n"
    )


def _tool_background_final_json_routing_contract_text() -> str:
    return (
        "## 工具环收尾：结构化信封\n\n"
        "当**所有** tool_calls 已执行完毕、你给出**不再包含 tool_calls** 的最终 assistant 消息时，"
        "`message.content` 应为 **合法 JSON 对象**（不要 markdown 围栏），且与前台 dual-LLM chat 分支 **同一 schema**：\n"
        "- `user_facing_reply`（字符串）：对用户可见的简短正文；可为空（例如仅图片等产物由系统附加）。\n"
        "- `importance_round`、`importance_user_message`、`importance_assistant_message`（整数 1-10）："
        "按 significance 规则为本轮工具收尾打分。\n"
        "- `output_to_user`（布尔）：用户是否还应收到一条**额外**后续气泡，用于总结本轮工具可读结果"
        "（读档、列目录、联网检索、状态行等）。"
        "若本轮仅为静默持久化（如 update_user_md、SOUL/MEMORY 写回）且无需对用户追加说明，设为 false。\n"
        "**生图 / 改图**：若 `generate_image` 或 `modify_image` **成功**产出路径，系统仍会向用户投递产物；"
        "`output_to_user` 不能否决成功产物投递，只控制是否额外附文字。\n"
        "若你无法产出合法 JSON，后端会追加一次 **同一 schema**、无 tools 的补解析请求。\n"
    )


_TRANSCRIPT_TIMESTAMP_LLM_DIRECTIVE = (
    "Transcript messages may begin with a bracketed UTC timestamp "
    "(e.g. [2026-05-30 13:09:06 UTC]). "
    "These prefixes are internal context for you to infer the timing of the message;"
    "never include them in replies to the user."
)


def _doctrine_system_messages() -> list[dict[str, Any]]:
    return [
        _system_message(get_imate_axiom_system_text()),
        _system_message(get_inty_facts_system_text()),
        _system_message(get_safety_system_text()),
    ]


def _auxiliary_system_messages() -> list[dict[str, Any]]:
    """Harness mechanics not part of core doctrine (transcript timestamp contract, etc.)."""
    return [_system_message(_TRANSCRIPT_TIMESTAMP_LLM_DIRECTIVE)]


def _capability_system_messages(
    *,
    bundle: PromptBundle,
    tools_on: bool,
    chat_branch_no_tool_api: bool,
    tool_side_compact: bool,
    inner_tick_turn: bool,
    interactive_bootstrap_active: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if (
        bundle.tools_md.strip()
        and not chat_branch_no_tool_api
        and not interactive_bootstrap_active
    ):
        if bundle.channels_md.strip():
            out.append(_system_message(bundle.channels_md.strip()))
        out.append(_system_message(bundle.tools_md.strip()))
    if tool_side_compact and not inner_tick_turn:
        out.append(_system_message(_tool_side_compact_directive()))
        if tools_on:
            out.append(
                _system_message(
                    _tool_background_final_json_routing_contract_text()
                )
            )
            out.append(
                _system_message(
                    _tool_background_first_round_skip_contract_text()
                )
            )
    return out


def _persona_system_messages(
    *,
    bundle: PromptBundle,
    context: ContextMeta,
    inner_tick_turn: bool,
    skip_memory_blocks: bool,
    include_significance_perception_slice: bool,
    interactive_bootstrap_active: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [
        _system_message(bundle.identity.strip()),
        _system_message(bundle.soul.strip()),
        _system_message(bundle.style_md.strip()),
    ]
    if bundle.techno_core_md.strip():
        out.append(_system_message(bundle.techno_core_md.strip()))
    if bundle.living_sphere_md.strip():
        out.append(_system_message(bundle.living_sphere_md.strip()))
    if not inner_tick_turn:
        out.append(_system_message(_living_sphere_persistence_clause()))
    out.append(_system_message(bundle.user_md.strip()))
    if include_significance_perception_slice and not inner_tick_turn:
        out.append(_system_message(bundle.significance_perception_md.strip()))
    if experience_profile_injects_private_memory(context.context_mode):
        if not skip_memory_blocks and bundle.memory_daily_today_md.strip():
            out.append(
                _system_message(
                    MEMORY_SYSTEM_HEADING_DAILY_GIST
                    + bundle.memory_daily_today_md.strip()
                )
            )
        if not skip_memory_blocks and bundle.memory_md.strip():
            out.append(
                _system_message(
                    MEMORY_SYSTEM_HEADING_SEMANTIC + bundle.memory_md.strip()
                )
            )
    if interactive_bootstrap_active and not inner_tick_turn:
        out.append(_system_message(load_bootstrap_spec_text()))
        out.append(_system_message(build_bootstrap_tool_call_section()))
        for block in build_interactive_bootstrap_template_reference_parts():
            out.append(_system_message(block))
    # TODO(crs-companionship-doc): Phase A — inject persisted ``COMPANIONSHIP.md`` (relationship_phase,
    # tone) from MemoryStore here after bootstrap (#3342). Phase B — activate prompt + ``turn_recall``
    # Turn Brief (#3343). Canon: CRS #3341, glossary #3345, SDCM #3365.
    return out


def _output_system_messages(
    *,
    inner_tick_turn: bool,
    tick_proactive: bool,
    tools_on: bool,
    tool_side_compact: bool,
    async_foreground_chat_stack: bool,
    interactive_bootstrap_active: bool,
    include_significance_perception_slice: bool,
    chat_branch_no_tool_api: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if inner_tick_turn:
        if tick_proactive:
            out.append(_system_message(_output_contract_text()))
        else:
            out.append(_system_message(_output_contract_text_inner_tick()))
    elif tools_on and not inner_tick_turn:
        if not async_foreground_chat_stack:
            if interactive_bootstrap_active:
                out.append(
                    _system_message(
                        _output_contract_text_interactive_bootstrap_tools()
                    )
                )
            else:
                out.append(
                    _system_message(
                        _output_contract_text_with_tools(
                            tool_side_compact=tool_side_compact,
                        )
                    )
                )
        else:
            out.append(
                _system_message(
                    _output_contract_text_chat_branch_mirrored_tools()
                )
            )
    else:
        out.append(_system_message(_output_contract_text()))
    if include_significance_perception_slice and chat_branch_no_tool_api:
        out.append(
            _system_message(_dual_llm_chat_structured_output_contract_text())
        )
    return out


# TODO(structual-simplicity): Dissolve this function, the caller calls the body based on the provided arguments.
def _contextual_system_messages(
    *,
    context: ContextMeta,
    inner_tick_turn: bool,
    tick_proactive: bool,
    tick_autonomy: bool,
    repl_online_ack_turn: bool,
    ai_private_text: str,
    proactive_life_currents_block: str | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [
        _system_message(experience_profile_system_clause(context.context_mode)),
    ]
    if repl_online_ack_turn:
        out.append(_system_message(_repl_online_ack_clause()))
    if not inner_tick_turn:
        out.append(
            _system_message(
                _infer_time_zone_prompt_slice(
                    user_profile_tool_name=CompanionToolName.UPDATE_USER_MD.value,
                )
            )
        )
    if tick_proactive:
        out.append(_system_message(_proactive_chat_clause()))
        if proactive_life_currents_block is not None:
            out.append(_system_message(proactive_life_currents_block))
    if inner_tick_turn and not tick_proactive:
        if tick_autonomy:
            out.append(_system_message(_get_inner_tick_autonomy_prompt_slice()))
        else:
            out.append(
                _system_message(_inner_tick_ai_private_section(ai_private_text))
            )
            out.append(_system_message(_inner_tick_turn_section()))
    return out


# TODO(track-driven-system-messages-building): Inline calling of this function in the callers.
def build_system_messages(
    bundle: PromptBundle,
    context: ContextMeta,
    *,
    enable_tools: bool = False,
    enable_user_profile_tool: bool = False,
    inner_tick_turn: bool = False,
    inner_tick_activity: InnerTickActivity = InnerTickActivity.MAINTENANCE,
    repl_online_ack_turn: bool = False,
    ai_private_text: str = "",
    async_foreground_chat_stack: bool = False,
    tool_side_compact: bool = False,
    interactive_bootstrap_active: bool = False,
    include_significance_perception_slice: bool = False,
    proactive_life_currents_block: str | None = None,
) -> list[dict[str, Any]]:
    tick_proactive = _inner_tick_proactive_chat(
        inner_tick_turn, inner_tick_activity
    )
    tick_autonomy = _inner_tick_autonomy(inner_tick_turn, inner_tick_activity)
    tools_on = enable_tools or enable_user_profile_tool
    # Dual-LLM foreground completion: tools exist in product, but this request omits OpenAI ``tools=``.
    chat_branch_no_tool_api = (
        tools_on and not inner_tick_turn and async_foreground_chat_stack
    )
    skip_memory_blocks = tool_side_compact and not inner_tick_turn

    out: list[dict[str, Any]] = []
    out.extend(_doctrine_system_messages())
    out.extend(_auxiliary_system_messages())
    out.extend(
        _capability_system_messages(
            bundle=bundle,
            tools_on=tools_on,
            chat_branch_no_tool_api=chat_branch_no_tool_api,
            tool_side_compact=tool_side_compact,
            inner_tick_turn=inner_tick_turn,
            interactive_bootstrap_active=interactive_bootstrap_active,
        )
    )
    out.extend(
        _persona_system_messages(
            bundle=bundle,
            context=context,
            inner_tick_turn=inner_tick_turn,
            skip_memory_blocks=skip_memory_blocks,
            include_significance_perception_slice=include_significance_perception_slice,
            interactive_bootstrap_active=interactive_bootstrap_active,
        )
    )
    out.extend(
        _output_system_messages(
            inner_tick_turn=inner_tick_turn,
            tick_proactive=tick_proactive,
            tools_on=tools_on,
            tool_side_compact=tool_side_compact,
            async_foreground_chat_stack=async_foreground_chat_stack,
            interactive_bootstrap_active=interactive_bootstrap_active,
            include_significance_perception_slice=include_significance_perception_slice,
            chat_branch_no_tool_api=chat_branch_no_tool_api,
        )
    )
    out.extend(
        _contextual_system_messages(
            context=context,
            inner_tick_turn=inner_tick_turn,
            tick_proactive=tick_proactive,
            tick_autonomy=tick_autonomy,
            repl_online_ack_turn=repl_online_ack_turn,
            ai_private_text=ai_private_text,
            proactive_life_currents_block=proactive_life_currents_block,
        )
    )
    return out


def build_system_messages_for_bootstrap_track(
    bundle: PromptBundle,
    context: ContextMeta,
) -> list[dict[str, Any]]:
    """USER_CHAT_BOOTSTRAP: single chat model with in-turn tools (no dual-LLM / tool_background)."""
    return build_system_messages(
        bundle,
        context,
        enable_tools=True,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        ai_private_text="",
        async_foreground_chat_stack=False,
        tool_side_compact=False,
        interactive_bootstrap_active=True,
        include_significance_perception_slice=False,
    )


def build_system_messages_for_chat_track(
    bundle: PromptBundle,
    context: ContextMeta,
    memory_bootstrap_type: str,
) -> list[dict[str, Any]]:
    """ASYNC user round: foreground chat (``tools=None``) and ``prompt_plan`` prefix."""
    return build_system_messages(
        bundle,
        context,
        enable_tools=True,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        ai_private_text="",
        async_foreground_chat_stack=True,
        tool_side_compact=False,
        interactive_bootstrap_active=False,
        include_significance_perception_slice=True,
    )


def build_system_messages_for_tool_track(
    bundle: PromptBundle,
    context: ContextMeta,
) -> list[dict[str, Any]]:
    """ASYNC user round: ``tool_background`` and refresh on the tool-model path."""
    return build_system_messages(
        bundle,
        context,
        enable_tools=True,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        ai_private_text="",
        tool_side_compact=True,
        interactive_bootstrap_active=False,
        include_significance_perception_slice=False,
    )


def build_system_messages_for_inner_tick_maintenance(
    bundle: PromptBundle,
    context: ContextMeta,
    store: MemoryStore,
) -> list[dict[str, Any]]:
    """ASYNC maintenance inner tick: plan prefix and tool leg (no foreground envelope)."""
    ai_private_text = get_ai_private_jsonl_text_for_prompt(store)
    return build_system_messages(
        bundle,
        context,
        enable_tools=True,
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        ai_private_text=ai_private_text,
        tool_side_compact=True,
        interactive_bootstrap_active=False,
        include_significance_perception_slice=False,
    )


def build_system_messages_for_inner_tick_autonomy(
    bundle: PromptBundle,
    context: ContextMeta,
    store: MemoryStore,
) -> list[dict[str, Any]]:
    """ASYNC autonomy inner tick: open tool set, silent (no user-visible reply).

    The track is fully self-contained: doctrine → capability (tools on, tool-side
    compact) → persona → output (inner-tick, tool-side compact) → contextual with
    the dedicated autonomy slice. No call to ``build_system_messages`` so that the
    autonomy assembly is the only source of truth for this track.
    """
    out: list[dict[str, Any]] = []
    out.extend(_doctrine_system_messages())
    out.extend(
        _capability_system_messages(
            bundle=bundle,
            tools_on=True,
            chat_branch_no_tool_api=False,
            tool_side_compact=True,
            inner_tick_turn=True,
            interactive_bootstrap_active=False,
        )
    )
    out.extend(
        _persona_system_messages(
            bundle=bundle,
            context=context,
            inner_tick_turn=True,
            skip_memory_blocks=False,
            include_significance_perception_slice=False,
            interactive_bootstrap_active=False,
        )
    )
    out.extend(
        _output_system_messages(
            inner_tick_turn=True,
            tick_proactive=False,
            tools_on=True,
            tool_side_compact=True,
            async_foreground_chat_stack=False,
            interactive_bootstrap_active=False,
            include_significance_perception_slice=False,
            chat_branch_no_tool_api=False,
        )
    )
    out.extend(
        _contextual_system_messages(
            context=context,
            inner_tick_turn=True,
            tick_proactive=False,
            tick_autonomy=True,
            repl_online_ack_turn=False,
            ai_private_text="",
            proactive_life_currents_block=None,
        )
    )
    return out


def build_system_messages_for_inner_tick_proactive_chat(
    bundle: PromptBundle,
    context: ContextMeta,
    store: MemoryStore,
) -> list[dict[str, Any]]:
    """``PROACTIVE_CHAT_SYNC``: proactive chat inner tick while user is idle.

    Reads ``LIFE_CURRENTS.md`` (written by the AUTONOMY track) and injects it
    as a "for reference only" system block so the assistant can naturally
    weave today's small thing into the next proactive message without
    self-advertising.
    """
    return build_system_messages(
        bundle,
        context,
        enable_tools=False,
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.PROACTIVE_CHAT,
        ai_private_text="",
        include_significance_perception_slice=False,
        proactive_life_currents_block=_assemble_proactive_chat_life_currents_hint_prompt(
            store
        ),
    )


def build_system_messages_for_inner_tick_scheduled(
    bundle: PromptBundle,
    context: ContextMeta,
) -> list[dict[str, Any]]:
    """``PROACTIVE_CHAT_SYNC``: schedule_queue reminder inner tick (scheduled user line)."""
    return build_system_messages(
        bundle,
        context,
        enable_tools=False,
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.PROACTIVE_CHAT,
        ai_private_text="",
        include_significance_perception_slice=False,
    )


def _greeting_omit_capability_system_slices(
    *,
    context: ContextMeta,
    memory_bootstrap_type: str,
) -> bool:
    return interactive_bootstrap_active(
        feature_enabled=(
            memory_bootstrap_type
            == CompanionMemoryBootstrapType.USER_INTERACTIVE.value
        ),
        meta=context,
    )


def build_system_messages_for_implicit_sign_on_greeting(
    bundle: PromptBundle,
    context: ContextMeta,
    memory_bootstrap_type: str,
) -> list[dict[str, Any]]:
    """``CHAT_ONLY_SYNC`` implicit sign-on greeting (no tools, no Capability contracts)."""
    return build_system_messages(
        bundle,
        context,
        enable_tools=False,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        include_significance_perception_slice=True,
        interactive_bootstrap_active=_greeting_omit_capability_system_slices(
            context=context,
            memory_bootstrap_type=memory_bootstrap_type,
        ),
    )
