package com.ai.inty.viewmodels

import ai.sxwl.android.utils.LogUtils
import com.ai.inty.base.BaseViewModel
import com.ai.inty.beans.GenerateBackgroundRequest
import com.ai.inty.beans.GenerateBackgroundResponse
import com.ai.inty.net.NetServiceMgr
import com.ai.inty.utils.AvatarManager
import com.ai.inty.utils.NetworkErrorHandler
import com.ai.inty.utils.NetworkManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext

class AvatarGenerateViewModel : BaseViewModel() {

    // 延迟获取依赖，避免在构造函数中立即获取导致空指针异常
    private val agentApi by lazy { NetServiceMgr.getAgentApi() }

    // UI States
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

        // Store the prompt and start generation in background
        AvatarManager.setGenerationPrompt(currentPrompt)
        LogUtils.i("Starting background generation with prompt: $currentPrompt")

        _isLoading.value = true
        clearError()

        launchWithNetCheck {
            try {
                val request = GenerateBackgroundRequest(prompt = currentPrompt)

                // Start generation in background - this will continue even after navigation
                val response = generateBackground(request = request)
                withContext(Dispatchers.Main) {
                    LogUtils.i("Generated image URLs: ${response.imageUrls}")

                    if (response.imageUrls.isNotEmpty()) {
                        // Store the generated URLs for CreateRoleActivity
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

                // 生成成功后，返回到Ai形象创建页面 Immediately navigate back to CreateRoleActivity
                withContext(Dispatchers.Main) {
                    onNavigateBack()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    NetworkErrorHandler.handleNetworkException(
                        isNetworkConnected = NetworkManager.getInstance().isNetworkConnected(),
                        exception = e,
                        showToast = { errorMessage ->
                            AvatarManager.setGenerationError(errorMessage)
                            _errorMessage.value = errorMessage
                        },
                    )
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

        // Clear current images and regenerate
        _generatedImageUrls.value = emptyList()
        _generatedImageUrl.value = null
        _selectedImageIndex.value = 0

        _isLoading.value = true
        _errorMessage.value = null

        launchWithNetCheck {
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
                is com.architecture.httplib.core.HttpResult.Success -> {
                    LogUtils.i("generateBackground success: ${result.data}")
                    return result.data
                }

                is com.architecture.httplib.core.HttpResult.Failure -> {
                    LogUtils.e("generateBackground error: $result")
                    val errorMessage =
                        result.message.ifBlank {
                            "Generation failed, please check your network connection"
                        }
                    throw Exception(errorMessage)
                }
            }
        } catch (e: Exception) {
            // Exception handling with detailed error messages
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
