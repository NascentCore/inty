package ai.sxwl.android.data.chat.repository

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.VoteConstants
import ai.sxwl.android.data.api.model.ChatImageGenerationResult
import ai.sxwl.android.data.chat.data.ChatLocalDataSource
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.domain.ChatRepository
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult

/** 聊天Repository实现 作为Domain层和Data层之间的桥梁 遵循Clean Architecture的Repository模式 */
class ChatRepositoryImpl(
    private val localDataSource: ChatLocalDataSource,
    private val remoteDataSource: ChatRemoteDataSource,
) : ChatRepository {

    companion object {
        private const val DEFAULT_PAGE_SIZE = 20
        private const val LOADING_PLACEHOLDER_CONTENT = "loading_animation"
        private const val ROLE_ASSISTANT = "assistant"
    }

    /** 将服务端返回的消息中的 user_vote 转换为 userFeedback */
    private fun convertUserVoteToFeedback(messages: List<MsgInfo>): List<MsgInfo> {
        return messages.map { msg ->
            if (msg.user_vote != null && msg.userFeedback == null) {
                // 如果消息有 user_vote 但没有 userFeedback，进行转换
                val userFeedback =
                    when (msg.user_vote) {
                        VoteConstants.LIKE -> MsgInfo.UserFeedback.LIKE
                        VoteConstants.DISLIKE -> MsgInfo.UserFeedback.DISLIKE
                        else -> null
                    }
                msg.copy(userFeedback = userFeedback)
            } else {
                msg
            }
        }
    }

    override fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String) {
        LogUtils.d(
            "ChatRepositoryImpl.updateMessageAudioUrl called for $agentId, messageId: $messageId"
        )
        localDataSource.updateMessageAudioUrl(agentId, messageId, audioUrl)
    }

    override fun updateMessageGeneratedImage(
        agentId: String,
        messageId: String,
        generatedImage: MsgInfo.MsgMetaData.GeneratedImage?,
    ) {
        LogUtils.d(
            "ChatRepositoryImpl.updateMessageGeneratedImage called for $agentId, messageId: $messageId, generatedImage: ${if (generatedImage != null) "set" else "null (remove)"}"
        )
        localDataSource.updateMessageGeneratedImage(agentId, messageId, generatedImage)
    }

    override suspend fun generateImageForMessage(
        agentId: String,
        messageId: String,
    ): HttpResult<ChatImageGenerationResult> {
        LogUtils.d(
            "ChatRepositoryImpl.generateImageForMessage called for $agentId, messageId: $messageId"
        )

        // 找到触发消息生图的那条消息
        val messages = localDataSource.getMessagesFlow(agentId).value
        val sourceMessage = messages.find { it.id == messageId || it.localMsgId == messageId }

        if (sourceMessage == null) {
            LogUtils.e(
                "ChatRepositoryImpl.generateImageForMessage: source message not found: $messageId"
            )
            return HttpResult.Failure("Source message not found", -1)
        }

        // 在触发消息上设置 loading 状态：通过设置一个临时的 generatedImage（imageUrl 为 "loading"）
        // 这样图片会显示在触发消息的下方，而不是创建新消息
        // 使用 9:16 的宽高比（竖屏），与生成的图片尺寸匹配
        val loadingImage =
            MsgInfo.MsgMetaData.GeneratedImage(
                imageUrl = "loading", // 特殊标记，表示正在生成图片
                width = 300,
                height = 533, // 9:16 比例 (300 * 16 / 9 ≈ 533)
            )
        localDataSource.updateMessageGeneratedImage(agentId, messageId, loadingImage)

        val result = remoteDataSource.messageGenerateImage(agentId, messageId)

        when (result) {
            is HttpResult.Success -> {
                // 更新触发消息的 generatedImage 为实际图片
                val generatedImage =
                    MsgInfo.MsgMetaData.GeneratedImage(
                        imageUrl = result.data.imageUrl,
                        width = result.data.width,
                        height = result.data.height,
                    )
                localDataSource.updateMessageGeneratedImage(agentId, messageId, generatedImage)
                LogUtils.i(
                    "ChatRepositoryImpl.generateImageForMessage success: ${result.data.imageUrl}"
                )
            }

            is HttpResult.Failure -> {
                LogUtils.e("ChatRepositoryImpl.generateImageForMessage failure: ${result.message}")
                // 生成失败时，移除 loading 状态
                localDataSource.updateMessageGeneratedImage(agentId, messageId, null)
            }
        }

        return result
    }

    override suspend fun clearChatData(agentId: String) {
        LogUtils.d("ChatRepositoryImpl.clearChatData called for $agentId")
        localDataSource.clearChatData(agentId)
    }

    override suspend fun clearAllChatData() {
        LogUtils.d("ChatRepositoryImpl.clearAllChatData called")
        localDataSource.clearAllChatData()
    }

    override suspend fun clearMessage(agentId: String): Boolean {
        return remoteDataSource.clearMessage(agentId)
    }
}
