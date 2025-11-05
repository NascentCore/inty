package ai.sxwl.android.data.http

/** 业务错误码定义 与后端 app/schemas/response.py 中的 BusinessErrorCode 保持一致 */
object BusinessErrorCodes {

//    /** Guest用户聊天受限，需要登录 */
//    const val GUEST_NEED_LOGIN_CODE = 10001005
//    const val GUEST_NEED_LOGIN_ERROR_CODE = "Guest Login Required"
//    const val GUEST_NEED_LOGIN_ERROR_MESSAGE = "Guest Login Required, Please sign in with Google"

    /** 音频tts生成，次数超限制 */
    const val VOICE_TTS_LIMIT_CODE = 10001004
    const val VOICE_TTS_LIMIT_ERROR_CODE = "VOICE_GENERATION_LIMIT_REACHED"
    const val VOICE_TTS_LIMIT_ERROR_MESSAGE = "voice generation limit reached"
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

    /** 业务错误消息映射 */
    val BUSINESS_ERROR_MESSAGES =
        mapOf(
            SUBSCRIPTION_REQUIRED_CODE to SUBSCRIPTION_REQUIRED_MESSAGE,
            IMAGE_GENERATION_LIMIT_REACHED_CODE to IMAGE_GENERATION_LIMIT_REACHED_MESSAGE,
            AGENT_CREATION_LIMIT_REACHED_CODE to AGENT_CREATION_LIMIT_REACHED_MESSAGE,
        )
}
