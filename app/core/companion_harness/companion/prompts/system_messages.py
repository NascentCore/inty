"""Companion **system context** assembly for leading ``role: system`` messages.

**Stack order (fixed):** Doctrine → Tools → Persona → Output → Contextual.

Contextual slices use plain lead-in lines (e.g. ``本轮（…）``), not markdown ``##`` headings.

**Scenario → entrypoint** (production; call from ``prompt_stack`` / ``turn`` / ``tool_background``):

| Scenario | Function |
|----------|----------|
| ASYNC user-round foreground + plan prefix | ``build_system_messages_for_chat_track`` |
| ASYNC user-round tool_background / refresh | ``build_system_messages_for_tool_track`` |
| ASYNC maintenance inner tick plan + tool leg | ``build_system_messages_for_inner_tick_maintenance`` |
| Proactive inner tick (``PROACTIVE_CHAT``) | ``build_system_messages_for_inner_tick_proactive_chat`` |
| Implicit sign-on greeting | ``build_system_messages_for_implicit_sign_on_greeting`` |

``build_system_messages`` is the internal combiner; tests may call it directly.

Post-transcript slices (e.g. ``## user-time-context`` in ``turn_pipeline``) are not built here.
"""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.experience_profile import (
    experience_profile_injects_private_memory,
    experience_profile_system_clause,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import CompanionMemoryBootstrapType

from ..ai_private_prompt import get_ai_private_jsonl_text_for_prompt
from ..bootstrap_user_interactive import (
    build_interactive_bootstrap_system_message_parts,
    interactive_bootstrap_active,
)
from app.core.companion_harness.memory.memory_store_scope import (
    get_imate_axiom_system_text,
    get_inty_facts_system_text,
    get_safety_system_text,
)
from app.core.companion_harness.memory.memory_taxonomy import (
    MEMORY_SYSTEM_HEADING_EPISODIC,
    MEMORY_SYSTEM_HEADING_GIST,
    MEMORY_SYSTEM_HEADING_SEMANTIC,
)
from living_sphere.models import LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME

from ..models import ContextMeta, InnerTickActivity, PromptBundle
from .inner_tick_ls_tc import (
    INNER_TICK_LS_TC_AUTONOMY_SECTION,
    INNER_TICK_LS_TC_TOOL_BULLET,
)


def _inner_tick_proactive_chat(
    inner_tick_turn: bool, inner_tick_activity: InnerTickActivity
) -> bool:
    return inner_tick_turn and inner_tick_activity == InnerTickActivity.PROACTIVE_CHAT


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
        "do **not** state concrete model ids, temperatures, or injected stack details here—the parallel tool branch may call "
        "`companion_runtime_inspect` for JSON facts. Do not imply you already ran that tool or «checked internally».\n"
        "  Do not refuse or claim you cannot access MemoryStore text in ways the parallel tool branch will contradict "
        "when it runs allowed file tools; keep this branch aligned with that branch as one persona (fast vs slow).\n"
        "- `importance_round` (integer 1-10): importance of this turn overall given transcript and system context.\n"
        "- `importance_user_message` (integer 1-10): importance of the latest user message alone.\n"
        "- `importance_assistant_message` (integer 1-10): importance of `user_facing_reply` alone.\n"
        "- `output_to_user` (boolean): **must be true** on this foreground dual-LLM chat branch "
        "(the parallel tool branch decides silent vs visible follow-ups).\n"
        "- `reply_modality` (string): `text` or `voice_message`. Choose `voice_message` when you are "
        "primarily sending a spoken voice note to the user (like a real person holding voice mode); "
        "otherwise `text`.\n"
        "- `voice_message_script` (string): exact spoken wording for TTS when `reply_modality` is "
        '`voice_message`; use `""` when modality is `text`. '
        "`user_facing_reply` may still hold a short caption or transcript line when helpful.\n\n"
        "This branch still must not call tools (`tool_choice=none`).\n"
    )


def _output_contract_text_chat_branch_mirrored_tools() -> str:
    return (
        "## 快思考路径（系统 1）与并行工具路径（系统 2）须一致\n\n"
        "你与**并行工具路**是同一人格的两种速度：本路优先低延迟外显；工具路负责读档案、联网、生图、`companion_runtime_inspect` "
        "等须核对或慢步骤。"
        "对用户的事实立场、边界与态度必须一致，禁止「一路拒绝、一路照做」的分裂。\n\n"
        "本路 **API 不带工具**（禁止在本路发起任何 tool_calls），系统提示里也可能未展开完整 TOOLS 操作说明，但你仍须遵守：凡应以持久化档案原文、检索结果或工具返回为准的问题，"
        "不得以「无法读取」「不能向你展示内部文件」等说法抢先否定并行路即将执行的核对；"
        "不要编造档案内容；若并行路会给出依据或原文，本路只用简短自然的承接语（可表示细节马上对齐），"
        "或将 `user_facing_reply` 留空/极短，把可核对正文交给工具路落点。\n\n"
        "当用户询问**当前模型、调用侧参数、真实注入的 system/对话栈**等须可核验的实现细节时："
        "本路只给即时、克制的衔接语，**不得**输出具体模型名、参数或栈细节，**不得**暗示已在无工具返回前完成自省；"
        "可核对事实由并行工具路自愿调用 `companion_runtime_inspect` 取得 JSON 后再由该路收口。\n\n"
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
        + "（1）用户自愿透露、适合长期保存的基本事实，可调用 user_profile_record 写入 USER 档案；"
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
        "且需要可核验的事实时，必须先调用 companion_runtime_inspect 读取 JSON 快照，再依据其中字段用自然语言作答；"
        "**禁止**编造与实现不符的技术说法（例如错误描述模型族系、温度或未发生的调用方式）。"
    )
    base += _repl_tool_contract_image_generation_clause()
    base += _repl_tool_contract_suffix_after_image_clause(
        tool_side_compact=tool_side_compact
    )
    return base


def _output_contract_text_interactive_bootstrap_tools(
    *,
    tool_side_compact: bool = False,
) -> str:
    base = (
        "输出与工具（交互式关系建立阶段）："
        + _MEMORYSTORE_PATH_TOOLS_INTRO_ZH
        + "（0）本阶段核心是**初始化 SOUL 切片**（并同时把 IDENTITY / STYLE / USER / MEMORY 落到可用初稿）；"
        "须用 **companion_update_prompt_slice** 写入上述五份根目录约定稿；**禁止**使用 memory_store_write_document 写入它们。"
        "调用 **companion_bootstrap_user_interactive_complete** 后，**SOUL 即锁定**（不可再改）；"
        "IDENTITY / STYLE / USER / MEMORY 在后续日常轮次仍可用 companion_update_prompt_slice 或 memory_store_write_document 按需更新。"
        "（TOOLS 操作说明与 significance 评分引导为包内固定模版，不由本工具写入。）"
        "当你判断本阶段目标已达成、可与用户进入日常相处节奏时，**必须**调用 "
        "**companion_bootstrap_user_interactive_complete**（可选短 note）；未调用该工具前不要声称阶段已结束。"
        "（1）用户自愿透露、适合长期保存的基本事实，可调用 user_profile_record 写入 USER 档案；"
        "（1.1）当用户明确提出未来提醒，必须先调用 schedule_task；exec_time_utc 须为带时区的 ISO8601。"
        "（2）确有核对持久化约定稿需求时可用 memory_store_list_paths / memory_store_read_document；勿编造内容。"
        "列表目录约束与上文「输出与工具」一致：勿为闲聊列根目录。"
        "（3）凡涉及可与持久化档案核对的事实，须先读到持久化正文再作答。"
        "（4）需要公开可核验信息且持久化文档无依据时，须先调用 google_web_search。"
        "（5）模型与实现细节类问题须先调用 companion_runtime_inspect。"
    )
    base += _repl_tool_contract_image_generation_clause()
    base += _repl_tool_contract_suffix_after_image_clause(
        tool_side_compact=tool_side_compact
    )
    return base


def _proactive_chat_clause() -> str:
    return (
        "本轮（陪伴主动聊天）\n"
        "用户尚未发送新消息。承接上文**同一语境**：延续当前场景、话题与表达风格，自然续一句或两句，"
        "勿改换语气或像重新开始一段对话；仅输出自然语言短句，不要调用工具。"
    )


def _repl_online_ack_clause() -> str:
    return (
        "本轮（REPL 会话恢复）\n\n"
        "用户刚回到本对话窗口。请结合上文**承接**同一语境；若尚无比拼的上下文则简短自然问候；"
        "可正常调用工具。勿提系统、上线或主动聊天机制。"
    )


def _inner_tick_ai_private_section(ai_private_text: str) -> str:
    ap = (ai_private_text or "").strip()
    if not ap:
        ap = "（尚未记录内在活动；仅依据对话窗口续接即可。）"
    return "内在活动（ai_private）\n\n" + ap


def _inner_tick_turn_section() -> str:
    return (
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
        + INNER_TICK_LS_TC_AUTONOMY_SECTION
        + (
            "**可见回复（对用户）**：\n"
            "- 默认 **不向用户发起可见闲聊**：若没有强烈的、此刻非说不可的一点点外显念头，"
            "请让**面向用户的正文为空或极短**（例如空字符串，或一句不引入新剧情负担的轻声旁白）。\n"
            "- 若确有外显（含为「下一拍」或软转场所需）：只输出**一句**自然语言为主，"
            "须与当前场景与语气连续，不要换风格、不要像新开一局；"
            "不要元叙述（不要提「我在想」「系统让我」等）。\n\n"
            "**工具（允许且鼓励在需要时使用）**：\n"
            "- 为维护**记忆与档案一致性**：例如将此刻值得长期保留的事实写入 USER 档案（`user_profile_record`）、"
            "在确有必要时读写持久化约定稿与 `memory/` 下文档（`memory_store_read_document` / `memory_store_write_document` 等，"
            "以包内 TOOLS 模版与路径工具规则为准；路径指向 MemoryStore）。\n"
        )
        + INNER_TICK_LS_TC_TOOL_BULLET
        + "- 为**缓解上下文压力**：若判断对话窗口与持久化记忆已出现冗余或漂移，可通过**读全文再写回**等方式做摘要、"
        "合并重复、删掉不再需要的草稿段落（具体可操作路径以当前路径工具能力为界；"
        "**不要**假设存在未在工具列表中出现的 API）。\n"
        "- **不要做**与「内在整理」无关的炫技：除非与已悬而未决且对话中已明确需要的任务强相关，"
        "否则本节拍**不要**生图、不要联网检索、不要安排与用户无关的定时提醒。\n\n"
        "**与 ai_private**：内在节拍轮从 MemoryStore `ai_private.jsonl` 注入（维护方可 append JSON 行）；"
        "本节拍仅用允许的工具维护持久化档案与 USER 档案一致，勿编造不存在的工具名。"
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
        "（联网检索、生图/改图、档案、持久化约定文档路径工具、companion_runtime_inspect 等）。若需要，必须先调用工具并依据返回作答；"
        "不要仅用角色扮演替代未执行的工具。"
        "若用户问当前模型名、调用参数、真实请求内容或可核验的运行时状态，须自愿调用 companion_runtime_inspect 再作答；"
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
        "若用户索要**可核验**的运行时/模型/实现细节而快路径仅有短承接，你仍须自愿调用 "
        "`companion_runtime_inspect`（不得以空话代替）。"
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
        "（读档、列目录、联网检索、状态行、runtime_inspect 等）。"
        "若本轮仅为静默持久化（如 user_profile_record、SOUL/MEMORY 写回）且无需对用户追加说明，设为 false。\n"
        "- `reply_modality`（字符串）：`text` 或 `voice_message`；主交付为语音便签时用 `voice_message`。\n"
        '- `voice_message_script`（字符串）：`voice_message` 时对用户诵读的完整口语文本；`text` 时为 `""`。\n'
        "**生图 / 改图**：若 `generate_image` 或 `modify_image` **成功**产出路径，系统仍会向用户投递产物；"
        "`output_to_user` 不能否决成功产物投递，只控制是否额外附文字。\n"
        "若你无法产出合法 JSON，后端会追加一次 **同一 schema**、无 tools 的补解析请求。\n"
    )


def _doctrine_system_messages() -> list[dict[str, Any]]:
    return [
        _system_message(get_imate_axiom_system_text()),
        _system_message(get_inty_facts_system_text()),
        _system_message(get_safety_system_text()),
    ]


def _tools_system_messages(
    *,
    bundle: PromptBundle,
    tools_on: bool,
    chat_branch_no_tool_api: bool,
    tool_side_compact: bool,
    inner_tick_turn: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if bundle.tools_md.strip() and not chat_branch_no_tool_api:
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
    tools_on: bool,
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
        if not skip_memory_blocks and bundle.memory_raw_diary_today_md.strip():
            out.append(
                _system_message(
                    MEMORY_SYSTEM_HEADING_EPISODIC
                    + bundle.memory_raw_diary_today_md.strip()
                )
            )
        if (
            not skip_memory_blocks
            and bundle.memory_day_summary_today_md.strip()
        ):
            out.append(
                _system_message(
                    MEMORY_SYSTEM_HEADING_GIST
                    + bundle.memory_day_summary_today_md.strip()
                )
            )
        if not skip_memory_blocks and bundle.memory_md.strip():
            out.append(
                _system_message(
                    MEMORY_SYSTEM_HEADING_SEMANTIC + bundle.memory_md.strip()
                )
            )
    if interactive_bootstrap_active and tools_on and not inner_tick_turn:
        for block in build_interactive_bootstrap_system_message_parts():
            out.append(_system_message(block))
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
                        _output_contract_text_interactive_bootstrap_tools(
                            tool_side_compact=tool_side_compact,
                        )
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


def _contextual_system_messages(
    *,
    context: ContextMeta,
    inner_tick_turn: bool,
    tick_proactive: bool,
    repl_online_ack_turn: bool,
    ai_private_text: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [
        _system_message(experience_profile_system_clause(context.context_mode)),
    ]
    if repl_online_ack_turn:
        out.append(_system_message(_repl_online_ack_clause()))
    if tick_proactive:
        out.append(_system_message(_proactive_chat_clause()))
    if inner_tick_turn and not tick_proactive:
        out.append(
            _system_message(_inner_tick_ai_private_section(ai_private_text))
        )
        out.append(_system_message(_inner_tick_turn_section()))
    return out


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
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
) -> list[dict[str, Any]]:
    tick_proactive = _inner_tick_proactive_chat(
        inner_tick_turn, inner_tick_activity
    )
    tools_on = enable_tools or enable_user_profile_tool
    # Dual-LLM foreground completion: tools exist in product, but this request omits OpenAI ``tools=``.
    chat_branch_no_tool_api = (
        tools_on and not inner_tick_turn and async_foreground_chat_stack
    )
    skip_memory_blocks = tool_side_compact and not inner_tick_turn

    out: list[dict[str, Any]] = []
    out.extend(_doctrine_system_messages())
    out.extend(
        _tools_system_messages(
            bundle=bundle,
            tools_on=tools_on,
            chat_branch_no_tool_api=chat_branch_no_tool_api,
            tool_side_compact=tool_side_compact,
            inner_tick_turn=inner_tick_turn,
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
            tools_on=tools_on,
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
            repl_online_ack_turn=repl_online_ack_turn,
            ai_private_text=ai_private_text,
        )
    )
    return out


def build_system_messages_for_chat_track(
    bundle: PromptBundle,
    context: ContextMeta,
    memory_bootstrap_type: str,
) -> list[dict[str, Any]]:
    """ASYNC user round: foreground chat (``tools=None``) and ``prompt_plan`` prefix."""
    bootstrap_on = interactive_bootstrap_active(
        feature_enabled=(
            memory_bootstrap_type
            == CompanionMemoryBootstrapType.USER_INTERACTIVE.value
        ),
        meta=context,
    )
    return build_system_messages(
        bundle,
        context,
        enable_tools=True,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        ai_private_text="",
        async_foreground_chat_stack=True,
        tool_side_compact=False,
        interactive_bootstrap_active=bootstrap_on,
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


def build_system_messages_for_inner_tick_proactive_chat(
    bundle: PromptBundle,
    context: ContextMeta,
) -> list[dict[str, Any]]:
    """``PROACTIVE_CHAT_SYNC``: proactive chat inner tick while user is idle."""
    return build_system_messages(
        bundle,
        context,
        enable_tools=False,
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.PROACTIVE_CHAT,
        ai_private_text="",
        include_significance_perception_slice=False,
    )


def build_system_messages_for_implicit_sign_on_greeting(
    bundle: PromptBundle,
    context: ContextMeta,
) -> list[dict[str, Any]]:
    """``CHAT_ONLY_SYNC`` implicit sign-on greeting (no tools, no tool contracts)."""
    return build_system_messages(
        bundle,
        context,
        enable_tools=False,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        include_significance_perception_slice=True,
    )
