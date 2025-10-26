package com.ai.intellimate.agent.generate

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.GenerateBackgroundRequest
import ai.sxwl.android.data.api.model.GenerateBackgroundResponse
import ai.sxwl.android.utils.LogUtils
import com.ai.intellimate.utils.AvatarManager
import com.ai.intellimate.utils.NetworkErrorHandler
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext

class AvatarGenerateViewModel : BaseVM() {
// 延迟获取依赖，避免在构造函数中立即导致获取空指针异常
    private val agentApi by lazy { NetServiceMgr.getAgentApi() }
// 用户界面状态
    private val _prompt = MutableStateFlow("")
    val prompt: StateFlow<String> = _prompt.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _generatedImageUrl = MutableStateFlow<String?>(null)
    val generatedImageUrl: StateFlow<String?> = _generatedImageUrl.asStateFlow()

    private val _generatedImageUrls = MutableStateFlow<List<String>>(emptyList())
    val generatedImageUrls: StateFlow<List<String>> = _generatedImageUrls.asStateFlow()

    private val _selectedImageIndex = MutableStateFlow(0)
    val selectedImageIndex: StateFlow<Int> = _selectedImageIndex.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    fun updatePrompt(newPrompt: String) {
        _prompt.value = newPrompt
    }

    fun selectImage(index: Int) {
        _selectedImageIndex.value = index
        AvatarManager.setSelectedImageIndex(index)
    }

    fun generateAvatar(onNavigateBack: () -> Unit) {
        val currentPrompt = _prompt.value
        if (currentPrompt.isBlank()) {
            _errorMessage.value = "Please enter a prompt"
            return
        }
// 存储 prompt 并在后台开始生成
        AvatarManager.setGenerationPrompt(currentPrompt)
        LogUtils.i("Starting background generation with prompt: $currentPrompt")

        _isLoading.value = true
        clearError()

        launchBackground {
            try {
                val request = GenerateBackgroundRequest(prompt = currentPrompt)
// 在后台开始生成 - 即使在导航后基因继续
                val response = generateBackground(request = request)
                withContext(Dispatchers.Main) {
                    LogUtils.i("Generated image URLs: ${response.imageUrls}")

                    if (response.imageUrls.isNotEmpty()) {
// 存储为CreateRoleActivity生成的URL
                        _generatedImageUrls.value = response.imageUrls
                        _selectedImageIndex.value = 0
                        AvatarManager.setGeneratedAvatarUrls(response.imageUrls)
                        LogUtils.i("Setting generatedImageUrls to: ${response.imageUrls}")
                    } else if (response.imageUrl.isNotBlank()) {
// 兼容单张图片的情况
                        _generatedImageUrl.value = response.imageUrl
                        AvatarManager.setGeneratedAvatarUrl(response.imageUrl)
                        LogUtils.i("Setting generatedImageUrl to: ${response.imageUrl}")
                    } else {
                        LogUtils.e("Empty image URLs received from server")
                        AvatarManager.setGenerationError("Generated image URLs are empty")
                    }

                    _isLoading.value = false
                }
// 生成成功后，返回Ai形象创建页面立即导航回CreateRoleActivity
                withContext(Dispatchers.Main) {
                    onNavigateBack()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    val errorMessage = NetworkErrorHandler.handleNetworkException(
                        exception = e,
                        operation = "generate avatar"
                    )
                    AvatarManager.setGenerationError(errorMessage)
                    _errorMessage.value = errorMessage
                    LogUtils.e("Ai头像生成异常: ${e.message}")
                    _isLoading.value = false
                    clearError()
                }
            }
        }
    }

    fun regenerateAvatar() {
        val currentPrompt = _prompt.value
        if (currentPrompt.isBlank()) {
            _errorMessage.value = "Please enter a prompt"
            return
        }
// 清除当前图像并重新生成
        _generatedImageUrls.value = emptyList()
        _generatedImageUrl.value = null
        _selectedImageIndex.value = 0

        _isLoading.value = true
        _errorMessage.value = null

        launchBackground {
            try {
                val request = GenerateBackgroundRequest(prompt = currentPrompt)

                val response = generateBackground(request = request)
                withContext(Dispatchers.Main) {
                    LogUtils.i("Regenerated image URLs: ${response.imageUrls}")
                    if (response.imageUrls.isNotEmpty()) {
                        _generatedImageUrls.value = response.imageUrls
                        _selectedImageIndex.value = 0 // 默认选中第一张
                        AvatarManager.setGeneratedAvatarUrls(response.imageUrls)
                        LogUtils.i("Setting regenerated imageUrls to: ${response.imageUrls}")
                    } else if (response.imageUrl.isNotBlank()) {
// 兼容单张图片的情况
                        _generatedImageUrl.value = response.imageUrl
                        AvatarManager.setGeneratedAvatarUrl(response.imageUrl)
                        LogUtils.i("Setting regenerated imageUrl to: ${response.imageUrl}")
                    } else {
                        LogUtils.e("Empty image URLs received from server during regeneration")
                        _errorMessage.value = "Regenerated image URLs are empty"
                    }
                    _isLoading.value = false
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    val errorMessage = e.message?.substringBefore(':') ?: "Unknown error"
                    _errorMessage.value = errorMessage
                    LogUtils.e("Regenerate avatar error: ${e.message}")
                    _isLoading.value = false
                }
            }
        }
    }

    fun getSelectedAvatarUrl(): String? {
        return when {
            _generatedImageUrls.value.isNotEmpty() &&
                    _selectedImageIndex.value < _generatedImageUrls.value.size -> {
                _generatedImageUrls.value[_selectedImageIndex.value]
            }

            _generatedImageUrl.value != null -> _generatedImageUrl.value
            else -> null
        }
    }

    fun clearError() {
        _errorMessage.value = null
    }

    private suspend fun generateBackground(
        request: GenerateBackgroundRequest
    ): GenerateBackgroundResponse {
        try {
            val result = agentApi.generateBackground(request)
            LogUtils.i("generateBackground = $result")

            when (result) {
                is HttpResult.Success -> {
                    LogUtils.i("generateBackground success: ${result.data}")
                    return result.data
                }

                is HttpResult.Failure -> {
                    LogUtils.e("generateBackground error: $result")
                    val errorMessage =
                        result.message.ifBlank {
                            "Generation failed, please check your network connection"
                        }
                    throw Exception(errorMessage)
                }
            }
        } catch (e: Exception) {
// 异常处理以及详细的错误消息
            val errorMessage =
                when {
                    e.message?.contains("timeout", ignoreCase = true) == true ->
                        "Network timeout, please try again later"

                    e.message?.contains("network", ignoreCase = true) == true ->
                        "Network connection failed, please check your network"

                    e.message?.contains("json", ignoreCase = true) == true ->
                        "Data format error, please try again later"

                    else -> e.message ?: "Unknown error"
                }
            throw Exception(errorMessage)
        }
    }
}
