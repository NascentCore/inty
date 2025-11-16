package com.ai.intellimate.settings

import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.config.Constant
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore.OverrideInfo
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

private const val TAG = "DebugBackendSettings"

class DebugBackendSettingsViewModel : ViewModel() {

    data class UiState(
        val isSupported: Boolean,
        val buildType: String,
        val activeBaseUrl: String,
        val pendingValue: String,
        val overrideInfo: OverrideInfo?,
        val message: String? = null,
        val error: String? = null,
    ) {
        val hasOverride: Boolean = overrideInfo != null
    }

    val quickPresets =
        listOf(
            "Dev" to "https://${Constant.USER_HOST_DEV}/",
            "Prod" to "https://${Constant.USER_HOST}/",
            "Local" to "http://${Constant.USER_HOST_LOCAL}/",
        )

    private val _uiState = MutableStateFlow(createInitialState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private fun createInitialState(): UiState {
        val overrideInfo = DebugBackendEndpointStore.getOverrideInfo()
        val activeBaseUrl = NetworkConfig.getBaseUrl()
        val pendingValue = overrideInfo?.url ?: activeBaseUrl
        return UiState(
            isSupported = DebugBackendEndpointStore.isRuntimeOverrideSupported(),
            buildType = NetworkConfig.getCurrentBuildType().value,
            activeBaseUrl = activeBaseUrl,
            pendingValue = pendingValue,
            overrideInfo = overrideInfo,
        )
    }

    fun onInputChanged(value: String) {
        _uiState.update { it.copy(pendingValue = value, message = null, error = null) }
    }

    fun applyOverride() {
        val pending = _uiState.value.pendingValue
        val normalized = DebugBackendEndpointStore.normalizeAndValidate(pending)
        if (normalized == null) {
            _uiState.update {
                it.copy(
                    error = "URL 无效，请确保包含合法的域名或 IP",
                    message = null,
                )
            }
            return
        }

        val info =
            runCatching { DebugBackendEndpointStore.persistOverride(pending) }
                .onFailure { LogUtils.e(TAG, "Failed to persist runtime backend override", it) }
                .getOrElse { throwable ->
                    _uiState.update {
                        it.copy(
                            error = throwable.message ?: "保存失败，请重试",
                            message = null,
                        )
                    }
                    return
                }

        IntyNetworkManager.clearClientCache()

        _uiState.update {
            it.copy(
                activeBaseUrl = NetworkConfig.getBaseUrl(),
                pendingValue = info.url,
                overrideInfo = info,
                message = "已切换到 ${info.url}",
                error = null,
            )
        }
    }

    fun resetOverride() {
        DebugBackendEndpointStore.clearOverride()
        IntyNetworkManager.clearClientCache()

        val active = NetworkConfig.getBaseUrl()
        _uiState.update {
            it.copy(
                activeBaseUrl = active,
                pendingValue = active,
                overrideInfo = null,
                message = "已恢复到默认后端",
                error = null,
            )
        }
    }

    fun usePreset(url: String) {
        _uiState.update { it.copy(pendingValue = url, error = null, message = null) }
    }
}
