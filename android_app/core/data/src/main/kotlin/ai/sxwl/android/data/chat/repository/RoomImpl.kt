package ai.sxwl.android.data.chat.repository

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.data.RoomDataSource
import ai.sxwl.android.data.chat.domain.ChatRepository
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult

/** 聊天Repository实现 作为Domain层和Data层之间的桥梁 遵循Clean Architecture的Repository模式 */
class RoomImpl(
    private val localDataSource: RoomDataSource,
    private val remoteDataSource: ChatRemoteDataSource,
) : ChatRepository {

    companion object {
        private const val LOADING_PLACEHOLDER_CONTENT = "loading_animation"
        private const val ROLE_ASSISTANT = "assistant"
    }

    override fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String) {
        LogUtils.d("RoomImpl.updateMessageAudioUrl called for $agentId, messageId: $messageId")
        localDataSource.updateMessageAudioUrl(agentId, messageId, audioUrl)
    }

    override fun updateMessageGeneratedImage(
        agentId: String,
        messageId: String,
        generatedImage: MsgInfo.MsgMetaData.GeneratedImage?,
    ) {
        LogUtils.d(
            "RoomImpl.updateMessageGeneratedImage called for $agentId, messageId: $messageId, generatedImage: ${if (generatedImage != null) "set" else "null (remove)"}"
        )
        localDataSource.updateMessageGeneratedImage(agentId, messageId, generatedImage)
    }

    override suspend fun generateImageForMessage(
        agentId: String,
        messageId: String,
    ): HttpResult<ai.sxwl.android.data.http.services.ChatService.ChatImageGenerationResult> {
        LogUtils.d("RoomImpl.generateImageForMessage called for $agentId, messageId: $messageId")

        val loadingImage =
            MsgInfo.MsgMetaData.GeneratedImage(imageUrl = "loading", width = 300, height = 533)
        localDataSource.updateMessageGeneratedImage(agentId, messageId, loadingImage)

        val result = remoteDataSource.messageGenerateImage(agentId, messageId)

        when (result) {
            is HttpResult.Success -> {
                val generatedImage =
                    MsgInfo.MsgMetaData.GeneratedImage(
                        imageUrl = result.data.imageUrl,
                        width = result.data.width,
                        height = result.data.height,
                    )
                localDataSource.updateMessageGeneratedImage(agentId, messageId, generatedImage)
                LogUtils.i("RoomImpl.generateImageForMessage success: ${result.data.imageUrl}")
            }

            is HttpResult.Failure -> {
                LogUtils.e("RoomImpl.generateImageForMessage failure: ${result.message}")
                localDataSource.updateMessageGeneratedImage(agentId, messageId, null)
            }
        }

        return result
    }

    override suspend fun clearChatData(agentId: String) {
        LogUtils.d("RoomImpl.clearChatData called for $agentId")
        localDataSource.clearChatData(agentId)
        LogUtils.i("RoomImpl.clearChatData completed for $agentId")
    }

    override suspend fun clearAllChatData() {
        LogUtils.d("RoomImpl.clearAllChatData called")
        localDataSource.clearAllChatData()
        LogUtils.i("RoomImpl.clearAllChatData completed")
    }

    override suspend fun clearMessage(agentId: String): Boolean {
        return remoteDataSource.clearMessage(agentId)
    }
}
