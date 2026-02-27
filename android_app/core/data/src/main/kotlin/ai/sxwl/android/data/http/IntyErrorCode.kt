package ai.sxwl.android.data.http

import kotlinx.serialization.Serializable

/** 与后端 app/schemas/response.py BusinessErrorCode 数字码一致 */
@Serializable
enum class IntyErrorCode(val code: Int) {
    /** 需要订阅 */
    SUBSCRIPTION_REQUIRED(BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE),
    /** 图片生成次数达到上限 */
    IMAGE_GENERATION_LIMIT_REACHED(BusinessErrorCodes.IMAGE_GENERATION_LIMIT_REACHED_CODE),
    /** 角色创建数量达到上限 */
    AGENT_CREATION_LIMIT_REACHED(BusinessErrorCodes.AGENT_CREATION_LIMIT_REACHED_CODE),
    /** 语音生成次数达到上限 */
    VOICE_GENERATION_LIMIT_REACHED(BusinessErrorCodes.VOICE_GENERATION_LIMIT_REACHED_CODE),
    /** 访客需登录 */
    GUEST_LOGIN_REQUIRED(BusinessErrorCodes.GUEST_LOGIN_REQUIRED_CODE),
    /** 图片生成被安全策略拦截 */
    IMAGE_GENERATION_BLOCKED(BusinessErrorCodes.IMAGE_GENERATION_BLOCKED_CODE),
    /** 实时通话 Agent 数量达到上限 */
    LIVE_CHAT_AGENT_LIMIT_REACHED(BusinessErrorCodes.LIVE_CHAT_AGENT_LIMIT_REACHED_CODE),
    /** 实时通话时长达到上限 */
    LIVE_CHAT_DURATION_LIMIT_REACHED(BusinessErrorCodes.LIVE_CHAT_DURATION_LIMIT_REACHED_CODE),
    SESSION_ERROR(10000000),
    UNKNOWN(-1),
}
