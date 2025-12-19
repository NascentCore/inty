package com.ai.intellimate.agent.info

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.data.RoomDataSource
import ai.sxwl.android.data.chat.domain.ChatRepository
import ai.sxwl.android.data.di.DataModule
import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.agent.info.AgentInfoViewModel.Companion.DEFAULT_GALLERY_DIMENSION
import com.ai.intellimate.utils.NetworkErrorHandler
import com.architecture.httplib.core.HttpResult
import com.squareup.moshi.JsonClass
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@JsonClass(generateAdapter = true)
data class AgentImageGalleryItem(
    val messageId: String = "",
    val imageUrl: String,
    val width: Int = 512,
    val height: Int = 512,
    val timestamp: String? = null,
)

class AgentInfoViewModel : BaseVM() {

    companion object {
        private const val GALLERY_PAGE_SIZE = 40
        private const val MAX_GALLERY_ITEMS = 12
        private const val DEFAULT_GALLERY_DIMENSION = 256
    }

    private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
    val agentInfo = _agentInfo.asStateFlow()

    private val _chatImageGallery = MutableStateFlow<List<AgentImageGalleryItem>>(emptyList())
    val chatImageGallery =
        _chatImageGallery
            .combine(agentInfo) { gallery, agent ->
                (gallery + agent?.backgroundImages?.filter { it != agent.avatar }?.map { AgentImageGalleryItem(imageUrl = it) }.orEmpty())
                    .distinctBy { it.imageUrl }
            }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(), emptyList())
    private val chatRepository: ChatRepository = DataModule.getChatRepository()
    private val roomDataSource: RoomDataSource = DataModule.getRoomDataSource()

    private var galleryAgentId: String? = null
    private var galleryJob: Job? = null

    fun setAgentID(agentId: String) {
        bindGallery(agentId)
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = NetServiceMgr.getChatApi().getAgentInfo(agentId)
                LogUtils.i("getAgentInfo = $result")
                when (result) {
                    is HttpResult.Success -> {
                        setAgentInfo(result.data)
                    }
                    is HttpResult.Failure -> {
                        NetworkErrorHandler.showNetworkAwareError(result.message)
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("setAgentID exception: ${e.message}")
            }
        }
    }

    fun setAgentInfo(agentInfo: AgentInfo?) {
        LogUtils.i("agent = $agentInfo")
        _agentInfo.value = agentInfo

        if (agentInfo == null) {
            resetGalleryState()
            return
        }

        bindGallery(agentInfo.id)
        // Refresh agent data to get latest follower count and follow status
        refreshAgentData(agentInfo.id)
    }

    private fun refreshAgentData(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = NetServiceMgr.getAgentApi().getAgentDetail(agentId)
                LogUtils.i("refreshAgentData = $result")
                when (result) {
                    is HttpResult.Success -> {
                        _agentInfo.value = result.data
                    }
                    is HttpResult.Failure -> {
                        NetworkErrorHandler.showNetworkAwareError(result.message)
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("refreshAgentData exception: ${e.message}")
            }
        }
    }

    private fun bindGallery(agentId: String) {
        if (agentId.isBlank() || galleryAgentId == agentId) return

        val cachedGallery = AgentImageGalleryCache.getCachedGallery(agentId)
        _chatImageGallery.value = cachedGallery
        galleryAgentId = agentId
        galleryJob?.cancel()

        galleryJob =
            viewModelScope.launch {
                launch(Dispatchers.IO) {
                    runCatching { chatRepository.ensureInitialHistory(agentId, GALLERY_PAGE_SIZE) }
                        .onFailure { throwable ->
                            LogUtils.e(
                                "ensureInitialHistory failed for $agentId: ${throwable.message}"
                            )
                        }
                }

                roomDataSource.getMessagesWithImagesFlow(agentId).collect { messages ->
                    val galleryItems =
                        messages
                            .asSequence()
                            .mapNotNull { message -> mapMessageToGalleryItem(message) }
                            .sortedByDescending { it.timestamp ?: "" }
                            .distinctBy { it.imageUrl }
                            .take(MAX_GALLERY_ITEMS)
                            .toList()
                    _chatImageGallery.value = galleryItems
                    AgentImageGalleryCache.cacheGallery(agentId, galleryItems)
                }
            }
    }

    private fun mapMessageToGalleryItem(message: MsgInfo): AgentImageGalleryItem? {
        val generatedImage = message.meta_data?.generatedImage ?: return null
        val messageId = message.id.ifBlank { message.localMsgId }
        return AgentImageGalleryItem(
            messageId = messageId,
            imageUrl = generatedImage.imageUrl,
            width = generatedImage.width.takeIf { it > 0 } ?: DEFAULT_GALLERY_DIMENSION,
            height = generatedImage.height.takeIf { it > 0 } ?: DEFAULT_GALLERY_DIMENSION,
            timestamp = message.timestamp,
        )
    }

    private fun resetGalleryState() {
        galleryJob?.cancel()
        galleryJob = null
        galleryAgentId = null
        _chatImageGallery.value = emptyList()
    }
}
