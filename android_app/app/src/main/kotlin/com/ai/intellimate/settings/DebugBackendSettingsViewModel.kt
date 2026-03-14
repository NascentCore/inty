package com.ai.intellimate.settings

import ai.sxwl.android.data.chat.data.ChatWebSocketSessionManager
import ai.sxwl.android.data.http.NetworkStackCoordinator
import ai.sxwl.android.data.http.config.Constant
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

private const val TAG = "DebugBackendSettings"

private const val PRESET_NAME_LOCAL = "local"
private const val PRESET_NAME_DEV = "dev"
private const val PRESET_NAME_PROD = "prod"

class DebugBackendSettingsViewModel : ViewModel() {

    data class UiState(
        // 在配置页面中显示构建类型
        val buildType: String,
        // 当前生效的后端地址
        val activeBaseUrl: String,
        // 自定义后端 URL 输入（如 WiFi 开发时填 http://<主机IP>:8000/）
        val customUrlInput: String,
        // 手动 Debug Mode 状态
        val debugModeEnabled: Boolean,
        // Remix 按钮可见性（仅在 debug 构建中有效）
        val remixButtonVisible: Boolean,
        // 用户时间上下文上报（仅在 debug 构建中有效）
        val userTimeContextReportingEnabled: Boolean,
        // 聊天是否走 WebSocket（仅在 debug 构建中有效）
        val chatWebSocketEnabled: Boolean,
    )

    val quickPresets =
        listOf(
            PRESET_NAME_LOCAL to "http://${Constant.USER_HOST_LOCAL}/",
            PRESET_NAME_DEV to "https://${Constant.USER_HOST_DEV}/",
            PRESET_NAME_PROD to "https://${Constant.USER_HOST}/",
        )

    private val _uiState = MutableStateFlow(createInitialState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    init {
        // 初始化时通知全局状态管理器
        val initialVisibility = getRemixButtonEffectiveVisibility()
        RemixButtonVisibilityManager.updateVisibility(initialVisibility)
    }

    private fun createInitialState(): UiState {
        val activeBaseUrl = NetworkConfig.getBaseUrl()
        val debugModeEnabled = AppUtils.isDebugMode()
        val remixButtonVisible = getRemixButtonEffectiveVisibility()
        val userTimeContextReportingEnabled =
            DebugBackendEndpointStore.getUserTimeContextReportingEnabled()
        val chatWebSocketEnabled = DebugBackendEndpointStore.getChatWebSocketEnabled()
        return UiState(
            buildType = NetworkConfig.getCurrentBuildType().value,
            activeBaseUrl = activeBaseUrl,
            customUrlInput = "",
            debugModeEnabled = debugModeEnabled,
            remixButtonVisible = remixButtonVisible,
            userTimeContextReportingEnabled = userTimeContextReportingEnabled,
            chatWebSocketEnabled = chatWebSocketEnabled,
        )
    }

    private fun getRemixButtonEffectiveVisibility(): Boolean {
        val buildType = NetworkConfig.getCurrentBuildType()
        // Release 构建始终隐藏
        if (buildType == NetworkConfig.BuildType.RELEASE) {
            return false
        }
        // Debug 构建：检查运行时覆盖
        val override = DebugBackendEndpointStore.getRemixButtonOverride()
        return override ?: true // 默认可见
    }

    fun applySelectedOverride(url: String) {
        runCatching { DebugBackendEndpointStore.persistOverride(url) }
            .onFailure { LogUtils.e(TAG, "Failed to persist runtime backend override", it) }
            .getOrElse {
                return
            }

        // 统一清除两套网络栈缓存，确保切换地址后使用新客户端
        NetworkStackCoordinator.clearAllRuntimeCaches()
        viewModelScope.launch { ChatWebSocketSessionManager.closeSession() }

        _uiState.update { it.copy(activeBaseUrl = NetworkConfig.getBaseUrl(), customUrlInput = "") }
    }

    fun setCustomUrlInput(value: String) {
        _uiState.update { it.copy(customUrlInput = value) }
    }

    /** 应用当前输入的自定义 URL（如 WiFi 开发时的主机地址 http://<主机IP>:8000/） */
    fun applyCustomUrl() {
        val url = _uiState.value.customUrlInput.trim()
        if (url.isBlank()) return
        val normalized = if (url.endsWith("/")) url else "$url/"
        applySelectedOverride(normalized)
    }

    fun resetOverride() {
        DebugBackendEndpointStore.clearOverride()
        // 统一清除两套网络栈缓存，确保重置地址后使用新客户端
        NetworkStackCoordinator.clearAllRuntimeCaches()
        viewModelScope.launch { ChatWebSocketSessionManager.closeSession() }

        val active = NetworkConfig.getBaseUrl()
        _uiState.update { it.copy(activeBaseUrl = active, customUrlInput = "") }
    }

    fun toggleRemixButton() {
        val currentVisibility = _uiState.value.remixButtonVisible
        val newVisibility = !currentVisibility
        DebugBackendEndpointStore.persistRemixButtonOverride(newVisibility)
        _uiState.update { it.copy(remixButtonVisible = newVisibility) }
        // 通知全局状态变化（通过更新 RemixButtonVisibilityManager）
        RemixButtonVisibilityManager.updateVisibility(newVisibility)
    }

    fun resetRemixButtonOverride() {
        DebugBackendEndpointStore.clearRemixButtonOverride()
        val defaultVisibility = getRemixButtonEffectiveVisibility()
        _uiState.update { it.copy(remixButtonVisible = defaultVisibility) }
        // 通知全局状态变化
        RemixButtonVisibilityManager.updateVisibility(defaultVisibility)
    }

    fun setDebugModeEnabled(enabled: Boolean) {
        _uiState.update { it.copy(debugModeEnabled = enabled) }
        viewModelScope.launch {
            runCatching { AppUtils.setDebugMode(enabled) }
                .onFailure { error ->
                    LogUtils.e(TAG, "Failed to persist debug mode", error)
                    _uiState.update { it.copy(debugModeEnabled = AppUtils.isDebugMode()) }
                }
        }
    }

    fun toggleUserTimeContextReporting() {
        val current = _uiState.value.userTimeContextReportingEnabled
        val updated = !current
        DebugBackendEndpointStore.persistUserTimeContextReportingEnabled(updated)
        _uiState.update { it.copy(userTimeContextReportingEnabled = updated) }
    }

    fun toggleChatWebSocketEnabled() {
        val current = _uiState.value.chatWebSocketEnabled
        val updated = !current
        DebugBackendEndpointStore.persistChatWebSocketEnabled(updated)
        _uiState.update { it.copy(chatWebSocketEnabled = updated) }
        FirebaseManager.logEvent(
            FirebaseManager.Events.SELECT_CONTENT,
            FirebaseManager.safeEventParams(
                "content_type" to "debug_chat_websocket_toggle",
                "item_id" to updated.toString(),
            ),
        )
        if (!updated) {
            viewModelScope.launch { ChatWebSocketSessionManager.closeSession() }
        }
    }
}

/** 全局 Remix 按钮可见性管理器 用于在设置页面和聊天页面之间同步状态 */
object RemixButtonVisibilityManager {
    private val _visibility = MutableStateFlow<Boolean?>(null)
    val visibility: StateFlow<Boolean?> = _visibility.asStateFlow()

    fun updateVisibility(visible: Boolean) {
        _visibility.value = visible
    }

    fun getCurrentVisibility(): Boolean {
        val buildType = NetworkConfig.getCurrentBuildType()
        // Release 构建始终隐藏
        if (buildType == NetworkConfig.BuildType.RELEASE) {
            return false
        }
        // Debug 构建：检查运行时覆盖
        val override = DebugBackendEndpointStore.getRemixButtonOverride()
        return override ?: true // 默认可见
    }

    init {
        // 初始化时设置当前可见性
        _visibility.value = getCurrentVisibility()
    }
}
