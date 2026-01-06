package ai.sxwl.android.data.http

import kotlinx.serialization.Serializable

@Serializable
enum class IntyErrorCode(val code: Int) {
    /** 需要订阅 */
    SUBSCRIPTION_REQUIRED(10001001),
    /** Agent数量达到上限 */
    LIVE_CHAT_AGENT_LIMIT_REACHED(10001007),
    /** 通话时长达到上限 */
    LIVE_CHAT_DURATION_LIMIT_REACHED(10001008),
    SESSION_ERROR(10000000),
    UNKNOWN(-1),
}
