package com.ai.intellimate.agent.generate

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.GenerateBackgroundRequest
import ai.sxwl.android.data.api.model.GenerateBackgroundResponse
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import com.ai.intellimate.utils.AvatarManager
import com.ai.intellimate.utils.NetworkErrorHandler
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext

/**
 * 头像生成风格模板（用于 UI 选择，并在生成时对 prompt 做轻量“模板化”增强）。
 *
 * 注意：
 * - 这里不改服务端协议，避免 Android/Backend 版本不一致导致请求失败；
 * - 通过在 prompt 末尾追加风格关键词来影响生成效果；
 * - 后续新增风格时，只需要新增 enum 项并在 UI 中展示即可。
 */
enum class AvatarImageStyleTemplate(
    /** 用于埋点/日志的稳定 key，避免依赖 UI 文案 */
    val key: String,
    /** 发送给模型前拼接到 prompt 末尾的风格描述片段（UI 不展示） */
    val promptSuffix: String,
) {
    REAL_FEEL(
        key = "real_feel",
        promptSuffix =
            "single, adult, real feel, photorealistic, natural skin texture, soft natural lighting, high detail, focus on expression, dynamic composition",
    ),
    CARTOON(
        key = "cartoon",
        promptSuffix =
            "single, solo, adult, cartoon style, clean lines, (perfect body), stunningly beautiful, soft natural lighting, high detail, focus on expression, dynamic composition, dynamic pose, depth of field",
    ),
}

class AvatarGenerateViewModel : BaseVM() {

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

    private val _styleTemplate = MutableStateFlow(AvatarImageStyleTemplate.REAL_FEEL)
    val styleTemplate: StateFlow<AvatarImageStyleTemplate> = _styleTemplate.asStateFlow()

    fun updatePrompt(newPrompt: String) {
        _prompt.value = newPrompt
        AvatarManager.updatePromptDraft(newPrompt)
    }

    fun selectStyleTemplate(template: AvatarImageStyleTemplate) {
        _styleTemplate.value = template
    }

    fun selectImage(index: Int) {
        _selectedImageIndex.value = index
        AvatarManager.setSelectedImageIndex(index)
    }

    fun generateAvatar(onNavigateBack: () -> Unit) {
        val userPrompt = _prompt.value
        val currentPrompt = buildStyledPrompt(userPrompt)
        if (currentPrompt.isBlank()) {
            _errorMessage.value = "Please enter a prompt"
            return
        }

        // Store the prompt and start generation in background
        // 注意：AvatarManager 的 prompt 会在 UI 中展示，因此只保存用户原始输入
        AvatarManager.setGenerationPrompt(userPrompt)
        LogUtils.i("Starting background generation with prompt: $currentPrompt")

        _isLoading.value = true
        clearError()

        launchBackground {
            val startTime = System.currentTimeMillis()

            // Firebase Analytics - 记录头像生成按钮点击
            FirebaseManager.logEvent(
                FirebaseManager.Events.AVATAR_GENERATION_BUTTON_CLICKED,
                FirebaseManager.safeEventParams(
                    "prompt" to currentPrompt,
                    "style_template" to _styleTemplate.value.key,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to startTime,
                ),
            )

            try {
                val request = GenerateBackgroundRequest(prompt = currentPrompt)

                // Start generation in background - this will continue even after navigation
                val response = generateBackground(request = request)
                val endTime = System.currentTimeMillis()
                val generationTime = endTime - startTime

                withContext(Dispatchers.Main) {
                    LogUtils.i("Generated image URLs: ${response.imageUrls}")

                    if (response.imageUrls.isNotEmpty()) {
                        // Store the generated URLs for CreateRoleActivity
                        _generatedImageUrls.value = response.imageUrls
                        _selectedImageIndex.value = 0
                        AvatarManager.appendAvatarUrls(response.imageUrls)
                        LogUtils.i("Setting generatedImageUrls to: ${response.imageUrls}")

                        // Firebase Analytics - 记录头像生成成功
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.AVATAR_GENERATION_SUCCESS,
                            FirebaseManager.safeEventParams(
                                "prompt" to currentPrompt,
                                "style_template" to _styleTemplate.value.key,
                                "image_count" to response.imageUrls.size,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )
                    } else if (response.imageUrl.isNotBlank()) {
                        // 兼容单张图片的情况
                        _generatedImageUrl.value = response.imageUrl
                        AvatarManager.setGeneratedAvatarUrl(response.imageUrl)
                        LogUtils.i("Setting generatedImageUrl to: ${response.imageUrl}")

                        // Firebase Analytics - 记录头像生成成功（单张图片）
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.AVATAR_GENERATION_SUCCESS,
                            FirebaseManager.safeEventParams(
                                "prompt" to currentPrompt,
                                "style_template" to _styleTemplate.value.key,
                                "image_count" to 1,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )
                    } else {
                        LogUtils.e("Empty image URLs received from server")
                        AvatarManager.setGenerationError("Generated image URLs are empty")

                        // Firebase Analytics - 记录头像生成失败（空结果）
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.AVATAR_GENERATION_FAILURE,
                            FirebaseManager.safeEventParams(
                                "prompt" to currentPrompt,
                                "style_template" to _styleTemplate.value.key,
                                "error_message" to "Empty image URLs received from server",
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )
                    }

                    _isLoading.value = false
                }

                // 生成成功后，返回到Ai形象创建页面 Immediately navigate back to CreateRoleActivity
                withContext(Dispatchers.Main) { onNavigateBack() }
            } catch (e: Exception) {
                val endTime = System.currentTimeMillis()
                val generationTime = endTime - startTime

                withContext(Dispatchers.Main) {
                    val errorMessage =
                        NetworkErrorHandler.handleNetworkException(
                            exception = e,
                            operation = "generate avatar",
                        )
                    AvatarManager.setGenerationError(errorMessage)
                    _errorMessage.value = errorMessage
                    LogUtils.e("Ai头像生成异常: ${e.message}")

                    // Firebase Analytics - 记录头像生成失败
                    // 检查是否是限制达到的错误
                    val isLimitReached =
                        e.message?.contains("limit", ignoreCase = true) == true ||
                            e.message?.contains(
                                "IMAGE_GENERATION_LIMIT_REACHED",
                                ignoreCase = true,
                            ) == true ||
                            e.message?.contains("SUBSCRIPTION_REQUIRED", ignoreCase = true) == true

                    if (isLimitReached) {
                        // 达到限制时，上报限制事件（与消息生图共享）
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.IMAGE_GENERATION_LIMIT_REACHED,
                            FirebaseManager.safeEventParams(
                                "prompt" to currentPrompt,
                                "style_template" to _styleTemplate.value.key,
                                "error_message" to
                                    "exception: ${e.javaClass.simpleName}, ${e.message ?: "unknown error"}",
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )
                    } else {
                        // 其他错误，上报失败事件
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.AVATAR_GENERATION_FAILURE,
                            FirebaseManager.safeEventParams(
                                "prompt" to currentPrompt,
                                "style_template" to _styleTemplate.value.key,
                                "error_message" to
                                    "exception: ${e.javaClass.simpleName}, ${e.message ?: "unknown error"}",
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )
                    }

                    _isLoading.value = false
                    clearError()
                }
            }
        }
    }

    fun regenerateAvatar() {
        val userPrompt = _prompt.value
        val currentPrompt = buildStyledPrompt(userPrompt)
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

        launchBackground {
            val startTime = System.currentTimeMillis()

            // Firebase Analytics - 记录头像重新生成按钮点击
            FirebaseManager.logEvent(
                FirebaseManager.Events.AVATAR_GENERATION_BUTTON_CLICKED,
                FirebaseManager.safeEventParams(
                    "prompt" to currentPrompt,
                    "style_template" to _styleTemplate.value.key,
                    "is_regenerate" to true,
                    "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                    "timestamp" to startTime,
                ),
            )

            try {
                val request = GenerateBackgroundRequest(prompt = currentPrompt)

                val response = generateBackground(request = request)
                val endTime = System.currentTimeMillis()
                val generationTime = endTime - startTime

                withContext(Dispatchers.Main) {
                    LogUtils.i("Regenerated image URLs: ${response.imageUrls}")
                    if (response.imageUrls.isNotEmpty()) {
                        _generatedImageUrls.value = response.imageUrls
                        _selectedImageIndex.value = 0 // 默认选中第一张
                        AvatarManager.setGeneratedAvatarUrls(response.imageUrls)
                        LogUtils.i("Setting regenerated imageUrls to: ${response.imageUrls}")

                        // Firebase Analytics - 记录头像重新生成成功
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.AVATAR_GENERATION_SUCCESS,
                            FirebaseManager.safeEventParams(
                                "prompt" to currentPrompt,
                                "style_template" to _styleTemplate.value.key,
                                "image_count" to response.imageUrls.size,
                                "is_regenerate" to true,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )
                    } else if (response.imageUrl.isNotBlank()) {
                        // 兼容单张图片的情况
                        _generatedImageUrl.value = response.imageUrl
                        AvatarManager.setGeneratedAvatarUrl(response.imageUrl)
                        LogUtils.i("Setting regenerated imageUrl to: ${response.imageUrl}")

                        // Firebase Analytics - 记录头像重新生成成功（单张图片）
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.AVATAR_GENERATION_SUCCESS,
                            FirebaseManager.safeEventParams(
                                "prompt" to currentPrompt,
                                "style_template" to _styleTemplate.value.key,
                                "image_count" to 1,
                                "is_regenerate" to true,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )
                    } else {
                        LogUtils.e("Empty image URLs received from server during regeneration")
                        _errorMessage.value = "Regenerated image URLs are empty"

                        // Firebase Analytics - 记录头像重新生成失败（空结果）
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.AVATAR_GENERATION_FAILURE,
                            FirebaseManager.safeEventParams(
                                "prompt" to currentPrompt,
                                "style_template" to _styleTemplate.value.key,
                                "error_message" to
                                    "Empty image URLs received from server during regeneration",
                                "is_regenerate" to true,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )
                    }
                    _isLoading.value = false
                }
            } catch (e: Exception) {
                val endTime = System.currentTimeMillis()
                val generationTime = endTime - startTime

                withContext(Dispatchers.Main) {
                    val errorMessage = e.message?.substringBefore(':') ?: "Unknown error"
                    _errorMessage.value = errorMessage
                    LogUtils.e("Regenerate avatar error: ${e.message}")

                    // Firebase Analytics - 记录头像重新生成失败
                    // 检查是否是限制达到的错误
                    val isLimitReached =
                        e.message?.contains("limit", ignoreCase = true) == true ||
                            e.message?.contains(
                                "IMAGE_GENERATION_LIMIT_REACHED",
                                ignoreCase = true,
                            ) == true ||
                            e.message?.contains("SUBSCRIPTION_REQUIRED", ignoreCase = true) == true

                    if (isLimitReached) {
                        // 达到限制时，上报限制事件（与消息生图共享）
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.IMAGE_GENERATION_LIMIT_REACHED,
                            FirebaseManager.safeEventParams(
                                "prompt" to currentPrompt,
                                "style_template" to _styleTemplate.value.key,
                                "error_message" to
                                    "exception: ${e.javaClass.simpleName}, ${e.message ?: "unknown error"}",
                                "is_regenerate" to true,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )
                    } else {
                        // 其他错误，上报失败事件
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.AVATAR_GENERATION_FAILURE,
                            FirebaseManager.safeEventParams(
                                "prompt" to currentPrompt,
                                "style_template" to _styleTemplate.value.key,
                                "error_message" to
                                    "exception: ${e.javaClass.simpleName}, ${e.message ?: "unknown error"}",
                                "is_regenerate" to true,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                                "generation_time_ms" to generationTime,
                                "timestamp" to endTime,
                            ),
                        )
                    }

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

    fun initializePrompt(initialPrompt: String?) {
        if (initialPrompt.isNullOrBlank()) {
            return
        }
        if (_prompt.value.isBlank()) {
            _prompt.value = initialPrompt
            AvatarManager.updatePromptDraft(initialPrompt)
        }
    }

    private fun buildStyledPrompt(userPrompt: String): String {
        val normalized = userPrompt.trim()
        if (normalized.isBlank()) {
            return ""
        }
        val suffix = _styleTemplate.value.promptSuffix.trim()
        if (suffix.isBlank()) {
            return normalized
        }
        return "$normalized, $suffix"
    }

    private suspend fun generateBackground(
        request: GenerateBackgroundRequest
    ): GenerateBackgroundResponse {
        try {
            val result = NetServiceMgr.getAgentApi().generateBackground(request)
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
