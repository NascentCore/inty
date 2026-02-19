package ai.sxwl.android.data.http

/**
 * 业务错误码常量。与后端 `app/schemas/response.py`（BusinessErrorCode 及 API 响应规则）保持一致。
 *
 * ## 规则：HTTP 状态码 / body.code / data.error_code
 *
 * - **HTTP status（HTTP 状态码）**：仅用于请求或基础设施失败（4xx/5xx）。
 *   服务端抛出 HTTPException 时，响应为该状态码且 body 常为 `{"detail": "..."}`。
 *   不要用 HTTP 状态码判断业务错误（如需要订阅）。
 *
 * - **Body code（响应 body 的 code）**：成功 = 200。业务错误使用数字码（如 [SUBSCRIPTION_REQUIRED_CODE]）。
 *   响应通常为 HTTP 200；根据解析后的 body 的 `code` 与 `data.error_code` 分支。
 *   NetServiceMgr 的 wrapper 将 body code 200 视为成功。
 *
 * - **data.error_code**：当 body 的 `code` != 200 时，`data` 可能包含字符串
 *   `error_code`（如 [SUBSCRIPTION_REQUIRED_ERROR_CODE]）及可选 `description`。
 *   用 `data.error_code` 做业务错误类型分支；用 body 的 `code` 做数字匹配，`message` 做展示。
 */
object BusinessErrorCodes {

    /** 订阅要求错误 */
    const val SUBSCRIPTION_REQUIRED_CODE = 10001001
    const val SUBSCRIPTION_REQUIRED_ERROR_CODE = "SUBSCRIPTION_REQUIRED"
    const val SUBSCRIPTION_REQUIRED_MESSAGE = "Subscription required"

    /** 图片生成限制达到错误 */
    const val IMAGE_GENERATION_LIMIT_REACHED_CODE = 10001002
    const val IMAGE_GENERATION_LIMIT_REACHED_ERROR_CODE = "IMAGE_GENERATION_LIMIT_REACHED"
    const val IMAGE_GENERATION_LIMIT_REACHED_MESSAGE = "Image generation limit reached"

    /** 角色创建限制达到错误 */
    const val AGENT_CREATION_LIMIT_REACHED_CODE = 10001003
    const val AGENT_CREATION_LIMIT_REACHED_ERROR_CODE = "AGENT_CREATION_LIMIT_REACHED"
    const val AGENT_CREATION_LIMIT_REACHED_MESSAGE = "Character creation limit reached"

    /** 语音生成次数超限制 */
    const val VOICE_GENERATION_LIMIT_REACHED_CODE = 10001004
    const val VOICE_GENERATION_LIMIT_REACHED_ERROR_CODE = "VOICE_GENERATION_LIMIT_REACHED"
    const val VOICE_GENERATION_LIMIT_REACHED_MESSAGE = "Voice generation limit reached"

    /** 访客需登录（请使用 Google 登录） */
    const val GUEST_LOGIN_REQUIRED_CODE = 10001005
    const val GUEST_LOGIN_REQUIRED_ERROR_CODE = "GUEST_LOGIN_REQUIRED"
    const val GUEST_LOGIN_REQUIRED_MESSAGE = "Guest login required - Please sign in with Google"

    /** 图片生成被安全策略拦截 */
    const val IMAGE_GENERATION_BLOCKED_CODE = 10001006
    const val IMAGE_GENERATION_BLOCKED_ERROR_CODE = "IMAGE_GENERATION_BLOCKED"
    const val IMAGE_GENERATION_BLOCKED_MESSAGE = "Image generation was blocked by safety filter"

    /** 实时通话 Agent 数量达到上限 */
    const val LIVE_CHAT_AGENT_LIMIT_REACHED_CODE = 10001007
    const val LIVE_CHAT_AGENT_LIMIT_REACHED_ERROR_CODE = "LIVE_CHAT_AGENT_LIMIT_REACHED"
    const val LIVE_CHAT_AGENT_LIMIT_REACHED_MESSAGE = "Live chat agent limit reached"

    /** 实时通话时长达到上限 */
    const val LIVE_CHAT_DURATION_LIMIT_REACHED_CODE = 10001008
    const val LIVE_CHAT_DURATION_LIMIT_REACHED_ERROR_CODE = "LIVE_CHAT_DURATION_LIMIT_REACHED"
    const val LIVE_CHAT_DURATION_LIMIT_REACHED_MESSAGE = "Live chat duration limit reached"

    /** 业务错误消息映射（code -> message），与后端 8 个错误码一致 */
    val BUSINESS_ERROR_MESSAGES =
        mapOf(
            SUBSCRIPTION_REQUIRED_CODE to SUBSCRIPTION_REQUIRED_MESSAGE,
            IMAGE_GENERATION_LIMIT_REACHED_CODE to IMAGE_GENERATION_LIMIT_REACHED_MESSAGE,
            AGENT_CREATION_LIMIT_REACHED_CODE to AGENT_CREATION_LIMIT_REACHED_MESSAGE,
            VOICE_GENERATION_LIMIT_REACHED_CODE to VOICE_GENERATION_LIMIT_REACHED_MESSAGE,
            GUEST_LOGIN_REQUIRED_CODE to GUEST_LOGIN_REQUIRED_MESSAGE,
            IMAGE_GENERATION_BLOCKED_CODE to IMAGE_GENERATION_BLOCKED_MESSAGE,
            LIVE_CHAT_AGENT_LIMIT_REACHED_CODE to LIVE_CHAT_AGENT_LIMIT_REACHED_MESSAGE,
            LIVE_CHAT_DURATION_LIMIT_REACHED_CODE to LIVE_CHAT_DURATION_LIMIT_REACHED_MESSAGE,
        )
}
